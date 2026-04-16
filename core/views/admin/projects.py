from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from core.decorators import admin_required
from core.models import Project, ProjectStatus, ProjectType, Employee, ManagerProjectNotification
from django.contrib import messages
from django.utils import timezone
from datetime import date
from decimal import Decimal, InvalidOperation
import re


def _available_managers_qs():
    return Employee.objects.filter(is_active=True, position__name="Руководитель проекта").order_by("last_name", "first_name")


def _project_form_context(mode, statuses, types, managers, project=None, form_data=None, form_errors=None):
    if form_data is None:
        form_data = {
            "name": project.name if project else "",
            "description": project.description if project else "",
            "start_date": project.start_date.isoformat() if project and project.start_date else "",
            "end_date": project.end_date.isoformat() if project and project.end_date else "",
            "budget": str(project.budget) if project and project.budget is not None else "",
            "status": str(project.status_id) if project and project.status_id else "",
            "type": str(project.type_id) if project and project.type_id else "",
            "manager": str(project.manager_id) if project and project.manager_id else "",
        }
    return {
        "mode": mode,
        "project": project,
        "statuses": statuses,
        "types": types,
        "managers": managers,
        "form_data": form_data,
        "form_errors": form_errors or {},
    }


def _validate_project_form(post_data):
    form_data = {
        "name": (post_data.get("name") or "").strip(),
        "description": (post_data.get("description") or "").strip(),
        "start_date": (post_data.get("start_date") or "").strip(),
        "end_date": (post_data.get("end_date") or "").strip(),
        "budget": (post_data.get("budget") or "").strip(),
        "status": (post_data.get("status") or "").strip(),
        "type": (post_data.get("type") or "").strip(),
        "manager": (post_data.get("manager") or "").strip(),
    }
    errors = {}
    cleaned = {
        "name": None,
        "description": None,
        "start_date": None,
        "end_date": None,
        "budget": None,
        "status_id": None,
        "type_id": None,
        "manager_id": None,
    }

    if not form_data["name"]:
        errors["name"] = "Укажите название проекта."
    elif len(form_data["name"]) > 255:
        errors["name"] = "Название проекта слишком длинное (до 255 символов)."
    elif not re.match(r"^[A-Za-zА-Яа-яЁё0-9\-\s.,:()]+$", form_data["name"]):
        errors["name"] = "Название содержит недопустимые символы."
    else:
        cleaned["name"] = form_data["name"]

    cleaned["description"] = form_data["description"] or None

    start_dt = None
    end_dt = None
    if form_data["start_date"]:
        try:
            start_dt = date.fromisoformat(form_data["start_date"])
        except ValueError:
            errors["start_date"] = "Введите корректную дату начала."
    if form_data["end_date"]:
        try:
            end_dt = date.fromisoformat(form_data["end_date"])
        except ValueError:
            errors["end_date"] = "Введите корректную дату окончания."
    if start_dt and end_dt and end_dt < start_dt:
        errors["end_date"] = "Дата окончания не может быть раньше даты начала."
    cleaned["start_date"] = start_dt
    cleaned["end_date"] = end_dt

    if form_data["budget"]:
        try:
            budget = Decimal(form_data["budget"])
        except (InvalidOperation, ValueError):
            errors["budget"] = "Введите корректный бюджет."
        else:
            if budget < 0:
                errors["budget"] = "Бюджет не может быть отрицательным."
            else:
                cleaned["budget"] = budget

    if not form_data["status"]:
        errors["status"] = "Выберите статус проекта."
    elif not form_data["status"].isdigit():
        errors["status"] = "Некорректный статус."
    else:
        status_id = int(form_data["status"])
        if not ProjectStatus.objects.filter(pk=status_id).exists():
            errors["status"] = "Выбранный статус не найден."
        else:
            cleaned["status_id"] = status_id

    if not form_data["type"]:
        errors["type"] = "Выберите тип проекта."
    elif not form_data["type"].isdigit():
        errors["type"] = "Некорректный тип проекта."
    else:
        type_id = int(form_data["type"])
        if not ProjectType.objects.filter(pk=type_id).exists():
            errors["type"] = "Выбранный тип проекта не найден."
        else:
            cleaned["type_id"] = type_id

    if form_data["manager"]:
        if not form_data["manager"].isdigit():
            errors["manager"] = "Некорректный руководитель."
        else:
            manager_id = int(form_data["manager"])
            if not _available_managers_qs().filter(pk=manager_id).exists():
                errors["manager"] = "Выбранный руководитель недоступен."
            else:
                cleaned["manager_id"] = manager_id

    for field_name in errors:
        form_data[field_name] = ""

    return cleaned, form_data, errors

@admin_required
def project_list(request):
    search_query = (request.GET.get("q") or "").strip()
    status_id = (request.GET.get("status") or "").strip()
    type_id = (request.GET.get("type") or "").strip()
    manager_id = (request.GET.get("manager") or "").strip()

    projects = Project.objects.select_related(
        "status", "type", "manager"
    ).order_by("-created_at")
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(type__name__icontains=search_query)
            | Q(status__name__icontains=search_query)
            | Q(manager__last_name__icontains=search_query)
            | Q(manager__first_name__icontains=search_query)
        )
    if status_id.isdigit():
        projects = projects.filter(status_id=int(status_id))
    if type_id.isdigit():
        projects = projects.filter(type_id=int(type_id))
    if manager_id.isdigit():
        projects = projects.filter(manager_id=int(manager_id))

    return render(request, "admin/projects/list.html", {
        "projects": projects,
        "search_query": search_query,
        "status_id": status_id,
        "type_id": type_id,
        "manager_id": manager_id,
        "statuses": ProjectStatus.objects.order_by("name"),
        "types": ProjectType.objects.order_by("name"),
        "managers": _available_managers_qs(),
        "projects_count": projects.count(),
    })


@admin_required
def project_create(request):
    statuses = ProjectStatus.objects.order_by("name")
    types = ProjectType.objects.order_by("name")
    managers = _available_managers_qs()

    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_project_form(request.POST)
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/projects/form.html",
                _project_form_context(
                    "create",
                    statuses,
                    types,
                    managers,
                    form_data=form_data,
                    form_errors=form_errors,
                ),
            )

        project = Project.objects.create(
            name=cleaned["name"],
            description=cleaned["description"],
            start_date=cleaned["start_date"],
            end_date=cleaned["end_date"],
            budget=cleaned["budget"],
            status_id=cleaned["status_id"],
            type_id=cleaned["type_id"],
            manager_id=cleaned["manager_id"],
            created_at=timezone.now(),
        )

        try:
            if project.manager_id:
                ManagerProjectNotification.objects.create(
                    manager_id=project.manager_id,
                    project=project,
                    seen=False,
                    created_at=timezone.now()
                )
        except Exception:
            pass

        messages.success(request, "Проект создан")
        return redirect("admin_projects")

    return render(request, "admin/projects/form.html", _project_form_context("create", statuses, types, managers))


@admin_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    statuses = ProjectStatus.objects.order_by("name")
    types = ProjectType.objects.order_by("name")
    managers = _available_managers_qs()

    if request.method == "POST":
        cleaned, form_data, form_errors = _validate_project_form(request.POST)
        if form_errors:
            messages.error(request, "Исправьте поля, выделенные красным.")
            return render(
                request,
                "admin/projects/form.html",
                _project_form_context(
                    "edit",
                    statuses,
                    types,
                    managers,
                    project=project,
                    form_data=form_data,
                    form_errors=form_errors,
                ),
            )

        old_manager = project.manager_id
        project.name = cleaned["name"]
        project.description = cleaned["description"]
        project.start_date = cleaned["start_date"]
        project.end_date = cleaned["end_date"]
        project.budget = cleaned["budget"]
        project.status_id = cleaned["status_id"]
        project.type_id = cleaned["type_id"]
        project.manager_id = cleaned["manager_id"]
        project.save()

        try:
            if project.manager_id and project.manager_id != old_manager:
                ManagerProjectNotification.objects.create(
                    manager_id=project.manager_id,
                    project=project,
                    seen=False,
                    created_at=timezone.now()
                )
        except Exception:
            pass

        messages.success(request, "Проект обновлен")
        return redirect("admin_projects")

    return render(request, "admin/projects/form.html", _project_form_context("edit", statuses, types, managers, project=project))



@admin_required
def project_detail(request, pk):
    project = get_object_or_404(Project.objects.select_related('type', 'status', 'manager', 'manager__position', 'manager__department'), pk=pk)
    budget_deviation = None
    if project.budget and project.actual_cost:
        budget_deviation = project.actual_cost - project.budget
    return render(request, "admin/projects/detail.html", {
        "project": project,
        "budget_deviation": budget_deviation
    })

@admin_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        # Попробуем сначала удалить связанные уведомления (если таблица существует)
        try:
            ManagerProjectNotification.objects.filter(project=project).delete()
        except Exception:
            # Игнорируем ошибку если таблицы нет или другая проблема с БД
            pass

        try:
            deleted = project.delete()
            # project.delete() возвращает кортеж (deleted_count, {model: count})
            if deleted and deleted[0] > 0:
                messages.success(request, "Проект удалён")
            else:
                messages.error(request, "Проект не был удалён (0 строк затронуто)")
        except Exception as e:
            messages.error(request, "Ошибка при удалении проекта: %s" % e)

        return redirect("admin_projects")

    # If GET, redirect back to list
    messages.warning(request, "Используйте диалог подтверждения для удаления.")
    return redirect("admin_projects")
