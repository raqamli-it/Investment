from django.contrib.messages.storage.cookie import MessageSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from chat.models import Notification, Message
from chat.serializers import NotificationSerializer


class NotificationListAPIView(generics.ListAPIView):
    """
    Foydalanuvchining barcha notifikatsiyalarini olish.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class MarkNotificationRead(APIView):
    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({"message": "Notification marked as read"}, status=status.HTTP_200_OK)


class MessageRetrieveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        message = get_object_or_404(Message, pk=pk)

        # Agar o'qilmagan bo‘lsa, is_read ni yangilaymiz
        if message.receiver == request.user and not message.is_read:
            message.is_read = True
            message.save()

            # WebSocket orqali senderga yuborish
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{message.sender.id}",
                {
                    "type": "message_read",
                    "message_id": message.id,
                    "reader": request.user.username
                }
            )

        serializer = MessageSerializer(message)
        return Response(serializer.data)
