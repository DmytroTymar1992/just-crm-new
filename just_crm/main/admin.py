from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Поля, які відображатимуться в списку адмін-панелі
    list_display = ('username', 'email', 'telegram_id', 'role', 'status', 'phonet_extension', 'is_staff', 'is_active',
                    'echat_instance_id',)
    list_filter = ('role', 'status', 'is_staff', 'is_active', 'phonet_extension')

    # Поля для редагування існуючого користувача
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'telegram_id', 'role', 'status', 'phonet_extension')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('E-chat', {'fields': ('echat_instance_id', 'echat_api_key')}),
        ('E-chat-telegram', {'fields': ('echat_instance_id_telegram', 'echat_api_key_telegram')}),
    )

    # Поля для створення нового користувача
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name', 'telegram_id', 'role', 'status', 'phonet_extension',
                'password1', 'password2', 'is_staff', 'is_active'
            ),
        }),
    )

    search_fields = ('username', 'email', 'telegram_id', 'phonet_extension')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

admin.site.register(CustomUser, CustomUserAdmin)