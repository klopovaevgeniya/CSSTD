from django.urls import path
from django.views.generic import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from .views.public import home, access_denied
from .views.auth import login_view, logout_view, change_password_view
from . import views
from core.views.admin import dashboard, projects, employees, audit, positions, departments, reports, statistics
from core.views.manager import projects as manager_projects_views, chat as manager_chat_views, calendar as manager_calendar_views, statistics as manager_statistics_views
from core.views.manager import notifications as manager_notifications_views
from core.views import task_chat as task_chat_views
from .views.employee.dashboard import (
    employee_dashboard,
    employee_project_detail,
    employee_projects,
    employee_projects_archive,
    employee_tasks,
    employee_task_detail,
)
from .views.employee import chat as employee_chat_views
from .views.employee.calendar import employee_calendar
from .views.employee.profile import employee_profile
from .views.employee import notifications as employee_notifications_views
from .views.dashboard import (
    admin_dashboard,
    readonly_dashboard,
)
from core.views.manager.dashboard import manager_dashboard

urlpatterns = [
    path('', home, name='home'),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('img/favicon.svg'), permanent=True)),

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('change-password/', change_password_view, name='change_password'),

    path("admin/", dashboard.admin_dashboard, name="admin_dashboard"),
    path('admin/projects/', projects.project_list, name='admin_projects'),
    path('admin/projects/archive/', projects.project_archive_list, name='admin_projects_archive'),
    path('admin/projects/create/', projects.project_create, name='project_create'),
    path('admin/projects/<int:pk>/edit/', projects.project_edit, name='project_edit'),
    path('admin/projects/<int:pk>/detail/', projects.project_detail, name='project_detail'),
    path('admin/projects/<int:pk>/delete/', projects.project_delete, name='project_delete'),

    path('admin/employees/', employees.employee_list, name='admin_employees'),
    path('admin/employees/create/', employees.employee_create, name='employee_create'),
    path('admin/employees/<int:pk>/edit/', employees.employee_edit, name='employee_edit'),
    path('admin/employees/<int:pk>/delete/', employees.employee_delete, name='employee_delete'),

    path('admin/positions/', positions.position_list, name='admin_positions'),
    path('admin/positions/create/', positions.position_create, name='position_create'),
    path('admin/positions/<int:pk>/edit/', positions.position_edit, name='position_edit'),
    path('admin/positions/<int:pk>/delete/', positions.position_delete, name='position_delete'),

    path('admin/departments/', departments.department_list, name='admin_departments'),
    path('admin/departments/create/', departments.department_create, name='department_create'),
    path('admin/departments/<int:pk>/edit/', departments.department_edit, name='department_edit'),
    path('admin/departments/<int:pk>/delete/', departments.department_delete, name='department_delete'),

    path('admin/reports/', reports.reports_list, name='admin_reports'),
    path('admin/reports/export/projects/excel/', reports.export_projects_excel, name='export_projects_excel'),
    path('admin/reports/export/projects/csv/', reports.export_projects_csv, name='export_projects_csv'),
    path('admin/reports/export/employees/excel/', reports.export_employees_excel, name='export_employees_excel'),
    path('admin/reports/export/employees/csv/', reports.export_employees_csv, name='export_employees_csv'),
    path('admin/reports/export/tasks/excel/', reports.export_tasks_excel, name='export_tasks_excel'),
    path('admin/reports/export/tasks/csv/', reports.export_tasks_csv, name='export_tasks_csv'),

    path('admin/statistics/', statistics.statistics_dashboard, name='admin_statistics'),

    path('manager/projects/', manager_projects_views.manager_projects_list, name='manager_projects'),
    path('manager/projects/archive/', manager_projects_views.manager_projects_archive, name='manager_projects_archive'),
    path('manager/projects/<int:pk>/detail/', manager_projects_views.manager_project_detail, name='manager_project_detail'),
    path('manager/projects/<int:project_id>/create-task/', manager_projects_views.manager_create_task, name='manager_create_task'),
    path('manager/tasks/', manager_projects_views.manager_tasks, name='manager_tasks'),
    path('manager/tasks/<int:task_id>/', manager_projects_views.manager_task_detail, name='manager_task_detail'),
    path('manager/tasks/<int:task_id>/edit/', manager_projects_views.manager_edit_task, name='manager_edit_task'),
    path('manager/tasks/<int:task_id>/chat/', task_chat_views.task_chat_view, name='manager_task_chat'),
    path('manager/projects/<int:pk>/chat/', manager_chat_views.manager_project_chat, name='manager_project_chat'),
    path('manager/projects/<int:pk>/chat/send/', manager_chat_views.manager_project_chat_send, name='manager_project_chat_send'),
    path('manager/projects/<int:pk>/chat/delete/<int:message_id>/', manager_chat_views.manager_delete_chat_message, name='manager_delete_chat_message'),
    path('manager/projects/<int:pk>/chat/edit/<int:message_id>/', manager_chat_views.manager_edit_chat_message, name='manager_edit_chat_message'),

    path('manager/calendar/', manager_calendar_views.manager_calendar, name='manager_calendar'),
    path('manager/notifications/', manager_notifications_views.manager_notifications, name='manager_notifications'),

    path('manager/statistics/', manager_statistics_views.manager_statistics, name='manager_statistics'),
    path('manager/statistics/export/projects/excel/', manager_statistics_views.export_manager_projects_excel, name='manager_export_projects_excel'),
    path('manager/statistics/export/tasks/excel/', manager_statistics_views.export_manager_tasks_excel, name='manager_export_tasks_excel'),

    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),

    path('dashboard/employee/', employee_dashboard, name='employee_dashboard'),
    path('dashboard/employee/profile/', employee_profile, name='employee_profile'),
    path('dashboard/employee/tasks/', employee_tasks, name='employee_tasks'),
    path('dashboard/employee/tasks/<int:task_id>/', employee_task_detail, name='employee_task_detail'),
    path('dashboard/employee/tasks/<int:task_id>/chat/', task_chat_views.task_chat_view, name='employee_task_chat'),
    path('dashboard/employee/projects/', employee_projects, name='employee_projects'),
    path('dashboard/employee/projects/archive/', employee_projects_archive, name='employee_projects_archive'),
    path('dashboard/employee/projects/<int:pk>/', employee_project_detail, name='employee_project_detail'),
    path('dashboard/employee/projects/<int:pk>/chat/', employee_chat_views.employee_project_chat, name='employee_project_chat'),
    path('dashboard/employee/projects/<int:pk>/chat/send/', employee_chat_views.employee_project_chat_send, name='employee_project_chat_send'),
    path('dashboard/employee/projects/<int:pk>/chat/delete/<int:message_id>/', employee_chat_views.employee_delete_chat_message, name='employee_delete_chat_message'),
    path('dashboard/employee/projects/<int:pk>/chat/edit/<int:message_id>/', employee_chat_views.employee_edit_chat_message, name='employee_edit_chat_message'),

    path('dashboard/employee/calendar/', employee_calendar, name='employee_calendar'),
    path('dashboard/employee/notifications/', employee_notifications_views.employee_notifications, name='employee_notifications'),

    path('dashboard/readonly/', readonly_dashboard, name='readonly_dashboard'),

    path('denied/', access_denied, name='access_denied'),
    path('tasks/<int:task_id>/chat/send/', task_chat_views.task_chat_send, name='task_chat_send'),
]
