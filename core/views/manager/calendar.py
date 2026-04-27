from django.shortcuts import render
from core.decorators import role_required
from core.models import Employee, Project
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

    # Только проекты с датой окончания
    projects_with_deadline = projects.exclude(end_date__isnull=True)

    # Подготовка данных для календаря
    project_events = []
    statuses = set()
    types = set()

    for p in projects_with_deadline:
        status_name = p.status.name if p.status else ''
        type_name = p.type.name if p.type else ''
        statuses.add(status_name)
        types.add(type_name)

        project_events.append({
            'id': p.id,
            'title': p.name,
            'start': p.end_date.isoformat() if p.end_date else None,
            'end': p.end_date.isoformat() if p.end_date else None,
            'status': status_name,
            'type': type_name,
            'description': p.description or '',
            'code': p.code or '',
            'start_date': p.start_date.isoformat() if p.start_date else '',
        })

    # Сортируем для удобства отображения
    sorted_statuses = sorted([s for s in statuses if s])
    sorted_types = sorted([t for t in types if t])

    context = {
        'projects_for_calendar': project_events,
        'calendar_statuses': sorted_statuses,
        'calendar_types': sorted_types,
    }

    return render(request, 'manager/calendar.html', context)
