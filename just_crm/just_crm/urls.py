
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    #path('sales/', include('sales.urls')),
    path('companies/', include('companies.urls')),
    path('contacts/', include('contacts.urls')),
    path('calls/', include('calls.urls')),
    path('chats/', include('chats.urls')),
    path('tasks/', include('tasks.urls')),
    path('integrations/echat/viber/', include('sales_viber.urls')),
    path('integrations/echat/telegram/', include('sales_telegram.urls')),
    path('ai-helper/', include('ai_helper.urls')),
]

# Додаємо маршрути для статичних і медіа-файлів під час розробки
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)