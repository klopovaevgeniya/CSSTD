import logging

logger = logging.getLogger(__name__)

# Summary: Файл `core/context_processors.py`: содержит код и настройки для раздела "context processors".
from core.models import (
    Employee,
    EmployeeProjectAssignmentNotification,
    EmployeeTaskAssignmentNotification,
    ManagerProjectNotification,
    ProjectChatMessageNotification,
    ProjectClosureRequest,
    ProjectExpenseRequest,
    TaskChatMessageNotification,
)
from django.contrib.auth.models import User


# Summary: Обрабатывает сценарий manager notifications.
def manager_notifications(request):
    """Глобальные счетчики уведомлений для всех ролей интерфейса."""
    base = {
        'manager_new_projects_count': 0,
        'manager_new_chat_count': 0,
        'manager_new_project_chat_count': 0,
        'manager_new_task_chat_count': 0,
        'manager_new_expense_requests_count': 0,
        'manager_new_closure_feedback_count': 0,
        'manager_total_notifications': 0,
        'new_assignment_notifications': 0,
        'new_task_notifications': 0,
        'employee_new_chat_count': 0,
        'employee_new_project_chat_count': 0,
        'employee_new_task_chat_count': 0,
        'employee_total_notifications': 0,
        'admin_pending_expense_requests_count': 0,
        'admin_pending_closure_requests_count': 0,
    }

    role = request.session.get('role')
    user_id = request.session.get('user_id')

    if role == 'admin':
        try:
            base['admin_pending_expense_requests_count'] = ProjectExpenseRequest.objects.filter(
                status=ProjectExpenseRequest.STATUS_NEEDS_ADMIN_REVIEW
            ).count()
            base['admin_pending_closure_requests_count'] = ProjectClosureRequest.objects.filter(
                status=ProjectClosureRequest.STATUS_PENDING
            ).count()
        except Exception:
            base['admin_pending_expense_requests_count'] = 0
            base['admin_pending_closure_requests_count'] = 0
        return base

    if role not in {'project_manager', 'employee'} or not user_id:
        return base

    employee = None
    try:
        user = User.objects.filter(id=user_id).first()
        if user:
            employee = Employee.objects.filter(employee_user_id=user.id).first()
            if not employee and user.email:
                employee = Employee.objects.filter(email__iexact=user.email).first()
        if not employee and request.session.get('employee_id'):
            employee = Employee.objects.filter(id=request.session.get('employee_id')).first()
    except Exception:
        employee = None

    if not employee:
        return base

    try:
        if role == 'project_manager':
            new_projects_count = ManagerProjectNotification.objects.filter(manager=employee, seen=False).count()
            new_project_chat_count = ProjectChatMessageNotification.objects.filter(employee=employee, seen=False).count()
            new_task_chat_count = TaskChatMessageNotification.objects.filter(employee=employee, seen=False).count()
            new_expense_count = ProjectExpenseRequest.objects.filter(
                project__manager=employee,
                status=ProjectExpenseRequest.STATUS_PENDING_MANAGER
            ).count()
            manager_closure_feedback_count = ProjectClosureRequest.objects.filter(
                project__manager=employee,
                status__in=[ProjectClosureRequest.STATUS_APPROVED, ProjectClosureRequest.STATUS_REJECTED],
                seen_by_manager=False
            ).count()

            base['manager_new_projects_count'] = new_projects_count
            base['manager_new_project_chat_count'] = new_project_chat_count
            base['manager_new_task_chat_count'] = new_task_chat_count
            base['manager_new_chat_count'] = new_project_chat_count + new_task_chat_count
            base['manager_new_expense_requests_count'] = new_expense_count
            base['manager_new_closure_feedback_count'] = manager_closure_feedback_count
            base['manager_total_notifications'] = (
                new_projects_count
                + new_project_chat_count
                + new_task_chat_count
                + new_expense_count
                + manager_closure_feedback_count
            )
            return base

        if role == 'employee':
            new_assignments_count = EmployeeProjectAssignmentNotification.objects.filter(
                employee=employee,
                seen=False
            ).count()
            new_tasks_count = EmployeeTaskAssignmentNotification.objects.filter(
                employee=employee,
                seen=False
            ).count()
            new_project_chat_count = ProjectChatMessageNotification.objects.filter(
                employee=employee,
                seen=False
            ).count()
            new_task_chat_count = TaskChatMessageNotification.objects.filter(
                employee=employee,
                seen=False
            ).count()

            base['new_assignment_notifications'] = new_assignments_count
            base['new_task_notifications'] = new_tasks_count
            base['employee_new_project_chat_count'] = new_project_chat_count
            base['employee_new_task_chat_count'] = new_task_chat_count
            base['employee_new_chat_count'] = new_project_chat_count + new_task_chat_count
            base['employee_total_notifications'] = (
                new_assignments_count
                + new_tasks_count
                + new_project_chat_count
                + new_task_chat_count
            )
            return base
    except Exception:
        return base

    return base
