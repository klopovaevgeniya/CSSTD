from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import admin_required
from core.models import Department
from django.contrib import messages

@admin_required
def department_list(request):
    departments = Department.objects.order_by('name')
    return render(request, "admin/departments/list.html", {
        "departments": departments
    })

@admin_required
def department_create(request):
    if request.method == "POST":
        name = request.POST.get("name")

        if not name:
            messages.error(request, "Название отдела обязательно")
        else:
            Department.objects.create(name=name)
            messages.success(request, "Отдел создан")
            return redirect("admin_departments")

    return render(request, "admin/departments/form.html", {
        "mode": "create"
    })

@admin_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name")

        if not name:
            messages.error(request, "Название отдела обязательно")
        else:
            department.name = name
            department.save()
            messages.success(request, "Отдел обновлен")
            return redirect("admin_departments")

    return render(request, "admin/departments/form.html", {
        "department": department,
        "mode": "edit"
    })

@admin_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        department.delete()
        messages.success(request, "Отдел удален")
        return redirect("admin_departments")

    # If GET, redirect back to list
    messages.warning(request, "Используйте диалог подтверждения для удаления.")
    return redirect("admin_departments")