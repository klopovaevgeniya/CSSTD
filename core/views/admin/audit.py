from django.shortcuts import render
from core.decorators import admin_required
from django.db.models import Q
from core.models import Project, Employee, AuditLog
from datetime import datetime, timedelta


import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для audit log.
@admin_required
def audit_log(request):
    """Отображение журнала аудита"""
    # Получить все записи логов
    logs = AuditLog.objects.all().order_by('-changed_at')
    
    # Фильтрация по таблице
    table_filter = request.GET.get('table')
    if table_filter:
        logs = logs.filter(table_name=table_filter)
    
    # Фильтрация по действию
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    # Фильтрация по дате
    date_filter = request.GET.get('date')
    if date_filter:
        from datetime import datetime as dt
        try:
            filter_date = dt.strptime(date_filter, '%Y-%m-%d').date()
            logs = logs.filter(changed_at__date=filter_date)
        except:
            pass
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Получить статистику
    stats = {
        'total_entries': AuditLog.objects.count(),
        'today_entries': AuditLog.objects.filter(
            changed_at__date=datetime.now().date()
        ).count(),
        'tables': AuditLog.objects.values_list('table_name', flat=True).distinct(),
        'actions': AuditLog.objects.values_list('action', flat=True).distinct(),
    }
    
    return render(request, 'admin/audit.html', {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'stats': stats,
    })

