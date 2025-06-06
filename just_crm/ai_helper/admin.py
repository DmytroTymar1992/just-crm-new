from django.contrib import admin
from .models import AiSuggestion

@admin.register(AiSuggestion)
class AiSuggestionAdmin(admin.ModelAdmin):
    list_display = ("chat", "contact", "type", "goal", "updated_at")
    list_filter  = ("type", "updated_at")
    search_fields = ("goal", "short_description", "contact__name")