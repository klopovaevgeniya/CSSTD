# Инструкция по запуску проекта

## Запуск через Docker

1. Убедитесь, что у вас установлен Docker и Docker Compose.
2. Откройте терминал в корне проекта.
3. Выполните команду:


docker-compose up --build


4. Приложение будет доступно по адресу http://localhost:8000 (или другому, если указан в настройках).
5. Для остановки контейнеров используйте:

docker-compose down

 Запуск без Docker (локально)

1. Убедитесь, что у вас установлен Python 3.10+ и pip.
2. Создайте и активируйте виртуальное окружение:

Windows:
python -m venv env
./env/Scripts/activate

Linux/MacOS:
python3 -m venv env
source env/bin/activate

3. Установите зависимости:
pip install -r requirements.txt

4. Примените миграции:
python manage.py migrate

5. Запустите сервер:
python manage.py runserver


6. Откройте браузер и перейдите по адресу http://localhost:8000

Вводимые данные для ручного пользования: 
- Авторизация за админстратора
    Логин: klopo Пароль: klopo123
-Авторизация за руководителя пользователя:
    Логин: serdyuk1 Пароль: a6hyzDx1
- Авторизация за сотрудника:
    Логин: klopova Пароль: F1vcn9eT

Примечания:
- Для доступа к админке используйте /admin
- Для создания суперпользователя выполните:

python manage.py createsuperuser
