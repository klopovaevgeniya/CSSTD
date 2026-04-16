from django.shortcuts import render, redirect, get_object_or_404
import os
from core.decorators import role_required
from core.models import (
    Employee, Project, ManagerProjectNotification, 
    ProjectParticipant, EmployeeProjectAssignmentNotification,
    ProjectChatMessageNotification, ProjectTask, EmployeeTaskAssignmentNotification, TaskAttachment, TaskAssignee, User
)
from core.forms import ProjectTaskForm
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from datetime import datetime


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
    selected_tab = request.GET.get('tab', 'info')
    if selected_tab not in {'info', 'tasks'}:
        selected_tab = 'info'

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

    # Подготовка задач проекта и фильтров
    task_search = (request.GET.get('task_search') or '').strip()
    task_status = (request.GET.get('task_status') or '').strip()
    task_priority = (request.GET.get('task_priority') or '').strip()
    task_assignee = (request.GET.get('task_assignee') or '').strip()
    task_due_date = (request.GET.get('task_due_date') or '').strip()

    tasks_base_qs = ProjectTask.objects.filter(project=project).select_related(
        'assigned_to', 'project'
    ).prefetch_related('task_assignees__employee')
    tasks_qs = tasks_base_qs.order_by('due_date', '-created_at')

    if task_search:
        tasks_qs = tasks_qs.filter(
            Q(name__icontains=task_search)
            | Q(description__icontains=task_search)
            | Q(assigned_to__first_name__icontains=task_search)
            | Q(assigned_to__last_name__icontains=task_search)
            | Q(assigned_to__middle_name__icontains=task_search)
            | Q(task_assignees__employee__first_name__icontains=task_search)
            | Q(task_assignees__employee__last_name__icontains=task_search)
            | Q(task_assignees__employee__middle_name__icontains=task_search)
        )
    if task_status:
        tasks_qs = tasks_qs.filter(status=task_status)
    if task_priority:
        tasks_qs = tasks_qs.filter(priority=task_priority)
    if task_assignee:
        tasks_qs = tasks_qs.filter(
            Q(assigned_to_id=task_assignee) | Q(task_assignees__employee_id=task_assignee)
        )

    today = timezone.localdate()
    if task_due_date:
        try:
            selected_due_date = datetime.strptime(task_due_date, '%Y-%m-%d').date()
            tasks_qs = tasks_qs.filter(due_date=selected_due_date)
        except ValueError:
            task_due_date = ''

    tasks_data = []
    for task in tasks_qs.distinct():
        status_value = task.status or ''
        status_class = status_value.replace(' ', '_').lower()
        is_completed = 'заверш' in status_value.lower()
        active_step = task.get_active_step()
        tasks_data.append({
            'task': task,
            'is_overdue': bool(task.due_date and task.due_date < today and not is_completed),
            'status_class': status_class,
            'is_completed': is_completed,
            'assignees': task.get_assignees(),
            'assignees_display': task.get_assignees_display(),
            'active_step': active_step,
        })

    task_status_options = list(
        tasks_base_qs.exclude(status__isnull=True)
        .exclude(status='')
        .values_list('status', flat=True)
        .distinct()
    )
    task_priority_options = list(
        tasks_base_qs.exclude(priority__isnull=True)
        .exclude(priority='')
        .values_list('priority', flat=True)
        .distinct()
    )
    task_assignee_options = Employee.objects.filter(
        Q(id__in=tasks_base_qs.exclude(assigned_to__isnull=True).values_list('assigned_to_id', flat=True).distinct())
        | Q(id__in=TaskAssignee.objects.filter(task__project=project).values_list('employee_id', flat=True).distinct())
    ).distinct().order_by('last_name', 'first_name')

    total_tasks_count = tasks_base_qs.count()
    completed_tasks_count = tasks_base_qs.filter(status__icontains='заверш').count()
    overdue_tasks_count = tasks_base_qs.filter(due_date__lt=today).exclude(status__icontains='заверш').count()

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
        'selected_tab': selected_tab,
        'tasks_data': tasks_data,
        'task_status_options': task_status_options,
        'task_priority_options': task_priority_options,
        'task_assignee_options': task_assignee_options,
        'task_search': task_search,
        'task_status': task_status,
        'task_priority': task_priority,
        'task_assignee': task_assignee,
        'task_due_date': task_due_date,
        'total_tasks_count': total_tasks_count,
        'completed_tasks_count': completed_tasks_count,
        'overdue_tasks_count': overdue_tasks_count,
    }

    return render(request, 'manager/projects/detail.html', context)


@role_required(['project_manager'])
def manager_tasks(request):
    """Список задач, созданных текущим руководителем."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # задачи, созданные этим менеджером и относящиеся к его проектам
    tasks = ProjectTask.objects.filter(created_by=employee, project__manager=employee).select_related(
        'project', 'assigned_to'
    ).prefetch_related('task_assignees__employee')

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
            'assignees_display': task.get_assignees_display(),
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

    task = get_object_or_404(
        ProjectTask.objects.select_related('assigned_to', 'project').prefetch_related('task_assignees__employee'),
        id=task_id,
        project__manager=manager_employee
    )
    chain_steps = list(task.get_chain_steps())
    active_step = task.get_active_step()

    # связанные файлы
    attachments = task.attachments.all().order_by('-uploaded_at')

    def build_attachments_data(items):
        image_ext = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
        result = []
        for attachment in items:
            filename = os.path.basename(attachment.file.name or '')
            ext = os.path.splitext(filename.lower())[1]
            if ext in image_ext:
                preview_type = 'image'
            elif ext == '.pdf':
                preview_type = 'pdf'
            else:
                preview_type = 'file'

            result.append({
                'obj': attachment,
                'filename': filename,
                'preview_type': preview_type,
            })
        return result

    if request.method == 'POST':
        # обработка загрузки файла
        if 'attachment' in request.FILES:
            TaskAttachment.objects.create(
                task=task,
                file=request.FILES['attachment'],
                uploaded_by=manager_employee,
                step_order=active_step.step_order if active_step else None,
            )
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
        'attachments_data': build_attachments_data(attachments),
        'task_assignees': task.get_assignees(),
        'chain_steps': chain_steps,
        'active_step': active_step,
        'is_manager': True,
        'manager_new_chat_count': ProjectChatMessageNotification.objects.filter(employee=manager_employee, seen=False).count(),
        'back_to_project_tasks_url': f"{reverse('manager_project_detail', kwargs={'pk': task.project.id})}?tab=tasks",
    }
    return render(request, 'manager/tasks/detail.html', context)


@role_required(['project_manager'])
def manager_edit_task(request, task_id):
    """Редактирование задачи руководителем."""
    manager_employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not manager_employee:
        return redirect('access_denied')

    task = get_object_or_404(
        ProjectTask.objects.select_related('project').prefetch_related('task_assignees__employee'),
        id=task_id,
        project__manager=manager_employee
    )
    project = task.project

    project_employees = ProjectParticipant.objects.filter(project=project).values_list('employee_id', flat=True)
    available_employees = Employee.objects.filter(
        id__in=project_employees,
        is_active=True
    ).select_related('position').order_by('last_name', 'first_name')

    current_steps = list(task.get_chain_steps())
    if current_steps:
        selected_assignee_ids = [step.employee_id for step in current_steps]
    elif task.assigned_to_id:
        selected_assignee_ids = [task.assigned_to_id]
    else:
        selected_assignee_ids = []

    if request.method == 'POST':
        form = ProjectTaskForm(request.POST, request.FILES)
        form.fields['assigned_to'].queryset = available_employees

        request_selected = request.POST.getlist('assigned_to')
        selected_assignee_ids = [int(value) for value in request_selected if str(value).isdigit()]

        if form.is_valid():
            try:
                with transaction.atomic():
                    selected_assignees = list(form.cleaned_data['assigned_to'])
                    chain_order_raw = (request.POST.get('chain_order') or '').strip()
                    if chain_order_raw:
                        chain_ids = [
                            int(value) for value in chain_order_raw.split(',')
                            if value.strip().isdigit()
                        ]
                        assignee_map = {employee.id: employee for employee in selected_assignees}
                        ordered_assignees = [assignee_map[employee_id] for employee_id in chain_ids if employee_id in assignee_map]
                        missing = [employee for employee in selected_assignees if employee.id not in chain_ids]
                        selected_assignees = ordered_assignees + missing

                    primary_assignee = selected_assignees[0] if selected_assignees else None

                    task.name = form.cleaned_data['name']
                    task.description = form.cleaned_data.get('description', '')
                    task.assigned_to = primary_assignee
                    task.due_date = form.cleaned_data.get('due_date')
                    task.priority = form.cleaned_data.get('priority', 'средний')
                    task.status = form.cleaned_data.get('status', task.status or 'в работе')
                    task.updated_at = timezone.now()
                    task.save()

                    TaskAssignee.objects.filter(task=task).exclude(employee__in=selected_assignees).delete()

                    TaskAssignee.objects.filter(task=task).update(
                        step_status=TaskAssignee.STEP_STATUS_PENDING,
                        started_at=None,
                        completed_at=None
                    )

                    for index, assignee in enumerate(selected_assignees, start=1):
                        TaskAssignee.objects.update_or_create(
                            task=task,
                            employee=assignee,
                            defaults={
                                'step_order': index,
                                'step_status': TaskAssignee.STEP_STATUS_ACTIVE if index == 1 else TaskAssignee.STEP_STATUS_PENDING,
                                'started_at': timezone.now() if index == 1 else None,
                                'completed_at': None,
                            }
                        )

                    if primary_assignee:
                        EmployeeTaskAssignmentNotification.objects.get_or_create(
                            employee=primary_assignee,
                            task=task,
                            defaults={
                                'project': project,
                                'seen': False,
                                'created_at': timezone.now(),
                            }
                        )

                return redirect('manager_task_detail', task_id=task.id)
            except Exception as e:
                return render(request, 'manager/tasks/create.html', {
                    'form': form,
                    'task': task,
                    'project': project,
                    'available_employees': available_employees,
                    'selected_assignee_ids': selected_assignee_ids,
                    'chain_order_initial': ','.join(str(id_value) for id_value in selected_assignee_ids),
                    'error': str(e),
                })
    else:
        initial = {
            'name': task.name,
            'description': task.description,
            'assigned_to': selected_assignee_ids,
            'due_date': task.due_date,
            'priority': task.priority,
            'status': task.status,
        }
        form = ProjectTaskForm(initial=initial)
        form.fields['assigned_to'].queryset = available_employees

    context = {
        'form': form,
        'task': task,
        'project': project,
        'available_employees': available_employees,
        'selected_assignee_ids': selected_assignee_ids,
        'chain_order_initial': ','.join(str(step.employee_id) for step in current_steps) if current_steps else ','.join(str(id_value) for id_value in selected_assignee_ids),
    }
    return render(request, 'manager/tasks/create.html', context)


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
    ).select_related('position').order_by('last_name', 'first_name')

    if request.method == 'POST':
        form = ProjectTaskForm(request.POST, request.FILES)
        # Переопределяем queryset для поля assigned_to (множественный выбор)
        form.fields['assigned_to'].queryset = available_employees
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    selected_assignees = list(form.cleaned_data['assigned_to'])
                    chain_order_raw = (request.POST.get('chain_order') or '').strip()
                    if chain_order_raw:
                        chain_ids = [
                            int(value) for value in chain_order_raw.split(',')
                            if value.strip().isdigit()
                        ]
                        assignee_map = {employee.id: employee for employee in selected_assignees}
                        ordered_assignees = [assignee_map[employee_id] for employee_id in chain_ids if employee_id in assignee_map]
                        missing = [employee for employee in selected_assignees if employee.id not in chain_ids]
                        selected_assignees = ordered_assignees + missing

                    primary_assignee = selected_assignees[0] if selected_assignees else None

                    # Создаём задачу
                    task = ProjectTask.objects.create(
                        project=project,
                        name=form.cleaned_data['name'],
                        description=form.cleaned_data.get('description', ''),
                        assigned_to=primary_assignee,
                        due_date=form.cleaned_data.get('due_date'),
                        priority=form.cleaned_data.get('priority', 'средний'),
                        status=form.cleaned_data.get('status', 'в работе'),
                        created_by=manager_employee,
                        created_at=timezone.now()
                    )

                    # Привязываем всех исполнителей к задаче
                    for index, assignee in enumerate(selected_assignees, start=1):
                        TaskAssignee.objects.update_or_create(
                            task=task,
                            employee=assignee,
                            defaults={
                                'step_order': index,
                                'step_status': TaskAssignee.STEP_STATUS_ACTIVE if index == 1 else TaskAssignee.STEP_STATUS_PENDING,
                                'started_at': timezone.now() if index == 1 else None,
                                'completed_at': None,
                            }
                        )

                    # Создаём уведомления для всех назначенных сотрудников
                    if selected_assignees:
                        assignee = selected_assignees[0]
                        EmployeeTaskAssignmentNotification.objects.get_or_create(
                            employee=assignee,
                            task=task,
                            defaults={
                                'project': project,
                                'seen': False,
                                'created_at': timezone.now(),
                            }
                        )

                    # Сохраняем вложения, если они были загружены
                    for uploaded_file in request.FILES.getlist('attachments'):
                        TaskAttachment.objects.create(
                            task=task,
                            file=uploaded_file,
                            uploaded_by=manager_employee,
                            step_order=1 if selected_assignees else None,
                        )

                # Возвращаем успешный ответ
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'message': f'Задача "{task.name}" создана. Цепочка: {" -> ".join(f"{emp.first_name} {emp.last_name}" for emp in selected_assignees)}'
                    })
                else:
                    return redirect(f"{reverse('manager_project_detail', kwargs={'pk': project_id})}?tab=tasks")
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': f'Ошибка при создании задачи: {str(e)}'}, status=400)
                else:
                    return render(request, 'manager/tasks/create.html', {
                        'form': form,
                        'project': project,
                        'available_employees': available_employees,
                        'selected_assignee_ids': [int(value) for value in request.POST.getlist('assigned_to') if str(value).isdigit()],
                        'chain_order_initial': request.POST.get('chain_order', ''),
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
        'selected_assignee_ids': [int(value) for value in request.POST.getlist('assigned_to') if str(value).isdigit()] if request.method == 'POST' else [],
        'chain_order_initial': request.POST.get('chain_order', '') if request.method == 'POST' else '',
    }

    return render(request, 'manager/tasks/create.html', context)
