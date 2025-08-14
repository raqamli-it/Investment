import pytz
from django.utils import timezone

def to_user_timezone(dt, tz_name="Asia/Tashkent"):
    if not dt:
        return None
    user_tz = pytz.timezone(tz_name)
    return timezone.localtime(dt, user_tz).isoformat()
