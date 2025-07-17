/**
 * КАЛЬКУЛЯТОР ЗАРАБОТКА - МОДУЛЬ
 * Расчет заработка для разных типов работы и городов
 */

// Данные по городам и коэффициентам заработка
const CITY_DATA = {
    'moscow': {
        name: 'Москва',
        coefficient: 1.5,
        avgOrder: {
            taxi: 450,
            courier_car: 350,
            courier_walk: 200,
            courier_bike: 250,
            cargo: 800
        }
    },
    'spb': {
        name: 'Санкт-Петербург',
        coefficient: 1.3,
        avgOrder: {
            taxi: 400,
            courier_car: 320,
            courier_walk: 180,
            courier_bike: 230,
            cargo: 750
        }
    },
    'ekb': {
        name: 'Екатеринбург',
        coefficient: 1.1,
        avgOrder: {
            taxi: 350,
            courier_car: 280,
            courier_walk: 150,
            courier_bike: 200,
            cargo: 650
        }
    },
    'nsk': {
        name: 'Новосибирск',
        coefficient: 1.0,
        avgOrder: {
            taxi: 320,
            courier_car: 260,
            courier_walk: 140,
            courier_bike: 180,
            cargo: 600
        }
    },
    'penza': {
        name: 'Пенза',
        coefficient: 0.8,
        avgOrder: {
            taxi: 280,
            courier_car: 220,
            courier_walk: 120,
            courier_bike: 150,
            cargo: 500
        }
    },
    'kazan': {
        name: 'Казань',
        coefficient: 1.0,
        avgOrder: {
            taxi: 330,
            courier_car: 270,
            courier_walk: 145,
            courier_bike: 185,
            cargo: 620
        }
    },
    'other': {
        name: 'Остальные регионы',
        coefficient: 0.85,
        avgOrder: {
            taxi: 300,
            courier_car: 240,
            courier_walk: 130,
            courier_bike: 160,
            cargo: 520
        }
    }
};

// Данные по типам работы
const JOB_TYPES = {
    'taxi': {
        name: 'Водитель такси',
        icon: '🚗',
        ordersPerHour: 2.5,
        driverPercent: 0.85,
        description: 'Перевозка пассажиров',
        minHours: 4,
        maxHours: 12
    },
    'courier_car': {
        name: 'Курьер на авто',
        icon: '🚙',
        ordersPerHour: 3,
        driverPercent: 0.8,
        description: 'Доставка на автомобиле',
        minHours: 4,
        maxHours: 12
    },
    'courier_walk': {
        name: 'Пеший курьер',
        icon: '🚶',
        ordersPerHour: 2,
        driverPercent: 0.9,
        description: 'Доставка пешком',
        minHours: 4,
        maxHours: 12
    },
    'courier_bike': {
        name: 'Курьер на велосипеде/самокате',
        icon: '🚴',
        ordersPerHour: 2.5,
        driverPercent: 0.85,
        description: 'Доставка на велосипеде/самокате',
        minHours: 4,
        maxHours: 12
    },
    'cargo': {
        name: 'Грузовые перевозки',
        icon: '🚛',
        ordersPerHour: 1.5,
        driverPercent: 0.75,
        description: 'Перевозка грузов',
        minHours: 4,
        maxHours: 12
    }
};

class EarningsCalculator {
    constructor() {
        this.currentCity = 'penza';
        this.currentJobType = 'taxi';
        this.elements = {};
        this.init();
    }

    init() {
        this.bindElements();
        this.setupEventListeners();
        this.populateCitySelect();
        this.populateJobTypeSelect();
        this.updateJobTypeInfo();
        this.calculateEarnings();
    }

    bindElements() {
        this.elements = {
            citySelect: document.getElementById('citySelect'),
            jobTypeSelect: document.getElementById('jobTypeSelect'),
            hoursPerDay: document.getElementById('hoursPerDay'),
            daysPerWeek: document.getElementById('daysPerWeek'),
            hoursValue: document.getElementById('hoursValue'),
            daysValue: document.getElementById('daysValue'),
            monthlyEarning: document.getElementById('monthlyEarning'),
            dailyEarning: document.getElementById('dailyEarning'),
            weeklyEarning: document.getElementById('weeklyEarning'),
            jobTypeInfo: document.getElementById('jobTypeInfo'),
            avgOrderInfo: document.getElementById('avgOrderInfo'),
            ordersPerHourInfo: document.getElementById('ordersPerHourInfo')
        };
    }

    setupEventListeners() {
        if (this.elements.citySelect) {
            this.elements.citySelect.addEventListener('change', () => {
                this.currentCity = this.elements.citySelect.value;
                this.updateJobTypeInfo();
                this.calculateEarnings();
            });
        }

        if (this.elements.jobTypeSelect) {
            this.elements.jobTypeSelect.addEventListener('change', () => {
                this.currentJobType = this.elements.jobTypeSelect.value;
                this.updateSliderLimits();
                this.updateJobTypeInfo();
                this.calculateEarnings();
            });
        }

        if (this.elements.hoursPerDay) {
            this.elements.hoursPerDay.addEventListener('input', () => {
                this.updateSliderValues();
                this.calculateEarnings();
            });
        }

        if (this.elements.daysPerWeek) {
            this.elements.daysPerWeek.addEventListener('input', () => {
                this.updateSliderValues();
                this.calculateEarnings();
            });
        }
    }

    populateCitySelect() {
        if (!this.elements.citySelect) return;

        this.elements.citySelect.innerHTML = '';
        Object.entries(CITY_DATA).forEach(([key, city]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = city.name;
            if (key === this.currentCity) option.selected = true;
            this.elements.citySelect.appendChild(option);
        });
    }

    populateJobTypeSelect() {
        if (!this.elements.jobTypeSelect) return;

        this.elements.jobTypeSelect.innerHTML = '';
        Object.entries(JOB_TYPES).forEach(([key, jobType]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = `${jobType.icon} ${jobType.name}`;
            if (key === this.currentJobType) option.selected = true;
            this.elements.jobTypeSelect.appendChild(option);
        });
    }

    updateSliderLimits() {
        const jobType = JOB_TYPES[this.currentJobType];
        if (!jobType || !this.elements.hoursPerDay) return;

        this.elements.hoursPerDay.min = jobType.minHours;
        this.elements.hoursPerDay.max = jobType.maxHours;

        // Если текущее значение выходит за пределы, корректируем
        const currentHours = parseInt(this.elements.hoursPerDay.value);
        if (currentHours < jobType.minHours) {
            this.elements.hoursPerDay.value = jobType.minHours;
        } else if (currentHours > jobType.maxHours) {
            this.elements.hoursPerDay.value = jobType.maxHours;
        }

        this.updateSliderValues();
    }

    updateSliderValues() {
        if (this.elements.hoursValue && this.elements.hoursPerDay) {
            this.elements.hoursValue.textContent = this.elements.hoursPerDay.value;
        }
        if (this.elements.daysValue && this.elements.daysPerWeek) {
            this.elements.daysValue.textContent = this.elements.daysPerWeek.value;
        }
    }

    updateJobTypeInfo() {
        const city = CITY_DATA[this.currentCity];
        const jobType = JOB_TYPES[this.currentJobType];

        if (!city || !jobType) return;

        const avgOrder = city.avgOrder[this.currentJobType];

        if (this.elements.jobTypeInfo) {
            this.elements.jobTypeInfo.innerHTML = `
                <div class="job-type-card">
                    <div class="job-icon">${jobType.icon}</div>
                    <div class="job-details">
                        <h5>${jobType.name}</h5>
                        <p>${jobType.description}</p>
                    </div>
                </div>
            `;
        }

        if (this.elements.avgOrderInfo) {
            this.elements.avgOrderInfo.textContent = `${avgOrder} ₽`;
        }

        if (this.elements.ordersPerHourInfo) {
            this.elements.ordersPerHourInfo.textContent = `${jobType.ordersPerHour}`;
        }
    }

    calculateEarnings() {
        // Трекинг использования калькулятора
        if (typeof trackCalculatorUse === 'function') {
            trackCalculatorUse();
        }

        const city = CITY_DATA[this.currentCity];
        const jobType = JOB_TYPES[this.currentJobType];

        if (!city || !jobType) return;

        const hoursPerDay = parseInt(this.elements.hoursPerDay ? this.elements.hoursPerDay.value : 8);
        const daysPerWeek = parseInt(this.elements.daysPerWeek ? this.elements.daysPerWeek.value : 5);
        const avgOrderCost = city.avgOrder[this.currentJobType];
        const ordersPerHour = jobType.ordersPerHour;
        const driverPercent = jobType.driverPercent;
        const weeksInMonth = 4.33;

        // Расчеты
        const ordersPerDay = hoursPerDay * ordersPerHour;
        const dailyEarnings = ordersPerDay * avgOrderCost * driverPercent;
        const weeklyEarnings = dailyEarnings * daysPerWeek;
        const monthlyEarnings = weeklyEarnings * weeksInMonth;

        // Обновляем отображение
        if (this.elements.dailyEarning) {
            this.elements.dailyEarning.textContent = `${Math.round(dailyEarnings).toLocaleString('ru-RU')} ₽`;
        }

        if (this.elements.weeklyEarning) {
            this.elements.weeklyEarning.textContent = `${Math.round(weeklyEarnings).toLocaleString('ru-RU')} ₽`;
        }

        if (this.elements.monthlyEarning) {
            this.elements.monthlyEarning.textContent = `${Math.round(monthlyEarnings).toLocaleString('ru-RU')} ₽`;
        }

        // Анимация изменения чисел
        this.animateNumbers();
    }

    animateNumbers() {
        const numberElements = [
            this.elements.dailyEarning,
            this.elements.weeklyEarning,
            this.elements.monthlyEarning
        ].filter(el => el);

        numberElements.forEach(element => {
            element.style.transform = 'scale(1.05)';
            element.style.color = 'var(--yandex-yellow)';

            setTimeout(() => {
                element.style.transform = 'scale(1)';
                element.style.color = '';
            }, 200);
        });
    }

    // Публичный метод для внешнего вызова
    recalculate() {
        this.calculateEarnings();
    }

    // Получение текущих данных для аналитики
    getCurrentData() {
        return {
            city: this.currentCity,
            jobType: this.currentJobType,
            hoursPerDay: parseInt(this.elements.hoursPerDay ? this.elements.hoursPerDay.value : 8),
            daysPerWeek: parseInt(this.elements.daysPerWeek ? this.elements.daysPerWeek.value : 5)
        };
    }
}

// Экспорт для использования в других модулях
window.EarningsCalculator = EarningsCalculator;

// Автоинициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('citySelect')) {
        window.calculatorInstance = new EarningsCalculator();
    }
});

// Глобальная функция для обратной совместимости
window.calculateEarnings = function() {
    if (window.calculatorInstance) {
        window.calculatorInstance.recalculate();
    }
};