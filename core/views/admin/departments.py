from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
import re
from core.decorators import admin_required
from core.models import Department, Employee, PositionDepartment
from django.contrib import messages

import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для department list.
@admin_required
def department_list(request):
    search_query = (request.GET.get('q') or '').strip()
    usage_filter = (request.GET.get('usage') or 'all').strip()

    departments = Department.objects.order_by('name')
    if search_query:
        departments = departments.filter(name__icontains=search_query)

    employee_counts = {}
    for row in (
        Employee.objects
        .filter(department_id__in=departments.values('id'))
        .values('department')
        .annotate(cnt=models.Count('id'))
    ):
        employee_counts[row['department']] = row['cnt']

    position_counts = {}
    for row in (
        PositionDepartment.objects
        .filter(department_id__in=departments.values('id'))
        .values('department')
        .annotate(cnt=models.Count('id'))
    ):
        position_counts[row['department']] = row['cnt']

    department_rows = []
    for department in departments:
        employee_count = employee_counts.get(department.id, 0)
        position_count = position_counts.get(department.id, 0)
        linked = employee_count > 0 or position_count > 0
        if usage_filter == 'linked' and not linked:
            continue
        if usage_filter == 'free' and linked:
            continue
        department_rows.append({
            "department": department,
            "employee_count": employee_count,
            "position_count": position_count,
            "linked": linked,
        })

    return render(request, "admin/departments/list.html", {
        "departments": department_rows,
        "search_query": search_query,
        "usage_filter": usage_filter,
        "departments_count": len(department_rows),
    })


# Summary: Содержит логику для department form context.
def _department_form_context(mode, department=None, form_data=None, form_errors=None):
    if form_data is None:
        form_data = {"name": department.name if department else ""}
    return {
        "mode": mode,
        "department": department,
        "form_data": form_data,
        "form_errors": form_errors or {},
    }


# Summary: Содержит логику для validate department form.
def _validate_department_form(post_data, current_department=None):
    form_data = {"name": (post_data.get("name") or "").strip()}
    errors = {}
    cleaned = {"name": None}

    if not form_data["name"]:
        errors["name"] = "Укажите название отдела."
    elif len(form_data["name"]) > 100:
        errors["name"] = "Название отдела слишком длинное (до 100 символов)."
    elif not re.match(r"^[A-Za-zА-Яа-яЁё0-9\-\s]+$", form_data["name"]):
        errors["name"] = "Название может содержать только буквы, цифры, пробел и дефис."
    else:
        duplicate_qs = Department.objects.filter(name__iexact=form_data["name"])
        if current_department:
            duplicate_qs = duplicate_qs.exclude(pk=current_department.pk)
        if duplicate_qs.exists():
            errors["name"] = "Такой отдел уже существует."
        else:
            cleaned["name"] = form_data["name"]

    for field_name in errors:
        form_data[field_name] = ""

    return cleaned, form_data, errors


# Summary: Содержит логику для department create.
@admin_required
def department_create(request):
    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_department_form(request.POST)
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/departments/form.html",
                _department_form_context("create", form_data=form_data, form_errors=form_errors),
            )

        Department.objects.create(name=cleaned["name"])
        messages.success(request, "Отдел создан")
        return redirect("admin_departments")

    return render(request, "admin/departments/form.html", _department_form_context("create"))

# Summary: Содержит логику для department edit.
@admin_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_department_form(request.POST, current_department=department)
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/departments/form.html",
                _department_form_context("edit", department=department, form_data=form_data, form_errors=form_errors),
            )

        department.name = cleaned["name"]
        department.save()
        messages.success(request, "Отдел обновлен")
        return redirect("admin_departments")

    return render(request, "admin/departments/form.html", _department_form_context("edit", department=department))

# Summary: Содержит логику для department delete.
@admin_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    employees_count = Employee.objects.filter(department=department).count()
    positions_count = PositionDepartment.objects.filter(department=department).count()

    if request.method == "POST":
        if employees_count > 0 or positions_count > 0:
            messages.error(
                request,
                f"Нельзя удалить отдел: есть связанные данные. "
                f"Сотрудников: {employees_count}, должностей: {positions_count}."
            )
            return redirect("admin_departments")
        department.delete()
        messages.success(request, "Отдел удален")
        return redirect("admin_departments")

    # If GET, redirect back to list
    messages.warning(request, "Используйте диалог подтверждения для удаления.")
    return redirect("admin_departments")
