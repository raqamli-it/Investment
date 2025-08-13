from django.conf import settings
from django.db.models import Q
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message


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
        has_unread_messages, read_message_ids = await self.mark_messages_as_read()
        if has_unread_messages:
            # Chatlar ro'yxatini yangilash (hozirgi kod)
            await self.update_user_chats()
            # O'qilgan xabarlar uchun event yuborish (yangi kod)
            await self.notify_sender_about_read(read_message_ids)  # me

    @database_sync_to_async
    def mark_messages_as_read(self):
        unread_messages = Message.objects.filter(
            chat=self.chat,
            is_read=False
        ).exclude(sender=self.user)

        has_unread_messages = unread_messages.exists()  # me
        read_ids = list(unread_messages.values_list("id", flat=True))  # me

        if has_unread_messages:
            unread_messages.update(is_read=True)

        return has_unread_messages, read_ids  # read_ids ni ham qoshdim!!!!

    async def messages_read(self, event):  # me
        await self.send(text_data=json.dumps({
            "type": "messages_read",
            "chat_id": event["chat_id"],
            "message_ids": event["message_ids"]
        }))

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
        site_url = getattr(settings, "SITE_URL", "")  # BASE_URL ni olish (agar mavjud bo‘lsa)
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

        # Chat oynasiga kirganda, o'qilmagan xabarlarni o'qilgan deb belgilash
        read = data.get("read")
        if read and hasattr(self, "chat"):
            has_unread_messages, read_message_ids = await self.mark_messages_as_read()  # me
            if has_unread_messages:
                await self.update_user_chats()
                await self.notify_sender_about_read(read_message_ids)  # me
            return

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
                    "is_read": message_obj.is_read,

                }
            )

            # Yangi xabar yuborilganda chat ro'yxatini yangilash
            await self.update_user_chats()

            # Yangi xabar yuborilganda qabul qiluvchiga o'qilmagan deb belgilash
            await self.update_unread_status_for_receiver(message_obj)

    async def notify_sender_about_read(self, read_message_ids):
        """
        Qarshi foydalanuvchiga xabarlar o'qilganini real-time yuboradi.
        """
        other_user_id = self.chat.user1.id if self.chat.user2.id == self.user.id else self.chat.user2.id
        other_user_room = f"user_{other_user_id}"

        # Senderga "messages_read" event yuborish
        await self.channel_layer.group_send(
            other_user_room,
            {
                "type": "messages_read",
                "message_ids": read_message_ids,
                "chat_id": self.chat.id
            }
        )

        # Oxirgi o‘qilgan xabarlarni "chat_message" qilib yangilab yuborish
        for msg_id in read_message_ids:
            message = await database_sync_to_async(
                lambda: Message.objects.select_related("sender").get(id=msg_id)
            )()
            await self.channel_layer.group_send(
                f"chat_{self.chat.id}",
                {
                    "type": "chat_message",
                    "message": message.content,
                    "sender": message.sender.id,
                    "timestamp": message.created_at.isoformat(),
                    "is_read": True
                }
            )

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
            "is_read": event.get("is_read", False)
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

        # Shaxsiy chatlarni olish
        chats = Chat.objects.filter(
            (Q(user1_id=user_id) | Q(user2_id=user_id)) & Q(
                Q(user1__first_name__icontains=search_query) |
                Q(user2__first_name__icontains=search_query)
            )
        ).distinct().prefetch_related("messages")

        # Guruh chatlarini olish
        groups = GroupChat.objects.filter(
            members__id=user_id, name__icontains=search_query
        ).prefetch_related("messages")

        site_url = getattr(settings, "SITE_URL", "")  # BASE_URL
        chat_list = []

        # Shaxsiy chatlar
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

        # Guruh chatlar
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

        # Chatlarni oxirgi xabar bo‘yicha saralash
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
        """Websocketga ulanish"""
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        # Har bir ulanayotgan foydalanuvchi uchun private kanal
        await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)

        query_params = parse_qs(self.scope["query_string"].decode())
        self.group_id = query_params.get("group_id", [None])[0]

        # Guruhlar ro'yxatini olish (agar kerak bo'lsa clientga jo'natish uchun)
        self.groups = await self.get_user_groups(self.user)

        if self.group_id:
            await self.add_user_to_group()
        await self.accept()

        if not self.group_id:
            # global group list updater
            await self.channel_layer.group_add("global_group_updates", self.channel_name)
            await self.send(json.dumps({"type": "group_list", "groups": self.groups}))
            return

        if self.group_id:
            # agar group_id bor bo'lsa: guruh kanaliga qo'shish va tarix yuborish
            self.room_group_name = f"group_{self.group_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            messages, members = await self.get_chat_history()
            await self.send(json.dumps({"type": "chat_history", "messages": messages}))

            # global group listni yangilash (agar kerak bo'lsa)
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
        """Foydalanuvchuni guruh azolariga qoshish"""
        group = GroupChat.objects.get(id=self.group_id)
        if not group.members.filter(id=self.user.id).exists():
            group.members.add(self.user)

    async def receive(self, text_data):
        """Yangi xabar yoki boshqa hodisalarni qabul qilish"""
        data = json.loads(text_data)

        # Search
        search_query = data.get("search", "").strip()
        if search_query:
            groups = await self.search_user_groups(self.user, search_query)
            await self.send(json.dumps({"type": "search_results", "results": groups}))
            return

        # Agar client "read": true yuborsa -> belgilash va yuborish logikasi
        if data.get("read") and self.group_id:
            read_ids = await self.mark_messages_as_read()
            if not read_ids:
                return

            for msg_id in read_ids:
                message = await database_sync_to_async(
                    lambda: GroupMessage.objects.select_related("sender").get(id=msg_id)
                )()

                members_count = await database_sync_to_async(
                    lambda: GroupChat.objects.get(id=self.group_id).members.count()
                )()
                read_count = await database_sync_to_async(
                    lambda: GroupMessageRead.objects.filter(message=message, is_read=True).count()
                )()

                # Agar barcha boshqa a'zolar o'qib bo'lgan bo'lsa -> bazada hamma uchun True
                if members_count <= 1 or read_count >= (members_count - 1):
                    await database_sync_to_async(
                        lambda: GroupMessageRead.objects.filter(message=message).update(is_read=True)
                    )()

                # Faqat yuboruvchiga xabarni o‘qilganini yuborish
                if message.sender_id != self.user.id:
                    await self.channel_layer.group_send(
                        f"user_{message.sender_id}",
                        {
                            "type": "chat_read",
                            "message_id": message.id,
                            "reader_id": self.user.id,
                            "is_read": True  # qo‘shildi
                        }
                    )
            return

        # Xabar yuborish (old behavior)
        message_text = data.get("message")
        if self.user.is_authenticated and self.group_id and message_text:
            site_url = getattr(settings, "SITE_URL", "")
            media_url = getattr(settings, "MEDIA_URL", "/media/")
            timestamp = timezone.localtime(timezone.now())

            # Xabarni bazaga yozish
            message_obj = await database_sync_to_async(GroupMessage.objects.create)(
                group_id=self.group_id,
                sender=self.user,
                content=message_text,
                created_at=timestamp
            )

            members = await database_sync_to_async(
                lambda: list(GroupChat.objects.get(id=self.group_id).members.all())
            )()

            unread_users = []
            for member in members:
                if member != self.user:
                    await database_sync_to_async(GroupMessageRead.objects.create)(
                        message=message_obj, user=member, is_read=False
                    )
                    unread_users.append(member.id)

            # Guruhlar ro'yxatini yangilash (global updater)
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

            #Guruhga xabarni yuborish (initial: is_read = False)
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
                    "is_read": False,
                }
            )

    async def chat_read(self, event):
        await self.send(json.dumps({
            "type": "chat_read",
            "message_id": event["message_id"],
            "reader_id": event["reader_id"],
            "is_read": event.get("is_read", True)  # default True
        }))

    async def chat_message(self, event):
        # Yangi xabar yuborish (har ikkala case uchun ishlaydi)
        await self.send(json.dumps({
            "type": "chat_message",
            "message_id": event.get("message_id"),
            "message": event.get("message"),
            "sender": event.get("sender"),
            "sender_name": event.get("sender_name"),
            "sender_photo": event.get("sender_photo"),
            "timestamp": event.get("timestamp"),
            "is_read": event.get("is_read", False)
        }))

    async def group_list_update(self, event):
        """Barcha foydalanuvchilarga guruhlar royxatini yangilash"""
        if event.get("user_id") == self.user.id:
            if self.group_id:
                return
            await self.send(json.dumps({
                "type": "group_list",
                "groups": event["groups"]
            }))

    @database_sync_to_async
    def get_user_groups(self, user):
        site_url = getattr(settings, "SITE_URL", "")
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        groups = GroupChat.objects.filter(members=user).prefetch_related("messages")
        return [
            {
                "id": group.id,
                "image": f"{site_url}{media_url}{group.image}" if group.image else None,
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
        media_url = getattr(settings, "MEDIA_URL", "/media/")

        messages = GroupMessage.objects.filter(
            group_id=self.group_id
        ).order_by("created_at").select_related("sender")

        members = list(GroupChat.objects.get(id=self.group_id).members.all())

        result = []
        for message in messages:
            # Agar sender o'zi bo'lsa -> o'qilganlar bo'yicha hisoblash
            if message.sender_id == self.user.id:
                # Agar barcha boshqa a'zolar o'qigan bo'lsa -> True
                members_count = len(members)
                read_count = GroupMessageRead.objects.filter(
                    message=message, is_read=True
                ).count()
                is_read = read_count >= (members_count - 1)
            else:
                # O'qigan foydalanuvchiga qarab
                is_read = GroupMessageRead.objects.filter(
                    message=message, user=self.user, is_read=True
                ).exists()

            result.append({
                "id": message.id,
                "sender": message.sender.id,
                "sender_name": message.sender.first_name,
                "message": message.content,
                "sender_photo": f"{site_url}{media_url}{message.sender.photo}" if message.sender.photo else None,
                "timestamp": message.created_at.isoformat(),
                "is_read": is_read
            })

        return result, members

    @database_sync_to_async
    def mark_messages_as_read(self):
        unread_qs = GroupMessageRead.objects.filter(message__group_id=self.group_id, user=self.user, is_read=False)
        read_ids = list(unread_qs.values_list("message_id", flat=True))
        unread_qs.update(is_read=True)
        return read_ids

    async def group_messages_read(self, event):
        await self.send(json.dumps({
            "type": "group_messages_read",
            "group_id": event["group_id"],
            "message_ids": event["message_ids"],
            "reader_id": event["reader_id"]
        }))

    async def disconnect(self, close_code):
        """ Foydalanuvchi chiqqanda WebSocket kanalidan chiqarish"""
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_discard("global_group_updates", self.channel_name)
        await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name) # me

    @database_sync_to_async
    def search_user_groups(self, user, search_query):
        site_url = getattr(settings, "SITE_URL", "")
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        groups = GroupChat.objects.filter(members=user, name__icontains=search_query).prefetch_related("messages")
        result = []
        for group in groups:
            last = group.messages.last()
            result.append({
                "type": "group",
                "id": group.id,
                "image": f"{site_url}{media_url}{group.image}" if group.image else None,
                "name": group.name,
                "last_message": last.content if last else "",
                "last_updated": last.created_at.isoformat() if last else "",
                "unread_count": GroupMessageRead.objects.filter(message__group=group, user=user, is_read=False).exclude(message__sender=user).count()
            })
        return result
