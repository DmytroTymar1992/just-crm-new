from django.urls import path
from .views import echat_telegram_webhook
from .api import ChatSendMessageView

urlpatterns = [
    path('webhook/', echat_telegram_webhook, name='echat_telegram_webhook'),
    path("api/chats/<int:chat_id>/send/", ChatSendMessageView.as_view(),
         name="chat-send-message-telegram"),
    #path("webhook/status/", echat_viber_status, name="echat_viber_status"),
]