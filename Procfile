web: gunicorn soulseer.wsgi --timeout 30 --workers 4 --worker-class sync --bind 0.0.0.0:$PORT
worker: celery -A soulseer worker -l info --concurrency 4
beat: celery -A soulseer beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
