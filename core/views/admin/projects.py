import logging

logger = logging.getLogger(__name__)

# Summary: Файл `core/views/admin/projects.py`: содержит код и настройки для раздела "projects".
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from core.decorators import admin_required
from core.models import (
    Project,
    ProjectClosureRequest,
    ProjectStatus,
    ProjectType,
    Employee,
    ManagerProjectNotification,
    ProjectExpenseRequest,
)
from django.contrib import messages
from django.utils import timezone
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from core.utils.project_archive import archived_project_q


# Summary: Содержит логику для recalculate project actual cost.
def _recalculate_project_actual_cost(project):
    approved_total = ProjectExpenseRequest.objects.filter(
        project=project,
        status=ProjectExpenseRequest.STATUS_APPROVED
    ).values_list('amount', flat=True)
    project.actual_cost = sum(approved_total, Decimal('0'))
    project.updated_at = timezone.now()
    project.save(update_fields=['actual_cost', 'updated_at'])


# Summary: Содержит логику для available managers qs.
def _available_managers_qs():
    return Employee.objects.filter(is_active=True, position__name="Руководитель проекта").order_by("last_name", "first_name")


# Summary: Содержит логику для project form context.
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


# Summary: Содержит логику для validate project form.
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

# Summary: Содержит логику для project list.
@admin_required
def project_list(request):
    return _project_list_common(request, archive_mode=False)


# Summary: Содержит логику для project archive list.
@admin_required
def project_archive_list(request):
    return _project_list_common(request, archive_mode=True)


# Summary: Содержит логику для project list common.
def _project_list_common(request, archive_mode=False):
    search_query = (request.GET.get("q") or "").strip()
    status_id = (request.GET.get("status") or "").strip()
    type_id = (request.GET.get("type") or "").strip()
    manager_id = (request.GET.get("manager") or "").strip()

    projects = Project.objects.select_related(
        "status", "type", "manager"
    ).order_by("-created_at")
    if archive_mode:
        projects = projects.filter(archived_project_q())
    else:
        projects = projects.exclude(archived_project_q())
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

    pending_expense_project_ids = set(
        ProjectExpenseRequest.objects.filter(
            status=ProjectExpenseRequest.STATUS_NEEDS_ADMIN_REVIEW
        ).values_list('project_id', flat=True)
    )
    pending_closure_project_ids = set(
        ProjectClosureRequest.objects.filter(
            status=ProjectClosureRequest.STATUS_PENDING
        ).values_list('project_id', flat=True)
    )

    return render(request, "admin/projects/list.html", {
        "projects": projects,
        "archive_mode": archive_mode,
        "search_query": search_query,
        "status_id": status_id,
        "type_id": type_id,
        "manager_id": manager_id,
        "statuses": ProjectStatus.objects.order_by("name"),
        "types": ProjectType.objects.order_by("name"),
        "managers": _available_managers_qs(),
        "projects_count": projects.count(),
        "pending_expense_project_ids": pending_expense_project_ids,
        "pending_closure_project_ids": pending_closure_project_ids,
    })


# Summary: Содержит логику для project create.
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


# Summary: Содержит логику для project edit.
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



# Summary: Содержит логику для project detail.
@admin_required
def project_detail(request, pk):
    project = get_object_or_404(Project.objects.select_related('type', 'status', 'manager', 'manager__position', 'manager__department'), pk=pk)
    is_archived = Project.objects.filter(id=project.id).filter(archived_project_q()).exists()
    selected_tab = request.GET.get("tab") or request.POST.get("tab") or "info"
    if selected_tab not in {"info", "expenses", "closure"}:
        selected_tab = "info"

    expense_error = None
    expense_success = None
    closure_error = None
    closure_success = None
    if request.method == "POST" and request.POST.get("expense_action") in {"approve", "reject"}:
        expense_action = request.POST.get("expense_action")
        expense_id = (request.POST.get("expense_id") or "").strip()
        admin_comment = (request.POST.get("admin_comment") or "").strip()

        if not expense_id.isdigit():
            expense_error = "Некорректный запрос на трату."
        else:
            expense_request = ProjectExpenseRequest.objects.filter(
                id=int(expense_id),
                project=project,
                status=ProjectExpenseRequest.STATUS_NEEDS_ADMIN_REVIEW
            ).first()
            if not expense_request:
                expense_error = "Запрос уже обработан или недоступен."
            else:
                expense_request.admin_comment = admin_comment or None
                expense_request.admin_decision_at = timezone.now()
                if expense_action == "approve":
                    expense_request.status = ProjectExpenseRequest.STATUS_APPROVED
                    expense_success = "Трата подтверждена администратором."
                else:
                    expense_request.status = ProjectExpenseRequest.STATUS_REJECTED
                    expense_success = "Трата отклонена администратором."
                expense_request.save(update_fields=["status", "admin_comment", "admin_decision_at", "updated_at"])
                _recalculate_project_actual_cost(project)
                selected_tab = "expenses"

    if request.method == "POST" and request.POST.get("closure_action") in {"approve", "reject"}:
        closure_action = request.POST.get("closure_action")
        closure_id = (request.POST.get("closure_request_id") or "").strip()
        admin_comment = (request.POST.get("admin_comment") or "").strip()
        selected_tab = "closure"

        if not closure_id.isdigit():
            closure_error = "Некорректный запрос на закрытие."
        else:
            closure_request = ProjectClosureRequest.objects.filter(
                id=int(closure_id),
                project=project,
                status=ProjectClosureRequest.STATUS_PENDING
            ).first()
            if not closure_request:
                closure_error = "Запрос уже обработан или недоступен."
            elif closure_action == "reject" and not admin_comment:
                closure_error = "При отклонении укажите комментарий для руководителя."
            else:
                closure_request.admin_comment = admin_comment or None
                closure_request.decided_at = timezone.now()
                closure_request.seen_by_manager = False
                if closure_action == "approve":
                    closed_status = ProjectStatus.objects.filter(name__icontains='заверш').first()
                    if not closed_status:
                        closure_error = "Не найден статус 'Завершён'. Добавьте его в справочник статусов и повторите."
                    else:
                        closure_request.status = ProjectClosureRequest.STATUS_APPROVED
                        project.status = closed_status
                        project.updated_at = timezone.now()
                        project.save(update_fields=['status', 'updated_at'])
                        closure_success = "Закрытие проекта подтверждено."
                else:
                    closure_request.status = ProjectClosureRequest.STATUS_REJECTED
                    closure_success = "Запрос на закрытие отклонен."
                if not closure_error:
                    closure_request.save(update_fields=["status", "admin_comment", "decided_at", "seen_by_manager", "updated_at"])

    budget_deviation = None
    if project.budget and project.actual_cost:
        budget_deviation = project.actual_cost - project.budget

    expense_requests = ProjectExpenseRequest.objects.filter(project=project).select_related('requested_by', 'task').order_by('-created_at')
    pending_admin_expenses = expense_requests.filter(status=ProjectExpenseRequest.STATUS_NEEDS_ADMIN_REVIEW)
    closure_requests = ProjectClosureRequest.objects.filter(project=project).select_related('requested_by').order_by('-requested_at')
    pending_closure_requests = closure_requests.filter(status=ProjectClosureRequest.STATUS_PENDING)
    approved_closure_requests_count = closure_requests.filter(status=ProjectClosureRequest.STATUS_APPROVED).count()
    rejected_closure_requests_count = closure_requests.filter(status=ProjectClosureRequest.STATUS_REJECTED).count()
    approved_expense_total = sum(
        expense_requests.filter(status=ProjectExpenseRequest.STATUS_APPROVED).values_list('amount', flat=True),
        Decimal('0')
    )

    return render(request, "admin/projects/detail.html", {
        "project": project,
        "budget_deviation": budget_deviation,
        "expense_requests": expense_requests,
        "pending_admin_expenses": pending_admin_expenses,
        "pending_admin_expenses_count": pending_admin_expenses.count(),
        "approved_expense_total": approved_expense_total,
        "expense_error": expense_error,
        "expense_success": expense_success,
        "closure_error": closure_error,
        "closure_success": closure_success,
        "selected_tab": selected_tab,
        "is_archived": is_archived,
        "closure_requests": closure_requests,
        "pending_closure_requests": pending_closure_requests,
        "pending_closure_requests_count": pending_closure_requests.count(),
        "approved_closure_requests_count": approved_closure_requests_count,
        "rejected_closure_requests_count": rejected_closure_requests_count,
        "admin_pending_expense_requests_count": ProjectExpenseRequest.objects.filter(
            status=ProjectExpenseRequest.STATUS_NEEDS_ADMIN_REVIEW
        ).count(),
    })

# Summary: Содержит логику для project delete.
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
