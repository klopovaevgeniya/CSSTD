from django.shortcuts import render
from ..decorators import login_required, role_required


@login_required
@role_required(['admin'])
def admin_dashboard(request):
    return render(request, 'dashboard/admin.html')


@login_required
@role_required(['project_manager'])
def manager_dashboard(request):
    return render(request, 'dashboard/manager.html')


@login_required
@role_required(['employee'])
def employee_dashboard(request):
    return render(request, 'dashboard/employee.html')


@login_required
@role_required(['readonly'])
def readonly_dashboard(request):
    return render(request, 'dashboard/readonly.html')
