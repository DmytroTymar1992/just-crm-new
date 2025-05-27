from django.urls import path
from .views import echat_viber_webhook, echat_viber_status
from sales_viber.api import ChatSendMessageView

urlpatterns = [
    path('webhook/', echat_viber_webhook, name='echat_viber_webhook'),
    path("api/chats/<int:chat_id>/send/", ChatSendMessageView.as_view(),
         name="chat-send-message"),
    path("webhook/status/", echat_viber_status, name="echat_viber_status"),
]