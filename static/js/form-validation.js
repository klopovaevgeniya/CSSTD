// Summary: Глобальная валидация форм: очищает и подсвечивает только некорректные поля.
document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');
    const TEXT_LIKE_TYPES = new Set(['text', 'search', 'email', 'password', 'url', 'tel', 'number']);

    function isValidatableField(field) {
        if (!field || field.disabled) {
            return false;
        }
        const tag = field.tagName.toLowerCase();
        if (!['input', 'select', 'textarea'].includes(tag)) {
            return false;
        }
        const type = (field.type || '').toLowerCase();
        if (['button', 'submit', 'reset'].includes(type)) {
            return false;
        }
        if (type === 'hidden') {
            return field.dataset.validateHidden === 'true';
        }
        return field.willValidate;
    }

    function looksLikePhoneField(field) {
        const type = (field.type || '').toLowerCase();
        if (type === 'tel') {
            return true;
        }
        const marker = ((field.name || '') + ' ' + (field.id || '')).toLowerCase();
        return marker.includes('phone') || marker.includes('tel');
    }

    function getDependentValue(form, key) {
        const byName = form.querySelector('[name="' + key + '"]');
        if (byName) {
            return byName.value;
        }
        const byId = document.getElementById(key);
        return byId ? byId.value : '';
    }

    function validateField(field, form) {
        field.setCustomValidity('');
        const tag = field.tagName.toLowerCase();
        const type = (field.type || '').toLowerCase();
        const value = field.value || '';
        const trimmed = value.trim();

        if (field.required && (tag === 'textarea' || TEXT_LIKE_TYPES.has(type)) && trimmed.length === 0) {
            field.setCustomValidity('Поле не может состоять только из пробелов.');
            return false;
        }

        if (looksLikePhoneField(field) && trimmed.length > 0) {
            const digits = trimmed.replace(/[^\d]/g, '');
            if (!/^\d{10,15}$/.test(digits)) {
                field.setCustomValidity('Укажите корректный номер телефона.');
                return false;
            }
        }

        if (field.dataset.matchWith) {
            const target = document.getElementById(field.dataset.matchWith) || form.querySelector('[name="' + field.dataset.matchWith + '"]');
            if (target && value !== target.value) {
                field.setCustomValidity('Значения полей не совпадают.');
                return false;
            }
        }

        if (field.dataset.requiredWhen) {
            const parts = field.dataset.requiredWhen.split(':');
            const dependencyKey = parts[0] || '';
            const dependencyValue = parts[1] || '';
            if (dependencyKey && dependencyValue && getDependentValue(form, dependencyKey) === dependencyValue && trimmed.length === 0) {
                field.setCustomValidity('Поле обязательно для заполнения.');
                return false;
            }
        }

        return field.checkValidity();
    }

    function clearFieldValue(field) {
        const type = (field.type || '').toLowerCase();
        const tag = field.tagName.toLowerCase();
        if (type === 'checkbox' || type === 'radio') {
            field.checked = false;
            return;
        }
        if (type === 'file') {
            field.value = '';
            return;
        }
        if (tag === 'select') {
            field.value = '';
            return;
        }
        field.value = '';
    }

    function clearInvalidState(field) {
        field.classList.remove('is-invalid');
        field.removeAttribute('aria-invalid');
        const group = field.closest('.form-group');
        if (group) {
            group.classList.remove('has-invalid');
        }
        const uiSelect = field.closest('.ui-select');
        if (uiSelect) {
            uiSelect.classList.remove('has-error');
        }
        const uiDate = field.closest('.ui-date');
        if (uiDate) {
            uiDate.classList.remove('has-error');
        }
        if ((field.type || '').toLowerCase() === 'hidden' && field.id) {
            const displayInput = document.getElementById(field.id + '_display');
            if (displayInput) {
                displayInput.classList.remove('is-invalid');
                displayInput.removeAttribute('aria-invalid');
            }
        }
    }

    function setInvalidState(field) {
        field.classList.add('is-invalid');
        field.setAttribute('aria-invalid', 'true');
        const group = field.closest('.form-group');
        if (group) {
            group.classList.add('has-invalid');
        }
        const uiSelect = field.closest('.ui-select');
        if (uiSelect) {
            uiSelect.classList.add('has-error');
        }
        const uiDate = field.closest('.ui-date');
        if (uiDate) {
            uiDate.classList.add('has-error');
        }
        if ((field.type || '').toLowerCase() === 'hidden' && field.id) {
            const displayInput = document.getElementById(field.id + '_display');
            if (displayInput) {
                displayInput.classList.add('is-invalid');
                displayInput.setAttribute('aria-invalid', 'true');
            }
        }
    }

    function wireCleanup(field, form) {
        const eventName = field.tagName.toLowerCase() === 'select' ? 'change' : 'input';
        field.addEventListener(eventName, function () {
            if (validateField(field, form)) {
                clearInvalidState(field);
            }
        });

        field.addEventListener('change', function () {
            if (validateField(field, form)) {
                clearInvalidState(field);
            }
        });
    }

    forms.forEach(function (form) {
        const fields = Array.from(form.elements).filter(isValidatableField);
        fields.forEach(function (field) {
            wireCleanup(field, form);
        });

        form.addEventListener('submit', function (event) {
            const invalidFields = [];

            fields.forEach(function (field) {
                clearInvalidState(field);
                if (!validateField(field, form)) {
                    invalidFields.push(field);
                }
            });

            if (!invalidFields.length) {
                return;
            }

            event.preventDefault();

            invalidFields.forEach(function (field) {
                clearFieldValue(field);
                setInvalidState(field);
                field.setCustomValidity('');
            });

            invalidFields[0].focus();
        });
    });
});
