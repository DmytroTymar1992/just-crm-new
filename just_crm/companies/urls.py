from django.urls import path
from . import views

urlpatterns = [
    path('companies/', views.company_list, name='company_list'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('api/check-company/', views.check_company_exists, name='check_company_exists'),
    path('<int:contact_id>/interactions/', views.contact_interactions, name='contact_interactions'),
]