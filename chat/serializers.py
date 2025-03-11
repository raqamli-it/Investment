from rest_framework import serializers
from chat.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'image', 'created_at', 'is_read', 'group_id']
