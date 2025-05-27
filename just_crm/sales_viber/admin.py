from django.contrib import admin
from .models import ViberMessage


@admin.register(ViberMessage)
class ViberMessageAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'contact', 'user', 'get_direction',
        'delivery_status', 'media_type', 'error_code',
    )
    list_filter = (
        'delivery_status',
        'media_type',
        'user',
        ('date', admin.DateFieldListFilter),
    )
    search_fields = (
        'contact__first_name', 'contact__last_name',
        'contact_phone__phone',
        'text', 'echat_message_id',
    )
    readonly_fields = ('raw_event',)

    # ----- власний стовпець Напрямок ---------------------------------
    @admin.display(description='Напрямок', ordering='interaction__sender')
    def get_direction(self, obj):
        """
        Повертає 'Incoming' / 'Outgoing' згідно з Interaction.sender
        """
        mapping = {
            'user':    'Outgoing',
            'contact': 'Incoming',
            'system':  'System'
        }
        return mapping.get(obj.interaction.sender, obj.interaction.sender)
