from django.db import migrations, models


import logging

logger = logging.getLogger(__name__)

# Summary: Определяет операции миграции базы данных для этого модуля.
class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_task_workflow_and_chat'),
    ]

    operations = [
        migrations.CreateModel(
            name='PositionDepartment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='position_links', to='core.department')),
                ('position', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='department_link', to='core.position')),
            ],
            options={
                'db_table': 'position_departments',
                'managed': True,
            },
        ),
    ]
