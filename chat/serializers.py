from rest_framework import serializers
from . import models


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Message
        fields = ['id', 'content', 'timestamp', 'is_viewed', 'user', 'room']


class UnreadMessageCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    last_message = serializers.DictField()
