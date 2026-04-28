from django.shortcuts import render
from core.decorators import role_required
from core.models import Employee, Project, ProjectTask
from core.utils.project_archive import archived_project_q


import logging

logger = logging.getLogger(__name__)

# Summary: Обрабатывает сценарий manager calendar.
@role_required(['project_manager'])
def manager_calendar(request):
    # Получаем объект Employee для текущего пользователя (руководителя)
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()

    if employee:
        # Проекты, где текущий пользователь указан как менеджер
        projects = Project.objects.filter(manager=employee).exclude(archived_project_q())
    else:
        projects = Project.objects.filter(manager__employee_user=request.user).exclude(archived_project_q())

    project_ids = list(projects.values_list('id', flat=True))

    tasks = ProjectTask.objects.filter(project_id__in=project_ids).exclude(
        due_date__isnull=True
    ).select_related('project')

    calendar_items = []

    for p in projects.exclude(end_date__isnull=True):
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
            'link': f'/manager/projects/{p.id}/detail/',
        })

    for t in tasks:
        project_name = t.project.name if t.project else ''

        calendar_items.append({
            'id': f'task-{t.id}',
            'title': t.name,
            'start': t.due_date.isoformat(),
            'end': t.due_date.isoformat(),
            'status': t.status or '',
            'type': 'Задача',
            'description': t.description or '',
            'code': project_name,
            'start_date': '',
            'item_type': 'task',
            'link': f'/manager/tasks/{t.id}/',
        })

    return render(request, 'manager/calendar.html', {'calendar_items': calendar_items})
