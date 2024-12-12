from django.urls import path
from .views import ChatMessagesAPIView, ChatViewSet

urlpatterns = [
    path('chat/<int:chat_id>/messages/', ChatMessagesAPIView.as_view(), name='chat_messages'),
    path('api/chat/', ChatViewSet.as_view({'get': 'list'}), name='chat-list'),
]
