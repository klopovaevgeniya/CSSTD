from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from ..forms import LoginForm
from ..services.auth_service import authenticate
from ..models import Employee

import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для login view.
def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            form.cleaned_data['username'],
            form.cleaned_data['password']
        )

        if user:
            request.session['user_id'] = user['id']
            request.session['role'] = user['role']

            # Проверяем, нужно ли менять пароль
            if user.get('force_password_change', False):
                return redirect('change_password')

            role_redirects = {
                'admin': 'admin_dashboard',
                'project_manager': 'manager_dashboard',
                'employee': 'employee_dashboard',
                'readonly': 'readonly_dashboard',
            }

            return redirect(role_redirects.get(user['role'], 'home'))

        form.add_error(None, 'Неверный логин или пароль')

    return render(request, 'auth/login.html', {'form': form})


# Summary: Содержит логику для logout view.
def logout_view(request):
    request.session.flush()
    return redirect('home')


# Summary: Содержит логику для change password view.
def change_password_view(request):
    """Страница принудительной смены пароля для новых сотрудников."""
    # Очищаем все старые сообщения из предыдущих операций
    list(messages.get_messages(request))
    
    # Получаем сотрудника
    employee = Employee.objects.filter(employee_user_id=request.session.get('user_id')).first()
    if not employee:
        return redirect('access_denied')

    # Если пароль уже изменен, перенаправляем на dashboard
    if not employee.force_password_change:
        role_redirects = {
            'admin': 'admin_dashboard',
            'project_manager': 'manager_dashboard',
            'employee': 'employee_dashboard',
            'readonly': 'readonly_dashboard',
        }
        return redirect(role_redirects.get(request.session.get('role'), 'home'))

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            messages.error(request, 'Все поля обязательны для заполнения.')
        elif new_password != confirm_password:
            messages.error(request, 'Новые пароли не совпадают.')
        elif len(new_password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов.')
        else:
            # Обновляем пароль пользователя
            user = employee.employee_user
            user.password = make_password(new_password)
            user.save()

            # Устанавливаем флаг, что пароль изменен
            employee.force_password_change = False
            employee.save()

            messages.success(request, 'Пароль успешно изменен!')

            # Перенаправляем на соответствующий dashboard
            role_redirects = {
                'admin': 'admin_dashboard',
                'project_manager': 'manager_dashboard',
                'employee': 'employee_dashboard',
                'readonly': 'readonly_dashboard',
            }
            return redirect(role_redirects.get(request.session.get('role'), 'home'))

    return render(request, 'auth/change_password.html')