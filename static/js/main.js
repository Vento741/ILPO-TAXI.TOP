/**
 * УМНЫЙ ТАКСОПАРК - ОСНОВНОЙ JAVASCRIPT
 * Интерактивность для сайта таксопарка с ИИ-консультантом (OpenRouter API)
 */

// Яндекс.Метрика - Событийная аналитика
function trackEvent(eventName, params = {}) {
    if (typeof ym !== 'undefined') {
        ym(101852978, 'reachGoal', eventName, params);
        console.log('YM Event tracked:', eventName, params);
    }
}

// SEO Events tracking functions
function trackPhoneClick() {
    trackEvent('PHONE_CLICK', {
        'phone_number': '+7-927-374-81-51',
        'source': 'website'
    });
}

function trackChatOpen() {
    trackEvent('CHAT_OPEN', {
        'chat_type': 'ai_consultant',
        'source': 'website'
    });
}

function trackSignupClick() {
    const section = document.activeElement.closest('section');
    trackEvent('SIGNUP_CLICK', {
        'button_location': section ? section.id || 'unknown' : 'unknown',
        'source': 'website'
    });
}

function trackCalculatorUse() {
    trackEvent('CALCULATOR_USE', {
        'tool': 'earnings_calculator',
        'source': 'website'
    });
}

function trackManagerTransfer() {
    trackEvent('MANAGER_TRANSFER', {
        'from': 'ai_chat',
        'to': 'human_manager'
    });
}

function trackFormSubmit(formType) {
    trackEvent('FORM_SUBMIT', {
        'form_type': formType,
        'source': 'website'
    });
}

function trackSectionView(sectionName) {
    trackEvent('SECTION_VIEW', {
        'section': sectionName,
        'source': 'website'
    });
}

// Глобальные переменные
let chatWidget = null;
let chatToggle = null;
let chatBody = null;
let chatInput = null;
let isTyping = false;
let websocket = null;
let sessionId = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let heartbeatInterval = null;
let connectionCheckInterval = null;
let lastHeartbeat = null;
let touchStartY = 0;
let touchEndY = 0;
let isMobile = window.innerWidth < 768;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeElements();
    initializeEventListeners();
    initializePhoneMask();
    initializeFormValidation();
    initializeAnimations();
    initializeNavigation();

    // Задержка инициализации свайперов для мобильных устройств
    // if (isMobile) {
    //     setTimeout(() => {
    //         initBenefitsSwiper();
    //         initReviewsSwiper();
    //     }, 100);
    // } else {
    //     initBenefitsSwiper();
    //     initReviewsSwiper();
    // }

    initProcessTabs();
    initCounterAnimations();
    initScrollAnimations();
    initScrollToTop();
    initShrinkHeader();
    initPageVisibilityHandling();
    initChatSwipeGestures();

    console.log('🚀 ILPO-TAXI инициализирован с OpenRouter AI');
});

/**
 * Инициализация элементов DOM
 */
function initializeElements() {
    chatWidget = document.getElementById('chatWidget');
    chatToggle = document.getElementById('chatToggle');
    chatBody = document.getElementById('chatBody');
    chatInput = document.getElementById('chatInput');
}

/**
 * Инициализация обработчиков событий
 */
function initializeEventListeners() {
    // Обработчик отправки формы регистрации
    const quickRegForm = document.getElementById('quickRegForm');
    if (quickRegForm) {
        quickRegForm.addEventListener('submit', handleQuickRegistration);
    }

    // Обработчик Enter в чате
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // Закрытие чата по Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && chatWidget && chatWidget.classList.contains('open')) {
            closeChat();
        }
    });

    // Отслеживание изменения размера окна для определения мобильного устройства
    window.addEventListener('resize', function() {
        isMobile = window.innerWidth < 768;
    });

    // Инициализация навигации будет выполнена отдельно
}

/**
 * Инициализация свайп-жестов для чата на мобильных устройствах
 */
function initChatSwipeGestures() {
    if (!chatWidget || !chatWidget.querySelector('.chat-header')) return;

    const chatHeader = document.querySelector('.chat-header');

    if (chatHeader) {
        // Обработчики для свайпа вниз по заголовку чата
        chatHeader.addEventListener('touchstart', handleTouchStart, { passive: true });
        chatHeader.addEventListener('touchmove', handleTouchMove, { passive: false });
        chatHeader.addEventListener('touchend', handleTouchEnd, { passive: true });
    }

    // Добавляем обработчики и для всего виджета чата
    chatWidget.addEventListener('touchstart', handleTouchStart, { passive: true });
    chatWidget.addEventListener('touchmove', handleTouchMove, { passive: false });
    chatWidget.addEventListener('touchend', handleTouchEnd, { passive: true });
}

/**
 * Обработчики свайп-жестов
 */
function handleTouchStart(event) {
    touchStartY = event.touches[0].clientY;
}

function handleTouchMove(event) {
    if (!chatWidget.classList.contains('open')) return;

    touchEndY = event.touches[0].clientY;
    const touchDiff = touchEndY - touchStartY;

    // Если свайп вниз и начинается с верхней части чата
    if (touchDiff > 0 && touchStartY < 150) {
        // Предотвращаем стандартное поведение скролла
        event.preventDefault();

        // Применяем трансформацию для эффекта "тянущегося" чата
        const translateY = Math.min(touchDiff * 0.5, 200);
        chatWidget.style.transform = `translateY(${translateY}px)`;
        chatWidget.style.opacity = 1 - (translateY / 400);
    }
}

function handleTouchEnd(event) {
    if (!chatWidget.classList.contains('open')) return;

    const touchDiff = touchEndY - touchStartY;

    // Если свайп был достаточно длинным для закрытия чата
    if (touchDiff > 100 && touchStartY < 150) {
        closeChat();
    }

    // Возвращаем чат в исходное положение с анимацией
    chatWidget.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
    chatWidget.style.transform = '';
    chatWidget.style.opacity = '';

    // Убираем transition после завершения анимации
    setTimeout(() => {
        chatWidget.style.transition = '';
    }, 300);
}

/**
 * ЧАТ-ВИДЖЕТ С WEBSOCKET И OPENROUTER API
 */

// Открытие чата
function openChat() {
    if (!chatWidget || !chatToggle) return;

    // Трекинг события открытия чата
    trackChatOpen();

    chatWidget.classList.add('open');
    chatToggle.classList.add('hidden');

    // Блокируем прокрутку страницы на мобильных устройствах
    if (isMobile) {
        document.body.style.overflow = 'hidden';
    }

    // Подключаемся к WebSocket если еще не подключены
    if (!websocket || websocket.readyState === WebSocket.CLOSED) {
        connectWebSocket();
    }

    // Фокус на поле ввода
    setTimeout(() => {
        if (chatInput) chatInput.focus();

        // Прокручиваем чат вниз
        if (chatBody) {
            chatBody.scrollTop = chatBody.scrollHeight;
        }
    }, 300);

    trackEvent('chat_opened');
}

// Закрытие чата
function closeChat() {
    if (!chatWidget || !chatToggle) return;

    chatWidget.classList.remove('open');
    chatToggle.classList.remove('hidden');

    // Разблокируем прокрутку страницы на мобильных устройствах
    if (isMobile) {
        document.body.style.overflow = '';
    }

    // Не закрываем WebSocket при закрытии чата, но останавливаем heartbeat для экономии ресурсов
    // stopHeartbeat();

    trackEvent('chat_closed');
}

// Подключение к WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat${sessionId ? '?session_id=' + sessionId : ''}`;

    console.log('🔌 Подключение к WebSocket:', wsUrl);

    websocket = new WebSocket(wsUrl);

    websocket.onopen = function(event) {
        console.log('✅ WebSocket подключен');
        reconnectAttempts = 0;
        showConnectionStatus('connected');
        startHeartbeat();
    };

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    websocket.onclose = function(event) {
        console.log('❌ WebSocket отключен:', event.code, event.reason);
        showConnectionStatus('disconnected');
        stopHeartbeat();

        // Пытаемся переподключиться с экспоненциальной задержкой
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            showConnectionStatus('reconnecting');
            const delay = Math.min(2000 * Math.pow(2, reconnectAttempts - 1), 30000); // Максимум 30 секунд
            console.log(`🔄 Попытка переподключения ${reconnectAttempts}/${maxReconnectAttempts} через ${delay/1000}с`);
            setTimeout(() => connectWebSocket(), delay);
        } else {
            console.log('💔 Превышено максимальное количество попыток переподключения');
            showErrorMessage('Потеряно соединение с сервером. Попробуйте обновить страницу.');
            // Предлагаем ручное переподключение
            showReconnectButton();
        }
    };

    websocket.onerror = function(error) {
        console.error('❌ Ошибка WebSocket:', error);
        showConnectionStatus('error');
        stopHeartbeat();
    };
}

// Обработка сообщений от WebSocket
function handleWebSocketMessage(data) {
    console.log('📨 Получено сообщение:', data);

    // Отладочная информация для длинных сообщений
    if (data.content && data.content.length > 1000) {
        console.log(`🔍 Получено длинное сообщение: ${data.content.length} символов`);
        console.log(`🔍 Первые 200 символов:`, data.content.substring(0, 200));
        console.log(`🔍 Последние 200 символов:`, data.content.substring(data.content.length - 200));
    }

    switch (data.type) {
        case 'ai_message':
            hideTypingIndicator();
            addMessage(data.content, 'ai', {
                timestamp: data.timestamp,
                intent: data.intent,
                processing_time: data.processing_time,
                model: data.model
            });

            // Сохраняем session_id
            if (data.session_id) {
                sessionId = data.session_id;
            }
            break;

        case 'manager_message':
            hideTypingIndicator();
            addMessage(data.content, 'manager', {
                timestamp: data.timestamp,
                sender_name: data.sender_name,
                chat_id: data.chat_id
            });
            break;

        case 'system_message':
            hideTypingIndicator();
            addMessage(data.content, 'system', {
                timestamp: data.timestamp
            });

            // Проверяем статус чата для возврата к ИИ
            if (data.chat_status === 'ai_mode') {
                updateChatStatus('ai', 'ИИ-консультант');
                // Показываем кнопку переключения на менеджера снова
                showTransferToManagerButton();
            }
            break;

        case 'typing':
            showTypingIndicator();
            break;

        case 'pong':
            // Обновляем время последнего heartbeat
            lastHeartbeat = Date.now();
            console.log('💓 Heartbeat получен');
            break;

        case 'error':
            hideTypingIndicator();
            showErrorMessage('Ошибка: ' + data.content);
            break;

        default:
            console.log('🤷 Неизвестный тип сообщения:', data.type);
    }
}

// Функции для поддержания соединения (heartbeat)
function startHeartbeat() {
    stopHeartbeat(); // Очищаем предыдущий интервал если есть

    // Отправляем ping каждые 30 секунд
    heartbeatInterval = setInterval(() => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'ping',
                timestamp: new Date().toISOString()
            }));
            lastHeartbeat = Date.now();
        }
    }, 30000);

    // Проверяем состояние соединения каждые 5 секунд
    connectionCheckInterval = setInterval(() => {
        checkConnection();
    }, 5000);
}

function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
        connectionCheckInterval = null;
    }
}

function checkConnection() {
    if (!websocket) return;

    // Если WebSocket в состоянии CONNECTING слишком долго
    if (websocket.readyState === WebSocket.CONNECTING) {
        const now = Date.now();
        if (!lastHeartbeat || (now - lastHeartbeat) > 60000) { // 1 минута без ответа
            console.log('⚠️ Соединение зависло, принудительно переподключаемся');
            websocket.close();
        }
    }

    // Если соединение закрыто, но мы этого не заметили
    if (websocket.readyState === WebSocket.CLOSED && !reconnectAttempts) {
        console.log('🔄 Обнаружено неожиданное отключение, переподключаемся');
        connectWebSocket();
    }
}

function showReconnectButton() {
    const statusDiv = document.querySelector('.chat-status');
    if (statusDiv) {
        statusDiv.innerHTML = `
            <span style="color: #FF9500; cursor: pointer;" onclick="forceReconnect()">
                🟡 Соединение потеряно - нажмите для переподключения
            </span>
        `;
    }
}

function forceReconnect() {
    console.log('🔄 Принудительное переподключение по запросу пользователя');
    reconnectAttempts = 0; // Сбрасываем счетчик
    stopHeartbeat();
    if (websocket) {
        websocket.close();
    }
    connectWebSocket();
}

// Отправка сообщения через WebSocket
function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isTyping) return;

    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        showErrorMessage('Нет соединения с сервером. Попробуйте еще раз.');
        return;
    }

    // Добавляем сообщение пользователя
    addMessage(message, 'user');

    // Отправляем через WebSocket
    websocket.send(JSON.stringify({
        type: 'user_message',
        content: message,
        timestamp: new Date().toISOString()
    }));

    // Очищаем поле ввода
    chatInput.value = '';

    // Показываем индикатор печатания сразу после отправки сообщения
    setTimeout(() => {
        showTypingIndicator();
    }, 300);

    trackEvent('message_sent', {
        message_length: message.length,
        session_id: sessionId
    });
}

// Добавление сообщения в чат
function addMessage(content, sender, metadata = {}) {
    if (!chatBody) return;

    // Отладочная информация
    console.log('📨 Добавляется сообщение:', {
        sender: sender,
        contentLength: content.length,
        content: content,
        metadata: metadata
    });

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;

    if (sender === 'ai' && metadata.intent) {
        messageDiv.setAttribute('data-intent', metadata.intent);
        messageDiv.setAttribute('data-sender', 'ai');
    } else if (sender === 'manager') {
        messageDiv.setAttribute('data-sender', 'manager');
        messageDiv.setAttribute('data-chat-id', metadata.chat_id || '');
    } else if (sender === 'system') {
        messageDiv.setAttribute('data-sender', 'system');
    }

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    // Преобразуем Markdown в HTML для сообщений ИИ и менеджеров
    if (sender === 'ai' || sender === 'manager') {
        messageContent.innerHTML = convertMarkdownToHTML(content);
    } else {
        messageContent.textContent = content;
    }

    // Добавляем имя отправителя для менеджеров
    if (sender === 'manager' && metadata.sender_name) {
        const senderLabel = document.createElement('div');
        senderLabel.className = 'sender-label';
        senderLabel.textContent = `👨‍💼 ${metadata.sender_name}`;
        messageDiv.appendChild(senderLabel);
    }

    messageDiv.appendChild(messageContent);

    // Добавляем время
    const messageTime = document.createElement('div');
    messageTime.className = 'message-time';

    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    messageTime.textContent = timeString;

    messageDiv.appendChild(messageTime);

    // Добавляем сообщение в чат
    chatBody.appendChild(messageDiv);

    // Прокручиваем чат вниз
    chatBody.scrollTop = chatBody.scrollHeight;

    // Добавляем анимацию появления
    setTimeout(() => {
        messageDiv.classList.add('animate-in');
    }, 10);

    // Добавляем haptic feedback на мобильных устройствах
    if ((sender === 'ai' || sender === 'manager') && isMobile && window.navigator && window.navigator.vibrate) {
        window.navigator.vibrate(50);
    }

    return messageDiv;
}

// Простая конвертация Markdown в HTML
function convertMarkdownToHTML(text) {
    let html = text;

    // Сначала обрабатываем жирный текст, чтобы не конфликтовать со списками
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Разбиваем на строки для обработки списков
    const lines = html.split('\n');
    let resultLines = [];
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Проверяем, является ли строка элементом списка (начинается с * но не **)
        if (line.match(/^\*\s+(.+)$/) && !line.includes('<strong>')) {
            if (!inList) {
                resultLines.push('<ul>');
                inList = true;
            }
            const listContent = line.replace(/^\*\s+(.+)$/, '$1');
            resultLines.push(`<li>${listContent}</li>`);
        } else {
            // Если мы были в списке, закрываем его
            if (inList) {
                resultLines.push('</ul>');
                inList = false;
            }
            // Добавляем обычную строку (может быть пустой)
            if (line.length > 0) {
                resultLines.push(`<p>${line}</p>`);
            } else if (!inList) {
                resultLines.push('<br>');
            }
        }
    }

    // Закрываем список если он остался открытым
    if (inList) {
        resultLines.push('</ul>');
    }

    html = resultLines.join('');

    // Курсив (только одиночные звездочки, не затрагивая списки и жирный текст)
    html = html.replace(/\*([^*\n<>]+?)\*/g, '<em>$1</em>');

    // Ссылки [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // Убираем лишние <p></p>
    html = html.replace(/<p><\/p>/g, '');

    console.log('Converted HTML:', html); // Временная отладка

    return html;
}

// Показать индикатор печати
function showTypingIndicator() {
    if (isTyping) return;

    isTyping = true;
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-message ai-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <span class="typing-dots">
                <span></span><span></span><span></span>
            </span>
            ИИ-консультант печатает...
        </div>
    `;
    chatBody.appendChild(typingDiv);
    chatBody.scrollTop = chatBody.scrollHeight;

    // Добавляем дополнительную проверку видимости индикатора
    setTimeout(() => {
        if (typingDiv && typingDiv.parentNode) {
            // Убедимся, что индикатор видим
            chatBody.scrollTop = chatBody.scrollHeight;
        }
    }, 100);
}

// Скрыть индикатор печати
function hideTypingIndicator() {
    isTyping = false;
    const typingIndicator = chatBody.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Показать статус соединения
function showConnectionStatus(status) {
    const statusMap = {
        'connected': { text: 'Подключено к ИИ-консультанту', color: '#34C759', icon: '🟢' },
        'disconnected': { text: 'Соединение потеряно', color: '#FF9500', icon: '🟡' },
        'error': { text: 'Ошибка соединения', color: '#FF3B30', icon: '🔴' },
        'reconnecting': { text: 'Переподключение...', color: '#007AFF', icon: '🔄' }
    };

    const statusInfo = statusMap[status];
    if (!statusInfo) return;

    // Показываем статус в чате
    const statusDiv = document.querySelector('.chat-status') || document.createElement('div');
    statusDiv.className = `chat-status ${status === 'reconnecting' ? 'reconnecting' : ''}`;
    statusDiv.innerHTML = `
        <span style="color: ${statusInfo.color}">
            ${statusInfo.icon} ${statusInfo.text}
        </span>
    `;

    if (!document.querySelector('.chat-status')) {
        const chatHeader = chatWidget ? chatWidget.querySelector('.chat-header') : null;
        if (chatHeader) {
            chatHeader.appendChild(statusDiv);
        }
    }

    // Убираем статус через 3 секунды если это успешное подключение
    if (status === 'connected') {
        setTimeout(() => {
            statusDiv.style.opacity = '0';
            setTimeout(() => {
                if (statusDiv.parentNode) {
                    statusDiv.remove();
                }
            }, 300);
        }, 3000);
    }
}

/**
 * КАЛЬКУЛЯТОР ЗАРАБОТКА
 * Перенесен в отдельный модуль calculator.js
 */

/**
 * МАСКА ДЛЯ ТЕЛЕФОНА
 */
function initializePhoneMask() {
    const phoneInput = document.getElementById('phone');
    if (!phoneInput) return;

    phoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');

        if (value.length > 0) {
            if (value[0] !== '7') {
                value = '7' + value;
            }

            let formattedValue = '+7 ';
            if (value.length > 1) formattedValue += '(' + value.substring(1, 4);
            if (value.length >= 5) formattedValue += ') ' + value.substring(4, 7);
            if (value.length >= 8) formattedValue += '-' + value.substring(7, 9);
            if (value.length >= 10) formattedValue += '-' + value.substring(9, 11);

            e.target.value = formattedValue;
        }
    });

    phoneInput.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && e.target.value === '+7 (') {
            e.target.value = '';
        }
    });
}

/**
 * ВАЛИДАЦИЯ ФОРМ
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required]');

    inputs.forEach(input => {
        if (!input.value.trim()) {
            showFieldError(input, 'Это поле обязательно для заполнения');
            isValid = false;
        } else if (input.type === 'tel' && !isValidPhone(input.value)) {
            showFieldError(input, 'Введите корректный номер телефона');
            isValid = false;
        } else {
            clearFieldError(input);
        }
    });

    return isValid;
}

function isValidPhone(phone) {
    const phoneRegex = /^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$/;
    return phoneRegex.test(phone);
}

function showFieldError(input, message) {
    clearFieldError(input);

    input.classList.add('is-invalid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
}

function clearFieldError(input) {
    input.classList.remove('is-invalid');
    const errorDiv = input.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

/**
 * ОБРАБОТКА ФОРМЫ РЕГИСТРАЦИИ
 */
function handleQuickRegistration(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name') || document.getElementById('name').value,
        phone: formData.get('phone') || document.getElementById('phone').value,
        role: formData.get('role') || document.getElementById('role').value,
        agreement: document.getElementById('agreement').checked
    };

    // Показываем лоадер
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Отправляем...';

    // Имитируем отправку (в реальном приложении здесь будет API запрос)
    setTimeout(() => {
        showSuccessMessage('Заявка отправлена! Наш менеджер свяжется с вами в течение 30 минут.');
        e.target.reset();

        // Восстанавливаем кнопку
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;

        // Открываем чат с приветствием
        setTimeout(() => {
            openChat();
            addMessage(`Спасибо за заявку, ${data.name}! Я помогу вам с дополнительными вопросами о подключении.`, 'ai');
        }, 2000);

        trackEvent('registration_submitted', data);
    }, 2000);
}

/**
 * АНИМАЦИИ
 */
function initializeAnimations() {
    // Intersection Observer для анимаций при скролле
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationDelay = `${Math.random() * 0.3}s`;
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Наблюдаем за элементами для анимации
    document.querySelectorAll('.benefit-card, .review-card, .process-step').forEach(el => {
        observer.observe(el);
    });
}

/**
 * УТИЛИТЫ
 */

// Показать сообщение об успехе
function showSuccessMessage(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-message success';
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">✅</span>
            <span class="toast-text">${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    // Показываем тост
    setTimeout(() => toast.classList.add('show'), 100);

    // Убираем тост
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Показать сообщение об ошибке
function showErrorMessage(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-message error';
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">❌</span>
            <span class="toast-text">${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Отслеживание событий (заглушка для аналитики)
function trackEvent(eventName, eventData = {}) {
    console.log(`📊 Event: ${eventName}`, eventData);

    // Здесь можно добавить отправку в Google Analytics, Яндекс.Метрику и т.д.
    // gtag('event', eventName, eventData);
    // ym(COUNTER_ID, 'reachGoal', eventName, eventData);
}

// Добавляем стили для тостов
const toastStyles = `
    .toast-message {
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        padding: 16px 20px;
        z-index: 10000;
        transform: translateX(400px);
        transition: transform 0.3s ease;
        max-width: 400px;
    }
    
    .toast-message.show {
        transform: translateX(0);
    }
    
    .toast-message.success {
        border-left: 4px solid #34C759;
    }
    
    .toast-message.error {
        border-left: 4px solid #FF3B30;
    }
    
    .toast-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .toast-icon {
        font-size: 18px;
    }
    
    .toast-text {
        color: #21201F;
        font-weight: 500;
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease-out forwards;
    }
    
    .typing-dots {
        display: inline-flex;
        gap: 4px;
        margin-right: 8px;
    }
    
    .typing-dots span {
        width: 4px;
        height: 4px;
        background: #FFDB4D;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dots span:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-dots span:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typing {
        0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
`;

// Добавляем стили в head
const styleSheet = document.createElement('style');
styleSheet.textContent = toastStyles;
document.head.appendChild(styleSheet);

/**
 * НАВИГАЦИЯ И СКРОЛЛ ЭФФЕКТЫ
 */
function initializeNavigation() {
    const header = document.querySelector('.header-nav');
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

    // Эффект появления шапки при скролле
    window.addEventListener('scroll', function() {
        if (window.scrollY > 100) {
            if (header) header.classList.add('scrolled');
        } else {
            if (header) header.classList.remove('scrolled');
        }
    });

    // Плавная прокрутка к секциям
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection && header) {
                const headerHeight = header.offsetHeight;
                const targetPosition = targetSection.offsetTop - headerHeight - 30;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Экспортируем функции для глобального доступа
window.openChat = openChat;
window.closeChat = closeChat;
window.sendMessage = sendMessage;
window.forceReconnect = forceReconnect;

/* =============================================================================
   НОВЫЕ ИНТЕРАКТИВНЫЕ ФУНКЦИИ ДЛЯ BENEFITS И PROCESS
   ============================================================================= */

// Универсальная функция инициализации Swiper
function initSwiper(containerSelector, config) {
    const swiperInstance = new Swiper(containerSelector, {
        // Базовые настройки
        loop: true,
        speed: 600,
        grabCursor: true,
        watchOverflow: true,

        // Автопрокрутка
        autoplay: {
            delay: 4500,
            disableOnInteraction: false, // Автопрокрутка будет возобновляться после взаимодействия
            pauseOnMouseEnter: true, // Пауза при наведении курсора на десктопе
        },

        // Ленивая загрузка
        preloadImages: false,
        lazy: true,

        // Переданные настройки (slidesPerView, breakpoints, pagination, navigation)
        ...config,

        // Оптимизация производительности
        roundLengths: true,

        // Исправление проблем с touch-событиями
        touchRatio: 1,
        touchAngle: 45,
        simulateTouch: true, // Для совместимости с десктопом
        allowTouchMove: true,

        // Убираем ручное управление autoplay, которое вызывает проблемы
        on: {
            // Можно добавить обработчики, если нужно, но без управления autoplay
        }
    });

    // Добавляем обработчик изменения ориентации для мобильных
    if (window.innerWidth < 768) {
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                swiperInstance.update();
            }, 150);
        });
    }
}

// Вызов DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    const isMobile = window.innerWidth < 768;

    // Настройки для свайпера "Преимущества"
    initSwiper('.benefits-swiper', {
        slidesPerView: 1,
        spaceBetween: 20,
        pagination: {
            el: '.benefits-pagination',
            clickable: true,
            dynamicBullets: true,
        },
        navigation: {
            nextEl: '.benefits-next',
            prevEl: '.benefits-prev',
        },
        breakpoints: {
            480: { slidesPerView: 1, spaceBetween: 20 },
            768: { slidesPerView: 2, spaceBetween: 25 },
            1024: { slidesPerView: 2, spaceBetween: 30 },
            1200: { slidesPerView: 3, spaceBetween: 30 }
        }
    });

    // Настройки для свайпера "Отзывы"
    initSwiper('.reviews-swiper', {
        slidesPerView: 1,
        spaceBetween: 20,
        pagination: {
            el: '.reviews-pagination',
            clickable: true,
            dynamicBullets: true,
        },
        navigation: {
            nextEl: '.reviews-next',
            prevEl: '.reviews-prev',
        },
        breakpoints: {
            480: { slidesPerView: 1, spaceBetween: 20 },
            768: { slidesPerView: 2, spaceBetween: 25 },
            1024: { slidesPerView: 2, spaceBetween: 30 },
            1200: { slidesPerView: 3, spaceBetween: 30 }
        }
    });

    initProcessTabs();
    initCounterAnimations();
    initScrollAnimations();
    initScrollToTop();
    initShrinkHeader();
    initPageVisibilityHandling();
    initChatSwipeGestures();

    console.log('🚀 ILPO-TAXI инициализирован с OpenRouter AI');
});

// Переключение табов в Process секции
function initProcessTabs() {
    const roleTabs = document.querySelectorAll('.role-tab');
    const processContents = document.querySelectorAll('.process-content');

    roleTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetRole = this.dataset.role;

            // Убираем активный класс у всех табов
            roleTabs.forEach(t => t.classList.remove('active'));
            // Добавляем активный класс к текущему табу
            this.classList.add('active');

            // Скрываем все контенты
            processContents.forEach(content => {
                content.style.display = 'none';
                content.style.opacity = '0';
            });

            // Показываем нужный контент с анимацией
            const targetContent = document.getElementById(`${targetRole}-process`);
            if (targetContent) {
                targetContent.style.display = 'block';
                setTimeout(() => {
                    targetContent.style.opacity = '1';
                    // Запускаем анимацию шагов
                    animateTimelineSteps(targetContent);
                }, 50);
            }
        });
    });
}

// Анимация шагов в таймлайне
function animateTimelineSteps(container) {
    const steps = container.querySelectorAll('.timeline-step');
    steps.forEach((step, index) => {
        step.style.opacity = '0';
        step.style.transform = 'translateY(30px)';

        setTimeout(() => {
            step.style.transition = 'all 0.6s ease-out';
            step.style.opacity = '1';
            step.style.transform = 'translateY(0)';
        }, index * 200);
    });
}

// Анимация счетчиков в статистике
function initCounterAnimations() {
    const counters = document.querySelectorAll('.stat-number[data-count]');
    const options = {
        threshold: 0.5,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, options);

    counters.forEach(counter => observer.observe(counter));
}

// Функция анимации счетчика
function animateCounter(element) {
    const target = parseInt(element.dataset.count);
    const duration = 2000; // 2 секунды
    const increment = target / (duration / 16); // 60 FPS
    let current = 0;

    const updateCounter = () => {
        current += increment;
        if (current < target) {
            element.textContent = Math.floor(current).toLocaleString();
            requestAnimationFrame(updateCounter);
        } else {
            element.textContent = target.toLocaleString();
        }
    };

    updateCounter();
}

// Анимации при скролле
function initScrollAnimations() {
    const animateElements = document.querySelectorAll('.benefit-card-modern, .timeline-step, .stat-item');
    const options = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';

                // Добавляем задержку для каждого элемента в группе
                const siblings = Array.from(entry.target.parentElement.children);
                const index = siblings.indexOf(entry.target);
                entry.target.style.transitionDelay = `${index * 0.1}s`;
            }
        });
    }, options);

    animateElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(element);
    });
}

// Эффект параллакса для фоновых элементов
function initParallaxEffects() {
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.benefits-modern::before, .process-modern::before');

        parallaxElements.forEach(element => {
            const speed = 0.5;
            element.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });
}

// Добавляем эффект hover для карточек
function initCardHoverEffects() {
    const cards = document.querySelectorAll('.benefit-card-modern, .step-content');

    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// Инициализация дополнительных эффектов
document.addEventListener('DOMContentLoaded', function() {
    initParallaxEffects();
    initCardHoverEffects();

    // Добавляем плавное появление секций
    const sections = document.querySelectorAll('.benefits-modern, .process-modern');
    sections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(50px)';
        section.style.transition = 'opacity 1s ease-out, transform 1s ease-out';
    });

    // Анимация появления секций при загрузке
    setTimeout(() => {
        sections.forEach((section, index) => {
            setTimeout(() => {
                section.style.opacity = '1';
                section.style.transform = 'translateY(0)';
            }, index * 300);
        });
    }, 500);
});

// Добавляем интерактивность к кнопкам CTA
function initCTAButtons() {
    const ctaButtons = document.querySelectorAll('.pulse-btn');

    ctaButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Создаем эффект ripple
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple-effect');

            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * SCROLL TO TOP WIDGET
 */
function initScrollToTop() {
    // Создаем кнопку прокрутки наверх
    const scrollButton = document.createElement('button');
    scrollButton.className = 'scroll-to-top';
    scrollButton.innerHTML = '↑';
    scrollButton.setAttribute('aria-label', 'Прокрутить наверх');
    scrollButton.setAttribute('title', 'Наверх');

    document.body.appendChild(scrollButton);

    // Показываем/скрываем кнопку при скролле
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        if (scrollTop > 300) {
            scrollButton.classList.add('visible');
        } else {
            scrollButton.classList.remove('visible');
        }

        // Небольшая задержка для оптимизации
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            // Дополнительная логика если нужна
        }, 100);
    });

    // Обработчик клика
    scrollButton.addEventListener('click', function() {
        // Плавная прокрутка наверх
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });

        // Трекинг события
        trackEvent('scroll_to_top_clicked');
    });
}

/**
 * SHRINK HEADER ON SCROLL
 */
function initShrinkHeader() {
    const header = document.querySelector('.header-nav');
    if (!header) return;

    let lastScrollTop = 0;
    let scrollTimeout;

    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        // Добавляем класс scrolled при скролле вниз
        if (scrollTop > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        // Скрываем/показываем шапку при быстром скролле
        if (scrollTop > 200) {
            if (scrollTop > lastScrollTop && scrollTop > 300) {
                // Скролл вниз - скрываем шапку
                header.classList.add('hidden');
            } else {
                // Скролл вверх - показываем шапку
                header.classList.remove('hidden');
            }
        } else {
            // В верхней части страницы всегда показываем шапку
            header.classList.remove('hidden');
        }

        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;

        // Оптимизация производительности
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            // Дополнительная логика при остановке скролла
            if (header.classList.contains('hidden') && scrollTop < 200) {
                header.classList.remove('hidden');
            }
        }, 150);
    });

    // Показываем шапку при наведении мыши в верхнюю часть экрана
    document.addEventListener('mousemove', function(e) {
        if (e.clientY <= 80 && header.classList.contains('hidden')) {
            header.classList.remove('hidden');
        }
    });
}

// CSS для эффекта ripple (добавляется динамически)
const rippleCSS = `
.ripple-effect {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple 0.6s linear;
    pointer-events: none;
}

@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}
`;

// Добавляем CSS для ripple эффекта
const style = document.createElement('style');
style.textContent = rippleCSS;
document.head.appendChild(style);

// Обработка видимости страницы для управления соединением
function initPageVisibilityHandling() {
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // Страница скрыта - можем снизить частоту heartbeat
            console.log('📱 Страница скрыта, снижаем активность heartbeat');
        } else {
            // Страница видима - проверяем соединение
            console.log('📱 Страница видима, проверяем соединение');
            if (websocket && websocket.readyState !== WebSocket.OPEN) {
                console.log('🔄 Соединение потеряно пока страница была скрыта, переподключаемся');
                connectWebSocket();
            }
        }
    });
}

// Инициализация CTA кнопок
document.addEventListener('DOMContentLoaded', initCTAButtons);

// Функция переключения на живого менеджера
async function requestManagerTransfer() {
    // Трекинг события перевода на менеджера
    trackManagerTransfer();

    const transferBtn = document.getElementById('transferToManagerBtn');

    // Сначала запрашиваем данные клиента
    const clientData = await showClientDataForm();

    if (!clientData) {
        // Пользователь отменил
        return;
    }

    // Блокируем кнопку
    transferBtn.disabled = true;
    transferBtn.innerHTML = '⏳ Подключаем менеджера...';

    try {
        // Добавляем сообщение в чат
        addMessage('Пожалуйста, подождите, подключаю живого менеджера...', 'system');

        // Отправляем запрос на сервер
        const response = await fetch('/api/chat/transfer-to-manager', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                chat_history: getChatHistory(),
                client_name: clientData.name,
                client_phone: clientData.phone
            })
        });

        const result = await response.json();

        if (result.success) {
            // Сохраняем ID чата для отправки сообщений
            window.managerChatId = result.chat_id;
            window.supportChatId = result.support_chat_id;

            addMessage(
                `👤 **Менеджер ${result.manager_name} подключен!**\n\n` +
                'Сейчас с вами будет общаться живой специалист ILPO-TAXI. ' +
                'Он поможет с любыми вопросами по подключению и работе.',
                'system'
            );

            // Скрываем кнопку после успешного переключения
            transferBtn.style.display = 'none';

            // Обновляем статус чата
            updateChatStatus('manager', result.manager_name);

        } else {
            addMessage(
                result.message ||
                '😔 К сожалению, все менеджеры сейчас заняты. Попробуйте чуть позже или оставьте заявку на сайте.',
                'system'
            );

            // Восстанавливаем кнопку
            transferBtn.disabled = false;
            transferBtn.innerHTML = '👤 Связаться с живым менеджером';
        }

    } catch (error) {
        console.error('Ошибка переключения на менеджера:', error);
        addMessage('❌ Произошла ошибка. Попробуйте позже.', 'system');

        // Восстанавливаем кнопку
        transferBtn.disabled = false;
        transferBtn.innerHTML = '👤 Связаться с живым менеджером';
    }
}

// Получить историю чата для передачи менеджеру
function getChatHistory() {
    const messages = [];
    const chatMessages = document.querySelectorAll('.chat-message');

    chatMessages.forEach(msg => {
        const content = msg.querySelector('.message-content');
        const time = msg.querySelector('.message-time');
        const isAI = msg.classList.contains('ai-message');
        const isUser = msg.classList.contains('user-message');
        const isManager = msg.classList.contains('manager-message');
        const isSystem = msg.classList.contains('system-message');

        if (content && (isAI || isUser || isManager || isSystem)) {
            messages.push({
                role: isUser ? 'user' : (isAI ? 'assistant' : (isManager ? 'manager' : 'system')),
                content: content.textContent,
                timestamp: time ? time.textContent : new Date().toLocaleTimeString()
            });
        }
    });

    return messages;
}

// Функция показа формы для сбора данных клиента
function showClientDataForm() {
    return new Promise((resolve) => {
        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-user-tie me-2"></i>
                            Подключение к менеджеру
                        </h5>
                        <button type="button" class="btn-close" onclick="closeClientDataForm()"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted mb-4">
                            Для подключения к живому менеджеру нам нужна небольшая информация о вас:
                        </p>
                        <form id="clientDataForm">
                            <div class="mb-3">
                                <label for="clientName" class="form-label">
                                    <i class="fas fa-user me-1"></i>
                                    Ваше имя *
                                </label>
                                <input type="text" class="form-control" id="clientName" name="name" 
                                       placeholder="Например: Алексей" required maxlength="50">
                                <div class="invalid-feedback"></div>
                            </div>
                            <div class="mb-3">
                                <label for="clientPhone" class="form-label">
                                    <i class="fas fa-phone me-1"></i>
                                    Номер телефона *
                                </label>
                                <input type="tel" class="form-control" id="clientPhone" name="phone" 
                                       placeholder="+7 (999) 123-45-67" required>
                                <div class="invalid-feedback"></div>
                                <small class="form-text text-muted">
                                    Менеджер сможет позвонить вам при необходимости
                                </small>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="closeClientDataForm()">
                            <i class="fas fa-times me-1"></i>
                            Отмена
                        </button>
                        <button type="button" class="btn btn-primary" onclick="submitClientDataForm()">
                            <i class="fas fa-user-tie me-1"></i>
                            Подключить менеджера
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Инициализируем маску для телефона
        const phoneInput = modal.querySelector('#clientPhone');
        initPhoneMaskForInput(phoneInput);

        // Сохраняем resolve функцию для доступа из других функций
        window.clientDataFormResolve = resolve;

        // Фокус на первое поле
        setTimeout(() => {
            modal.querySelector('#clientName').focus();
        }, 100);

        // Обработка Enter для отправки формы
        modal.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitClientDataForm();
            }
        });

        // Обработка Escape для закрытия
        modal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeClientDataForm();
            }
        });
    });
}

// Закрытие формы данных клиента
function closeClientDataForm() {
    const modal = document.querySelector('.modal.show');
    if (modal) {
        modal.remove();
    }
    if (window.clientDataFormResolve) {
        window.clientDataFormResolve(null);
        window.clientDataFormResolve = null;
    }
}

// Отправка формы данных клиента
function submitClientDataForm() {
    const form = document.getElementById('clientDataForm');
    const nameInput = form.querySelector('#clientName');
    const phoneInput = form.querySelector('#clientPhone');

    let isValid = true;

    // Валидация имени
    if (!nameInput.value.trim()) {
        showFieldError(nameInput, 'Пожалуйста, введите ваше имя');
        isValid = false;
    } else if (nameInput.value.trim().length < 2) {
        showFieldError(nameInput, 'Имя должно содержать не менее 2 символов');
        isValid = false;
    } else {
        clearFieldError(nameInput);
    }

    // Валидация телефона
    if (!phoneInput.value.trim()) {
        showFieldError(phoneInput, 'Пожалуйста, введите номер телефона');
        isValid = false;
    } else if (!isValidPhone(phoneInput.value)) {
        showFieldError(phoneInput, 'Пожалуйста, введите корректный номер телефона');
        isValid = false;
    } else {
        clearFieldError(phoneInput);
    }

    if (!isValid) {
        return;
    }

    // Данные валидны - отправляем
    const clientData = {
        name: nameInput.value.trim(),
        phone: phoneInput.value.trim()
    };

    // Закрываем форму
    const modal = document.querySelector('.modal.show');
    if (modal) {
        modal.remove();
    }

    // Возвращаем данные
    if (window.clientDataFormResolve) {
        window.clientDataFormResolve(clientData);
        window.clientDataFormResolve = null;
    }
}

// Инициализация маски телефона для конкретного поля
function initPhoneMaskForInput(phoneInput) {
    if (!phoneInput) return;

    phoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');

        if (value.length > 0) {
            if (value[0] !== '7') {
                value = '7' + value;
            }

            let formattedValue = '+7 ';
            if (value.length > 1) formattedValue += '(' + value.substring(1, 4);
            if (value.length >= 5) formattedValue += ') ' + value.substring(4, 7);
            if (value.length >= 8) formattedValue += '-' + value.substring(7, 9);
            if (value.length >= 10) formattedValue += '-' + value.substring(9, 11);

            e.target.value = formattedValue;
        }
    });

    phoneInput.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && e.target.value === '+7 (') {
            e.target.value = '';
        }
    });
}

// Обновить статус чата
function updateChatStatus(status, managerName = 'ИИ-Консультант') {
    const chatHeader = document.querySelector('.chat-header .chat-info h5');
    const chatStatus = document.querySelector('.chat-header .chat-info .chat-status');

    if (status === 'manager') {
        if (chatHeader) chatHeader.textContent = `Менеджер ${managerName}`;
        if (chatStatus) chatStatus.textContent = 'Онлайн';
    } else {
        if (chatHeader) chatHeader.textContent = 'ИИ-Консультант';
        if (chatStatus) chatStatus.textContent = 'Онлайн';
    }
}

// Показать кнопку переключения на менеджера
function showTransferToManagerButton() {
    // Проверяем, есть ли уже кнопка
    let transferBtn = document.getElementById('transferToManagerBtn');

    if (!transferBtn) {
        // Создаем кнопку заново
        transferBtn = document.createElement('button');
        transferBtn.id = 'transferToManagerBtn';
        transferBtn.className = 'btn btn-outline-primary btn-sm mt-2';
        transferBtn.innerHTML = '👤 Связаться с живым менеджером';
        transferBtn.onclick = requestManagerTransfer;

        // Добавляем кнопку в чат
        const chatInput = document.querySelector('.chat-input');
        if (chatInput) {
            chatInput.appendChild(transferBtn);
        }
    } else {
        // Если кнопка уже есть, просто показываем её
        transferBtn.style.display = 'block';
        transferBtn.disabled = false;
        transferBtn.innerHTML = '👤 Связаться с живым менеджером';
    }
}