from django.shortcuts import render
from ..decorators import login_required, role_required


import logging

logger = logging.getLogger(__name__)

# Summary: Обрабатывает сценарий admin dashboard.
@login_required
@role_required(['admin'])
def admin_dashboard(request):
    return render(request, 'dashboard/admin.html')


# Summary: Обрабатывает сценарий manager dashboard.
@login_required
@role_required(['project_manager'])
def manager_dashboard(request):
    return render(request, 'dashboard/manager.html')


# Summary: Обрабатывает сценарий employee dashboard.
@login_required
@role_required(['employee'])
def employee_dashboard(request):
    return render(request, 'dashboard/employee.html')


# Summary: Содержит логику для readonly dashboard.
@login_required
@role_required(['readonly'])
def readonly_dashboard(request):
    return render(request, 'dashboard/readonly.html')
