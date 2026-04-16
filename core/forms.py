from django import forms
from .models import ProjectStatus, ProjectType, Employee, ProjectTask

class LoginForm(forms.Form):
    username = forms.CharField(label='Логин', max_length=50)
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput
    )
    
class ProjectForm(forms.Form):
    name = forms.CharField(
        label='Название проекта',
        max_length=255
    )

    code = forms.CharField(
        label='Код проекта',
        max_length=50,
        required=False
    )

    status = forms.ModelChoiceField(
        label='Статус',
        queryset=ProjectStatus.objects.all(),
        required=False
    )

    type = forms.ModelChoiceField(
        label='Тип проекта',
        queryset=ProjectType.objects.all(),
        required=False
    )

    manager = forms.ModelChoiceField(
        label='Руководитель проекта',
        queryset=Employee.objects.all(),
        required=False
    )

    budget = forms.DecimalField(
        label='Бюджет',
        required=False,
        max_digits=15,
        decimal_places=2
    )

    start_date = forms.DateField(
        label='Дата начала',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    end_date = forms.DateField(
        label='Дата окончания',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    description = forms.CharField(
        label='Описание',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4})
    )

class ProjectTaskForm(forms.Form):
    """Форма для создания и редактирования задачи в проекте."""
    name = forms.CharField(
        label='Название задачи',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите название задачи'
        })
    )

    description = forms.CharField(
        label='Описание',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите описание задачи (опционально)'
        })
    )

    assigned_to = forms.ModelMultipleChoiceField(
        label='Назначить сотрудникам',
        queryset=Employee.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': 6})
    )

    due_date = forms.DateField(
        label='Дата сдачи',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    priority = forms.ChoiceField(
        label='Приоритет',
        required=False,
        choices=[
            ('низкий', 'Низкий'),
            ('средний', 'Средний'),
            ('высокий', 'Высокий'),
            ('критический', 'Критический'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    status = forms.ChoiceField(
        label='Статус',
        required=False,
        choices=[
            ('в работе', 'В работе'),
            ('завершена', 'Завершена'),
            ('на проверке', 'На проверке'),
            ('отложена', 'Отложена'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='в работе'
    )

