import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soulseer.settings')
app = Celery('soulseer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
