from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import role_required
from core.models import (
    Employee, ProjectTask, ProjectParticipant, EmployeeProjectAssignmentNotification,
    ProjectChatMessageNotification, EmployeeTaskAssignmentNotification
)
from django.db.models import Count, Q
from datetime import date, timedelta


@role_required(['employee'])
def employee_profile(request):
    """Профиль сотрудника с личными данными и статистикой."""
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем все задачи сотрудника
    all_tasks = ProjectTask.objects.filter(assigned_to=employee)
    total_tasks = all_tasks.count()

    # Завершенные задачи
    completed_tasks = all_tasks.filter(status__icontains='завершена').count()

    # Активные задачи
    active_tasks = all_tasks.exclude(status__icontains='завершена').count()

    # Задачи на сегодня
    today = date.today()
    today_tasks = all_tasks.filter(
        Q(due_date=today) | Q(created_at__date=today)
    ).exclude(status__icontains='завершена').count()

    # Просроченные задачи
    overdue_tasks = all_tasks.filter(due_date__lt=today).exclude(status__icontains='завершена').count()

    # Проекты сотрудника
    employee_projects = ProjectParticipant.objects.filter(employee=employee).select_related('project')
    total_projects = employee_projects.count()

    # Активные проекты
    active_projects = employee_projects.filter(project__status__name__icontains='актив').count()

    # Завершенные проекты
    completed_projects = employee_projects.filter(project__status__name__icontains='заверш').count()

    # Процент выполнения задач
    completion_percentage = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)

    # Среднее время выполнения задач (в днях) - упрощенная логика
    avg_completion_time = 0
    if completed_tasks > 0:
        # Используем created_at как приблизительную дату начала
        completed_with_dates = all_tasks.filter(
            status__icontains='завершена',
            created_at__isnull=False
        )
        if completed_with_dates.exists():
            # Предполагаем, что задачи завершаются примерно через неделю после создания
            # Это упрощенная логика, так как нет точных дат завершения
            avg_completion_time = 7.0  # дней

    # Задачи за последний месяц
    last_month = today - timedelta(days=30)
    tasks_last_month = all_tasks.filter(
        created_at__gte=last_month
    ).count()

    # Эффективность (завершенные в срок) - упрощенная логика
    # Поскольку нет точных дат завершения, считаем все завершенные задачи выполненными в срок
    efficiency_percentage = completion_percentage

    # Получаем количество новых уведомлений о задачах
    new_task_notifications = EmployeeTaskAssignmentNotification.objects.filter(
        employee=employee, 
        seen=False
    ).count()
    
    # Непрочитанные сообщения в чатах
    employee_new_chat_count = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()
    
    # Получаем количество новых уведомлений о назначении на проекты
    new_assignment_notifications = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee, 
        seen=False
    ).count()

    context = {
        'employee': employee,
        'new_task_notifications': new_task_notifications,
        'employee_new_chat_count': employee_new_chat_count,
        'new_assignment_notifications': new_assignment_notifications,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'active_tasks': active_tasks,
        'today_tasks': today_tasks,
        'overdue_tasks': overdue_tasks,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'completion_percentage': completion_percentage,
        'avg_completion_time': avg_completion_time,
        'tasks_last_month': tasks_last_month,
        'efficiency_percentage': efficiency_percentage,
    }

    return render(request, 'employee/profile.html', context)