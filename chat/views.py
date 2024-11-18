from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from chat.models import Room, Message
from .serializers import MessageSerializer, UnreadMessageCountSerializer


class MessagePagination(PageNumberPagination):
    page_size = 20


class RoomMessageListView(ListAPIView):
    serializer_class = MessageSerializer
    pagination_class = MessagePagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room_name = self.kwargs['room_name']
        user = self.request.user
        try:
            room = Room.objects.get(name=room_name)
        except Room.DoesNotExist:
            raise PermissionDenied("This room does not exist.")

        if user not in room.user.all():
            raise PermissionDenied("You do not have access to this room.")

        return Message.objects.filter(room=room).order_by('timestamp')


class UnreadMessageCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_name):
        try:
            room = Room.objects.get(name=room_name)
        except Room.DoesNotExist:
            return Response({"detail": "This room does not exist."}, status=404)

        # Faqat request.user yozmagan xabarlarni qidirish
        unread_messages = Message.objects.filter(room=room, is_viewed=False).exclude(user=request.user)
        unread_count = unread_messages.count()
        last_message = unread_messages.last()

        if last_message:
            last_message_data = {
                'sender': last_message.user.username,
                'content': last_message.content[:10],
                # Yoki boshqa last_message attributlari
            }
        else:
            last_message_data = None

        serializer = UnreadMessageCountSerializer({
            'unread_count': unread_count,
            'last_message': last_message_data
        })

        return Response(serializer.data)


class MarkMessagesAsViewed(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_name):
        room = get_object_or_404(Room, name=room_name)
        user = request.user

        # Barcha xabarlarning is_viewed maydonini yangilash
        Message.objects.filter(room=room).exclude(user=user).update(is_viewed=True)

        return Response({"status": "success", "message": "All messages marked as viewed"})


def index(request):
    return render(request, "chat/index.html")


def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})


def index_view_admin(request):
    return render(request, 'index.html', {
        'rooms': Room.objects.all(),
    })


def room_view_admin(request, room_name):
    try:
        chat_room = Room.objects.get(name=room_name)

    except Exception as e:
        return HttpResponse("Room mavjud emas")
    return render(request, 'room.html', {
        'room': chat_room,
    })


def room_view_user(request, room_name):
    chat_room, created = Room.objects.get_or_create(name=room_name)
    return render(request, 'room.html', {
        'room': chat_room,
    })


def index_view_user(request):
    return render(request, 'user_page.html', {
        'rooms': Room.objects.all(),
    })
