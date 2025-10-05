import logging
from asyncio.log import logger

from django.conf import settings
from django.db.models import Q
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message
from .utils import to_user_timezone
from django.contrib.auth import get_user_model
from .utils import set_user_online, set_user_offline
from collections import defaultdict

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # So'rov parametrlarini olish
        query_params = parse_qs(self.scope["query_string"].decode())
        self.receiver_id = query_params.get("receiver_id", [None])[0]
        receiver = None
        if self.receiver_id:
            receiver = await database_sync_to_async(User.objects.get)(id=self.receiver_id)

        if self.user.is_authenticated:

            await self.channel_layer.group_add(
                f"user_{self.user.id}",
                self.channel_name
            )

            await set_user_online(self.user) # user ni online deb belgilash uchun
            # 🔹 Barcha userlarga shu user onlayn bo‘ldi deb xabar berish
            if self.receiver_id:
                # o‘zini receiverga yuborish
                await self.channel_layer.group_send(
                    f"user_{self.receiver_id}",
                    {
                        "type": "user_status_update",
                        "user_id": self.user.id,
                        "is_online": True,
                        "last_seen": None
                    }
                )

                # 🔹 O‘ziga ham receiverning statusini yuborish
                await self.channel_layer.group_send(
                    f"user_{self.user.id}",
                    {
                        "type": "user_status_update",
                        "user_id": int(self.receiver_id),
                        "is_online": receiver.is_online,
                        "last_seen": to_user_timezone(receiver.last_seen, "Asia/Tashkent").strftime(
                            "%Y-%m-%d %H:%M:%S") if receiver.last_seen else None
                        if receiver.last_seen else None
                    }
                )

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

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await set_user_offline(self.user)  #  userni oxirgi martta qachon online bolganini olish

            # boshqa userlarga xabar berish
            await self.channel_layer.group_send(
                f"user_{self.receiver_id}",
                {
                    "type": "user_status_update",
                    "user_id": self.user.id,
                    "is_online": False,
                    "last_seen": to_user_timezone(timezone.now(), "Asia/Tashkent").strftime("%Y-%m-%d %H:%M:%S")
                }
            )

    async def user_status_update(self, event):
        """
        Boshqa userning statusi (online/offline) haqida xabar olish
        """
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "user_id": event["user_id"],
            "is_online": event["is_online"],
            "last_seen": event["last_seen"],
        }))

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
                    "timestamp": to_user_timezone(message.created_at).isoformat(), # timmeeeeeeee
                    "is_read": message.is_read,  # Xabar o‘qilganligini ko‘rsatish
                    "parent_id": message.parent.id if message.parent else None,
                }
                for message in messages
            ]
        }

    @database_sync_to_async
    def get_user_chats(self, user_id):
        # User_id asosida chatlarni olish
        chats = Chat.objects.filter(Q(user1_id=user_id) | Q(user2_id=user_id)).distinct()

        site_url = getattr(settings, "SITE_URL", "")  # BASE_URL

        chat_list = []
        for chat in chats:
            last_message = chat.messages.last()
            unread_messages = chat.messages.filter(is_read=False).exclude(sender_id=user_id).count()

            # Qarama-qarshi userni aniqlash
            other_user = chat.user1 if chat.user2.id == user_id else chat.user2

            grouped_messages = defaultdict(list)
            for message in chat.messages.all().order_by("created_at"):
                local_time = to_user_timezone(message.created_at, "Asia/Tashkent")
                date_str = local_time.strftime("%Y-%m-%d")  # Sana
                time_str = local_time.strftime("%H:%M:%S")  # Faqat vaqt

                grouped_messages[date_str].append({
                    "sender": message.sender.id,
                    "message": message.content,
                    "timestamp": time_str,
                    "is_read": message.is_read,
                    "parent_id": message.parent.id if message.parent else None,

                })

            messages_by_date = [
                {"date": date, "messages": msgs}
                for date, msgs in sorted(grouped_messages.items())
            ]

            chat_data = {
                "other_user": {
                    "id": other_user.id,
                    "photo": f"{site_url}{other_user.photo.url}" if other_user.photo else None,
                    "username": other_user.first_name,
                },
                "last_message": last_message.content if last_message else "",
                "last_updated": to_user_timezone(last_message.created_at,
                                                 "Asia/Tashkent").isoformat() if last_message else "",
                "unread_messages": unread_messages,
                "messages_by_date": messages_by_date,
            }

            chat_list.append(chat_data)

        # Chatlarni oxirgi xabarga qarab saralash
        chat_list.sort(key=lambda x: x["last_updated"], reverse=True)

        return chat_list

    async def receive(self, text_data):
        # Xabar ma'lumotlarini olish
        data = json.loads(text_data)
        action = data.get("action")

        if not action:
            return

        # 🔹 Xabar yuborish (yangi / reply)
        if action == "send_message":
            await self.handle_send_message(data)

        # 🔹 Edit qilish
        elif action == "edit_message":
            await self.handle_edit_message(data)

        # Delete qilish (list ni ham delete qilish mumkin va 1 ta message ni ham)
        elif action == "delete_messages":
            await self.handle_delete_messages(data)


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


    async def handle_send_message(self, data):
        if not (self.user.is_authenticated and hasattr(self, "chat")):
            return

        message_text = data.get("message")
        parent_id = data.get("parent_id")

        created_at_utc = timezone.now()

        msg = await database_sync_to_async(Message.objects.create)(
            chat=self.chat,
            sender=self.user,
            content=message_text,
            parent_id=parent_id if parent_id else None,
            created_at=created_at_utc
        )

        message_dict = {
            "id": msg.id,
            "message": msg.content,
            "sender": self.user.id,
            "timestamp": to_user_timezone(msg.created_at).isoformat(),
            "is_read": msg.is_read,
            "parent_id": parent_id,
        }
        # logger.info(f"GROUP_SEND PAYLOAD: {json.dumps(message_dict)}")


        # xabarni group_send orqali yuborish
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_dict
            }
        )

        # 🔹 Chat list va unread update qilish
        await self.update_user_chats()
        await self.update_unread_status_for_receiver(msg)

    async def handle_edit_message(self, data):   # Message  Edit qilish
        msg_id = data.get("id")
        new_text = data.get("text")

        msg = await database_sync_to_async(lambda: Message.objects.select_related("sender").get(id=msg_id))()

        if msg.sender == self.user and not msg.is_deleted:
            msg.content = new_text
            msg.edited_at = timezone.now()
            await database_sync_to_async(msg.save)()

            response = {
                "action": "edit_message",
                "id": msg.id,
                "new_text": msg.content,
                "edited_at": str(msg.edited_at)
            }

            await self.channel_layer.group_send(self.room_group_name, {
                "type": "chat_message",
                "message": response
            })

    async def handle_delete_messages(self, data):
        ids = data.get("ids")
        msg_id = data.get("id")

        # 1️⃣ Agar ids bitta son bo‘lsa, uni listga o‘gir
        if isinstance(ids, int):
            ids = [ids]

        # 2️⃣ Agar ids string bo‘lsa, uni vergul bo‘yicha bo‘lib, int ga o‘giramiz
        elif isinstance(ids, str):
            ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]

        # 3️⃣ Agar ids yo‘q bo‘lsa, msg_id ni tekshiramiz
        elif not ids and msg_id:
            ids = [msg_id]

        # 4️⃣ Agar umuman yo‘q bo‘lsa chiqamiz
        if not ids:
            await self.send(text_data=json.dumps({
                "error": "No valid message IDs provided"
            }))
            return

        # ✅ Faqat o‘zining yozgan va o‘chirilmagan xabarlarini olish
        msgs = await database_sync_to_async(list)(
            Message.objects.filter(id__in=ids, sender=self.user, is_deleted=False)
        )

        if not msgs:
            await self.send(text_data=json.dumps({
                "error": "No messages found or you don't have permission"
            }))
            return

        deleted_ids = []
        for msg in msgs:
            msg.is_deleted = True
            msg.content = "This message was deleted"
            await database_sync_to_async(msg.save)()
            deleted_ids.append(msg.id)

        response = {
            "action": "delete_messages",
            "ids": deleted_ids
        }

        await self.channel_layer.group_send(self.room_group_name, {
            "type": "chat_message",
            "message": response
        })

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
                    "timestamp": to_user_timezone(message.created_at).isoformat(), # timeeee
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
        await self.channel_layer    .group_send(
            sender_room_group_name,
            {
                "type": "chat_list_update",
                "chats": sender_chats
            }
        )

    async def chat_message(self, event):
        raw_data = event["message"]

        if isinstance(raw_data, str) and raw_data.strip():  # bo'sh emasligini tekshiramiz
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                # Xato bo'lsa log qilamiz va chiqamiz
                # logger.warning(f"Invalid JSON data received: {raw_data}")
                return
        elif isinstance(raw_data, dict):
            data = raw_data
        else:
                # # raw_data bo'sh yoki noto'g'ri formatda bo'lsa, chiqamiz
                # logger.warning(f"Empty or invalid data received: {raw_data}")
            return

        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "id": data.get("id"),
            "message": data.get("message") or data.get("new_text"),
            "sender": data.get("sender"),
            "timestamp": data.get("timestamp"),
            "is_read": data.get("is_read", False),
            "parent_id": data.get("parent_id")
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
            return []  #  Agar qidiruv so‘rovi bo‘lmasa, bo‘sh ro‘yxat qaytariladi.

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
                "last_updated": to_user_timezone(last_message.created_at).isoformat() if last_message else "",# timeee
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
                "last_updated": to_user_timezone(last_message.created_at).isoformat() if last_message else "",# timeee
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
        group_id_str = query_params.get("group_id", [None])[0]

        try:
            self.group_id = int(group_id_str) if group_id_str else None
        except ValueError:
            self.group_id = None

        # Guruhlar ro'yxatini olish
        self.groups = await self.get_user_groups(self.user)

        if self.group_id:
            await self.add_user_to_group()

        await self.accept()

        if not self.group_id:
            # global group list updater
            await self.channel_layer.group_add("global_group_updates", self.channel_name)
            await self.send(json.dumps({"type": "group_list", "groups": self.groups}))
            return

        # agar group_id bor bo'lsa: guruh kanaliga qo'shish va tarix yuborish
        self.room_group_name = f"group_{self.group_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        history = await self.get_chat_history()
        await self.send(json.dumps({"type": "chat_history", **history}))

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
            timestamp = timezone.now()
            # timestamp = timezone.localtime(timezone.now())

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
                    "timestamp": to_user_timezone(message_obj.created_at).isoformat(),
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
                "last_updated": (
                    to_user_timezone(group.messages.last().created_at).isoformat()
                    if group.messages.exists() else ""
                ),
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

        group = GroupChat.objects.filter(id=self.group_id).prefetch_related("members").first()
        if not group:
            return {"messages_by_date": [], "members": []}

        # O‘qilganlar jadvali oldindan olish
        reads = GroupMessageRead.objects.filter(
            message__group_id=self.group_id, is_read=True
        ).exclude(user_id__in=messages.values("sender_id"))
        reads_map = {r.message_id: True for r in reads}

        grouped_messages = defaultdict(list)
        for message in messages:
            local_time = to_user_timezone(message.created_at, "Asia/Tashkent")
            date_str = local_time.strftime("%Y-%m-%d")
            time_str = local_time.strftime("%H:%M:%S")

            grouped_messages[date_str].append({
                "id": message.id,
                "sender": message.sender.id,
                "sender_name": message.sender.first_name,
                "message": message.content,
                "sender_photo": f"{site_url}{media_url}{message.sender.photo}" if message.sender.photo else None,
                "timestamp": time_str,
                "is_read": reads_map.get(message.id, False)
            })

        messages_by_date = [
            {"date": date, "messages": msgs}
            for date, msgs in sorted(grouped_messages.items())
        ]

        members_data = [
            {
                "id": member.id,
                "username": member.username,
                "photo": f"{site_url}{media_url}{member.photo}" if member.photo else None,
                "first_name": member.first_name,
                "last_name": member.last_name,
            }
            for member in group.members.all()
        ]

        return {
            "messages_by_date": messages_by_date,
            "members": members_data
        }

        # @database_sync_to_async
    # def get_chat_history(self):
    #     site_url = getattr(settings, "SITE_URL", "")
    #     media_url = getattr(settings, "MEDIA_URL", "/media/")
    #
    #     messages = GroupMessage.objects.filter(
    #         group_id=self.group_id
    #     ).order_by("created_at").select_related("sender")
    #
    #     members = list(GroupChat.objects.get(id=self.group_id).members.all())
    #
    #     result = []
    #     for message in messages:
    #         # Agar sender o'zi bo'lsa -> o'qilganlar bo'yicha hisoblash
    #         if message.sender_id == self.user.id:
    #             # Agar barcha boshqa a'zolar o'qigan bo'lsa -> True
    #             members_count = len(members)
    #             read_count = GroupMessageRead.objects.filter(
    #                 message=message, is_read=True
    #             ).count()
    #             is_read = read_count >= (members_count - 1)
    #         else:
    #             # O'qigan foydalanuvchiga qarab
    #             is_read = GroupMessageRead.objects.filter(
    #                 message=message, user=self.user, is_read=True
    #             ).exists()
    #
    #         result.append({
    #             "id": message.id,
    #             "sender": message.sender.id,
    #             "sender_name": message.sender.first_name,
    #             "message": message.content,
    #             "sender_photo": f"{site_url}{media_url}{message.sender.photo}" if message.sender.photo else None,
    #             "timestamp": to_user_timezone(message.created_at).isoformat(),
    #             "is_read": is_read
    #         })

        # return result, members

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
                "last_updated": to_user_timezone(last.created_at).isoformat() if last else "",
                "unread_count": GroupMessageRead.objects.filter(message__group=group, user=user, is_read=False).exclude(message__sender=user).count()
            })
        return result