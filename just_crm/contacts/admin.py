# contacts/admin.py
from django.contrib import admin
from .models import Contact, ContactPhone, ContactEmail


class ContactPhoneInline(admin.TabularInline):
    model = ContactPhone
    extra = 0
    fields = (
        'phone', 'has_viber', 'viber_id', 'viber_name',
    )
    readonly_fields = ('viber_id', 'viber_name')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'company', 'created_at')
    search_fields = ('first_name', 'last_name', 'company__name')
    inlines = [ContactPhoneInline]


@admin.register(ContactPhone)
class ContactPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone', 'contact', 'has_viber', 'viber_id')
    list_filter = ('has_viber',)
    search_fields = ('phone', 'contact__first_name', 'contact__last_name')

