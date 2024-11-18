from accounts.models import User
from django.db import models


# class User(User):
#     pass

class Room(models.Model):
    name = models.CharField(max_length=128)
    user = models.ManyToManyField(to=User, blank=True, related_name='room')

    def join(self, user):
        self.user.add(user)
        self.save()

    def leave(self, user):
        self.user.remove(user)
        self.save()

    def __str__(self):
        return f'{self.name} '


class Message(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='message', null=True, blank=True)
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE, related_name='message', blank=True, null=True)
    content = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_viewed = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return f'{self.user.email if self.user else "Anonymous"} | {self.room.name}'
