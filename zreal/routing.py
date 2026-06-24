from django.urls import re_path
from properties.consumers import PropertyConsumer

websocket_urlpatterns = [
    re_path(r'ws/property/(?P<property_id>\w+)/$', PropertyConsumer.as_asgi()),
]
