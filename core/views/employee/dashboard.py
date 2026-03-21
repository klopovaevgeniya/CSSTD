from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import role_required
from core.models import (
    Employee, ProjectParticipant, ProjectTask, EmployeeProjectAssignmentNotification, 
    Project, ProjectChatMessageNotification, EmployeeTaskAssignmentNotification, TaskAttachment
)
from django.db import transaction
from datetime import date


@role_required(['employee'])
def employee_dashboard(request):
    """Дашборд сотрудника с реальной информацией."""
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем количество новых уведомлений о назначении на проекты
    new_assignment_notifications = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee, 
        seen=False
    ).count()
    
    # Получаем количество новых уведомлений о задачах
    new_task_notifications = EmployeeTaskAssignmentNotification.objects.filter(
        employee=employee, 
        seen=False
    ).count()
    
    # Непрочитанные сообщения в чатах
    employee_new_chat_count = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()
    
    # Получаем проекты, где сотрудник является участником
    my_projects = ProjectParticipant.objects.filter(
        employee=employee
    ).select_related('project', 'project__status', 'project__type', 'project__manager')
    
    # Получаем все задачи сотрудника
    all_tasks = ProjectTask.objects.filter(assigned_to=employee)
    
    # Активные задачи (не завершённые)
    active_tasks = all_tasks.exclude(status__icontains='завершена').count()
    
    # Завершённые задачи
    completed_tasks = all_tasks.filter(status__icontains='завершена').count()
    
    # Расчёт прогресса (если есть задачи)
    total_tasks = all_tasks.count()
    progress_percent = 0
    if total_tasks > 0:
        progress_percent = int((completed_tasks / total_tasks) * 100)
    
    # Перегруженные задачи (просрочены или на сегодня)
    overdue_tasks = all_tasks.filter(
        due_date__lte=date.today()
    ).exclude(status__icontains='завершена').count()
    
    # Недавние задачи для отображения
    recent_tasks = all_tasks.exclude(status__icontains='завершена').order_by('due_date')[:5]

    context = {
        'user': request.user,
        'employee': employee,
        'new_assignment_notifications': new_assignment_notifications,
        'new_task_notifications': new_task_notifications,
        'employee_new_chat_count': employee_new_chat_count,
        'my_projects_count': my_projects.count(),
        'active_tasks_count': active_tasks,
        'completed_tasks_count': completed_tasks,
        'progress_percent': progress_percent,
        'overdue_tasks_count': overdue_tasks,
        'user_first_name': employee.first_name,
        'user_last_name': employee.last_name,
        'user_email': employee.email,
        'user_position': employee.position.name if employee.position else 'Не указана',
        'user_department': employee.department.name if employee.department else 'Не указана',
        'recent_tasks': recent_tasks,
    }
    return render(request, 'employee/dashboard.html', context)


@role_required(['employee'])
def employee_projects(request):
    """Список проектов сотрудника вкладка в дашборде."""
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем уведомления о назначении на проекты
    unseen_notifications = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee, 
        seen=False
    )
    project_ids_with_notification = list(unseen_notifications.values_list('project_id', flat=True))

    # Отмечаем уведомления как прочитанные при открытии вкладки
    if unseen_notifications.exists():
        with transaction.atomic():
            unseen_notifications.update(seen=True)

    # Пометить все уведомления чата для сотрудника как прочитанные при открытии вкладки проектов
    employee_chat_unseen = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False)
    if employee_chat_unseen.exists():
        with transaction.atomic():
            employee_chat_unseen.update(seen=True)

    # Получаем все проекты, где сотрудник является участником
    projects = ProjectParticipant.objects.filter(
        employee=employee
    ).select_related('project', 'project__status', 'project__type', 'project__manager')

    # Получаем непрочитанные сообщения в чате для каждого проекта
    projects_data = []
    for participant in projects:
        unread_messages = ProjectChatMessageNotification.objects.filter(
            project=participant.project,
            employee=employee,
            seen=False
        ).count()
        projects_data.append({
            'participant': participant,
            'unread_chat_messages': unread_messages,
            'has_new': participant.project.id in project_ids_with_notification
        })

    context = {
        'projects_data': projects_data,
        'project_ids_with_notification': project_ids_with_notification,
        'employee_new_chat_count': ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count(),
        'new_assignment_notifications': len(project_ids_with_notification),
    }

    return render(request, 'employee/projects.html', context)


@role_required(['employee'])
def employee_project_detail(request, pk):
    """Детальная страница проекта для сотрудника."""
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем проект и проверяем, что сотрудник на нём назначен
    project = get_object_or_404(Project, id=pk)
    participant = get_object_or_404(ProjectParticipant, project=project, employee=employee)

    # Получаем все задачи сотрудника в этом проекте
    project_tasks = ProjectTask.objects.filter(
        project=project,
        assigned_to=employee
    ).select_related('project')

    # Активные задачи
    active_tasks = project_tasks.exclude(status__icontains='завершена')
    completed_tasks = project_tasks.filter(status__icontains='завершена')

    # Прогресс по проекту для этого сотрудника
    total_project_tasks = project_tasks.count()
    progress_percent = 0
    if total_project_tasks > 0:
        progress_percent = int((completed_tasks.count() / total_project_tasks) * 100)

    # Получаем всех участников проекта
    all_participants = ProjectParticipant.objects.filter(
        project=project
    ).select_related('employee', 'employee__position')

    context = {
        'project': project,
        'participant': participant,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'total_tasks': total_project_tasks,
        'progress_percent': progress_percent,
        'all_participants': all_participants,
        'user': request.user,
    }

    return render(request, 'employee/project_detail.html', context)


@role_required(['employee'])
def employee_tasks(request):
    """Список всех задач сотрудника."""
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем уведомления о новых назначениях на задачи
    unseen_task_notifications = EmployeeTaskAssignmentNotification.objects.filter(
        employee=employee, 
        seen=False
    )
    task_ids_with_notification = list(unseen_task_notifications.values_list('task_id', flat=True))

    # Отмечаем уведомления как прочитанные при открытии вкладки
    if unseen_task_notifications.exists():
        with transaction.atomic():
            unseen_task_notifications.update(seen=True)

    # Получаем все задачи сотрудника
    all_tasks = ProjectTask.objects.filter(
        assigned_to=employee
    ).select_related('project', 'created_by').order_by('-created_at')

    # Разделяем задачи на активные и завершённые
    active_tasks = all_tasks.exclude(status__icontains='завершена')
    completed_tasks = all_tasks.filter(status__icontains='завершена')

    # Просрочены ли задачи
    overdue_tasks = all_tasks.filter(
        due_date__lt=date.today()
    ).exclude(status__icontains='завершена')

    # Формируем данные всех задач с информацией о новых назначениях
    tasks_data = []
    for task in all_tasks:
        # Преобразуем статус в CSS класс (заменяем пробелы на подчеркивание)
        status_class = task.status.replace(' ', '_').lower() if task.status else ''
        
        tasks_data.append({
            'task': task,
            'is_new': task.id in task_ids_with_notification,
            'is_overdue': task.due_date and task.due_date < date.today() and task.status != 'завершена',
            'status_class': status_class
        })

    context = {
        'tasks_data': tasks_data,
        'all_tasks': all_tasks,
        'active_tasks': active_tasks.count(),
        'completed_tasks': completed_tasks.count(),
        'overdue_tasks_count': overdue_tasks.count(),
        'total_tasks': all_tasks.count(),
        'task_ids_with_notification': task_ids_with_notification,
        'employee': employee,
    }

    return render(request, 'employee/tasks.html', context)


@role_required(['employee'])
def employee_task_detail(request, task_id):
    """Детальная страница задачи для сотрудника с возможностью сдачи и прикрепления файлов."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    task = get_object_or_404(ProjectTask, id=task_id, assigned_to=employee)
    attachments = task.attachments.all()

    if request.method == 'POST':
        if 'attachment' in request.FILES:
            TaskAttachment.objects.create(task=task, file=request.FILES['attachment'])
        action = request.POST.get('action')
        if action == 'submit_task':
            task.status = 'завершена'
            task.save()
        return redirect('employee_task_detail', task_id=task_id)

    context = {
        'task': task,
        'attachments': attachments,
        'is_manager': False,
    }
    return render(request, 'employee/task_detail.html', context)



@role_required(['employee'])
def employee_task_detail(request, task_id):
    """Детальная страница задачи для сотрудника с возможностью сдачи и прикрепления файлов."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    task = get_object_or_404(ProjectTask, id=task_id, assigned_to=employee)
    attachments = task.attachments.all()

    if request.method == 'POST':
        if 'attachment' in request.FILES:
            TaskAttachment.objects.create(task=task, file=request.FILES['attachment'])
        action = request.POST.get('action')
        if action == 'submit_task':
            task.status = 'завершена'
            task.save()
        return redirect('employee_task_detail', task_id=task_id)

    context = {
        'task': task,
        'attachments': attachments,
        'is_manager': False,
    }
    return render(request, 'employee/task_detail.html', context)