from django.shortcuts import redirect, render

from core.decorators import role_required
from core.models import (
    Employee,
    ManagerProjectNotification,
    ProjectChatMessageNotification,
    ProjectClosureRequest,
    ProjectExpenseRequest,
    TaskChatMessageNotification,
)


@role_required(['project_manager'])
def manager_notifications(request):
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()
        if action in {'mark_all_read', 'mark_projects_read'}:
            ManagerProjectNotification.objects.filter(manager=employee, seen=False).update(seen=True)
        if action in {'mark_all_read', 'mark_project_chat_read'}:
            ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).update(seen=True)
        if action in {'mark_all_read', 'mark_task_chat_read'}:
            TaskChatMessageNotification.objects.filter(employee=employee, seen=False).update(seen=True)
        if action in {'mark_all_read', 'mark_closure_feedback_read'}:
            ProjectClosureRequest.objects.filter(
                project__manager=employee,
                status__in=[ProjectClosureRequest.STATUS_APPROVED, ProjectClosureRequest.STATUS_REJECTED],
                seen_by_manager=False
            ).update(seen_by_manager=True)
        return redirect('manager_notifications')

    new_projects = ManagerProjectNotification.objects.filter(
        manager=employee,
        seen=False
    ).select_related('project').order_by('-created_at')
    unread_project_chat = ProjectChatMessageNotification.objects.filter(
        employee=employee,
        seen=False
    ).select_related('project', 'message', 'message__author').order_by('-created_at')
    unread_task_chat = TaskChatMessageNotification.objects.filter(
        employee=employee,
        seen=False
    ).select_related('task', 'task__project', 'message', 'message__author').order_by('-created_at')
    pending_expenses = ProjectExpenseRequest.objects.filter(
        project__manager=employee,
        status=ProjectExpenseRequest.STATUS_PENDING_MANAGER
    ).select_related('project', 'requested_by').order_by('-created_at')
    closure_feedback = ProjectClosureRequest.objects.filter(
        project__manager=employee,
        status__in=[ProjectClosureRequest.STATUS_APPROVED, ProjectClosureRequest.STATUS_REJECTED],
        seen_by_manager=False
    ).select_related('project').order_by('-updated_at')

    return render(request, 'manager/notifications.html', {
        'new_projects': new_projects,
        'unread_project_chat': unread_project_chat,
        'unread_task_chat': unread_task_chat,
        'pending_expenses': pending_expenses,
        'closure_feedback': closure_feedback,
        'total_new_count': (
            new_projects.count()
            + unread_project_chat.count()
            + unread_task_chat.count()
            + pending_expenses.count()
            + closure_feedback.count()
        ),
    })
