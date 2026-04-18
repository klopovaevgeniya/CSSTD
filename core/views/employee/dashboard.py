from datetime import date, datetime
import os
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import role_required
from core.models import (
    Employee,
    EmployeeProjectAssignmentNotification,
    EmployeeTaskAssignmentNotification,
    Project,
    ProjectChatMessageNotification,
    ProjectExpenseRequest,
    ProjectParticipant,
    ProjectTask,
    TaskAttachment,
    TaskChatMessageNotification,
)
from core.utils.project_archive import archived_project_q


def _employee_tasks_queryset(employee):
    return ProjectTask.objects.filter(
        Q(assigned_to=employee) | Q(task_assignees__employee=employee, task_assignees__step_status__in=['active', 'completed'])
    ).exclude(
        archived_project_q(prefix='project')
    ).select_related('project', 'created_by').prefetch_related('task_assignees__employee').distinct()


@role_required(['employee'])
def employee_dashboard(request):
    """Дашборд сотрудника с реальной информацией."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    new_assignment_notifications = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    ).count()

    new_task_notifications = EmployeeTaskAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    ).count()

    employee_new_chat_count = (
        ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()
        + TaskChatMessageNotification.objects.filter(employee=employee, seen=False).count()
    )

    my_projects = ProjectParticipant.objects.filter(
        employee=employee
    ).exclude(
        archived_project_q(prefix='project')
    ).select_related('project', 'project__status', 'project__type', 'project__manager')

    all_tasks = _employee_tasks_queryset(employee)

    active_tasks = all_tasks.exclude(status__icontains='завершена').count()
    completed_tasks = all_tasks.filter(status__icontains='завершена').count()

    total_tasks = all_tasks.count()
    progress_percent = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    overdue_tasks = all_tasks.filter(
        due_date__lte=date.today()
    ).exclude(status__icontains='завершена').count()

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
    return _employee_projects_common(request, archive_mode=False)


@role_required(['employee'])
def employee_projects_archive(request):
    return _employee_projects_common(request, archive_mode=True)


def _employee_projects_common(request, archive_mode=False):
    """Список проектов сотрудника вкладка в дашборде."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    unseen_notifications = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    )
    project_ids_with_notification = list(unseen_notifications.values_list('project_id', flat=True))

    if not archive_mode and unseen_notifications.exists():
        with transaction.atomic():
            unseen_notifications.update(seen=True)

    project_search = (request.GET.get('project_search') or '').strip()
    project_status = (request.GET.get('project_status') or '').strip()
    project_type = (request.GET.get('project_type') or '').strip()
    project_start_date = (request.GET.get('project_start_date') or '').strip()

    projects_base_qs = ProjectParticipant.objects.filter(
        employee=employee
    ).select_related('project', 'project__status', 'project__type', 'project__manager')
    if archive_mode:
        projects_base_qs = projects_base_qs.filter(archived_project_q(prefix='project'))
    else:
        projects_base_qs = projects_base_qs.exclude(archived_project_q(prefix='project'))
    projects = projects_base_qs.order_by('-project__created_at')

    if project_search:
        projects = projects.filter(
            Q(project__name__icontains=project_search)
            | Q(project__description__icontains=project_search)
            | Q(project__code__icontains=project_search)
            | Q(project__type__name__icontains=project_search)
            | Q(project__status__name__icontains=project_search)
            | Q(project__manager__first_name__icontains=project_search)
            | Q(project__manager__last_name__icontains=project_search)
        )
    if project_status:
        projects = projects.filter(project__status_id=project_status)
    if project_type:
        projects = projects.filter(project__type_id=project_type)
    if project_start_date:
        try:
            selected_start_date = datetime.strptime(project_start_date, '%Y-%m-%d').date()
            projects = projects.filter(project__start_date=selected_start_date)
        except ValueError:
            project_start_date = ''

    project_status_options = (
        projects_base_qs.exclude(project__status__isnull=True)
        .values('project__status_id', 'project__status__name')
        .distinct()
        .order_by('project__status__name')
    )
    project_type_options = (
        projects_base_qs.exclude(project__type__isnull=True)
        .values('project__type_id', 'project__type__name')
        .distinct()
        .order_by('project__type__name')
    )

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
        'archive_mode': archive_mode,
        'project_ids_with_notification': project_ids_with_notification,
        'employee_new_chat_count': (
            ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()
            + TaskChatMessageNotification.objects.filter(employee=employee, seen=False).count()
        ),
        'new_assignment_notifications': len(project_ids_with_notification),
        'new_task_notifications': EmployeeTaskAssignmentNotification.objects.filter(employee=employee, seen=False).count(),
        'project_search': project_search,
        'project_status': project_status,
        'project_type': project_type,
        'project_start_date': project_start_date,
        'project_status_options': project_status_options,
        'project_type_options': project_type_options,
    }

    return render(request, 'employee/projects.html', context)


@role_required(['employee'])
def employee_project_detail(request, pk):
    """Детальная страница проекта для сотрудника."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    project = get_object_or_404(Project, id=pk)
    is_archived = Project.objects.filter(id=project.id).filter(archived_project_q()).exists()
    participant = get_object_or_404(ProjectParticipant, project=project, employee=employee)
    selected_tab = request.GET.get('tab') or request.POST.get('tab') or 'info'
    if selected_tab not in {'info', 'tasks', 'expenses'}:
        selected_tab = 'info'

    expense_error = None
    expense_success = None
    if request.method == 'POST' and request.POST.get('action') == 'create_expense_request':
        if is_archived:
            expense_error = 'Архивный проект доступен только для просмотра.'
        else:
            title = (request.POST.get('title') or '').strip()
            amount_raw = (request.POST.get('amount') or '').strip().replace(',', '.')
            expense_date_raw = (request.POST.get('expense_date') or '').strip()
            description = (request.POST.get('description') or '').strip()

            amount_value = None
            if not title:
                expense_error = 'Укажите назначение траты.'
            elif not amount_raw:
                expense_error = 'Укажите сумму траты.'
            else:
                try:
                    amount_value = Decimal(amount_raw)
                except (InvalidOperation, ValueError):
                    expense_error = 'Введите корректную сумму.'

            expense_date_value = None
            if not expense_error:
                try:
                    expense_date_value = date.fromisoformat(expense_date_raw)
                except ValueError:
                    expense_error = 'Укажите корректную дату траты.'

            if not expense_error and amount_value is not None and amount_value <= 0:
                expense_error = 'Сумма должна быть больше нуля.'

            if (
                not expense_error
                and amount_value is not None
                and project.budget is not None
                and amount_value > project.budget
            ):
                expense_error = f'Сумма заявки не может превышать бюджет проекта ({project.budget:.2f} ₽).'

            if not expense_error:
                ProjectExpenseRequest.objects.create(
                    project=project,
                    requested_by=employee,
                    amount=amount_value,
                    expense_date=expense_date_value,
                    title=title,
                    description=description or None,
                    status=ProjectExpenseRequest.STATUS_PENDING_MANAGER,
                )
                expense_success = 'Запрос на трату отправлен руководителю.'

    task_search = (request.GET.get('task_search') or '').strip()
    task_status = (request.GET.get('task_status') or '').strip()
    task_priority = (request.GET.get('task_priority') or '').strip()
    task_due_date = (request.GET.get('task_due_date') or '').strip()

    project_tasks = ProjectTask.objects.filter(
        project=project
    ).filter(
        Q(assigned_to=employee) | Q(task_assignees__employee=employee, task_assignees__step_status__in=['active', 'completed'])
    ).select_related('project', 'created_by').prefetch_related('task_assignees__employee').distinct()
    tasks_qs = project_tasks.order_by('due_date', '-created_at')
    if task_search:
        tasks_qs = tasks_qs.filter(
            Q(name__icontains=task_search)
            | Q(description__icontains=task_search)
        )
    if task_status:
        tasks_qs = tasks_qs.filter(status=task_status)
    if task_priority:
        tasks_qs = tasks_qs.filter(priority=task_priority)

    if task_due_date:
        try:
            selected_due_date = datetime.strptime(task_due_date, '%Y-%m-%d').date()
            tasks_qs = tasks_qs.filter(due_date=selected_due_date)
        except ValueError:
            task_due_date = ''

    active_tasks = project_tasks.exclude(status__icontains='завершена')
    completed_tasks = project_tasks.filter(status__icontains='завершена')

    total_project_tasks = project_tasks.count()
    progress_percent = int((completed_tasks.count() / total_project_tasks) * 100) if total_project_tasks > 0 else 0
    overdue_tasks_count = project_tasks.filter(due_date__lt=date.today()).exclude(status__icontains='заверш').count()

    tasks_data = []
    for task in tasks_qs:
        status_value = task.status or ''
        tasks_data.append({
            'task': task,
            'status_class': status_value.replace(' ', '_').lower(),
            'is_completed': 'заверш' in status_value.lower(),
            'is_overdue': bool(task.due_date and task.due_date < date.today() and 'заверш' not in status_value.lower()),
        })

    if selected_tab == 'tasks':
        EmployeeTaskAssignmentNotification.objects.filter(
            employee=employee,
            project=project,
            seen=False
        ).update(seen=True)

    task_status_options = list(
        project_tasks.exclude(status__isnull=True).exclude(status='').values_list('status', flat=True).distinct()
    )
    task_priority_options = list(
        project_tasks.exclude(priority__isnull=True).exclude(priority='').values_list('priority', flat=True).distinct()
    )

    all_participants = ProjectParticipant.objects.filter(
        project=project
    ).select_related('employee', 'employee__position')

    my_expense_requests = ProjectExpenseRequest.objects.filter(
        project=project,
        requested_by=employee
    ).order_by('-created_at')
    approved_expense_requests_count = my_expense_requests.filter(status=ProjectExpenseRequest.STATUS_APPROVED).count()
    pending_expense_requests_count = my_expense_requests.filter(
        status__in=[ProjectExpenseRequest.STATUS_PENDING_MANAGER, ProjectExpenseRequest.STATUS_NEEDS_ADMIN_REVIEW]
    ).count()

    context = {
        'project': project,
        'participant': participant,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'total_tasks': total_project_tasks,
        'progress_percent': progress_percent,
        'selected_tab': selected_tab,
        'tasks_data': tasks_data,
        'task_status_options': task_status_options,
        'task_priority_options': task_priority_options,
        'task_search': task_search,
        'task_status': task_status,
        'task_priority': task_priority,
        'task_due_date': task_due_date,
        'total_tasks_count': total_project_tasks,
        'active_tasks_count': active_tasks.count(),
        'completed_tasks_count': completed_tasks.count(),
        'overdue_tasks_count': overdue_tasks_count,
        'all_participants': all_participants,
        'user': request.user,
        'my_expense_requests': my_expense_requests,
        'approved_expense_requests_count': approved_expense_requests_count,
        'pending_expense_requests_count': pending_expense_requests_count,
        'expense_error': expense_error,
        'expense_success': expense_success,
        'is_archived': is_archived,
        'new_task_notifications': EmployeeTaskAssignmentNotification.objects.filter(employee=employee, seen=False).count(),
    }

    return render(request, 'employee/project_detail.html', context)


@role_required(['employee'])
def employee_tasks(request):
    """Список всех задач сотрудника."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    unseen_task_notifications = EmployeeTaskAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    )
    task_ids_with_notification = list(unseen_task_notifications.values_list('task_id', flat=True))

    if unseen_task_notifications.exists():
        with transaction.atomic():
            unseen_task_notifications.update(seen=True)

    all_tasks = _employee_tasks_queryset(employee).order_by('-created_at')

    unread_task_chat_map = {
        row['task_id']: row['unread_count']
        for row in TaskChatMessageNotification.objects.filter(
            employee=employee,
            seen=False,
            task__in=all_tasks
        ).values('task_id').annotate(unread_count=Count('id'))
    }

    active_tasks = all_tasks.exclude(status__icontains='завершена')
    completed_tasks = all_tasks.filter(status__icontains='завершена')

    overdue_tasks = all_tasks.filter(
        due_date__lt=date.today()
    ).exclude(status__icontains='завершена')

    tasks_data = []
    for task in all_tasks:
        status_class = task.status.replace(' ', '_').lower() if task.status else ''

        tasks_data.append({
            'task': task,
            'is_new': task.id in task_ids_with_notification,
            'is_overdue': task.due_date and task.due_date < date.today() and task.status != 'завершена',
            'status_class': status_class,
            'unread_task_chat_messages': unread_task_chat_map.get(task.id, 0),
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

    task_queryset = ProjectTask.objects.filter(
        Q(assigned_to=employee) | Q(task_assignees__employee=employee, task_assignees__step_status__in=['active', 'completed'])
    ).select_related('project', 'created_by').prefetch_related('task_assignees__employee').distinct()
    task = get_object_or_404(task_queryset, id=task_id)
    is_project_archived = Project.objects.filter(id=task.project_id).filter(archived_project_q()).exists()
    EmployeeTaskAssignmentNotification.objects.filter(employee=employee, task=task, seen=False).update(seen=True)
    attachments = task.attachments.all().order_by('-uploaded_at')
    chain_steps = list(task.get_chain_steps())
    current_employee_step = task.task_assignees.filter(employee=employee).order_by('step_order').first()
    active_step = task.get_active_step()

    if request.method == 'POST':
        if is_project_archived:
            return redirect('employee_task_detail', task_id=task_id)
        if 'attachment' in request.FILES and current_employee_step and current_employee_step.step_status == 'active':
            TaskAttachment.objects.create(
                task=task,
                file=request.FILES['attachment'],
                uploaded_by=employee,
                step_order=current_employee_step.step_order if current_employee_step else None,
            )
        action = request.POST.get('action')
        if action == 'submit_task' and current_employee_step and current_employee_step.step_status == 'active':
            with transaction.atomic():
                current_employee_step.step_status = 'completed'
                current_employee_step.completed_at = timezone.now()
                current_employee_step.save(update_fields=['step_status', 'completed_at'])

                next_step = task.task_assignees.select_related('employee').filter(
                    step_order__gt=current_employee_step.step_order,
                    step_status='pending'
                ).order_by('step_order').first()

                if next_step:
                    next_step.step_status = 'active'
                    next_step.started_at = timezone.now()
                    next_step.save(update_fields=['step_status', 'started_at'])
                    task.assigned_to = next_step.employee
                    task.status = 'в работе'
                    task.save(update_fields=['assigned_to', 'status', 'updated_at'])

                    EmployeeTaskAssignmentNotification.objects.get_or_create(
                        employee=next_step.employee,
                        task=task,
                        defaults={
                            'project': task.project,
                            'seen': False,
                            'created_at': timezone.now(),
                        }
                    )
                else:
                    task.status = 'на проверке'
                    task.save(update_fields=['status', 'updated_at'])
        return redirect('employee_task_detail', task_id=task_id)

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

    context = {
        'task': task,
        'attachments': attachments,
        'attachments_data': build_attachments_data(attachments),
        'is_manager': False,
        'chain_steps': chain_steps,
        'current_employee_step': current_employee_step,
        'active_step': active_step,
        'today': date.today(),
        'new_task_notifications': EmployeeTaskAssignmentNotification.objects.filter(employee=employee, seen=False).count(),
        'back_to_project_tasks_url': f"/dashboard/employee/projects/{task.project.id}/?tab=tasks",
        'is_project_archived': is_project_archived,
    }
    return render(request, 'employee/task_detail.html', context)
