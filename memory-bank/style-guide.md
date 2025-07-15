# 🎨 STYLE GUIDE - ilpo-taxi.top

**Проект**: Умный Таксопарк с ИИ-агентом  
**Стиль**: Яндекс.Такси  
**Дата**: 2025-01-27  

---

## 🎨 ЦВЕТОВАЯ ПАЛИТРА (Яндекс.Такси)

### Основные цвета
```css
:root {
  /* Фирменный желтый Яндекс.Такси */
  --primary-yellow: #FFDB4D;
  --primary-yellow-dark: #F5C842;
  --primary-yellow-light: #FFF3A0;
  
  /* Черный основной */
  --primary-black: #21201F;
  --secondary-black: #2D2D2D;
  
  /* Серые тона */
  --gray-dark: #404040;
  --gray-medium: #737373;
  --gray-light: #E6E6E6;
  --gray-ultralight: #F5F5F5;
  
  /* Статусные цвета */
  --success-green: #34C759;
  --warning-orange: #FF9500;
  --error-red: #FF3B30;
  --info-blue: #007AFF;
}
```

### Применение цветов
- **Основной фон**: `#FFFFFF` (белый)
- **Акцентный цвет**: `#FFDB4D` (желтый Яндекс.Такси)
- **Текст основной**: `#21201F` (черный)
- **Текст вторичный**: `#737373` (серый средний)
- **Границы**: `#E6E6E6` (серый светлый)

---

## 📝 ТИПОГРАФИКА

### Шрифты
```css
/* Основной шрифт */
font-family: 'YS Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;

/* Заголовки */
.heading-1 { font-size: 32px; font-weight: 500; line-height: 1.25; }
.heading-2 { font-size: 24px; font-weight: 500; line-height: 1.33; }
.heading-3 { font-size: 20px; font-weight: 500; line-height: 1.4; }
.heading-4 { font-size: 16px; font-weight: 500; line-height: 1.5; }

/* Основной текст */
.body-large { font-size: 16px; font-weight: 400; line-height: 1.5; }
.body-medium { font-size: 14px; font-weight: 400; line-height: 1.43; }
.body-small { font-size: 12px; font-weight: 400; line-height: 1.33; }

/* Интерфейсный текст */
.ui-text { font-size: 14px; font-weight: 500; line-height: 1.43; }
.caption { font-size: 11px; font-weight: 400; line-height: 1.45; }
```

---

## 📏 СИСТЕМА ИНТЕРВАЛОВ

### Базовая единица: 4px

```css
/* Интервалы */
--space-xs: 4px;   /* 1 unit */
--space-s: 8px;    /* 2 units */
--space-m: 16px;   /* 4 units */
--space-l: 24px;   /* 6 units */
--space-xl: 32px;  /* 8 units */
--space-xxl: 48px; /* 12 units */

/* Радиусы скругления */
--radius-s: 4px;
--radius-m: 8px;
--radius-l: 12px;
--radius-xl: 16px;
--radius-full: 50%;
```

---

## 🔲 КОМПОНЕНТЫ

### Кнопки (Яндекс.Такси стиль)

#### Primary кнопка (Bootstrap 5 override)
```scss
// Bootstrap переменные
$primary: #FFDB4D;
$btn-border-radius: 8px;

// Кастомные стили
.btn-primary {
  background-color: $primary;
  border-color: $primary;
  color: #21201F;
  font-weight: 500;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #F5C842;
    border-color: #F5C842;
    color: #21201F;
    transform: translateY(-1px);
  }
  
  &:active, &.active {
    background-color: #E6B838;
    border-color: #E6B838;
    transform: translateY(0);
  }
}
```

#### Secondary кнопка (Bootstrap 5)
```scss
.btn-outline-primary {
  border-color: #FFDB4D;
  color: #21201F;
  font-weight: 500;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #FFDB4D;
    border-color: #FFDB4D;
    color: #21201F;
  }
  
  &:focus {
    box-shadow: 0 0 0 0.25rem rgba(255, 219, 77, 0.25);
  }
}
```

### Поля ввода (Bootstrap 5)
```scss
// Bootstrap переменные для форм
$input-border-color: #E6E6E6;
$input-focus-border-color: #FFDB4D;
$input-focus-box-shadow: 0 0 0 0.25rem rgba(255, 219, 77, 0.25);

.form-control {
  border: 2px solid $input-border-color;
  font-size: 16px;
  color: #21201F;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  
  &:focus {
    border-color: $input-focus-border-color;
    box-shadow: $input-focus-box-shadow;
  }
  
  &::placeholder {
    color: #737373;
  }
}
```

### Карточки (Bootstrap 5)
```scss
// Bootstrap переменные для карточек
$card-border-radius: 12px;
$card-border-color: #E6E6E6;

.card {
  border: 1px solid $card-border-color;
  border-radius: $card-border-radius;
  box-shadow: 0 2px 8px rgba(33, 32, 31, 0.08);
  transition: all 0.3s ease;
  
  .card-body {
    padding: 1.5rem; // 24px
  }
  
  &:hover {
    box-shadow: 0 4px 16px rgba(33, 32, 31, 0.12);
    transform: translateY(-2px);
  }
}
```

### Чат-виджет (специально для ИИ)
```css
.chat-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 380px;
  height: 520px;
  background: #FFFFFF;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(33, 32, 31, 0.16);
  border: 1px solid #E6E6E6;
  overflow: hidden;
  z-index: 1000;
}

.chat-header {
  background: linear-gradient(135deg, #FFDB4D 0%, #F5C842 100%);
  padding: 16px 20px;
  color: #21201F;
  font-weight: 500;
  font-size: 16px;
}

.chat-messages {
  height: 380px;
  overflow-y: auto;
  padding: 16px;
  background: #F5F5F5;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #E6E6E6;
  background: #FFFFFF;
}
```

---

## 🎯 ПРИНЦИПЫ ДИЗАЙНА

### 1. Простота и ясность
- Минималистичный интерфейс
- Четкая иерархия информации
- Интуитивно понятные элементы

### 2. Яндекс.Такси DNA
- Фирменный желтый как основной акцент
- Скругленные углы для дружелюбности
- Функциональность превыше всего

### 3. Доступность
- Контрастность текста не менее 4.5:1
- Поддержка навигации с клавиатуры
- Понятные подсказки и статусы

### 4. Отзывчивость
- Адаптация под мобильные устройства
- Быстрые анимации (≤ 300ms)
- Плавные переходы между состояниями

---

## 📱 АДАПТИВНОСТЬ

### Breakpoints (Bootstrap 5)
```scss
// Bootstrap 5 breakpoints
$grid-breakpoints: (
  xs: 0,
  sm: 576px,
  md: 768px,
  lg: 992px,
  xl: 1200px,
  xxl: 1400px
);
```

### Мобильные особенности
- Увеличенные области нажатия (min 44px)
- Упрощенная навигация
- Оптимизированные формы
- Сжатый контент

---

## 🔧 ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ

### CSS Framework
- **Bootstrap 5+** с кастомными переменными
- **CSS Custom Properties** для темизации
- **SCSS** для расширения Bootstrap компонентов

### Анимации
```css
/* Стандартные переходы */
.transition-smooth { transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
.transition-bounce { transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55); }

/* Микроанимации */
.hover-lift:hover { transform: translateY(-2px); }
.press:active { transform: scale(0.98); }
```

---

## ✅ ЧЕКЛИСТ СООТВЕТСТВИЯ

При создании нового компонента проверить:

- [ ] Используются цвета из палитры
- [ ] Шрифты соответствуют типографике
- [ ] Интервалы кратны базовой единице (4px)
- [ ] Скругления соответствуют системе
- [ ] Компонент адаптивен
- [ ] Доступность обеспечена
- [ ] Анимации плавные и быстрые
- [ ] Соответствует принципам Яндекс.Такси

---

**📝 Примечание**: Этот Style Guide является основой для всех дизайнерских решений в проекте ilpo-taxi.top. Все компоненты должны строго соответствовать этим принципам для обеспечения единообразия интерфейса. 