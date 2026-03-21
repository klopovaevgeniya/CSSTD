from django.urls import path
from .views.public import home, access_denied
from .views.auth import login_view, logout_view
from . import views
from core.views.admin import dashboard, projects, employees, audit, positions, departments
from .views.manager import projects as manager_projects_views, chat as manager_chat_views, calendar as manager_calendar_views
from .views.employee.dashboard import employee_dashboard, employee_projects, employee_project_detail, employee_tasks, employee_task_detail
from .views.employee import chat as employee_chat_views
from .views.employee.calendar import employee_calendar
from .views.dashboard import (
    admin_dashboard,
    readonly_dashboard,
)
from core.views.manager.dashboard import manager_dashboard

urlpatterns = [
    path('', home, name='home'),

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path("admin/", dashboard.admin_dashboard, name="admin_dashboard"),
    path('admin/projects/', projects.project_list, name='admin_projects'),
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

    path('manager/projects/', manager_projects_views.manager_projects_list, name='manager_projects'),
    path('manager/projects/<int:pk>/detail/', manager_projects_views.manager_project_detail, name='manager_project_detail'),
    path('manager/projects/<int:project_id>/create-task/', manager_projects_views.manager_create_task, name='manager_create_task'),
    path('manager/tasks/', manager_projects_views.manager_tasks, name='manager_tasks'),
    path('manager/tasks/<int:task_id>/', manager_projects_views.manager_task_detail, name='manager_task_detail'),
    path('manager/projects/<int:pk>/chat/', manager_chat_views.manager_project_chat, name='manager_project_chat'),
    path('manager/projects/<int:pk>/chat/send/', manager_chat_views.manager_project_chat_send, name='manager_project_chat_send'),
    path('manager/projects/<int:pk>/chat/delete/<int:message_id>/', manager_chat_views.manager_delete_chat_message, name='manager_delete_chat_message'),
    path('manager/projects/<int:pk>/chat/edit/<int:message_id>/', manager_chat_views.manager_edit_chat_message, name='manager_edit_chat_message'),

    path('manager/calendar/', manager_calendar_views.manager_calendar, name='manager_calendar'),

    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),

    path('dashboard/employee/', employee_dashboard, name='employee_dashboard'),
    path('dashboard/employee/tasks/', employee_tasks, name='employee_tasks'),
    path('dashboard/employee/tasks/<int:task_id>/', employee_task_detail, name='employee_task_detail'),
    path('dashboard/employee/projects/', employee_projects, name='employee_projects'),
    path('dashboard/employee/projects/<int:pk>/', employee_project_detail, name='employee_project_detail'),
    path('dashboard/employee/projects/<int:pk>/chat/', employee_chat_views.employee_project_chat, name='employee_project_chat'),
    path('dashboard/employee/projects/<int:pk>/chat/send/', employee_chat_views.employee_project_chat_send, name='employee_project_chat_send'),
    path('dashboard/employee/projects/<int:pk>/chat/delete/<int:message_id>/', employee_chat_views.employee_delete_chat_message, name='employee_delete_chat_message'),
    path('dashboard/employee/projects/<int:pk>/chat/edit/<int:message_id>/', employee_chat_views.employee_edit_chat_message, name='employee_edit_chat_message'),

    path('dashboard/employee/calendar/', employee_calendar, name='employee_calendar'),

    path('dashboard/readonly/', readonly_dashboard, name='readonly_dashboard'),

    path('denied/', access_denied, name='access_denied'),
]
