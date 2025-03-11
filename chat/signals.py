from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User
from chat.models import GroupChat
from chat.models import Notification

@receiver(post_save, sender=GroupChat)
def send_notification_on_group_create(sender, instance, created, **kwargs):
    """
    Yangi guruh yaratilganda barcha foydalanuvchilarga xabar yuborish.
    """
    if created:  # Faqat yangi yaratilganda ishlaydi
        group_name = instance.name
        group_id = instance.id
        group_image = instance.image.url if instance.image else None
        message = f"Yangi guruh yaratildi: {group_name}"

        users = User.objects.all()  # Barcha foydalanuvchilarni olish
        notifications = [Notification(user=user, message=message, image=group_image, group_id=group_id) for user in users]
        Notification.objects.bulk_create(notifications)  # Bir martada barcha xabarlarni saqlash
