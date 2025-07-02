from django.urls import path
from . import views



urlpatterns = [
    path('', views.chat_view, name='chat_list'),
    path('<int:chat_id>/', views.chat_view, name='chat_detail'),
    path('<int:chat_id>/vacancies/html/', views.get_company_vacancies_html, name='chat-vacancies-html'),
    path('list-html/', views.get_chat_list_html, name='chat_list_html'),
    path('mark-read/', views.mark_interaction_read, name='mark_interaction_read'),

    #path("api/gpt_completion_simple/", views.gpt_completion_simple, name="gpt_completion_stream"),
]