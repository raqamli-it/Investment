import json
import logging
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from djangochannelsrestframework.mixins import UpdateModelMixin, CreateModelMixin, DeleteModelMixin, ListModelMixin
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer

from django.contrib.auth import get_user_model

from .models import Room, Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)
User = get_user_model()
import logging
from django.utils import timezone


class ChatConsumer(WebsocketConsumer):

    def connect(self, **kwargs):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        room, created = Room.objects.get_or_create(name=self.room_name)

        # Room name foydalanuvchi ID'siga to'g'ri kelishini nazarda tutamiz
        user = User.objects.filter(id=self.room_name).first()
        if not user:
            user = None
        room.user.add(user)

        # Ulanayotgan foydalanuvchidan boshqa hamma xabarlarni is_viewed ni True qilib yangilash
        # Message.objects.filter(room=room).exclude(user=user).update(is_viewed=True)

        # if not Room.objects.filter(name=self.room_name):
        #     Room.objects.create(name=self.room_name)
        #     room = Room.objects.get(name=self.room_name)
        #     user = User.objects.filter(id=self.room_name).first()
        #     if not user:
        #         user = None
        #
        #     room.user.add(user)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        username = text_data_json.get("username", None)

        # Extract user information
        # user = self.scope["user"]
        #
        # username = user.email if user.is_authenticated else "Anonymous"

        # Get user and room instances
        room = Room.objects.get(name=self.room_name)
        user = User.objects.filter(id=username).first()
        if not user:
            user = None

        room.user.add(user)

        # Save the message to the database
        Message.objects.create(
            user=user,
            room=room,
            content=message,
            timestamp=timezone.now(),
            is_viewed=False
        )

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "chat.message",
                                   "message": message,
                                   "username": username}
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event["message"]
        username = event["username"]

        # Log event data
        logger.info(f"Received event: {event}")

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message,
                                        "username": username
                                        }))


# class MessageConsumer(ListModelMixin, GenericAsyncAPIConsumer, CreateModelMixin):
#     queryset = Message.objects.all()
#     serializer_class = MessageSerializer
#
#     def get_queryset(self, **kwargs):
#         qs = super().get_queryset(**kwargs)
#         user = self.scope['user']
#         room_name = self.scope['url_route']['kwargs']['room_name']
#         queryset = qs.filter(room__name=room_name)
#
#         return queryset
#
#     async def connect(self, **kwargs):
#         await super().connect()
#         await self.model_change.subscribe()
#         print("Connection is made")
#         print(self.scope['user'])
#
#     @model_observer(Message)
#     async def model_change(self, message, observer=None, **kwargs):
#         await self.send_json(message)
#
#     @model_change.serializer
#     def model_serialize(self, instance, action, request_id=None, **kwargs):
#         print(dict(data=MessageSerializer(instance=instance).data, action=action.value))
#         return dict(data=MessageSerializer(instance=instance).data, action=action.value)
#
#     async def disconnect(self, message):
#         print("Connection is over")
#         await super().disconnect(message)
