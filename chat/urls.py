from django.urls import path

from . import views
from .views import RoomMessageListView, UnreadMessageCountView, MarkMessagesAsViewed

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:room_name>/", views.room, name="room"),
    path('messages/<room_name>/', RoomMessageListView.as_view(), name='room-message-list'),
    path('unread_messages/<str:room_name>/', UnreadMessageCountView.as_view(), name='unread-message-count'),
    path('mark_messages_as_viewed/<str:room_name>/', MarkMessagesAsViewed.as_view(), name='mark_messages_as_viewed'),

    path('chatadmin/', views.index_view_admin, name='chat-index-admin'),
    path('chatuser/', views.index_view_user, name='chat-index-user'),
    path('<str:room_name>/', views.room_view_admin, name='chat-room-admin'),
    path('room-create/<str:room_name>/', views.room_view_user, name='chat-roomuser'),
]



