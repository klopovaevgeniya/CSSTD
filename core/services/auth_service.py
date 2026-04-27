from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth.models import User
from django.db import connection

import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для authenticate.
def authenticate(username, password):
    username = username.lower()  # Make username case-insensitive
    
    # Сначала попробуем Django User (новые пользователи)
    user = django_authenticate(username=username, password=password)
    if user:
        if user.is_active:
            try:
                employee = user.employee
                position = employee.position
                # Определяем роль на основе должности сотрудника
                if position and position.name == "Руководитель проекта":
                    role = 'project_manager'
                elif position and position.name == "Администратор":
                    role = 'admin'
                else:
                    role = 'employee'
                
                print(f"Django auth success: {username}, role: {role}")
                return {'id': user.id, 'role': role, 'force_password_change': employee.force_password_change}
            except Exception as e:
                print(f"Django auth: no employee for {username}: {e}")
                return None
        else:
            print(f"Django auth: user {username} not active")
            return None
    
    # Если не найден в Django User, проверим в старой таблице 'users' с crypt (старые пользователи)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, role
            FROM users
            WHERE username = %s
              AND crypt(%s, password_hash) = password_hash
              AND is_active = TRUE
        """, [username, password])
        row = cursor.fetchone()
        if row:
            print(f"Old user auth success: {username}, role: {row[1]}")
            return {'id': row[0], 'role': row[1]}
    
    print(f"Auth failed for: {username}")
    return None
