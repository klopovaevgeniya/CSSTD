from django.shortcuts import redirect
from functools import wraps

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if 'role' not in request.session:
                return redirect('login')

            if request.session['role'] not in allowed_roles:
                return redirect('access_denied')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get("role") != "admin":
            return redirect("access_denied")
        return view_func(request, *args, **kwargs)
    return wrapper
    return wrapper