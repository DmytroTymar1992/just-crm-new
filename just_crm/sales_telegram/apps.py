from django.apps import AppConfig

class SalesTelegramConfig(AppConfig):
    name = 'sales_telegram'

    def ready(self):
        import sales_telegram.signals