from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from core.decorators import role_required
from core.models import (
    Employee, Project, ProjectChatMessage, ProjectChatAttachment,
    ProjectChatMessageNotification, ProjectParticipant
)


@role_required(['project_manager'])
def manager_project_chat(request, pk):
    """Открытие чата проекта для менеджера."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Получаем проект и проверяем, что менеджер - создатель проекта
    project = get_object_or_404(Project, id=pk, manager=employee)

    # Получаем все сообщения
    messages = ProjectChatMessage.objects.filter(project=project).select_related('author').prefetch_related('attachments')

    # Отмечаем уведомления как просмотренные
    ProjectChatMessageNotification.objects.filter(
        project=project,
        employee=employee,
        seen=False
    ).update(seen=True)

    # Получаем участников проекта
    participants = ProjectParticipant.objects.filter(project=project).select_related('employee')

    context = {
        'project': project,
        'messages': messages,
        'participants': participants,
        'current_user': employee,
    }

    return render(request, 'manager/projects/chat.html', context)


@role_required(['project_manager'])
@require_http_methods(["POST"])
def manager_project_chat_send(request, pk):
    """Отправка сообщения в чат проекта (менеджер)."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    project = get_object_or_404(Project, id=pk, manager=employee)

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

            # Создаем уведомления для всех участников
            participants = ProjectParticipant.objects.filter(project=project).exclude(employee=employee)
            for participant in participants:
                ProjectChatMessageNotification.objects.create(
                    project=project,
                    employee=participant.employee,
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


@role_required(['project_manager'])
@require_http_methods(["POST"])
def manager_delete_chat_message(request, pk, message_id):
    """Удаление сообщения из чата (менеджер)."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    project = get_object_or_404(Project, id=pk, manager=employee)
    message = get_object_or_404(ProjectChatMessage, id=message_id, project=project, author=employee)

    try:
        message.delete()
        return JsonResponse({'success': True, 'message': 'Сообщение удалено'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@role_required(['project_manager'])
@require_http_methods(["POST"])
def manager_edit_chat_message(request, pk, message_id):
    """Редактирование сообщения в чате (менеджер)."""
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'}, status=400)

    project = get_object_or_404(Project, id=pk, manager=employee)
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
