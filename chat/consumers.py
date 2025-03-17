import json

from django.conf import settings
from django.db.models import Q
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
        # Chatdagi boshqa foydalanuvchini aniqlash
        other_user = self.chat.user1 if self.chat.user2.id == self.user.id else self.chat.user2

        site_url = getattr(settings, "SITE_URL", "")  # Saytning bazaviy URL manzili

        return {
            "other_user": {
                "id": other_user.id,
                "photo": f"{site_url}{other_user.photo.url}" if other_user.photo else None,
                "username": other_user.first_name,
            },
            "messages": [
                {
                    "sender": message.sender.id,
                    "message": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "is_read": message.is_read,  # Xabar o‘qilganligini ko‘rsatish
                }
                for message in messages
            ]
        }

    @database_sync_to_async
    def get_user_chats(self, user_id):
        # User_id asosida chatlarni olish
        chats = Chat.objects.filter(user1_id=user_id) | Chat.objects.filter(user2_id=user_id)
        chats = chats.distinct()
        site_url = getattr(settings, "SITE_URL", "")  # ✅ BASE_URL ni olish (agar mavjud bo‘lsa)
        # media_url = getattr(settings, "MEDIA_URL", "/media/")  # MEDIA URL-ni olish

        chat_list = []
        for chat in chats:
            last_message = chat.messages.last()
            unread_messages = chat.messages.filter(is_read=False).exclude(sender_id=user_id).count()

            # Jo'natuvchini to'g'ri aniqlash
            sender_user = chat.user1 if chat.user2.id == user_id else chat.user2

            chat_data = {
                "other_user": {  # Bu yerda "other_user" o'rniga "sender" desak ham bo'ladi
                    "id": sender_user.id,
                    "photo": f"{site_url}{sender_user.photo.url}" if sender_user.photo else None,
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

        search_query = data.get("search", "").strip()

        if search_query:
            search_results = await self.search_chats_and_groups(self.user.id, search_query)
            await self.send(text_data=json.dumps({
                "type": "search_results",
                "results": search_results
            }))
            return
        message = data.get("message")
        timestamp = data.get("timestamp", timezone.localtime(timezone.now()))

        if self.user.is_authenticated and hasattr(self, "chat"):
            # Xabarni bazaga saqlash
            message_obj = await database_sync_to_async(Message.objects.create)(
                chat=self.chat,
                sender=self.user,
                content=message,
                created_at=timestamp,
                # is_read = False
            )

            # Barcha ishtirokchilarga xabarni yuborish
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message_obj.content,
                    "sender": self.user.id,
                    "timestamp": timestamp.isoformat(),
                    # "is_read": message_obj.is_read,

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
            # "is_read": event.get("is_read", False)
        }))

    async def chat_list_update(self, event):
        # Foydalanuvchining chat ro'yxatini yangilash
        await self.send(text_data=json.dumps({
            "type": "chat_list",
            "chats": event["chats"]
        }))

    @database_sync_to_async
    def search_chats_and_groups(self, user_id, search_query=""):
        """Foydalanuvchining shaxsiy chatlari va guruhlarini qidirish"""
        if not search_query.strip():
            return []  # ⚠️ Agar qidiruv so‘rovi bo‘lmasa, bo‘sh ro‘yxat qaytariladi.

        # ✅ Shaxsiy chatlarni olish
        chats = Chat.objects.filter(
            (Q(user1_id=user_id) | Q(user2_id=user_id)) & Q(
                Q(user1__first_name__icontains=search_query) |
                Q(user2__first_name__icontains=search_query)
            )
        ).distinct().prefetch_related("messages")

        # ✅ Guruh chatlarini olish
        groups = GroupChat.objects.filter(
            members__id=user_id, name__icontains=search_query
        ).prefetch_related("messages")

        site_url = getattr(settings, "SITE_URL", "")  # ✅ BASE_URL
        chat_list = []

        # ✅ Shaxsiy chatlar
        for chat in chats:
            last_message = chat.messages.last()
            unread_messages = chat.messages.filter(is_read=False).exclude(sender_id=user_id).count()

            other_user = chat.user1 if chat.user2.id == user_id else chat.user2

            chat_list.append({
                "type": "private",
                "other_user": {
                    "id": other_user.id,
                    "photo": f"{site_url}{other_user.photo.url}" if other_user.photo else None,
                    "username": other_user.first_name,
                },
                "last_message": last_message.content if last_message else "",
                "last_updated": timezone.localtime(last_message.created_at).isoformat() if last_message else "",
                "unread_messages": unread_messages,
            })

        # ✅ Guruh chatlar
        for group in groups:
            last_message = group.messages.last()
            unread_count = GroupMessageRead.objects.filter(
                message__group=group, user_id=user_id, is_read=False
            ).exclude(message__sender_id=user_id).count()

            chat_list.append({
                "type": "group",
                "id": group.id,
                "image": f"{site_url}{group.image.url}" if group.image else None,
                "name": group.name,
                "last_message": last_message.content if last_message else "",
                "last_updated": timezone.localtime(last_message.created_at).isoformat() if last_message else "",
                "unread_count": unread_count,
            })

        # 🏆 Chatlarni oxirgi xabar bo‘yicha saralash
        chat_list.sort(key=lambda x: x.get("last_updated", ""), reverse=True)

        return chat_list


import json
from urllib.parse import parse_qs
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from chat.models import GroupChat, GroupMessage, GroupMessageRead


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """WebSocketga ulanish"""
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        query_params = parse_qs(self.scope["query_string"].decode())
        self.group_id = query_params.get("group_id", [None])[0]

        self.groups = await self.get_user_groups(self.user)
        if self.group_id:
            await self.add_user_to_group()
        await self.accept()

        if not self.group_id:
            await self.channel_layer.group_add("global_group_updates", self.channel_name)
            await self.send(json.dumps({"type": "group_list", "groups": self.groups}))

        if self.group_id:
            self.room_group_name = f"group_{self.group_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            messages, members = await self.get_chat_history()
            await self.send(json.dumps({"type": "chat_history", "messages": messages}))

            for member in members:
                updated_groups = await self.get_user_groups(member)
                await self.channel_layer.group_send(
                    "global_group_updates",
                    {
                        "type": "group_list_update",
                        "groups": updated_groups,
                        "user_id": member.id
                    }
                )

    @database_sync_to_async
    def add_user_to_group(self):
        """Foydalanuvchini guruh a'zolariga qo‘shish"""
        group = GroupChat.objects.get(id=self.group_id)
        if not group.members.filter(id=self.user.id).exists():
            group.members.add(self.user)

    async def receive(self, text_data):
        """Yangi xabar qabul qilish"""
        data = json.loads(text_data)
        message = data.get("message")
        read = data.get("read")

        if read and self.group_id:
            await self.mark_messages_as_read()
            return

        if self.user.is_authenticated and self.group_id and message:
            site_url = getattr(settings, "SITE_URL", "")  # ✅ BASE_URL ni olish (agar mavjud bo‘lsa)
            media_url = getattr(settings, "MEDIA_URL", "/media/")  # MEDIA URL-ni olish
            timestamp = timezone.localtime(timezone.now())

            message_obj = await database_sync_to_async(GroupMessage.objects.create)(
                group_id=self.group_id,
                sender=self.user,
                content=message,
                created_at=timestamp
            )

            members = await database_sync_to_async(
                lambda: list(GroupChat.objects.get(id=self.group_id).members.all()))()

            unread_users = []
            for member in members:
                if member != self.user:
                    await database_sync_to_async(GroupMessageRead.objects.create)(
                        message=message_obj, user=member, is_read=False
                    )
                    unread_users.append(member.id)

            for member in members:
                updated_groups = await self.get_user_groups(member)
                await self.channel_layer.group_send(
                    "global_group_updates",
                    {
                        "type": "group_list_update",
                        "groups": updated_groups,
                        "user_id": member.id
                    }
                )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_id": message_obj.id,
                    "message": message_obj.content,
                    "sender": self.user.id,
                    "sender_name": self.user.first_name,
                    "sender_photo": f"{site_url}{media_url}{self.user.photo}" if self.user.photo else None,
                    "timestamp": timestamp.isoformat(),
                }
            )

    async def chat_message(self, event):
        """Yangi xabarni yuborish"""
        await self.send(json.dumps({
            "type": "chat_message",
            "message_id": event["message_id"],
            "message": event["message"],
            "sender": event["sender"],
            "sender_name": event["sender_name"],
            "sender_photo": event["sender_photo"],
            "timestamp": event["timestamp"],
        }))

    async def group_list_update(self, event):
        """Barcha foydalanuvchilarga guruhlar ro‘yxatini yangilash"""
        if event.get("user_id") == self.user.id:
            if self.group_id:
                return
            await self.send(json.dumps({
                "type": "group_list",
                "groups": event["groups"]
            }))

    @database_sync_to_async
    def get_user_groups(self, user):
        site_url = getattr(settings, "SITE_URL", "")  # ✅ BASE_URL ni olish (agar mavjud bo‘lsa)
        media_url = getattr(settings, "MEDIA_URL", "/media/")  # MEDIA URL-ni olish
        """Foydalanuvchi obuna bo‘lgan barcha guruhlarni olish"""
        groups = GroupChat.objects.filter(members=user).prefetch_related("messages")
        return [
            {
                "id": group.id,
                "image": f"{site_url}{media_url}{group.image}" if group.image else None,  # ✅ To‘liq URL
                "name": group.name,
                "last_message": (group.messages.last().content if group.messages.exists() else ""),
                "last_updated": group.messages.last().created_at.isoformat() if group.messages.exists() else "",
                "unread_count": GroupMessageRead.objects.filter(
                    message__group=group, user=user, is_read=False
                ).exclude(message__sender=user).count()
            }
            for group in groups
        ]

    @database_sync_to_async
    def get_chat_history(self):
        site_url = getattr(settings, "SITE_URL", "")
        media_url = getattr(settings, "MEDIA_URL", "/media/")  # MEDIA URL-ni olish

        """Guruh tarixini olish va oxirgi xabarni o‘qilgan deb belgilash"""
        messages = GroupMessage.objects.filter(group_id=self.group_id).order_by("created_at").select_related("sender")
        members = list(GroupChat.objects.get(id=self.group_id).members.all())
        return [
            {
                "id": message.id,
                "sender": message.sender.id,
                "sender_name": message.sender.first_name,
                "message": message.content,
                # "sender_photo": message.sender.photo.url,
                "sender_photo": f"{site_url}{media_url}{message.sender.photo}" if message.sender.photo else None,
                "timestamp": message.created_at.isoformat(),
            }
            for message in messages
        ], members

    @database_sync_to_async
    def mark_messages_as_read(self):
        """Barcha o‘qilmagan xabarlarni o‘qilgan deb belgilash"""
        GroupMessageRead.objects.filter(
            message__group_id=self.group_id, user=self.user, is_read=False
        ).update(is_read=True)

    async def disconnect(self, close_code):
        """Foydalanuvchi chiqqanda WebSocket kanalidan chiqarish"""
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_discard("global_group_updates", self.channel_name)
