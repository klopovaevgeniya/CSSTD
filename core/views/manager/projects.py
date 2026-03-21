from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import role_required
from core.models import (
    Employee, Project, ManagerProjectNotification, 
    ProjectParticipant, EmployeeProjectAssignmentNotification,
    ProjectChatMessageNotification, ProjectTask, EmployeeTaskAssignmentNotification, TaskAttachment, User
)
from core.forms import ProjectTaskForm
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone


@role_required(['project_manager'])
def manager_projects_list(request):
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Список уведомлений для менеджера
    unseen_notifications = ManagerProjectNotification.objects.filter(manager=employee, seen=False)
    new_project_ids = list(unseen_notifications.values_list('project_id', flat=True))

    # Отметим уведомления как прочитанные — при открытии вкладки проектов точка должна пропасть
    if unseen_notifications.exists():
        with transaction.atomic():
            unseen_notifications.update(seen=True)

    projects = Project.objects.select_related('status', 'type', 'manager').filter(manager=employee).order_by('-created_at')
    
    # Получаем непрочитанные сообщения в чате для каждого проекта
    projects_data = []
    for project in projects:
        unread_messages = ProjectChatMessageNotification.objects.filter(
            project=project,
            employee=employee,
            seen=False
        ).count()
        projects_data.append({
            'project': project,
            'unread_chat_messages': unread_messages
        })

    # Общее количество непрочитанных сообщений в чатах (для индикатора на вкладке)
    manager_new_chat_count = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()

    # Отметить уведомления чата как прочитанные при открытии вкладки проектов
    if manager_new_chat_count > 0:
        with transaction.atomic():
            ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).update(seen=True)

    return render(request, 'manager/projects/list.html', {
        'projects_data': projects_data,
        'new_project_ids': new_project_ids,
        'manager_new_chat_count': manager_new_chat_count,
        'manager_new_projects_count': len(new_project_ids),

    })


@role_required(['project_manager'])
def manager_project_detail(request, pk):
    """Детальная информация о проекте с возможностью назначения сотрудников."""
    # Получаем объект Employee для текущего пользователя
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем проект
    project = get_object_or_404(Project, id=pk, manager=employee)

    # Обработка удаления участника
    if request.method == 'POST' and 'participant_id' in request.POST:
        participant_id = request.POST.get('participant_id')
        try:
            participant = ProjectParticipant.objects.get(id=participant_id, project=project)
            participant.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Сотрудник удален из проекта'})
            else:
                return redirect('manager_project_detail', pk=pk)
        except ProjectParticipant.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Участник не найден'}, status=404)

    # Получаем уже назначенных сотрудников на проект
    assigned_employees = ProjectParticipant.objects.filter(project=project).values_list('employee_id', flat=True)

    # Получаем всех доступных сотрудников для назначения
    available_employees = Employee.objects.filter(is_active=True).exclude(id__in=assigned_employees)

    # Получаем уже назначенных сотрудников с полной информацией
    participants = ProjectParticipant.objects.filter(project=project).select_related('employee', 'employee__position')

    # Обработка добавления нового участника
    if request.method == 'POST' and 'employee_id' in request.POST:
        employee_id = request.POST.get('employee_id')

        if employee_id:
            selected_employee = get_object_or_404(Employee, id=employee_id)

            # Роль в проекте = должность сотрудника
            role = selected_employee.position.name if selected_employee.position else 'Team Member'

            # Создаем участие в проекте
            try:
                with transaction.atomic():
                    ProjectParticipant.objects.create(
                        project=project,
                        employee=selected_employee,
                        role=role
                    )

                    # Создаем уведомление для сотрудника
                    EmployeeProjectAssignmentNotification.objects.create(
                        employee=selected_employee,
                        project=project,
                        seen=False,
                        created_at=timezone.now()
                    )

                # Возвращаем успешный ответ
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Сотрудник успешно назначен на проект'})
                else:
                    return redirect('manager_project_detail', pk=pk)
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)

    context = {
        'project': project,
        'participants': participants,
        'available_employees': available_employees,
    }

    return render(request, 'manager/projects/detail.html', context)


@role_required(['project_manager'])
def manager_tasks(request):
    """Список задач, созданных текущим руководителем."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # задачи, созданные этим менеджером и относящиеся к его проектам
    tasks = ProjectTask.objects.filter(created_by=employee, project__manager=employee).select_related('project', 'assigned_to')

    # подготовка списка задач с дополнительными полями
    tasks_data = []
    for task in tasks:
        status_class = task.status.replace(' ', '_').lower() if task.status else ''
        is_completed = task.status and 'завершена' in task.status.lower()
        tasks_data.append({
            'task': task,
            'is_overdue': task.due_date and task.due_date < timezone.now().date() and not is_completed,
            'status_class': status_class,
            'is_completed': is_completed,
        })

    context = {
        'tasks_data': tasks_data,
        'manager_new_chat_count': ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count(),
    }
    return render(request, 'manager/tasks/list.html', context)


@role_required(['project_manager'])
def manager_task_detail(request, task_id):
    """Детальная страница задачи для менеджера с возможностью управления и загрузки файлов."""
    manager_employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not manager_employee:
        return redirect('access_denied')

    task = get_object_or_404(ProjectTask, id=task_id, project__manager=manager_employee)

    # связанные файлы
    attachments = task.attachments.all()

    if request.method == 'POST':
        # обработка загрузки файла
        if 'attachment' in request.FILES:
            TaskAttachment.objects.create(task=task, file=request.FILES['attachment'])
        action = request.POST.get('action')
        if action == 'close_task':
            task.status = 'завершена'
        elif action == 'take_review':
            task.status = 'на проверке'
        elif action == 'pause_task':
            # если на проверке, вернуть в работу; иначе отложить
            if task.status == 'на проверке':
                task.status = 'в работе'
            else:
                task.status = 'отложена'
        elif action == 'open_task':
            task.status = 'в работе'
            new_due = request.POST.get('new_due_date')
            if new_due:
                task.due_date = new_due
        if action in ['close_task', 'take_review', 'pause_task', 'open_task']:
            task.save()
        return redirect('manager_task_detail', task_id=task_id)

    context = {
        'task': task,
        'attachments': attachments,
        'is_manager': True,
        'manager_new_chat_count': ProjectChatMessageNotification.objects.filter(employee=manager_employee, seen=False).count(),
    }
    return render(request, 'manager/tasks/detail.html', context)


@role_required(['project_manager'])
def manager_create_task(request, project_id):
    """Создание новой задачи в проекте."""
    # Получаем объект Employee для текущего пользователя
    manager_employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not manager_employee:
        return redirect('access_denied')

    # Получаем проект и проверяем, что он принадлежит текущему менеджеру
    project = get_object_or_404(Project, id=project_id, manager=manager_employee)

    # Получаем сотрудников, назначенных на этот проект
    project_employees = ProjectParticipant.objects.filter(project=project).values_list('employee_id', flat=True)
    
    # Получаем активных сотрудников проекта
    available_employees = Employee.objects.filter(
        id__in=project_employees, 
        is_active=True
    )

    if request.method == 'POST':
        form = ProjectTaskForm(request.POST)
        # Переопределяем queryset для поля assigned_to
        form.fields['assigned_to'].queryset = available_employees
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Создаём задачу
                    task = ProjectTask.objects.create(
                        project=project,
                        name=form.cleaned_data['name'],
                        description=form.cleaned_data.get('description', ''),
                        assigned_to=form.cleaned_data['assigned_to'],
                        due_date=form.cleaned_data.get('due_date'),
                        priority=form.cleaned_data.get('priority', 'средний'),
                        status=form.cleaned_data.get('status', 'в работе'),
                        created_by=manager_employee,
                        created_at=timezone.now()
                    )

                    # Создаём уведомление для сотрудника, которому назначена задача
                    EmployeeTaskAssignmentNotification.objects.create(
                        employee=task.assigned_to,
                        task=task,
                        project=project,
                        seen=False,
                        created_at=timezone.now()
                    )

                # Возвращаем успешный ответ
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'message': f'Задача "{task.name}" успешно создана и назначена {task.assigned_to.first_name} {task.assigned_to.last_name}'
                    })
                else:
                    return redirect('manager_project_detail', pk=project_id)
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': f'Ошибка при создании задачи: {str(e)}'}, status=400)
                else:
                    return render(request, 'manager/tasks/create.html', {
                        'form': form,
                        'project': project,
                        'available_employees': available_employees,
                        'error': str(e)
                    })
    else:
        form = ProjectTaskForm()
        # Фильтруем queryset формы только для сотрудников проекта
        form.fields['assigned_to'].queryset = available_employees

    context = {
        'form': form,
        'project': project,
        'available_employees': available_employees,
    }

    return render(request, 'manager/tasks/create.html', context)
