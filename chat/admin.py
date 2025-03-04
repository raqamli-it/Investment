from django.contrib import admin

from chat.models import Chat, Message, GroupChat, GroupMessage, GroupMessageRead

admin.site.register(Chat)
admin.site.register(Message)
admin.site.register(GroupChat)
admin.site.register(GroupMessage)
admin.site.register(GroupMessageRead)