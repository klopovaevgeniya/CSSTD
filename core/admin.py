import logging

logger = logging.getLogger(__name__)

# Summary: Файл `core/admin.py`: содержит код и настройки для раздела "admin".
from django.contrib import admin
from .models import Project, Employee, Partner, Event

admin.site.register(Project)
admin.site.register(Employee)
admin.site.register(Partner)
admin.site.register(Event)
