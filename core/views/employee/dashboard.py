from datetime import date
import os

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import role_required
from core.models import (
    Employee,
    EmployeeProjectAssignmentNotification,
    EmployeeTaskAssignmentNotification,
    Project,
    ProjectChatMessageNotification,
    ProjectParticipant,
    ProjectTask,
    TaskAttachment,
)


def _employee_tasks_queryset(employee):
    return ProjectTask.objects.filter(
        Q(assigned_to=employee) | Q(task_assignees__employee=employee, task_assignees__step_status__in=['active', 'completed'])
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

    employee_new_chat_count = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()

    my_projects = ProjectParticipant.objects.filter(
        employee=employee
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
    """Список проектов сотрудника вкладка в дашборде."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    unseen_notifications = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    )
    project_ids_with_notification = list(unseen_notifications.values_list('project_id', flat=True))

    if unseen_notifications.exists():
        with transaction.atomic():
            unseen_notifications.update(seen=True)

    employee_chat_unseen = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False)
    if employee_chat_unseen.exists():
        with transaction.atomic():
            employee_chat_unseen.update(seen=True)

    projects = ProjectParticipant.objects.filter(
        employee=employee
    ).select_related('project', 'project__status', 'project__type', 'project__manager')

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
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    project = get_object_or_404(Project, id=pk)
    participant = get_object_or_404(ProjectParticipant, project=project, employee=employee)

    project_tasks = _employee_tasks_queryset(employee).filter(project=project)

    active_tasks = project_tasks.exclude(status__icontains='завершена')
    completed_tasks = project_tasks.filter(status__icontains='завершена')

    total_project_tasks = project_tasks.count()
    progress_percent = int((completed_tasks.count() / total_project_tasks) * 100) if total_project_tasks > 0 else 0

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

    task_queryset = ProjectTask.objects.filter(
        Q(assigned_to=employee) | Q(task_assignees__employee=employee, task_assignees__step_status__in=['active', 'completed'])
    ).select_related('project', 'created_by').prefetch_related('task_assignees__employee').distinct()
    task = get_object_or_404(task_queryset, id=task_id)
    attachments = task.attachments.all().order_by('-uploaded_at')
    chain_steps = list(task.get_chain_steps())
    current_employee_step = task.task_assignees.filter(employee=employee).order_by('step_order').first()
    active_step = task.get_active_step()

    if request.method == 'POST':
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
    }
    return render(request, 'employee/task_detail.html', context)
