from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from core.decorators import admin_required
from core.models import Project, Employee, ProjectTask, Department, ProjectStatus
from decimal import Decimal
import json


@admin_required
def statistics_dashboard(request):
    """Дашборд со статистикой"""
    
    # Статистика проектов
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(
        status__name__icontains='актив'
    ).count()
    completed_projects = Project.objects.filter(
        status__name__icontains='завершён'
    ).count()
    
    # Статистика сотрудников
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()
    
    # Статистика задач
    total_tasks = ProjectTask.objects.count()
    completed_tasks = ProjectTask.objects.filter(status__icontains='завершён').count()
    in_progress_tasks = ProjectTask.objects.filter(status__icontains='работе').count()
    overdue_tasks = ProjectTask.objects.filter(
        due_date__lt=timezone.now().date(),
        status__icontains='работе'
    ).count()
    
    # Статистика по отделам
    departments_stats = Department.objects.annotate(
        employee_count=Count('employee')
    ).filter(employee_count__gt=0).values('name', 'employee_count')
    
    # Статистика по приоритетам задач
    priority_stats = ProjectTask.objects.values('priority').annotate(
        count=Count('id')
    ).exclude(priority__isnull=True)
    
    # Статистика статусов задач
    status_stats = ProjectTask.objects.values('status').annotate(
        count=Count('id')
    ).exclude(status__isnull=True)
    # Топ сотрудников по количеству назначенных задач
    top_employees = Employee.objects.annotate(
        task_count=Count('projecttask')
    ).order_by('-task_count')[:5]
    
    # Статистика проектов по статусам
    project_status_stats = ProjectStatus.objects.annotate(
        project_count=Count('project')
    ).filter(project_count__gt=0)
    
    # График загрузки сотрудников (количество активных задач)
    employee_load = Employee.objects.annotate(
        active_task_count=Count(
            'projecttask',
            filter=Q(projecttask__status__icontains='работе')
        )
    ).order_by('-active_task_count')[:10]
    
    # Данные для графиков
    dept_names = [d['name'] for d in departments_stats]
    dept_counts = [d['employee_count'] for d in departments_stats]
    
    priority_labels = [p['priority'] or 'Не указан' for p in priority_stats]
    priority_counts = [p['count'] for p in priority_stats]
    
    status_labels = [s['status'] for s in status_stats]
    status_counts = [s['count'] for s in status_stats]
    
    project_status_labels = [ps.name for ps in project_status_stats]
    project_status_counts = [ps.project_count for ps in project_status_stats]
    
    emp_load_names = [f"{e.last_name} {e.first_name[:1]}." for e in employee_load]
    emp_load_counts = [e.active_task_count for e in employee_load]
    
    # Бюджет проектов
    total_budget = sum((p.budget or Decimal("0")) for p in Project.objects.all())
    total_actual = sum((p.actual_cost or Decimal("0")) for p in Project.objects.all())
    budget_delta = total_budget - total_actual
    budget_usage_percent = int((total_actual / total_budget) * 100) if total_budget > 0 else 0
    budget_usage_percent = max(0, min(budget_usage_percent, 999))

    project_completion_percent = int((completed_projects / total_projects) * 100) if total_projects else 0
    tasks_completion_percent = int((completed_tasks / total_tasks) * 100) if total_tasks else 0
    employee_active_percent = int((active_employees / total_employees) * 100) if total_employees else 0
    
    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'top_employees': top_employees,
        'employee_load': employee_load,
        'total_budget': f"{total_budget:,.2f}",
        'total_actual': f"{total_actual:,.2f}",
        'budget_delta': f"{budget_delta:,.2f}",
        'budget_usage_percent': budget_usage_percent,
        'project_completion_percent': project_completion_percent,
        'tasks_completion_percent': tasks_completion_percent,
        'employee_active_percent': employee_active_percent,
        
        # Данные для графиков
        'dept_names': json.dumps(dept_names),
        'dept_counts': json.dumps(dept_counts),
        'priority_labels': json.dumps(priority_labels),
        'priority_counts': json.dumps(priority_counts),
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'project_status_labels': json.dumps(project_status_labels),
        'project_status_counts': json.dumps(project_status_counts),
        'emp_load_names': json.dumps(emp_load_names),
        'emp_load_counts': json.dumps(emp_load_counts),
    }
    
    return render(request, 'admin/statistics/dashboard.html', context)
