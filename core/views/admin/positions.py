from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
import re
from core.decorators import admin_required
from core.models import Position, Department, PositionDepartment, Employee
from django.contrib import messages

@admin_required
def position_list(request):
    search_query = (request.GET.get('q') or '').strip()
    department_filter = (request.GET.get('department') or '').strip()
    usage_filter = (request.GET.get('usage') or 'all').strip()
    positions = Position.objects.order_by('name')
    if search_query:
        positions = positions.filter(name__icontains=search_query)
    if department_filter.isdigit():
        positions = positions.filter(department_link__department_id=int(department_filter))

    position_department_map = {
        link.position_id: link.department
        for link in PositionDepartment.objects.select_related('department').filter(position_id__in=positions.values('id'))
    }
    position_rows = [
        {
            "position": position,
            "department": position_department_map.get(position.id),
            "employee_count": 0,
        }
        for position in positions
    ]
    employee_counts = {
        row['position']: row['cnt']
        for row in (
            Employee.objects
            .filter(position_id__in=positions.values('id'))
            .values('position')
            .annotate(cnt=Count('id'))
        )
    }
    for row in position_rows:
        row["employee_count"] = employee_counts.get(row["position"].id, 0)

    if usage_filter == 'linked':
        position_rows = [row for row in position_rows if row["employee_count"] > 0]
    elif usage_filter == 'free':
        position_rows = [row for row in position_rows if row["employee_count"] == 0]

    return render(request, "admin/positions/list.html", {
        "positions": position_rows,
        "search_query": search_query,
        "department_filter": department_filter,
        "usage_filter": usage_filter,
        "departments": Department.objects.order_by('name'),
        "positions_count": len(position_rows),
    })


def _position_form_context(mode, departments, position=None, form_data=None, form_errors=None):
    if form_data is None:
        linked_department = PositionDepartment.objects.filter(position=position).first() if position else None
        form_data = {
            "name": position.name if position else "",
            "department": str(linked_department.department_id) if linked_department else "",
        }
    return {
        "mode": mode,
        "position": position,
        "departments": departments,
        "form_data": form_data,
        "form_errors": form_errors or {},
    }


def _validate_position_form(post_data, current_position=None):
    form_data = {
        "name": (post_data.get("name") or "").strip(),
        "department": (post_data.get("department") or "").strip(),
    }
    errors = {}
    cleaned = {"name": None, "department_id": None}

    if not form_data["name"]:
        errors["name"] = "Укажите название должности."
    elif len(form_data["name"]) > 150:
        errors["name"] = "Название должности слишком длинное (до 150 символов)."
    elif not re.match(r"^[A-Za-zА-Яа-яЁё0-9\-\s]+$", form_data["name"]):
        errors["name"] = "Название может содержать только буквы, цифры, пробел и дефис."
    else:
        duplicate_qs = Position.objects.filter(name__iexact=form_data["name"])
        if current_position:
            duplicate_qs = duplicate_qs.exclude(pk=current_position.pk)
        if duplicate_qs.exists():
            errors["name"] = "Такая должность уже существует."
        else:
            cleaned["name"] = form_data["name"]

    if not form_data["department"]:
        errors["department"] = "Выберите отдел."
    elif not form_data["department"].isdigit():
        errors["department"] = "Некорректный отдел."
    else:
        department_id = int(form_data["department"])
        if not Department.objects.filter(pk=department_id).exists():
            errors["department"] = "Выбранный отдел не найден."
        else:
            cleaned["department_id"] = department_id

    for field_name in errors:
        form_data[field_name] = ""

    return cleaned, form_data, errors


@admin_required
def position_create(request):
    departments = Department.objects.order_by('name')
    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_position_form(request.POST)
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/positions/form.html",
                _position_form_context("create", departments, form_data=form_data, form_errors=form_errors),
            )

        position = Position.objects.create(name=cleaned["name"])
        PositionDepartment.objects.create(position=position, department_id=cleaned["department_id"])
        messages.success(request, "Должность создана")
        return redirect("admin_positions")

    return render(request, "admin/positions/form.html", _position_form_context("create", departments))

@admin_required
def position_edit(request, pk):
    position = get_object_or_404(Position, pk=pk)
    departments = Department.objects.order_by('name')

    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_position_form(request.POST, current_position=position)
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/positions/form.html",
                _position_form_context("edit", departments, position=position, form_data=form_data, form_errors=form_errors),
            )

        position.name = cleaned["name"]
        position.save()
        PositionDepartment.objects.update_or_create(
            position=position,
            defaults={"department_id": cleaned["department_id"]},
        )
        messages.success(request, "Должность обновлена")
        return redirect("admin_positions")

    return render(request, "admin/positions/form.html", _position_form_context("edit", departments, position=position))

@admin_required
def position_delete(request, pk):
    position = get_object_or_404(Position, pk=pk)
    linked_employees_qs = Employee.objects.filter(position=position).order_by('last_name', 'first_name')
    linked_count = linked_employees_qs.count()

    if request.method == "POST":
        if linked_count > 0:
            sample_names = ", ".join(
                f"{emp.last_name} {emp.first_name}"
                for emp in linked_employees_qs[:3]
            )
            if linked_count > 3:
                sample_names = f"{sample_names} и еще {linked_count - 3}"
            messages.error(
                request,
                f"Нельзя удалить должность: к ней привязаны сотрудники ({linked_count}). "
                f"Сначала переназначьте их на другую должность. {sample_names}"
            )
            return redirect("admin_positions")
        position.delete()
        messages.success(request, "Должность удалена")
        return redirect("admin_positions")

    # If GET, redirect back to list
    messages.warning(request, "Используйте диалог подтверждения для удаления.")
    return redirect("admin_positions")
