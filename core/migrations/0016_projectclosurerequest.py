from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_taskchatmessagenotification'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectClosureRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Ожидает решения администратора'), ('approved', 'Подтверждено администратором'), ('rejected', 'Отклонено администратором')], default='pending', max_length=16)),
                ('manager_comment', models.TextField(blank=True, null=True)),
                ('admin_comment', models.TextField(blank=True, null=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('seen_by_manager', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='closure_requests', to='core.project')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_closure_requests', to='core.employee')),
            ],
            options={
                'db_table': 'project_closure_requests',
                'managed': True,
                'ordering': ['-requested_at'],
            },
        ),
    ]

