from django.db import migrations, models


def seed_task_chain(apps, schema_editor):
    ProjectTask = apps.get_model('core', 'ProjectTask')
    TaskAssignee = apps.get_model('core', 'TaskAssignee')

    for task in ProjectTask.objects.all().iterator():
        assignees = list(TaskAssignee.objects.filter(task=task).order_by('id'))

        # Если ассайни нет, но есть legacy assigned_to — создаем первый этап.
        if not assignees and getattr(task, 'assigned_to_id', None):
            assignees = [
                TaskAssignee.objects.create(
                    task_id=task.id,
                    employee_id=task.assigned_to_id,
                )
            ]

        # Нормализуем порядок и статусы.
        active_found = False
        for index, assignee in enumerate(assignees, start=1):
            assignee.step_order = index
            if not active_found:
                assignee.step_status = 'active'
                active_found = True
            else:
                assignee.step_status = 'pending'
            assignee.save(update_fields=['step_order', 'step_status'])


def unseed_task_chain(apps, schema_editor):
    # Откат не требуется.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_taskassignee'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignee',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskassignee',
            name='started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskassignee',
            name='step_order',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='taskassignee',
            name='step_status',
            field=models.CharField(choices=[('pending', 'Ожидает'), ('active', 'В работе'), ('completed', 'Завершен')], default='pending', max_length=20),
        ),
        migrations.AddField(
            model_name='taskattachment',
            name='step_order',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskattachment',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='uploaded_task_attachments', to='core.employee'),
        ),
        migrations.CreateModel(
            name='TaskChatMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='task_chat_messages', to='core.employee')),
                ('task', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='chat_messages', to='core.projecttask')),
            ],
            options={
                'db_table': 'task_chat_messages',
                'managed': True,
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='TaskChatAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='task_chat_attachments/%Y/%m/%d/')),
                ('filename', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='attachments', to='core.taskchatmessage')),
            ],
            options={
                'db_table': 'task_chat_attachments',
                'managed': True,
            },
        ),
        migrations.RunPython(seed_task_chain, unseed_task_chain),
    ]
