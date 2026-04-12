# Используем официальный образ Python 3.10 на базе Debian (slim-версия для уменьшения размера)
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их (слой кешируется, если requirements.txt не менялся)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Создаём непривилегированного пользователя для повышения безопасности
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Открываем порт, на котором работает приложение
EXPOSE 5000

# Команда запуска приложения
CMD ["python", "app.py"]