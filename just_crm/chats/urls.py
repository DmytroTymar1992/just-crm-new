from django.urls import path
from . import views



urlpatterns = [
    path('', views.chat_view, name='chat_list'),
    path('<int:chat_id>/', views.chat_view, name='chat_detail'),
]