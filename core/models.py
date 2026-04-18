from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    table_name = models.TextField(blank=True, null=True)
    action = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(blank=True, null=True)
    old_data = models.JSONField(blank=True, null=True)
    new_data = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'audit_log'


class Contact(models.Model):
    partner = models.ForeignKey('Partner', models.CASCADE, blank=True, null=True)
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=150, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_main_contact = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contacts'


class Position(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'positions'

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'departments'

    def __str__(self):
        return self.name


class PositionDepartment(models.Model):
    position = models.OneToOneField(Position, models.CASCADE, related_name='department_link')
    department = models.ForeignKey(Department, models.CASCADE, related_name='position_links')

    class Meta:
        managed = True
        db_table = 'position_departments'


class Employee(models.Model):
    employee_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee', blank=True, null=True)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, blank=True, null=True, db_column='position')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, db_column='department')
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    hire_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    force_password_change = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'employees'


class EventParticipant(models.Model):
    event = models.ForeignKey('Event', models.CASCADE, blank=True, null=True)
    participant_type = models.CharField(max_length=20, blank=True, null=True)
    employee = models.ForeignKey(Employee, models.CASCADE, blank=True, null=True)
    partner = models.ForeignKey('Partner', models.CASCADE, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'event_participants'


class EventType(models.Model):
    name = models.CharField(unique=True, max_length=100)
    is_public = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'event_types'


class Event(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.ForeignKey(EventType, models.CASCADE, blank=True, null=True)
    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    project = models.ForeignKey('Project', models.CASCADE, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'events'


class PartnerType(models.Model):
    name = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'partner_types'


class Partner(models.Model):
    name = models.CharField(max_length=255)
    type = models.ForeignKey(PartnerType, models.CASCADE, blank=True, null=True)
    legal_form = models.CharField(max_length=100, blank=True, null=True)
    inn = models.CharField(max_length=12, blank=True, null=True)
    kpp = models.CharField(max_length=9, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'partners'


class ProjectParticipant(models.Model):
    project = models.ForeignKey('Project', models.CASCADE, blank=True, null=True)
    employee = models.ForeignKey(Employee, models.CASCADE, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'project_participant'
        unique_together = (('project', 'employee'),)

class ProjectPartner(models.Model):
    project = models.ForeignKey('Project', models.CASCADE, blank=True, null=True)
    partner = models.ForeignKey(Partner, models.CASCADE, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'project_partner'
        unique_together = (('project', 'partner'),)

class ProjectStatus(models.Model):
    name = models.CharField(unique=True, max_length=50)
    color_code = models.CharField(max_length=7, blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'project_statuses'


class ProjectTask(models.Model):
    project = models.ForeignKey('Project', models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True, default='в работе')
    priority = models.CharField(max_length=20, blank=True, null=True)
    assigned_to = models.ForeignKey(Employee, models.CASCADE, db_column='assigned_to', blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(Employee, models.CASCADE, related_name='created_tasks', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'project_tasks'
        
    def __str__(self):
        return self.name

    def get_assignees(self):
        """Возвращает список исполнителей задачи с fallback на legacy assigned_to."""
        employees = [assignment.employee for assignment in self.task_assignees.select_related('employee').all()]
        if employees:
            return employees
        return [self.assigned_to] if self.assigned_to else []

    def get_assignees_display(self):
        employees = self.get_assignees()
        return ", ".join(f"{employee.first_name} {employee.last_name}" for employee in employees)

    def get_chain_steps(self):
        return self.task_assignees.select_related('employee').order_by('step_order')

    def get_active_step(self):
        return self.task_assignees.select_related('employee').filter(
            step_status=TaskAssignee.STEP_STATUS_ACTIVE
        ).order_by('step_order').first()


class ProjectType(models.Model):
    name = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'project_types'


class Project(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    type = models.ForeignKey(ProjectType, models.CASCADE, blank=True, null=True)
    status = models.ForeignKey(ProjectStatus, models.CASCADE, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    manager = models.ForeignKey(Employee, models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'projects'


class ProjectExpenseRequest(models.Model):
    STATUS_PENDING_MANAGER = 'pending_manager'
    STATUS_NEEDS_ADMIN_REVIEW = 'needs_admin_review'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING_MANAGER, 'Ожидает руководителя'),
        (STATUS_NEEDS_ADMIN_REVIEW, 'Передано администратору'),
        (STATUS_APPROVED, 'Подтверждено'),
        (STATUS_REJECTED, 'Отклонено'),
    ]

    project = models.ForeignKey(Project, models.CASCADE, related_name='expense_requests')
    requested_by = models.ForeignKey(Employee, models.CASCADE, related_name='created_expense_requests')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expense_date = models.DateField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING_MANAGER)
    manager_comment = models.TextField(blank=True, null=True)
    admin_comment = models.TextField(blank=True, null=True)
    manager_decision_at = models.DateTimeField(blank=True, null=True)
    admin_decision_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'project_expense_requests'
        ordering = ['-created_at']


class ProjectClosureRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает решения администратора'),
        (STATUS_APPROVED, 'Подтверждено администратором'),
        (STATUS_REJECTED, 'Отклонено администратором'),
    ]

    project = models.ForeignKey(Project, models.CASCADE, related_name='closure_requests')
    requested_by = models.ForeignKey(Employee, models.CASCADE, related_name='created_closure_requests')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    manager_comment = models.TextField(blank=True, null=True)
    admin_comment = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(blank=True, null=True)
    seen_by_manager = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'project_closure_requests'
        ordering = ['-requested_at']


class ManagerProjectNotification(models.Model):
    """Уведомление о новом проекте для руководителя."""
    manager = models.ForeignKey(Employee, models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, models.CASCADE, blank=True, null=True)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'manager_project_notifications'


class EmployeeProjectAssignmentNotification(models.Model):
    """Уведомление о назначении сотрудника на проект."""
    employee = models.ForeignKey(Employee, models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, models.CASCADE, blank=True, null=True)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'employee_project_assignment_notifications'


class EmployeeTaskAssignmentNotification(models.Model):
    """Уведомление о назначении сотрудника на задачу."""
    employee = models.ForeignKey(Employee, models.CASCADE, blank=True, null=True)
    task = models.ForeignKey(ProjectTask, models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, models.CASCADE, blank=True, null=True)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'employee_task_assignment_notifications'
        unique_together = (('employee', 'task'),)

    def __str__(self):
        return f"Task notification for {self.employee} - {self.task.name}"


class TaskAttachment(models.Model):
    """Файлы, прикреплённые к задаче."""
    task = models.ForeignKey(ProjectTask, models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    uploaded_by = models.ForeignKey(Employee, models.SET_NULL, blank=True, null=True, related_name='uploaded_task_attachments')
    step_order = models.PositiveIntegerField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'task_attachments'

    def __str__(self):
        return f"Attachment for {self.task.name}: {self.file.name}"


class TaskAssignee(models.Model):
    """Связка задача -> сотрудник для назначения нескольких исполнителей."""
    STEP_STATUS_PENDING = 'pending'
    STEP_STATUS_ACTIVE = 'active'
    STEP_STATUS_COMPLETED = 'completed'
    STEP_STATUS_CHOICES = [
        (STEP_STATUS_PENDING, 'Ожидает'),
        (STEP_STATUS_ACTIVE, 'В работе'),
        (STEP_STATUS_COMPLETED, 'Завершен'),
    ]

    task = models.ForeignKey(ProjectTask, models.CASCADE, related_name='task_assignees')
    employee = models.ForeignKey(Employee, models.CASCADE, related_name='task_assignees')
    step_order = models.PositiveIntegerField(default=1)
    step_status = models.CharField(max_length=20, choices=STEP_STATUS_CHOICES, default=STEP_STATUS_PENDING)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'task_assignees'
        unique_together = (('task', 'employee'),)

    def __str__(self):
        return f"{self.task.name} -> {self.employee.first_name} {self.employee.last_name}"


class TaskChatMessage(models.Model):
    """Сообщение в чате задачи."""
    task = models.ForeignKey(ProjectTask, models.CASCADE, related_name='chat_messages')
    author = models.ForeignKey(Employee, models.CASCADE, related_name='task_chat_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'task_chat_messages'
        ordering = ['created_at']


class TaskChatAttachment(models.Model):
    """Вложение к сообщению чата задачи."""
    message = models.ForeignKey(TaskChatMessage, models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_chat_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'task_chat_attachments'


class TaskChatMessageNotification(models.Model):
    """Уведомление о новом сообщении в чате задачи."""
    task = models.ForeignKey(ProjectTask, models.CASCADE, related_name='task_chat_notifications')
    employee = models.ForeignKey(Employee, models.CASCADE, related_name='task_chat_notifications')
    message = models.ForeignKey(TaskChatMessage, models.CASCADE, related_name='notifications')
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'task_chat_message_notifications'
        unique_together = (('task', 'employee', 'message'),)


class ResourceType(models.Model):
    name = models.CharField(unique=True, max_length=100)
    category = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resource_types'


class ResourceUsage(models.Model):
    resource = models.ForeignKey('Resource', models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, models.CASCADE, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resource_usage'


class Resource(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.ForeignKey(ResourceType, models.CASCADE, blank=True, null=True)
    is_available = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resources'


class User(models.Model):
    employee = models.OneToOneField(Employee, models.DO_NOTHING, blank=True, null=True)
    username = models.CharField(unique=True, max_length=50)
    password_hash = models.TextField()
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.username


class ProjectChatMessage(models.Model):
    """Сообщение в чате проекта."""
    project = models.ForeignKey(Project, models.CASCADE, related_name='chat_messages')
    author = models.ForeignKey(Employee, models.CASCADE, related_name='chat_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'project_chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author} - {self.project.name} ({self.created_at})"


class ProjectChatAttachment(models.Model):
    """Прикрепленный файл к сообщению чата."""
    message = models.ForeignKey(ProjectChatMessage, models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='project_chat_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'project_chat_attachments'

    def __str__(self):
        return self.filename


class ProjectChatMessageNotification(models.Model):
    """Уведомление о новом сообщении в чате проекта для сотрудников."""
    project = models.ForeignKey(Project, models.CASCADE, related_name='chat_notifications')
    employee = models.ForeignKey(Employee, models.CASCADE, related_name='chat_notifications')
    message = models.ForeignKey(ProjectChatMessage, models.CASCADE)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'project_chat_message_notifications'
        unique_together = (('project', 'employee', 'message'),)
