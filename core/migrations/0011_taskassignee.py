from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_auto_20260404_0926'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskAssignee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='task_assignees', to='core.employee')),
                ('task', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='task_assignees', to='core.projecttask')),
            ],
            options={
                'db_table': 'task_assignees',
                'managed': True,
                'unique_together': {('task', 'employee')},
            },
        ),
    ]
