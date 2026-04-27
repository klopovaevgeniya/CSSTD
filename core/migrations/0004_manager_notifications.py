import logging

logger = logging.getLogger(__name__)

# Generated manually: create ManagerProjectNotification model
from django.db import migrations, models
import django.db.models.deletion


# Summary: Определяет операции миграции базы данных для этого модуля.
class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_department'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagerProjectNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seen', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(blank=True, null=True)),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.employee')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.project')),
            ],
            options={
                'db_table': 'manager_project_notifications',
            },
        ),
    ]
