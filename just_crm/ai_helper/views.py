# ai_helper/views.py
from django.http import JsonResponse, Http404
from django.views import View
from ai_helper.models import AiSuggestion   # :contentReference[oaicite:7]{index=7}

class SuggestionDetail(View):
    def get(self, request, chat_id):
        try:
            s = AiSuggestion.objects.get(chat_id=chat_id)
        except AiSuggestion.DoesNotExist:
            raise Http404("No suggestion")

        return JsonResponse({
            "type":  s.type,              # 'Дзвінок' / 'лист' / 'повідомлення'
            "goal":  s.goal,
            "short_description": s.short_description,
        })
