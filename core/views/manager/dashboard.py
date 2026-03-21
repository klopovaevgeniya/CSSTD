from django.shortcuts import render
from core.decorators import role_required
from core.models import Employee, Project, ProjectTask, ProjectParticipant
from datetime import date


@role_required(['project_manager'])
def manager_dashboard(request):
    # Получаем объект Employee для текущего пользователя (руководителя)
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    
    if not employee:
        # Если нет вязи с Employee, используем User напрямую
        projects = Project.objects.filter(manager__employee_user=request.user).select_related('status', 'type')
    else:
        # Получаем все проекты, где текущий пользователь является руководителем
        projects = Project.objects.filter(manager=employee).select_related('status', 'type')
    
    # Активные проекты (исключаем завершённые)
    active_projects = projects.exclude(status__name__icontains='завершён')
    
    # Получаем все задачи для проектов руководителя
    if employee:
        all_tasks = ProjectTask.objects.filter(project__manager=employee)
    else:
        all_tasks = ProjectTask.objects.filter(project__manager__employee_user=request.user)
    
    # Задачи на сегодня (не завершённые)
    today_tasks = all_tasks.filter(
        due_date=date.today()
    ).exclude(status__icontains='завершена')
    
    # Получаем уникальных членов команды (участников всех проектов руководителя)
    if employee:
        team_members = ProjectParticipant.objects.filter(
            project__manager=employee
        ).values('employee').distinct().count()
    else:
        team_members = ProjectParticipant.objects.filter(
            project__manager__employee_user=request.user
        ).values('employee').distinct().count()
    
    # Последние проекты для отображения на дашборде
    recent_projects = active_projects[:3]
    
    # Последние задачи
    recent_tasks = all_tasks.exclude(status__icontains='завершена').order_by('-due_date')[:5]
    # Количество созданных этим менеджером задач
    if employee:
        manager_tasks_count = ProjectTask.objects.filter(created_by=employee, project__manager=employee).count()
    else:
        manager_tasks_count = 0
    
    context = {
        'user': request.user,
        'manager_tasks_count': manager_tasks_count,
        'employee': employee,
        'active_projects_count': active_projects.count(),
        'today_tasks_count': today_tasks.count(),
        'team_members_count': team_members,
        'total_projects_count': projects.count(),
        'all_tasks_count': all_tasks.count(),
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
    }
    return render(request, 'manager/dashboard.html', context)