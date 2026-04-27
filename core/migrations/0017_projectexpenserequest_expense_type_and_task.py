from django.db import migrations, models
import django.db.models.deletion


import logging

logger = logging.getLogger(__name__)

# Summary: Определяет операции миграции базы данных для этого модуля.
class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_projectclosurerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectexpenserequest',
            name='expense_type',
            field=models.CharField(
                choices=[('project', 'Трата по проекту'), ('task', 'Трата по задаче')],
                default='project',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='projectexpenserequest',
            name='task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='expense_requests',
                to='core.projecttask',
            ),
        ),
        migrations.RemoveField(
            model_name='projectexpenserequest',
            name='expense_date',
        ),
        migrations.AddConstraint(
            model_name='projectexpenserequest',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(expense_type='project', task__isnull=True)
                    | models.Q(expense_type='task', task__isnull=False)
                ),
                name='expense_task_required_for_task_type',
            ),
        ),
    ]
