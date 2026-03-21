from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import admin_required
from core.models import Position
from django.contrib import messages

@admin_required
def position_list(request):
    positions = Position.objects.order_by('name')
    return render(request, "admin/positions/list.html", {
        "positions": positions
    })

@admin_required
def position_create(request):
    if request.method == "POST":
        name = request.POST.get("name")

        if not name:
            messages.error(request, "Название должности обязательно")
        else:
            Position.objects.create(name=name)
            messages.success(request, "Должность создана")
            return redirect("admin_positions")

    return render(request, "admin/positions/form.html", {
        "mode": "create"
    })

@admin_required
def position_edit(request, pk):
    position = get_object_or_404(Position, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name")

        if not name:
            messages.error(request, "Название должности обязательно")
        else:
            position.name = name
            position.save()
            messages.success(request, "Должность обновлена")
            return redirect("admin_positions")

    return render(request, "admin/positions/form.html", {
        "position": position,
        "mode": "edit"
    })

@admin_required
def position_delete(request, pk):
    position = get_object_or_404(Position, pk=pk)

    if request.method == "POST":
        position.delete()
        messages.success(request, "Должность удалена")
        return redirect("admin_positions")

    # If GET, redirect back to list
    messages.warning(request, "Используйте диалог подтверждения для удаления.")
    return redirect("admin_positions")