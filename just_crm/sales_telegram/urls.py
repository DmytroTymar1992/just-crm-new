from django.urls import path
from .views import echat_telegram_webhook, echat_telegram_status
from .api import ChatSendMessageView

urlpatterns = [
    path('webhook/', echat_telegram_webhook, name='echat_telegram_webhook'),
    path("api/chats/<int:chat_id>/send/", ChatSendMessageView.as_view(),
         name="chat-send-message-telegram"),
    path("webhook/status/", echat_telegram_status, name="echat_telegram_status"),
]