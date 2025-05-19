from django.urls import path
from . import views

urlpatterns = [
    path('webhook/phonet/', views.phonet_webhook, name='phonet_webhook'),
]