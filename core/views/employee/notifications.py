import logging

logger = logging.getLogger(__name__)

# Summary: Файл `core/views/employee/notifications.py`: содержит код и настройки для раздела "notifications".
from django.shortcuts import redirect, render

from core.decorators import role_required
from core.models import (
    Employee,
    EmployeeProjectAssignmentNotification,
    EmployeeTaskAssignmentNotification,
    ProjectChatMessageNotification,
    ProjectExpenseRequest,
    TaskChatMessageNotification,
)


# Summary: Обрабатывает сценарий employee notifications.
@role_required(['employee'])
def employee_notifications(request):
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()
        if action in {'mark_all_read', 'mark_project_assignments_read'}:
            EmployeeProjectAssignmentNotification.objects.filter(employee=employee, seen=False).update(seen=True)
        if action in {'mark_all_read', 'mark_task_assignments_read'}:
            EmployeeTaskAssignmentNotification.objects.filter(employee=employee, seen=False).update(seen=True)
        if action in {'mark_all_read', 'mark_project_chat_read'}:
            ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).update(seen=True)
        if action in {'mark_all_read', 'mark_task_chat_read'}:
            TaskChatMessageNotification.objects.filter(employee=employee, seen=False).update(seen=True)
        return redirect('employee_notifications')

    project_assignments = EmployeeProjectAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    ).select_related('project').order_by('-created_at')
    task_assignments = EmployeeTaskAssignmentNotification.objects.filter(
        employee=employee,
        seen=False
    ).select_related('project', 'task').order_by('-created_at')
    unread_project_chat = ProjectChatMessageNotification.objects.filter(
        employee=employee,
        seen=False
    ).select_related('project', 'message', 'message__author').order_by('-created_at')
    unread_task_chat = TaskChatMessageNotification.objects.filter(
        employee=employee,
        seen=False
    ).select_related('task', 'task__project', 'message', 'message__author').order_by('-created_at')
    recent_expense_status_updates = ProjectExpenseRequest.objects.filter(
        requested_by=employee
    ).exclude(
        status=ProjectExpenseRequest.STATUS_PENDING_MANAGER
    ).select_related('project').order_by('-updated_at')[:10]

    return render(request, 'employee/notifications.html', {
        'project_assignments': project_assignments,
        'task_assignments': task_assignments,
        'unread_project_chat': unread_project_chat,
        'unread_task_chat': unread_task_chat,
        'recent_expense_status_updates': recent_expense_status_updates,
        'total_new_count': (
            project_assignments.count()
            + task_assignments.count()
            + unread_project_chat.count()
            + unread_task_chat.count()
        ),
    })

