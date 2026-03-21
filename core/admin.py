from django.contrib import admin
from .models import Project, Employee, Partner, Event

admin.site.register(Project)
admin.site.register(Employee)
admin.site.register(Partner)
admin.site.register(Event)
