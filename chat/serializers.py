from rest_framework import serializers
from .models import Message, Chat


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender', 'sender_name', 'content', 'created_at', 'is_read', 'image']


class ChatSerializer(serializers.ModelSerializer):
    user1 = serializers.StringRelatedField()
    user2 = serializers.StringRelatedField()
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = Chat
        fields = ['id', 'user1', 'user2', 'created_at']
