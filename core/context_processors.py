from core.models import Employee, ManagerProjectNotification
from django.contrib.auth.models import User


def manager_notifications(request):
    """Добавляет в контекст количество новых проектов у менеджера (непрочитанных уведомлений).

    Пытаемся найти Employee по связке с Django User, а при отсутствии связи — по email пользователя.
    """
    try:
        if request.session.get('role') == 'project_manager' and request.session.get('user_id'):
            user = User.objects.filter(id=request.session.get('user_id')).first()
            employee = None
            if user:
                employee = Employee.objects.filter(employee_user_id=user.id).first()
                if not employee and user.email:
                    employee = Employee.objects.filter(email__iexact=user.email).first()

            # Последняя попытка: если в сессии хранится явный employee_id
            if not employee and request.session.get('employee_id'):
                employee = Employee.objects.filter(id=request.session.get('employee_id')).first()

            if employee:
                unseen = ManagerProjectNotification.objects.filter(manager=employee, seen=False).count()
                return {'manager_new_projects_count': unseen}
    except Exception:
        pass

    return {'manager_new_projects_count': 0}
