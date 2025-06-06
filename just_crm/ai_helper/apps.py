from django.apps import AppConfig

class AiHelperConfig(AppConfig):
    name = 'ai_helper'

    def ready(self):
        import ai_helper.signals
