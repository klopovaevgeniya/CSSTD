import json
import random
import re
import string
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import connection
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from core.decorators import admin_required
from core.models import (
    Department,
    Employee,
    Position,
    PositionDepartment,
    Project,
    ProjectParticipant,
    ProjectTask,
    TaskAssignee,
)

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


def _get_position_department_map():
    """
    Возвращает соответствие должность -> отдел.
    В приоритете явная связь из position_departments, fallback — по текущим сотрудникам.
    """
    explicit_map = {
        link.position_id: link.department_id
        for link in PositionDepartment.objects.all().only('position_id', 'department_id')
    }

    fallback_map = {}
    fallback_rows = (
        Employee.objects
        .filter(position_id__isnull=False, department_id__isnull=False)
        .values('position_id', 'department_id')
        .annotate(cnt=Count('id'))
        .order_by('position_id', '-cnt', 'department_id')
    )
    for row in fallback_rows:
        position_id = row['position_id']
        if position_id not in fallback_map:
            fallback_map[position_id] = row['department_id']

    fallback_map.update(explicit_map)
    return fallback_map


def _resolve_role(position_id):
    if not position_id:
        return "employee"
    position = Position.objects.filter(id=position_id).first()
    if not position:
        return "employee"
    if position.name == "Руководитель проекта":
        return "project_manager"
    if position.name == "Администратор":
        return "admin"
    return "employee"


def _empty_employee_form_data():
    return {
        "last_name": "",
        "first_name": "",
        "middle_name": "",
        "position": "",
        "department": "",
        "email": "",
        "phone": "",
        "hire_date": "",
        "is_active": "true",
    }


def _employee_to_form_data(employee):
    return {
        "last_name": employee.last_name or "",
        "first_name": employee.first_name or "",
        "middle_name": employee.middle_name or "",
        "position": str(employee.position_id) if employee.position_id else "",
        "department": str(employee.department_id) if employee.department_id else "",
        "email": employee.email or "",
        "phone": employee.phone or "",
        "hire_date": employee.hire_date.isoformat() if employee.hire_date else "",
        "is_active": "true" if employee.is_active else "false",
    }


def _validate_employee_form(post_data, position_department_map, current_employee=None):
    errors = {}
    form_data = {
        "last_name": (post_data.get("last_name") or "").strip(),
        "first_name": (post_data.get("first_name") or "").strip(),
        "middle_name": (post_data.get("middle_name") or "").strip(),
        "position": (post_data.get("position") or "").strip(),
        "department": (post_data.get("department") or "").strip(),
        "email": (post_data.get("email") or "").strip(),
        "phone": (post_data.get("phone") or "").strip(),
        "hire_date": (post_data.get("hire_date") or "").strip(),
        "is_active": "false" if (post_data.get("is_active") or "").strip() == "false" else "true",
    }
    cleaned = {
        "last_name": None,
        "first_name": None,
        "middle_name": None,
        "position_id": None,
        "department_id": None,
        "email": None,
        "phone": None,
        "hire_date": None,
        "is_active": form_data["is_active"] == "true",
    }

    name_regex = r"^[A-Za-zА-Яа-яЁё\-\s]+$"

    if not form_data["last_name"]:
        errors["last_name"] = "Укажите фамилию."
    elif not re.match(name_regex, form_data["last_name"]):
        errors["last_name"] = "Фамилия может содержать только буквы, пробел и дефис."
    else:
        cleaned["last_name"] = form_data["last_name"]

    if not form_data["first_name"]:
        errors["first_name"] = "Укажите имя."
    elif not re.match(name_regex, form_data["first_name"]):
        errors["first_name"] = "Имя может содержать только буквы, пробел и дефис."
    else:
        cleaned["first_name"] = form_data["first_name"]

    if form_data["middle_name"]:
        if not re.match(name_regex, form_data["middle_name"]):
            errors["middle_name"] = "Отчество может содержать только буквы, пробел и дефис."
        else:
            cleaned["middle_name"] = form_data["middle_name"]
    else:
        cleaned["middle_name"] = None

    if not form_data["position"]:
        errors["position"] = "Выберите должность."
    elif not form_data["position"].isdigit():
        errors["position"] = "Некорректная должность."
    else:
        position_id = int(form_data["position"])
        if not Position.objects.filter(id=position_id).exists():
            errors["position"] = "Выбранная должность не найдена."
        else:
            cleaned["position_id"] = position_id
            mapped_department_id = position_department_map.get(position_id)
            if not mapped_department_id:
                errors["position"] = "Для выбранной должности не задан отдел."
                errors["department"] = "Отдел не найден для выбранной должности."
            else:
                cleaned["department_id"] = mapped_department_id
                form_data["department"] = str(mapped_department_id)

    if not form_data["email"]:
        errors["email"] = "Укажите email."
    else:
        try:
            validate_email(form_data["email"])
        except ValidationError:
            errors["email"] = "Введите корректный email."
        else:
            email_qs = Employee.objects.filter(email__iexact=form_data["email"])
            if current_employee:
                email_qs = email_qs.exclude(pk=current_employee.pk)
            if email_qs.exists():
                errors["email"] = "Сотрудник с таким email уже существует."
            else:
                cleaned["email"] = form_data["email"]

    if form_data["phone"]:
        if not re.match(r"^\+?[0-9()\-\s]{7,20}$", form_data["phone"]):
            errors["phone"] = "Введите корректный телефон."
        else:
            cleaned["phone"] = form_data["phone"]
    else:
        cleaned["phone"] = None

    if form_data["hire_date"]:
        try:
            parsed_date = date.fromisoformat(form_data["hire_date"])
        except ValueError:
            errors["hire_date"] = "Введите корректную дату."
        else:
            if parsed_date > date.today():
                errors["hire_date"] = "Дата приема не может быть в будущем."
            else:
                cleaned["hire_date"] = parsed_date
    else:
        cleaned["hire_date"] = None

    for field_name in errors:
        form_data[field_name] = ""

    return cleaned, form_data, errors


def _employee_form_context(mode, position_department_map, employee=None, form_data=None, form_errors=None):
    if form_data is None:
        form_data = _employee_to_form_data(employee) if employee else _empty_employee_form_data()
    return {
        "mode": mode,
        "employee": employee,
        "positions": Position.objects.order_by("name"),
        "departments": Department.objects.order_by("name"),
        "position_department_map_json": json.dumps(position_department_map),
        "form_data": form_data,
        "form_errors": form_errors or {},
    }


@admin_required
def employee_list(request):
    search_query = (request.GET.get("q") or "").strip()
    position_filter = (request.GET.get("position") or "").strip()
    department_filter = (request.GET.get("department") or "").strip()
    status_filter = (request.GET.get("status") or "all").strip()

    employees = Employee.objects.select_related("employee_user", "position", "department").order_by("last_name", "first_name")
    if search_query:
        employees = employees.filter(
            Q(last_name__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(middle_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(position__name__icontains=search_query)
            | Q(department__name__icontains=search_query)
        )

    if position_filter.isdigit():
        employees = employees.filter(position_id=int(position_filter))
    if department_filter.isdigit():
        employees = employees.filter(department_id=int(department_filter))
    if status_filter == "active":
        employees = employees.filter(is_active=True)
    elif status_filter == "inactive":
        employees = employees.filter(is_active=False)

    return render(request, "admin/employees/list.html", {
        "employees": employees,
        "positions": Position.objects.order_by("name"),
        "departments": Department.objects.order_by("name"),
        "search_query": search_query,
        "position_filter": position_filter,
        "department_filter": department_filter,
        "status_filter": status_filter,
        "employees_count": employees.count(),
    })


@admin_required
def employee_create(request):
    position_department_map = _get_position_department_map()

    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_employee_form(
            request.POST, position_department_map
        )

        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/employees/form.html",
                _employee_form_context(
                    mode="create",
                    position_department_map=position_department_map,
                    form_data=form_data,
                    form_errors=form_errors,
                ),
            )

        username = transliterate(cleaned["last_name"]).lower()
        counter = 1
        original_username = username
        while True:
            user_exists = User.objects.filter(username=username).exists()
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", [username])
                users_count = cursor.fetchone()[0]
            if not user_exists and users_count == 0:
                break
            username = f"{original_username}{counter}"
            counter += 1

        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user = User.objects.create_user(username=username, email=cleaned["email"], password=password)

        Employee.objects.create(
            employee_user=user,
            last_name=cleaned["last_name"],
            first_name=cleaned["first_name"],
            middle_name=cleaned["middle_name"],
            position_id=cleaned["position_id"],
            department_id=cleaned["department_id"],
            email=cleaned["email"],
            phone=cleaned["phone"],
            hire_date=cleaned["hire_date"],
            is_active=cleaned["is_active"],
        )

        role = _resolve_role(cleaned["position_id"])
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (id, username, password_hash, role, is_active)
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), %s, %s)
                """,
                [user.id, username, password, role, cleaned["is_active"]],
            )

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
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [cleaned["email"]])
        msg.attach_alternative(html_content, "text/html")
        try:
            msg.send()
        except Exception as e:
            messages.warning(request, f"Сотрудник создан, но email не отправлен: {str(e)}")

        messages.success(request, "Сотрудник создан")
        return redirect("admin_employees")

    return render(
        request,
        "admin/employees/form.html",
        _employee_form_context(mode="create", position_department_map=position_department_map),
    )


@admin_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    position_department_map = _get_position_department_map()

    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_employee_form(
            request.POST, position_department_map, current_employee=employee
        )
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/employees/form.html",
                _employee_form_context(
                    mode="edit",
                    employee=employee,
                    position_department_map=position_department_map,
                    form_data=form_data,
                    form_errors=form_errors,
                ),
            )

        employee.last_name = cleaned["last_name"]
        employee.first_name = cleaned["first_name"]
        employee.middle_name = cleaned["middle_name"]
        employee.position_id = cleaned["position_id"]
        employee.department_id = cleaned["department_id"]
        employee.email = cleaned["email"]
        employee.phone = cleaned["phone"]
        employee.hire_date = cleaned["hire_date"]
        employee.is_active = cleaned["is_active"]
        employee.save()

        if employee.employee_user:
            employee.employee_user.email = cleaned["email"]
            employee.employee_user.is_active = cleaned["is_active"]
            employee.employee_user.save()

            role = _resolve_role(cleaned["position_id"])
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET role = %s, is_active = %s WHERE id = %s", [role, cleaned["is_active"], employee.employee_user.id])

        messages.success(request, "Сотрудник обновлен")
        return redirect("admin_employees")

    return render(
        request,
        "admin/employees/form.html",
        _employee_form_context(
            mode="edit",
            employee=employee,
            position_department_map=position_department_map,
        ),
    )

@admin_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    # Проверить связи с проектами
    managed_projects = Project.objects.filter(manager=employee)
    participated_projects = ProjectParticipant.objects.filter(employee=employee).select_related('project')
    assigned_tasks = ProjectTask.objects.filter(assigned_to=employee).select_related('project')
    multi_assigned_tasks = TaskAssignee.objects.filter(employee=employee).select_related('task__project')

    in_projects = managed_projects.exists() or participated_projects.exists() or assigned_tasks.exists() or multi_assigned_tasks.exists()
    projects_list = set()
    if managed_projects:
        projects_list.update(managed_projects.values_list('name', flat=True))
    if participated_projects:
        projects_list.update(participated_projects.values_list('project__name', flat=True))
    if assigned_tasks:
        projects_list.update(assigned_tasks.values_list('project__name', flat=True))
    if multi_assigned_tasks:
        projects_list.update(multi_assigned_tasks.values_list('task__project__name', flat=True))
    projects_str = ', '.join(projects_list)

    if request.method == "POST":
        # Каскадное удаление связей
        Project.objects.filter(manager=employee).update(manager=None)
        ProjectTask.objects.filter(assigned_to=employee).update(assigned_to=None)
        TaskAssignee.objects.filter(employee=employee).delete()
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
