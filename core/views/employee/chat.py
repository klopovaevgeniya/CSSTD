from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from core.decorators import role_required
from core.models import (
    Employee, Project, ProjectChatMessage, ProjectChatAttachment,
    ProjectChatMessageNotification, ProjectParticipant
)


@role_required(['employee'])
def employee_project_chat(request, pk):
    """Открытие чата проекта для сотрудника."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Проверяем, что сотрудник назначен на этот проект
    project = get_object_or_404(Project, id=pk)
    participant = get_object_or_404(ProjectParticipant, project=project, employee=employee)

    # Получаем все сообщения
    messages = ProjectChatMessage.objects.filter(project=project).select_related('author').prefetch_related('attachments')

    # Отмечаем уведомления как просмотренные
    ProjectChatMessageNotification.objects.filter(
        project=project,
        employee=employee,
        seen=False
    ).update(seen=True)

    # Получаем всех участников проекта
    participants = ProjectParticipant.objects.filter(project=project).select_related('employee')

    context = {
        'project': project,
        'messages': messages,
        'participants': participants,
        'current_user': employee,
    }

    return render(request, 'employee/project_chat.html', context)


@role_required(['employee'])
@require_http_methods(["POST"])
def employee_project_chat_send(request, pk):
    """Отправка сообщения в чат проекта (сотрудник)."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    project = get_object_or_404(Project, id=pk)
    
    # Проверяем, что сотрудник назначен на проект
    participant = get_object_or_404(ProjectParticipant, project=project, employee=employee)

    text = request.POST.get('text', '').strip()
    if not text and not request.FILES:
        return JsonResponse({'success': False, 'message': 'Сообщение не может быть пустым'}, status=400)

    try:
        with transaction.atomic():
            # Создаем сообщение
            message = ProjectChatMessage.objects.create(
                project=project,
                author=employee,
                text=text
            )

            # Обрабатываем прикрепленные файлы
            for file in request.FILES.getlist('attachments'):
                ProjectChatAttachment.objects.create(
                    message=message,
                    file=file,
                    filename=file.name
                )

            # Создаем уведомления для менеджера проекта
            if project.manager and project.manager != employee:
                ProjectChatMessageNotification.objects.create(
                    project=project,
                    employee=project.manager,
                    message=message,
                    seen=False
                )

            # Создаем уведомления для других участников
            participants = ProjectParticipant.objects.filter(project=project).exclude(employee=employee)
            for part in participants:
                ProjectChatMessageNotification.objects.create(
                    project=project,
                    employee=part.employee,
                    message=message,
                    seen=False
                )

        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'message': 'Сообщение отправлено успешно'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@role_required(['employee'])
@require_http_methods(["POST"])
def employee_delete_chat_message(request, pk, message_id):
    """Удаление сообщения из чата (сотрудник)."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    project = get_object_or_404(Project, id=pk)
    get_object_or_404(ProjectParticipant, project=project, employee=employee)
    
    message = get_object_or_404(ProjectChatMessage, id=message_id, project=project, author=employee)

    try:
        message.delete()
        return JsonResponse({'success': True, 'message': 'Сообщение удалено'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@role_required(['employee'])
@require_http_methods(["POST"])
def employee_edit_chat_message(request, pk, message_id):
    """Редактирование сообщения в чате (сотрудник)."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    project = get_object_or_404(Project, id=pk)
    get_object_or_404(ProjectParticipant, project=project, employee=employee)
    
    message = get_object_or_404(ProjectChatMessage, id=message_id, project=project, author=employee)

    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'success': False, 'message': 'Сообщение не может быть пустым'}, status=400)

    try:
        message.text = text
        message.save(update_fields=['text', 'updated_at'])
        return JsonResponse({'success': True, 'message': 'Сообщение отредактировано'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
