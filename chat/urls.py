from django.urls import path
from chat.views import NotificationListAPIView, MarkNotificationRead

urlpatterns = [
    path('notifications/', NotificationListAPIView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/read', MarkNotificationRead.as_view(), name='mark_notification_read'),
]
