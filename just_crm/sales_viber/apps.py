# sales_viber/apps.py
from django.apps import AppConfig


class SalesViberConfig(AppConfig):
    name = 'sales_viber'

    def ready(self):
        import sales_viber.signals
