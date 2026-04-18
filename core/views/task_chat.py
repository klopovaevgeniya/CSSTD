from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.decorators import role_required
from core.models import (
    Employee,
    ProjectTask,
    TaskChatAttachment,
    TaskChatMessage,
    TaskChatMessageNotification,
)


def _is_task_participant(task, employee):
    if task.project and task.project.manager_id == employee.id:
        return True
    return task.task_assignees.filter(employee=employee).exists()


@role_required(['project_manager', 'employee'])
def task_chat_view(request, task_id):
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    task = get_object_or_404(
        ProjectTask.objects.select_related('project', 'project__manager').prefetch_related(
            'task_assignees__employee',
            'chat_messages__attachments',
            'chat_messages__author',
        ),
        id=task_id,
    )

    if not _is_task_participant(task, employee):
        return redirect('access_denied')

    messages = TaskChatMessage.objects.filter(task=task).select_related('author').prefetch_related('attachments')
    participants = [step.employee for step in task.get_chain_steps()]
    if task.project and task.project.manager and task.project.manager.id not in [p.id for p in participants]:
        participants.append(task.project.manager)

    TaskChatMessageNotification.objects.filter(
        task=task,
        employee=employee,
        seen=False
    ).update(seen=True)

    template = 'manager/tasks/chat.html' if request.session.get('role') == 'project_manager' else 'employee/task_chat.html'
    back_url_name = 'manager_task_detail' if request.session.get('role') == 'project_manager' else 'employee_task_detail'

    return render(request, template, {
        'task': task,
        'messages': messages,
        'participants': participants,
        'current_user': employee,
        'back_url_name': back_url_name,
    })


@role_required(['project_manager', 'employee'])
@require_http_methods(["POST"])
def task_chat_send(request, task_id):
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    task = get_object_or_404(ProjectTask, id=task_id)
    if not _is_task_participant(task, employee):
        return JsonResponse({'success': False, 'message': 'Нет доступа к чату задачи'}, status=403)

    text = request.POST.get('text', '').strip()
    if not text and not request.FILES:
        return JsonResponse({'success': False, 'message': 'Сообщение не может быть пустым'}, status=400)

    with transaction.atomic():
        message = TaskChatMessage.objects.create(task=task, author=employee, text=text)
        for uploaded_file in request.FILES.getlist('attachments'):
            TaskChatAttachment.objects.create(message=message, file=uploaded_file, filename=uploaded_file.name)

        recipient_ids = set(
            task.task_assignees.exclude(employee=employee).values_list('employee_id', flat=True)
        )
        if task.project and task.project.manager_id and task.project.manager_id != employee.id:
            recipient_ids.add(task.project.manager_id)

        if recipient_ids:
            TaskChatMessageNotification.objects.bulk_create(
                [
                    TaskChatMessageNotification(
                        task=task,
                        employee_id=recipient_id,
                        message=message,
                        seen=False,
                    )
                    for recipient_id in recipient_ids
                ],
                ignore_conflicts=True,
            )

    return JsonResponse({'success': True, 'message_id': message.id})
