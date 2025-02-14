import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message
from urllib.parse import parse_qs


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # So'rov parametrlarini olish
        query_params = parse_qs(self.scope["query_string"].decode())
        self.receiver_id = query_params.get("receiver_id", [None])[0]

        if self.user.is_authenticated:
            if self.receiver_id:
                # receiver_id orqali chatni olish yoki yaratish
                self.chat = await database_sync_to_async(Chat.get_or_create_chat)(
                    self.user,
                    self.receiver_id
                )

                # Chatga o'z kanalini qo'shish
                self.room_group_name = f"chat_{self.chat.id}"
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )

                await self.accept()

                # Chat tarixini yuborish
                messages = await self.get_chat_history()
                await self.send(text_data=json.dumps({
                    "type": "chat_history",
                    "messages": messages
                }))

                # Foydalanuvchi chatga kirganda barcha o'qilmagan xabarlarni o'qilgan deb belgilash
                await self.mark_messages_as_read_and_update()

            else:
                # receiver_id bo'lmagan holat, ya'ni chatlar ro'yxatini yuborish
                self.room_group_name = f"user_{self.user.id}"
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()

                # Foydalanuvchiga tegishli chatlarni yuborish
                user_chats = await self.get_user_chats(self.user.id)
                await self.send(text_data=json.dumps({
                    "type": "chat_list",
                    "chats": user_chats
                }))
        else:
            await self.close()

    async def mark_messages_as_read_and_update(self):
        has_unread_messages = await self.mark_messages_as_read()
        if has_unread_messages:
            await self.update_user_chats()

    @database_sync_to_async
    def mark_messages_as_read(self):
        # Foydalanuvchi chatga kirganda, o'zi yozgan xabarlarni o'qilmagan deb belgilash
        unread_messages = Message.objects.filter(chat=self.chat, is_read=False).exclude(sender=self.user)
        has_unread_messages = unread_messages.exists()

        # Agar o‘qilmagan xabar bo‘lsa, ularni o‘qilgan deb belgilaymiz
        if has_unread_messages:
            unread_messages.update(is_read=True)

        return has_unread_messages

    @database_sync_to_async
    def get_chat_history(self):
        # Foydalanuvchilar o'rtasidagi barcha xabarlarni olish
        messages = Message.objects.filter(chat=self.chat).order_by("created_at")
        return [
            {
                "sender": message.sender.first_name,
                "message": message.content,
                "timestamp": message.created_at.isoformat(),
                "is_read": message.is_read,  # Xabarni o'qilganligini ko'rsatish
            }
            for message in messages
        ]

    @database_sync_to_async
    def get_user_chats(self, user_id):
        # User_id asosida chatlarni olish
        chats = Chat.objects.filter(user1_id=user_id) | Chat.objects.filter(user2_id=user_id)
        chats = chats.distinct()

        chat_list = []
        for chat in chats:
            last_message = chat.messages.last()
            unread_messages = chat.messages.filter(is_read=False).exclude(sender_id=user_id).count()

            # Jo'natuvchini to'g'ri aniqlash
            sender_user = chat.user1 if chat.user2.id == user_id else chat.user2

            chat_data = {
                "other_user": {  # Bu yerda "other_user" o'rniga "sender" desak ham bo'ladi
                    "id": sender_user.id,
                    "username": sender_user.first_name,
                },
                "last_message": last_message.content if last_message else "",
                "last_updated": timezone.localtime(last_message.created_at).isoformat() if last_message else "",
                "unread_messages": unread_messages,
            }

            chat_list.append(chat_data)

        chat_list.sort(key=lambda x: x["last_updated"], reverse=True)

        return chat_list

    async def receive(self, text_data):
        # Xabar ma'lumotlarini olish
        data = json.loads(text_data)
        message = data.get("message")
        timestamp = data.get("timestamp", timezone.localtime(timezone.now()))

        if self.user.is_authenticated and self.chat:
            # Xabarni bazaga saqlash
            message_obj = await database_sync_to_async(Message.objects.create)(
                chat=self.chat,
                sender=self.user,
                content=message,
                created_at=timestamp
            )

            # Barcha ishtirokchilarga xabarni yuborish
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message_obj.content,
                    "sender": self.user.first_name,
                    "timestamp": timestamp.isoformat(),
                }
            )

            # Yangi xabar yuborilganda chat ro'yxatini yangilash
            await self.update_user_chats()

            # Yangi xabar yuborilganda qabul qiluvchiga o'qilmagan deb belgilash
            await self.update_unread_status_for_receiver(message_obj)

    @database_sync_to_async
    def update_unread_status_for_receiver(self, message_obj):
        # Yangi xabar qabul qiluvchiga o'qilmagan deb belgilash
        if message_obj.sender != self.user:
            message_obj.is_read = False
            message_obj.save()

    async def update_user_chats(self):
        # Qabul qiluvchining barcha chatlarini olish
        receiver_chats = await self.get_user_chats(self.receiver_id)

        # Faqat qabul qiluvchiga chat ro'yxatini yuborish
        receiver_room_group_name = f"user_{self.receiver_id}"
        await self.channel_layer.group_send(
            receiver_room_group_name,
            {
                "type": "chat_list_update",
                "chats": receiver_chats
            }
        )

        sender_chats = await self.get_user_chats(self.user.id)

        sender_room_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_send(
            sender_room_group_name,
            {
                "type": "chat_list_update",
                "chats": sender_chats
            }
        )

    async def chat_message(self, event):
        # WebSocket orqali xabarni yuborish
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "sender": event["sender"],
            "timestamp": event["timestamp"],
        }))

    async def chat_list_update(self, event):
        # Foydalanuvchining chat ro'yxatini yangilash
        await self.send(text_data=json.dumps({
            "type": "chat_list",
            "chats": event["chats"]
        }))
