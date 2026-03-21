from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import admin_required
from core.models import Project, ProjectStatus, ProjectType, Employee, ManagerProjectNotification
from django.contrib import messages
from django.utils import timezone
from datetime import date

@admin_required
def project_list(request):
    projects = Project.objects.select_related(
        "status", "type", "manager"
    ).order_by("-created_at")

    return render(request, "admin/projects/list.html", {
        "projects": projects
    })


@admin_required
def project_create(request):
    statuses = ProjectStatus.objects.all()
    types = ProjectType.objects.all()
    managers = Employee.objects.filter(is_active=True, position__name="Руководитель проекта")

    if request.method == "POST":
        name = request.POST.get("name")

        if not name:
            messages.error(request, "Название проекта обязательно")
        else:
            project = Project.objects.create(
                name=name,
                description=request.POST.get("description"),
                start_date=request.POST.get("start_date") or None,
                end_date=request.POST.get("end_date") or None,
                budget=request.POST.get("budget") or None,
                status_id=request.POST.get("status"),
                type_id=request.POST.get("type"),
                manager_id=request.POST.get("manager"),
                created_at=timezone.now()
            )

            # Создаём уведомление для менеджера, если он назначен
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

            return redirect("admin_projects")

    return render(request, "admin/projects/form.html", {
        "statuses": statuses,
        "types": types,
        "managers": managers,
        "mode": "create"
    })


@admin_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    statuses = ProjectStatus.objects.all()
    types = ProjectType.objects.all()
    managers = Employee.objects.filter(is_active=True, position__name="Руководитель проекта")

    if request.method == "POST":
        name = request.POST.get("name")

        if not name:
            messages.error(request, "Название проекта обязательно")
        else:
            old_manager = project.manager_id

            project.name = name
            project.description = request.POST.get("description")
            project.start_date = request.POST.get("start_date") or None
            project.end_date = request.POST.get("end_date") or None
            project.budget = request.POST.get("budget") or None
            project.status_id = request.POST.get("status")
            project.type_id = request.POST.get("type")
            project.manager_id = request.POST.get("manager")
            project.save()

            # Если менеджер изменился — создаём новое уведомление для нового менеджера
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

            return redirect("admin_projects")

    return render(request, "admin/projects/form.html", {
        "project": project,
        "statuses": statuses,
        "types": types,
        "managers": managers,
        "mode": "edit"
    })



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
