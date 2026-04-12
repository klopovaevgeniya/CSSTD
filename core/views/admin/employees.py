from django.db import connection
from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import admin_required
from core.models import Employee, Position, Department, Project, ProjectParticipant, ProjectTask
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import random
import string

def transliterate(text):
    translit_dict = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    result = ''
    for char in text:
        result += translit_dict.get(char, char)
    return result

@admin_required
def employee_list(request):
    employees = Employee.objects.select_related('employee_user', 'position', 'department').order_by('last_name')
    return render(request, "admin/employees/list.html", {
        "employees": employees
    })

@admin_required
def employee_create(request):
    if request.method == "POST":
        last_name = request.POST.get("last_name")
        first_name = request.POST.get("first_name")
        middle_name = request.POST.get("middle_name")
        position_id = request.POST.get("position") or None
        department_id = request.POST.get("department") or None
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        hire_date = request.POST.get("hire_date") or None
        is_active = request.POST.get("is_active") == "true"

        if not last_name or not first_name or not email:
            messages.error(request, "Фамилия, имя и email обязательны")
        else:
            # Генерация username
            username = transliterate(last_name).lower()
            counter = 1
            original_username = username
            while True:
                # Проверка существования в User и users
                user_exists = User.objects.filter(username=username).exists()
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", [username])
                    users_count = cursor.fetchone()[0]
                if not user_exists and users_count == 0:
                    break
                username = f"{original_username}{counter}"
                counter += 1

            # Generate random password
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # Create User
            user = User.objects.create_user(username=username, email=email, password=password)

            # Create Employee
            employee = Employee.objects.create(
                employee_user=user,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                position_id=position_id,
                department_id=department_id,
                email=email,
                phone=phone,
                hire_date=hire_date,
                is_active=is_active
            )

            # Determine role based on position
            role = 'employee'
            if position_id:
                position = Position.objects.get(id=position_id)
                if position.name == "Руководитель проекта":
                    role = 'project_manager'

            # Insert into users table for authentication logging
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (id, username, password_hash, role, is_active)
                    VALUES (%s, %s, crypt(%s, gen_salt('bf')), %s, %s)
                """, [user.id, username, password, role, is_active])

            # Send email
            subject = 'Добро пожаловать в ЦСУРТ!'
            text_content = f'Добро пожаловать! Ваш логин: {username}, Ваш пароль: {password}. Легкой и успешной работы!'
            html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Добро пожаловать</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        <h2 style="color: #333;">Добро пожаловать в ЦСУРТ!</h2>
        <p>Ваши учетные данные для входа в систему:</p>
        <p><strong>Логин:</strong> {username}</p>
        <p><strong>Пароль:</strong> {password}</p>
        <p>Пожалуйста, измените пароль после первого входа.</p>
        <p>Легкой и успешной работы в нашей компании!</p>
    </div>
</body>
</html>
"""
            print(f"Created user: {username}, password: {password}, role: {role}")  # Для тестирования
            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
            msg.attach_alternative(html_content, "text/html")
            try:
                msg.send()
            except Exception as e:
                messages.warning(request, f"Сотрудник создан, но email не отправлен: {str(e)}")

            messages.success(request, "Сотрудник создан")
            return redirect("admin_employees")

    positions = Position.objects.all()
    departments = Department.objects.all()
    return render(request, "admin/employees/form.html", {
        "mode": "create",
        "positions": positions,
        "departments": departments
    })

@admin_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        last_name = request.POST.get("last_name")
        first_name = request.POST.get("first_name")
        middle_name = request.POST.get("middle_name")
        position_id = request.POST.get("position")
        department_id = request.POST.get("department")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        hire_date = request.POST.get("hire_date") or None
        is_active = request.POST.get("is_active") == "true"

        if not last_name or not first_name or not email:
            messages.error(request, "Фамилия, имя и email обязательны")
        else:
            employee.last_name = last_name
            employee.first_name = first_name
            employee.middle_name = middle_name
            employee.position_id = position_id
            employee.department_id = department_id
            employee.email = email
            employee.phone = phone
            employee.hire_date = hire_date
            employee.is_active = is_active
            employee.save()

            # Update user email and active status if changed
            if employee.employee_user:
                employee.employee_user.email = email
                employee.employee_user.is_active = is_active
                employee.employee_user.save()

                # Update role in users table based on new position
                role = 'employee'
                if position_id:
                    position = Position.objects.get(id=position_id)
                    if position.name == "Руководитель проекта":
                        role = 'project_manager'
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE users SET role = %s WHERE id = %s", [role, employee.employee_user.id])

            messages.success(request, "Сотрудник обновлен")
            return redirect("admin_employees")

    positions = Position.objects.all()
    departments = Department.objects.all()
    return render(request, "admin/employees/form.html", {
        "employee": employee,
        "mode": "edit",
        "positions": positions,
        "departments": departments
    })

@admin_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    # Проверить связи с проектами
    managed_projects = Project.objects.filter(manager=employee)
    participated_projects = ProjectParticipant.objects.filter(employee=employee).select_related('project')
    assigned_tasks = ProjectTask.objects.filter(assigned_to=employee).select_related('project')

    in_projects = managed_projects.exists() or participated_projects.exists() or assigned_tasks.exists()
    projects_list = set()
    if managed_projects:
        projects_list.update(managed_projects.values_list('name', flat=True))
    if participated_projects:
        projects_list.update(participated_projects.values_list('project__name', flat=True))
    if assigned_tasks:
        projects_list.update(assigned_tasks.values_list('project__name', flat=True))
    projects_str = ', '.join(projects_list)

    if request.method == "POST":
        # Каскадное удаление связей
        Project.objects.filter(manager=employee).update(manager=None)
        ProjectTask.objects.filter(assigned_to=employee).update(assigned_to=None)
        ProjectParticipant.objects.filter(employee=employee).delete()

        # Удалить Employee (каскадно удалит связанного User благодаря on_delete=models.CASCADE)
        employee.delete()
        messages.success(request, "Сотрудник удален")
        return redirect("admin_employees")

    # GET: показать страницу подтверждения
    return render(request, "admin/employees/delete.html", {
        "employee": employee,
        "in_projects": in_projects,
        "projects_str": projects_str,
    })