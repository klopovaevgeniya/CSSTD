import logging

logger = logging.getLogger(__name__)

# Summary: Файл `core/views/employee/calendar.py`: содержит код и настройки для раздела "calendar".
from django.shortcuts import render, redirect
from django.db.models import Q
from core.decorators import role_required
from core.models import (
    Employee,
    ProjectTask,
    ProjectParticipant,
    EmployeeTaskAssignmentNotification,
    EmployeeProjectAssignmentNotification,
    ProjectChatMessageNotification,
    TaskChatMessageNotification,
)
from core.utils.project_archive import archived_project_q


# Summary: Обрабатывает сценарий employee calendar.
@role_required(['employee'])
def employee_calendar(request):
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Уведомления для бокового меню
    new_task_notifications = EmployeeTaskAssignmentNotification.objects.filter(employee=employee, seen=False).count()
    new_assignment_notifications = EmployeeProjectAssignmentNotification.objects.filter(employee=employee, seen=False).count()
    employee_new_chat_count = (
        ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()
        + TaskChatMessageNotification.objects.filter(employee=employee, seen=False).count()
    )

    # Проекты, где сотрудник является участником
    project_participants = ProjectParticipant.objects.filter(employee=employee).select_related(
        'project', 'project__status', 'project__type', 'project__manager'
    ).exclude(
        archived_project_q(prefix='project')
    )
    projects = [p.project for p in project_participants if p.project]

    # Задачи сотрудника
    tasks = ProjectTask.objects.filter(
        Q(assigned_to=employee) | Q(task_assignees__employee=employee, task_assignees__step_status__in=['active', 'completed'])
    ).exclude(
        archived_project_q(prefix='project')
    ).select_related('project').distinct()

    # Подготовка данных для календаря
    calendar_items = []

    for p in projects:
        if not p.end_date:
            continue
        status_name = p.status.name if p.status else ''
        type_name = p.type.name if p.type else ''

        calendar_items.append({
            'id': f'project-{p.id}',
            'title': p.name,
            'start': p.end_date.isoformat(),
            'end': p.end_date.isoformat(),
            'status': status_name,
            'type': type_name,
            'description': p.description or '',
            'code': p.code or '',
            'start_date': p.start_date.isoformat() if p.start_date else '',
            'item_type': 'project',
            'link': f'/dashboard/employee/projects/{p.id}/',
        })

    for t in tasks:
        if not t.due_date:
            continue

        project_name = t.project.name if t.project else ''
        status_name = t.status or ''

        calendar_items.append({
            'id': f'task-{t.id}',
            'title': t.name,
            'start': t.due_date.isoformat(),
            'end': t.due_date.isoformat(),
            'status': status_name,
            'type': 'Задача',
            'description': t.description or '',
            'code': project_name,
            'start_date': '',
            'item_type': 'task',
            'link': f'/dashboard/employee/tasks/{t.id}/',
        })

    context = {
        'calendar_items': calendar_items,
        'new_task_notifications': new_task_notifications,
        'new_assignment_notifications': new_assignment_notifications,
        'employee_new_chat_count': employee_new_chat_count,
    }

    return render(request, 'employee/calendar.html', context)
