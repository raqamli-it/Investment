import os

import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'einvestment.settings')
django.setup()

from chat.middleware import UserAuthMiddleware  # Siz yaratgan middleware
from chat.routing import websocket_urlpatterns  # WebSocket routing uchun

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        UserAuthMiddleware(  # UserAuthMiddleware-ning qo'shilishi
            AuthMiddlewareStack(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        )
    ),

})
