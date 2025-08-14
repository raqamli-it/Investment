import datetime

import pytz
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
