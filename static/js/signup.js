// Глобальные переменные
let selectedCategory = '';
const categoryTitles = {
    'driver': 'Заявка водителя',
    'courier': 'Заявка курьера',
    'both': 'Заявка водителя + курьера',
    'cargo': 'Заявка на грузовые перевозки'
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    setupPhoneMask();
    setupFormValidation();
    setupConditionalFields();
    restoreFormProgress();
});

// Инициализация обработчиков событий
function initializeEventListeners() {
    // Обработка выбора категории
    const categoryCards = document.querySelectorAll('.category-card');
    categoryCards.forEach(card => {
        const selectBtn = card.querySelector('.select-btn');
        selectBtn.addEventListener('click', () => {
            selectedCategory = card.dataset.category;
            showForm();
        });
    });

    // Кнопка "Назад"
    const backBtn = document.getElementById('backBtn');
    backBtn.addEventListener('click', showCategories);

    // Отправка формы
    const signupForm = document.getElementById('signupForm');
    signupForm.addEventListener('submit', handleFormSubmit);
}

// Настройка условных полей
function setupConditionalFields() {
    // Показ/скрытие деталей автомобиля
    const hasCarField = document.getElementById('hasCar');
    if (hasCarField) {
        hasCarField.addEventListener('change', function() {
            const carDetails = document.querySelectorAll('.car-details');
            if (this.value === 'own') {
                carDetails.forEach(field => field.classList.remove('hidden'));
            } else {
                carDetails.forEach(field => field.classList.add('hidden'));
            }
        });
    }

    // Показ/скрытие полей для автокурьеров
    const transportField = document.getElementById('transport');
    if (transportField) {
        transportField.addEventListener('change', function() {
            const courierAutoFields = document.querySelectorAll('.courier-auto-field');
            if (this.value === 'car' || this.value === 'motorcycle') {
                courierAutoFields.forEach(field => field.classList.remove('hidden'));
            } else {
                courierAutoFields.forEach(field => field.classList.add('hidden'));
            }
        });
    }

    // Обработка множественного выбора для категорий доставки
    const allDeliveryCheckbox = document.querySelector('input[name="deliveryType"][value="all"]');
    if (allDeliveryCheckbox) {
        allDeliveryCheckbox.addEventListener('change', function() {
            const otherCheckboxes = document.querySelectorAll('input[name="deliveryType"]:not([value="all"])');
            if (this.checked) {
                otherCheckboxes.forEach(cb => {
                    cb.checked = false;
                    cb.disabled = true;
                });
            } else {
                otherCheckboxes.forEach(cb => {
                    cb.disabled = false;
                });
            }
        });
    }

    // Обработка других checkbox для категорий доставки
    const otherDeliveryCheckboxes = document.querySelectorAll('input[name="deliveryType"]:not([value="all"])');
    otherDeliveryCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked && allDeliveryCheckbox) {
                allDeliveryCheckbox.checked = false;
            }
        });
    });
}

// Показать форму для выбранной категории
function showForm() {
    const categorySelection = document.getElementById('categorySelection');
    const formContainer = document.getElementById('formContainer');
    const formTitle = document.getElementById('formTitle');

    // Анимация скрытия категорий
    categorySelection.style.opacity = '0';
    categorySelection.style.transform = 'translateY(-20px)';

    setTimeout(() => {
        categorySelection.style.display = 'none';

        // Настройка заголовка формы
        formTitle.textContent = categoryTitles[selectedCategory];

        // Показать/скрыть поля в зависимости от категории
        setupFormFields();

        // Показать форму с анимацией
        formContainer.style.display = 'block';
        setTimeout(() => {
            formContainer.style.opacity = '1';
            formContainer.style.transform = 'translateY(0)';
        }, 50);
    }, 300);
}

// Показать категории
function showCategories() {
    const categorySelection = document.getElementById('categorySelection');
    const formContainer = document.getElementById('formContainer');

    // Анимация скрытия формы
    formContainer.style.opacity = '0';
    formContainer.style.transform = 'translateY(20px)';

    setTimeout(() => {
        formContainer.style.display = 'none';

        // Показать категории с анимацией
        categorySelection.style.display = 'flex';
        setTimeout(() => {
            categorySelection.style.opacity = '1';
            categorySelection.style.transform = 'translateY(0)';
        }, 50);

        // Сбросить форму
        resetForm();
    }, 300);
}

// Настройка полей формы в зависимости от категории
function setupFormFields() {
    const driverFields = document.querySelectorAll('.driver-field');
    const courierFields = document.querySelectorAll('.courier-field');
    const cargoFields = document.querySelectorAll('.cargo-field');
    const experienceField = document.getElementById('experience');
    const transportField = document.getElementById('transport');
    const loadCapacityField = document.getElementById('loadCapacity');

    // Сброс всех полей
    driverFields.forEach(field => field.classList.remove('hidden'));
    courierFields.forEach(field => field.classList.remove('hidden'));
    cargoFields.forEach(field => field.classList.remove('hidden'));

    // Настройка обязательных полей
    experienceField.removeAttribute('required');
    transportField.removeAttribute('required');
    loadCapacityField.removeAttribute('required');

    switch (selectedCategory) {
        case 'driver':
            courierFields.forEach(field => field.classList.add('hidden'));
            cargoFields.forEach(field => field.classList.add('hidden'));
            experienceField.setAttribute('required', 'required');
            break;
        case 'courier':
            driverFields.forEach(field => field.classList.add('hidden'));
            cargoFields.forEach(field => field.classList.add('hidden'));
            transportField.setAttribute('required', 'required');
            break;
        case 'both':
            cargoFields.forEach(field => field.classList.add('hidden'));
            experienceField.setAttribute('required', 'required');
            transportField.setAttribute('required', 'required');
            break;
        case 'cargo':
            courierFields.forEach(field => field.classList.add('hidden'));
            experienceField.setAttribute('required', 'required');
            loadCapacityField.setAttribute('required', 'required');
            break;
    }

    // Скрыть условные поля по умолчанию
    document.querySelectorAll('.car-details').forEach(field => field.classList.add('hidden'));
    document.querySelectorAll('.courier-auto-field').forEach(field => field.classList.add('hidden'));
}

// Маска для телефона
function setupPhoneMask() {
    const phoneInput = document.getElementById('phone');

    phoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');

        if (value.length > 0) {
            if (value[0] === '8') {
                value = '7' + value.slice(1);
            }
            if (value[0] !== '7') {
                value = '7' + value;
            }
        }

        if (value.length >= 1) value = '+' + value;
        if (value.length >= 2) value = value.slice(0, 2) + ' (' + value.slice(2);
        if (value.length >= 7) value = value.slice(0, 7) + ') ' + value.slice(7);
        if (value.length >= 12) value = value.slice(0, 12) + '-' + value.slice(12);
        if (value.length >= 15) value = value.slice(0, 15) + '-' + value.slice(15, 17);

        e.target.value = value;
    });

    phoneInput.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && e.target.value === '+7 (') {
            e.target.value = '';
        }
    });
}

// Валидация формы
function setupFormValidation() {
    const form = document.getElementById('signupForm');
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');

    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
}

// Валидация отдельного поля
function validateField(e) {
    const field = e.target;
    const value = field.value.trim();

    // Удаляем предыдущие ошибки
    clearFieldError(e);

    // Проверяем только видимые поля
    if (field.closest('.hidden')) {
        return true;
    }

    if (!value && field.hasAttribute('required')) {
        showFieldError(field, 'Это поле обязательно для заполнения');
        return false;
    }

    // Специальная валидация для разных типов полей
    switch (field.type) {
        case 'email':
            if (value && !isValidEmail(value)) {
                showFieldError(field, 'Введите корректный email');
                return false;
            }
            break;
        case 'tel':
            if (value && !isValidPhone(value)) {
                showFieldError(field, 'Введите корректный номер телефона');
                return false;
            }
            break;
        case 'number':
            if (field.id === 'age') {
                if (value && (parseInt(value) < 16 || parseInt(value) > 70)) {
                    showFieldError(field, 'Возраст должен быть от 16 до 70 лет');
                    return false;
                }
            }
            if (field.id === 'experience') {
                if (value && (parseInt(value) < 1 || parseInt(value) > 50)) {
                    showFieldError(field, 'Стаж должен быть от 1 до 50 лет');
                    return false;
                }
            }
            if (field.id === 'carYear') {
                const currentYear = new Date().getFullYear();
                if (value && (parseInt(value) < 2000 || parseInt(value) > currentYear)) {
                    showFieldError(field, `Год выпуска должен быть от 2000 до ${currentYear}`);
                    return false;
                }
            }
            break;
    }

    // Валидация имени
    if (field.id === 'fullName') {
        if (value && !isValidFullName(value)) {
            showFieldError(field, 'Введите полное имя (Фамилия Имя Отчество)');
            return false;
        }
    }

    return true;
}

// Показать ошибку поля
function showFieldError(field, message) {
    field.style.borderColor = '#ff5252';

    // Создаем элемент ошибки, если его нет
    let errorElement = field.parentNode.querySelector('.field-error');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'field-error';
        errorElement.style.color = '#ff5252';
        errorElement.style.fontSize = '0.8rem';
        errorElement.style.marginTop = '5px';
        field.parentNode.appendChild(errorElement);
    }

    errorElement.textContent = message;
}

// Очистить ошибку поля
function clearFieldError(e) {
    const field = e.target;
    field.style.borderColor = '#e0e0e0';

    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// Валидация email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Валидация телефона
function isValidPhone(phone) {
    const phoneRegex = /^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$/;
    return phoneRegex.test(phone);
}

// Валидация полного имени
function isValidFullName(name) {
    const nameRegex = /^[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(\s+[А-ЯЁ][а-яё]+)?$/;
    return nameRegex.test(name.trim());
}

// Обработка отправки формы
async function handleFormSubmit(e) {
    e.preventDefault();

    // Валидация всех полей
    const form = e.target;
    const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    requiredInputs.forEach(input => {
        // Проверяем только видимые поля
        if (!input.closest('.hidden') && !validateField({ target: input })) {
            isValid = false;
        }
    });

    // Проверка обязательных checkbox-групп
    if (selectedCategory === 'courier' || selectedCategory === 'both') {
        const deliveryTypes = document.querySelectorAll('input[name="deliveryType"]:checked');
        if (deliveryTypes.length === 0) {
            showNotification('Выберите хотя бы одну категорию доставки', 'error');
            isValid = false;
        }
    }

    if (!isValid) {
        showNotification('Пожалуйста, исправьте ошибки в форме', 'error');
        // Прокрутка к первой ошибке
        const firstError = form.querySelector('.field-error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }

    // Собираем данные формы
    const formData = collectFormData(form);

    // Показываем загрузку
    showLoadingState();

    // Отправляем данные на сервер
    try {
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        hideLoadingState();

        if (result.success) {
            showSuccessMessage();
            clearSavedProgress();
            showNotification(result.message || 'Заявка успешно отправлена!', 'success');
        } else {
            showNotification(result.error || 'Произошла ошибка при отправке заявки', 'error');
        }

    } catch (error) {
        hideLoadingState();
        console.error('Ошибка отправки формы:', error);
        showNotification('Ошибка соединения с сервером. Попробуйте позже.', 'error');
    }
}

// Сбор данных формы
function collectFormData(form) {
    const formData = new FormData(form);
    const data = {
        category: selectedCategory,
        timestamp: new Date().toISOString()
    };

    // Обычные поля
    for (let [key, value] of formData.entries()) {
        if (value.trim() && key !== 'deliveryType' && key !== 'documents') {
            data[key] = value.trim();
        }
    }

    // Обработка множественных checkbox-полей
    const deliveryTypes = [];
    const checkedDeliveryTypes = form.querySelectorAll('input[name="deliveryType"]:checked');
    checkedDeliveryTypes.forEach(checkbox => {
        deliveryTypes.push(checkbox.value);
    });
    if (deliveryTypes.length > 0) {
        data.deliveryType = deliveryTypes;
    }

    const documents = [];
    const checkedDocuments = form.querySelectorAll('input[name="documents"]:checked');
    checkedDocuments.forEach(checkbox => {
        documents.push(checkbox.value);
    });
    if (documents.length > 0) {
        data.documents = documents;
    }

    return data;
}

// Показать состояние загрузки
function showLoadingState() {
    const submitBtn = document.querySelector('.submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправляем...';
    submitBtn.style.opacity = '0.7';
}

// Скрыть состояние загрузки
function hideLoadingState() {
    const submitBtn = document.querySelector('.submit-btn');
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Отправить заявку';
    submitBtn.style.opacity = '1';
}

// Показать сообщение об успехе
function showSuccessMessage() {
    const formContainer = document.getElementById('formContainer');
    const successMessage = document.getElementById('successMessage');

    // Анимация скрытия формы
    formContainer.style.opacity = '0';
    formContainer.style.transform = 'translateY(-20px)';

    setTimeout(() => {
        formContainer.style.display = 'none';

        // Показать сообщение об успехе
        successMessage.style.display = 'block';
        setTimeout(() => {
            successMessage.style.opacity = '1';
            successMessage.style.transform = 'translateY(0)';
        }, 50);

        // Прокрутка к сообщению об успехе
        successMessage.scrollIntoView({ behavior: 'smooth' });
    }, 300);
}

// Сброс формы
function resetForm() {
    const form = document.getElementById('signupForm');
    form.reset();

    // Очистить все ошибки
    const errorElements = form.querySelectorAll('.field-error');
    errorElements.forEach(error => error.remove());

    // Сбросить стили полей
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.style.borderColor = '#e0e0e0';
    });

    // Сбросить состояние checkbox-полей
    const allDeliveryCheckbox = document.querySelector('input[name="deliveryType"][value="all"]');
    if (allDeliveryCheckbox) {
        allDeliveryCheckbox.checked = false;
    }

    const otherDeliveryCheckboxes = document.querySelectorAll('input[name="deliveryType"]:not([value="all"])');
    otherDeliveryCheckboxes.forEach(cb => {
        cb.checked = false;
        cb.disabled = false;
    });

    selectedCategory = '';
}

// Показать уведомление
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 10px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        max-width: 300px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    `;

    if (type === 'error') {
        notification.style.background = 'linear-gradient(135deg, #ff5252, #f44336)';
    } else if (type === 'success') {
        notification.style.background = 'linear-gradient(135deg, #4caf50, #45a049)';
    } else {
        notification.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
    }

    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    // Анимация появления
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);

    // Автоматическое скрытие
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 5000);

    // Клик для закрытия
    notification.addEventListener('click', () => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    });
}

// Анимация при скролле (для улучшения UX)
function setupScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Наблюдаем за элементами, которые должны анимироваться
    const animatedElements = document.querySelectorAll('.category-card, .form-section');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// Запуск анимаций после загрузки
window.addEventListener('load', () => {
    setupScrollAnimations();
});

// Обработка изменения размера окна
window.addEventListener('resize', () => {
    // Адаптивные корректировки при необходимости
});

// Предотвращение отправки формы при нажатии Enter в текстовых полях
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type !== 'submit') {
        e.preventDefault();

        // Переходим к следующему полю
        const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([disabled]):not(.hidden), select:not([disabled]):not(.hidden), textarea:not([disabled]):not(.hidden)'));
        const visibleInputs = inputs.filter(input => !input.closest('.hidden'));
        const currentIndex = visibleInputs.indexOf(e.target);

        if (currentIndex < visibleInputs.length - 1) {
            visibleInputs[currentIndex + 1].focus();
        }
    }
});

// Сохранение прогресса заполнения формы в localStorage
function saveFormProgress() {
    if (!selectedCategory) return;

    const form = document.getElementById('signupForm');
    const formData = new FormData(form);
    const data = {};

    for (let [key, value] of formData.entries()) {
        if (key !== 'deliveryType' && key !== 'documents') {
            data[key] = value;
        }
    }

    // Сохранение checkbox-групп
    const deliveryTypes = [];
    const checkedDeliveryTypes = form.querySelectorAll('input[name="deliveryType"]:checked');
    checkedDeliveryTypes.forEach(checkbox => {
        deliveryTypes.push(checkbox.value);
    });
    if (deliveryTypes.length > 0) {
        data.deliveryType = deliveryTypes;
    }

    const documents = [];
    const checkedDocuments = form.querySelectorAll('input[name="documents"]:checked');
    checkedDocuments.forEach(checkbox => {
        documents.push(checkbox.value);
    });
    if (documents.length > 0) {
        data.documents = documents;
    }

    localStorage.setItem('ilpo_signup_progress', JSON.stringify({
        category: selectedCategory,
        data: data,
        timestamp: Date.now()
    }));
}

// Восстановление прогресса заполнения формы
function restoreFormProgress() {
    const saved = localStorage.getItem('ilpo_signup_progress');
    if (!saved) return;

    try {
        const progress = JSON.parse(saved);

        // Проверяем, не устарел ли прогресс (24 часа)
        if (Date.now() - progress.timestamp > 24 * 60 * 60 * 1000) {
            localStorage.removeItem('ilpo_signup_progress');
            return;
        }

        selectedCategory = progress.category;

        // Заполняем поля
        Object.entries(progress.data).forEach(([key, value]) => {
            if (key === 'deliveryType' && Array.isArray(value)) {
                value.forEach(type => {
                    const checkbox = document.querySelector(`input[name="deliveryType"][value="${type}"]`);
                    if (checkbox) checkbox.checked = true;
                });
            } else if (key === 'documents' && Array.isArray(value)) {
                value.forEach(doc => {
                    const checkbox = document.querySelector(`input[name="documents"][value="${doc}"]`);
                    if (checkbox) checkbox.checked = true;
                });
            } else {
                const field = document.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = value;
                    if (field.type === 'checkbox') {
                        field.checked = value === 'on';
                    }
                }
            }
        });

        showForm();
    } catch (e) {
        localStorage.removeItem('ilpo_signup_progress');
    }
}

// Автосохранение прогресса
setInterval(() => {
    if (selectedCategory && document.getElementById('formContainer').style.display !== 'none') {
        saveFormProgress();
    }
}, 30000); // Каждые 30 секунд

// Очистка сохраненного прогресса при успешной отправке
function clearSavedProgress() {
    localStorage.removeItem('ilpo_signup_progress');
}