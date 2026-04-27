import logging

logger = logging.getLogger(__name__)

# Summary: Файл `csstd/urls.py`: содержит код и настройки для раздела "urls".
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('core.urls')), 
]

# during development serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
