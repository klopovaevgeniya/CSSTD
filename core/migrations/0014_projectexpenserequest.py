from django.db import migrations, models


import logging

logger = logging.getLogger(__name__)

# Summary: Определяет операции миграции базы данных для этого модуля.
class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_positiondepartment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectExpenseRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('expense_date', models.DateField()),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending_manager', 'Ожидает руководителя'), ('needs_admin_review', 'Передано администратору'), ('approved', 'Подтверждено'), ('rejected', 'Отклонено')], default='pending_manager', max_length=32)),
                ('manager_comment', models.TextField(blank=True, null=True)),
                ('admin_comment', models.TextField(blank=True, null=True)),
                ('manager_decision_at', models.DateTimeField(blank=True, null=True)),
                ('admin_decision_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='expense_requests', to='core.project')),
                ('requested_by', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='created_expense_requests', to='core.employee')),
            ],
            options={
                'db_table': 'project_expense_requests',
                'managed': True,
                'ordering': ['-created_at'],
            },
        ),
    ]
