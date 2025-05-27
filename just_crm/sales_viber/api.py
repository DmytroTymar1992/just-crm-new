# sales_viber/api.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from sales_viber.services import send_text_in_chat
from chats.models import Chat


class ChatSendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id: int):
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Текст порожній"},
                            status=status.HTTP_400_BAD_REQUEST)

        chat = Chat.objects.select_related("contact").get(pk=chat_id)
        msg  = send_text_in_chat(request.user, chat, text)
        return Response(
            {
                "id":      msg.id,
                "text":    msg.text,
                "date":    msg.date.strftime("%d.%m.%Y %H:%M"),
                "pending": True          # фронт знає, що очікує статусу
            },
            status=status.HTTP_202_ACCEPTED
        )