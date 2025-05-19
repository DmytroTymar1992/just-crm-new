from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Поля, які відображатимуться в списку адмін-панелі
    list_display = ('username', 'email', 'role', 'status', 'phonet_extension', 'is_staff', 'is_active')
    list_filter = ('role', 'status', 'is_staff', 'is_active', 'phonet_extension')


    # Поля для редагування існуючого користувача
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'role', 'status', 'phonet_extension')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Поля для створення нового користувача
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name', 'role', 'status', 'phonet_extension',
                'password1', 'password2', 'is_staff', 'is_active'
            ),
        }),
    )

    search_fields = ('username', 'email', 'phonet_extension')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

admin.site.register(CustomUser, CustomUserAdmin)