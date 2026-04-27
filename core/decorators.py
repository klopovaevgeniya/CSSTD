from django.shortcuts import redirect
from functools import wraps

import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для login required.
def login_required(view_func):
    # Summary: Оборачивает целевую функцию проверками доступа и выполнения.
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# Summary: Содержит логику для role required.
def role_required(allowed_roles):
    # Summary: Декорирует целевую функцию общими правилами политики доступа.
    def decorator(view_func):
        # Summary: Оборачивает целевую функцию проверками доступа и выполнения.
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if 'role' not in request.session:
                return redirect('login')

            if request.session['role'] not in allowed_roles:
                return redirect('access_denied')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Summary: Обрабатывает сценарий admin required.
def admin_required(view_func):
    # Summary: Оборачивает целевую функцию проверками доступа и выполнения.
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get("role") != "admin":
            return redirect("access_denied")
        return view_func(request, *args, **kwargs)
    return wrapper
    return wrapper