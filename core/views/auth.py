from django.shortcuts import render, redirect
from ..forms import LoginForm
from ..services.auth_service import authenticate

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

            role_redirects = {
                'admin': 'admin_dashboard',
                'project_manager': 'manager_dashboard',
                'employee': 'employee_dashboard',
                'readonly': 'readonly_dashboard',
            }

            return redirect(role_redirects.get(user['role'], 'home'))

        form.add_error(None, 'Неверный логин или пароль')

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    request.session.flush()
    return redirect('home')