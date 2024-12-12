from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Chat, Message
from .serializers import MessageSerializer, ChatSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class ChatViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Foydalanuvchining barcha chatlarini olish
        return Chat.objects.filter(user1=user).union(Chat.objects.filter(user2=user))


class ChatMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chat_id):
        """
        Chat ID asosida barcha xabarlarni qaytarish.
        Faqat chat ishtirokchilari xabarlarni ko‘ra oladi.
        """
        # Chat mavjudligini tekshirish
        try:
            chat = Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=404)

        # Faqat chat ishtirokchilari ma'lumotlarni ko‘ra olishi uchun ruxsat
        if request.user not in [chat.user1, chat.user2]:
            return Response({"error": "You do not have permission to access this chat"}, status=403)

        # Xabarlarni olish va serializer yordamida qaytarish
        messages = Message.objects.filter(chat=chat).order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
