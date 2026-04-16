from django.shortcuts import render
from core.decorators import admin_required
from django.utils import timezone
from core.models import Project, Employee, Department, ProjectTask

@admin_required
def admin_dashboard(request):
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status__name__icontains='актив').count()
    completed_projects = Project.objects.filter(status__name__icontains='заверш').count()
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()
    total_departments = Department.objects.count()

    total_tasks = ProjectTask.objects.count()
    in_progress_tasks = ProjectTask.objects.filter(status__icontains='работе').count()
    overdue_tasks = ProjectTask.objects.filter(
        due_date__lt=timezone.now().date(),
        status__icontains='работе',
    ).count()

    project_activity_percent = int((active_projects / total_projects) * 100) if total_projects else 0
    employee_activity_percent = int((active_employees / total_employees) * 100) if total_employees else 0

    return render(request, "admin/dashboard.html", {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_departments': total_departments,
        'total_tasks': total_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'project_activity_percent': project_activity_percent,
        'employee_activity_percent': employee_activity_percent,
    })
