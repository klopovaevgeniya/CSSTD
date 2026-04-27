import logging

logger = logging.getLogger(__name__)

# Summary: Файл `csstd/wsgi.py`: содержит код и настройки для раздела "wsgi".
"""
WSGI config for csstd project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csstd.settings')

application = get_wsgi_application()
