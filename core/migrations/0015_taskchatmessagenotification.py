from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_projectexpenserequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskChatMessageNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seen', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_chat_notifications', to='core.employee')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='core.taskchatmessage')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_chat_notifications', to='core.projecttask')),
            ],
            options={
                'db_table': 'task_chat_message_notifications',
                'managed': True,
                'unique_together': {('task', 'employee', 'message')},
            },
        ),
    ]
