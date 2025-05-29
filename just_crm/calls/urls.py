from django.urls import path
from . import views

urlpatterns = [
    path('webhook/call/dial/', views.phonet_dial_webhook, name='phonet_dial_webhook'),
    path('webhook/call/bridge/', views.phonet_bridge_webhook, name='phonet_bridge_webhook'),
    path('webhook/call/hangup/', views.phonet_hangup_webhook, name='phonet_hangup_webhook'),
    path('update-result/', views.update_call_result, name='update_call_result'),

]