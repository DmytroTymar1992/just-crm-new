import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'just_crm.settings')

app = Celery('just_crm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
