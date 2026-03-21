from django.shortcuts import render
from core.decorators import admin_required
from core.models import Project, Employee

@admin_required
def admin_dashboard(request):
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status__name__icontains='актив').count()  # Assuming status has name
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()

    return render(request, "admin/dashboard.html", {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_employees': total_employees,
        'active_employees': active_employees,
    })
