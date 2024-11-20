import json
import datetime
from django.utils.timezone import now, localtime
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Chat, Message
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
import urllib.parse

User = get_user_model()

import redis

# Redisga bevosita ulanishni o'rnatish
redis_client = redis.StrictRedis.from_url("redis://redis:6379/0", decode_responses=True)



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # URL query string'dan receiver_id ni olish
        query_string = self.scope["query_string"].decode()
        params = urllib.parse.parse_qs(query_string)
        self.receiver_id = params.get('receiver_id', [None])[0]

        if not self.receiver_id:
            await self.close()
            return

        # Receiverni ID orqali olish
        self.receiver = await self.get_user_by_id(self.receiver_id)
        if not self.receiver:
            await self.close()
            return

        # Ikkita foydalanuvchi o'rtasida chatni olish yoki yaratish
        self.chat = await self.get_or_create_chat(self.user, self.receiver)

        # Chat guruhiga qo'shish
        self.room_group_name = f"chat_{self.chat.id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # WebSocket ulanishini qabul qilish
        await self.accept()

        # Foydalanuvchining online holatini o'zgartirish
        await self.set_user_online_status(True)

        # Barcha o'qilmagan xabarlarni o'qilgan deb belgilash
        await self.mark_all_unread_messages_as_read()

        # Redisga foydalanuvchi qo'shish
        await self.add_user_to_chat(self.user)

        # Chatdagi foydalanuvchilar sonini olish
        participants_count = await self.get_chat_participants_count()

        # Foydalanuvchilar sonini guruhga yuborish
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_participants_count',
                'count': participants_count
            }
        )

    async def disconnect(self, close_code):
        """Foydalanuvchi chatdan chiqqanda online holatini yangilash"""
        # Foydalanuvchini offline deb belgilash
        await self.set_user_online_status(False)
        await self.remove_user_from_chat(self.user)

        # Chatdan chiqish
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        participants_count = await self.get_chat_participants_count()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_participants_count',
                'count': participants_count
            }
        )

    async def receive(self, text_data):
        # Xabarni olish
        text_data_json = json.loads(text_data)
        message_content = text_data_json["message"]

        # Xabar yuborilgan vaqtni generatsiya qilish
        sent_at = localtime(now())

        # Xabarni bazaga saqlash
        message = await self.save_message(self.chat, self.user, message_content, sent_at)

        # Xabarni guruhdagi barcha ulanishlarga yuborish
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': self.format_message(message, sent_at)  # format_message funksiyasi bu yerda ishlatiladi
            }
        )

    async def chat_message(self, event):
        # Xabarni WebSocket orqali yuborish
        message = event['message']
        await self.send(text_data=json.dumps(message))



    def format_message(self, message, sent_at):
        """Xabarni formatlash uchun metod."""
        return {
            'sender_id': message.sender.id,
            'sender_name': message.sender.username,
            'chat_id': message.chat.id,
            'content': message.content,
            'created_at': sent_at.isoformat()  # ISO formatdagi vaqt
        }

    @sync_to_async
    def get_user_by_id(self, user_id):
        """Receiverni ID orqali olish."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @sync_to_async
    def get_or_create_chat(self, user1, user2):
        """Ikkita foydalanuvchi o'rtasida chatni olish yoki yaratish."""
        return Chat.get_or_create_chat(user1, user2)

    @sync_to_async
    def save_message(self, chat, user, message_content, sent_at):
        """Yangi xabarni bazaga saqlash."""
        return Message.objects.create(
            chat=chat,
            sender=user,
            content=message_content,
            created_at=sent_at
        )

    @sync_to_async
    def mark_all_unread_messages_as_read(self):
        """Foydalanuvchi kirganida barcha o'qilmagan xabarlarni 'o'qilgan' deb belgilash."""
        unread_messages = Message.objects.filter(
            chat=self.chat,
            is_read=False,
        ).exclude(sender=self.user)  # Xabarni boshqa foydalanuvchi yuborgan bo'lsa

        unread_messages.update(is_read=True)

    @sync_to_async
    def set_user_online_status(self, status):
        """Foydalanuvchi online holatini belgilash."""
        self.user.is_online = status
        self.user.save()



    @sync_to_async
    def add_user_to_chat(self, user):
        """Foydalanuvchini Redisga qo'shish"""
        redis_client.sadd(f"chat_{self.chat.id}_participants", user.id)

    @sync_to_async
    def remove_user_from_chat(self, user):
        """Foydalanuvchini Redisdan olib tashlash"""
        redis_client.srem(f"chat_{self.chat.id}_participants", user.id)

    @sync_to_async
    def get_chat_participants_count(self):
        """Chatdagi foydalanuvchilar sonini Redis orqali hisoblash"""
        # Redisda chatdagi foydalanuvchilarni olish
        participants = redis_client.smembers(f"chat_{self.chat.id}_participants")
        return len(participants)

    async def send_participants_count(self, event):
        """Foydalanuvchilarga guruhdagi ishtirokchilar sonini yuborish"""
        count = event['count']
        await self.send(text_data=json.dumps({
            'type': 'participants_count',
            'count': count
        }))