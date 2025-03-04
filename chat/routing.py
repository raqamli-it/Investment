from django.urls import re_path
from .consumers import ChatConsumer, GroupChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/$", ChatConsumer.as_asgi()),
    re_path(r"ws/gr_chat/$", GroupChatConsumer.as_asgi()),
]
