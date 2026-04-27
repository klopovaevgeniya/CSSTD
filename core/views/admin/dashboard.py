from django.shortcuts import render
from core.decorators import admin_required
from django.utils import timezone
from core.models import Project, Employee, Department, ProjectTask
from core.utils.project_archive import archived_project_q

import logging

logger = logging.getLogger(__name__)

# Summary: Обрабатывает сценарий admin dashboard.
@admin_required
def admin_dashboard(request):
    active_projects_qs = Project.objects.exclude(archived_project_q())
    total_projects = active_projects_qs.count()
    active_projects = active_projects_qs.filter(status__name__icontains='актив').count()
    completed_projects = active_projects_qs.filter(status__name__icontains='заверш').count()
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()
    total_departments = Department.objects.count()

    active_tasks_qs = ProjectTask.objects.exclude(archived_project_q(prefix='project'))
    total_tasks = active_tasks_qs.count()
    in_progress_tasks = active_tasks_qs.filter(status__icontains='работе').count()
    overdue_tasks = active_tasks_qs.filter(
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
