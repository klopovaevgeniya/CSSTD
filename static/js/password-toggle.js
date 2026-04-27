// Summary: Файл `static/js/password-toggle.js`: содержит код и настройки для раздела "password toggle".
document.addEventListener('DOMContentLoaded', function () {
    const toggleButtons = document.querySelectorAll('[data-password-toggle]');

    toggleButtons.forEach(function (button) {
        const targetId = button.getAttribute('data-target');
        const input = targetId ? document.getElementById(targetId) : null;
        const icon = button.querySelector('i');

        if (!input || !icon) {
            return;
        }

        button.addEventListener('click', function (event) {
            event.preventDefault();
            const isHidden = input.type === 'password';

            input.type = isHidden ? 'text' : 'password';
            icon.classList.toggle('fa-eye', !isHidden);
            icon.classList.toggle('fa-eye-slash', isHidden);
            button.setAttribute('aria-label', isHidden ? 'Скрыть пароль' : 'Показать пароль');
            button.setAttribute('aria-pressed', isHidden ? 'true' : 'false');
        });
    });
});
