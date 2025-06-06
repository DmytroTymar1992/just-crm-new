# urls.py (ai_helper)
from django.urls import path
from .views import SuggestionDetail

urlpatterns = [
    path("suggestion/<int:chat_id>/", SuggestionDetail.as_view(), name="ai_suggestion"),
]
