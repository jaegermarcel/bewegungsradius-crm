"""
Celery Konfiguration für Bewegungsradius
"""

import os

from celery import Celery

# Django Settings Module setzen
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bewegungsradius.settings")

app = Celery("bewegungsradius")

# Celery Konfiguration aus Django Settings laden
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatisch Tasks aus allen installierten Apps laden
app.autodiscover_tasks()
