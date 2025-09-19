import datetime

import pytz
from channels.db import database_sync_to_async
from django.utils import timezone


def to_user_timezone(dt, tz="Asia/Tashkent"):
    if isinstance(dt, str):
        # ISO format string bo‘lsa — datetime’ga aylantiramiz
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt  # noto‘g‘ri format bo‘lsa, o‘zini qaytaramiz

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(pytz.timezone(tz))



@database_sync_to_async
def set_user_online(user):
    user.is_online = True
    user.save(update_fields=["is_online"])

@database_sync_to_async
def set_user_offline(user):
    user.is_online = False
    user.last_seen = timezone.now()
    user.save(update_fields=["is_online", "last_seen"])
