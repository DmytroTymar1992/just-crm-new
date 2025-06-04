from django.urls import path
from . import views

urlpatterns = [
    path('', views.kanban_board, name='kanban_board'),
    path('kanban/tasks/', views.kanban_tasks_api, name='kanban_tasks_api'),
    path('create/', views.create_task, name='create_task'),
    path('create/<int:chat_id>/', views.create_task_in_chat, name='create_task_in_chat'),  # Новий URL
    path('edit/<int:task_id>/', views.edit_task, name='edit_task'),
    path('complete/<int:task_id>/', views.complete_task, name='complete_task'),
    path('transfer/<int:task_id>/', views.transfer_task, name='transfer_task'),
    path('confirm_new/<int:contact_id>/', views.confirm_new, name='confirm_new'),
    path('get_available_slots/', views.get_available_slots, name='get_available_slots'),
    path('detail/<int:task_id>/', views.task_detail, name='task_detail'),
]