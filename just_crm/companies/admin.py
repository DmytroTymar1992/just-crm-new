from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'is_active', 'responsible', 'created_at')
    list_filter = ('status', 'is_active', 'responsible')
    search_fields = ('name', 'work_id', 'rabota_id', 'just_id')
    fields = (
        'name', 'work_id', 'rabota_id', 'just_id',
        'responsible', 'status', 'is_active', 'slug'
    )
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 25

    def get_readonly_fields(self, request, obj=None):
        if obj:  # При редагуванні існуючого об'єкта
            return self.readonly_fields + ('slug',)
        return self.readonly_fields  # При створенні нового об'єкта
