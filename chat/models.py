from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Chat(models.Model):
    user1 = models.ForeignKey(User, related_name='chats_user1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='chats_user2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat between {self.user1} and {self.user2}"

    def formatted_created_at(self):
        """Asia/Tashkent vaqt mintaqasida formatlangan vaqtni qaytaradi."""
        return timezone.localtime(self.created_at).strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def get_or_create_chat(cls, user1, user2_id):
        """Get or create a chat between two users."""
        try:
            # user2 ni `User` modelidan olish
            user2 = User.objects.get(id=user2_id)
        except User.DoesNotExist:
            raise ValueError("Receiver ID bilan foydalanuvchi topilmadi.")

        # user1 va user2 ni tartiblash
        if user1.id < user2.id:
            user_a, user_b = user1, user2
        else:
            user_a, user_b = user2, user1

        # Chatni olish yoki yaratish
        chat, created = cls.objects.get_or_create(
            user1=user_a,
            user2=user_b
        )
        return chat


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField()
    image = models.ImageField(upload_to='message_images/', blank=True, null=True)  # Rasmni saqlash
    is_read = models.BooleanField(default=False)  # O'qilgan status

    def __str__(self):
        return f"Message from {self.sender} in chat {self.chat.id}"


class GroupChat(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(User, related_name="group_chats")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"


class GroupMessageRead(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="read_status")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    class Meta:
        unique_together = (
        'message', 'user')  # Bir foydalanuvchi har bir xabar uchun faqat bitta yozuvga ega bo‘lishi kerak

    def __str__(self):
        return f"{self.user.username} - {self.message.id}: {'Read' if self.is_read else 'Unread'}"
