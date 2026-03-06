# Uzum Price Tracker

**Uzum Price Tracker** --- Telegram-бот для отслеживания цен на товары
на платформе **Uzum**.
Пользователь добавляет ссылку на товар, после чего бот автоматически
отслеживает изменения цены и уведомляет при её изменении.

Проект построен на **асинхронной архитектуре** с использованием брокера
сообщений и отдельного воркера для парсинга страниц.

------------------------------------------------------------------------

# Основные возможности

### Отслеживание товаров

Пользователь может отправить ссылку на товар в Uzum, после чего бот
начнёт отслеживать его цену.

### Уведомления об изменении цены

При изменении цены бот отправляет пользователю уведомление.

### История цен

Для каждого товара сохраняется история изменений цен.

### Автоматическая проверка цен

Фоновый планировщик регулярно проверяет изменения цен на отслеживаемые
товары.

------------------------------------------------------------------------

# Архитектура проекта

Проект состоит из нескольких компонентов:

    Telegram Bot
         │
         │ publish event
         ▼
    RabbitMQ (message broker)
         │
         ▼
    Worker (Playwright parser)
         │
         ▼
    PostgreSQL

### Telegram Bot

-   принимает команды пользователей
-   сохраняет товары в базе данных
-   отправляет задачи на парсинг в RabbitMQ

### Worker

-   получает задачи из RabbitMQ
-   открывает страницу товара через Playwright
-   извлекает название и цену
-   сохраняет данные в PostgreSQL

### Scheduler

-   периодически проверяет обновления цен
-   отправляет уведомления пользователям

------------------------------------------------------------------------

# Технологический стек

-   Python
-   Aiogram
-   PostgreSQL
-   SQLAlchemy (async)
-   Playwright
-   RabbitMQ
-   APScheduler
-   Docker

------------------------------------------------------------------------

# Структура проекта

    app/
     ├── bot/            # Telegram bot
     ├── config/         # конфиг
     ├── db/             # модели и клиент БД
     ├── parser/         # Uzum page parser
     ├── publisher/      # отправка сообщений в RabbitMQ
     ├── scheduler/      # задачи проверки цен
     ├── services/       # бизнес-логика
     └── workers/        # consumer-воркеры

------------------------------------------------------------------------

# Запуск проекта

## 1. Настроить `.env.docker`

Пример:

    # DB
    POSTGRES_DB=...
    POSTGRES_USER=...
    POSTGRES_PASSWORD=...
    POSTGRES_HOST=...
    POSTGRES_PORT=5432
    
    # Telegram
    TG_TOKEN=...
    
    # Parser
    PARSER_HEADLESS_MODE=true
    
    # Scheduler
    SCHEDULER_RUN_INTERVAL=8  # in hours
    SCHEDULER_RUN_ON_STARTUP=false
    
    # RabbitMQ
    RABBITMQ_HOST=...
    RABBITMQ_PORT=5672
    RABBITMQ_DEFAULT_USER=guest
    RABBITMQ_DEFAULT_PASS=guest
    RABBITMQ_MANAGEMENT_PORT=15672

## 2. Запуск

``` bash
docker compose up -d
```

------------------------------------------------------------------------

# TODO

-   [ ] Caching layer (Redis)
-   [ ] Unit and integration tests
-   [ ] CI/CD (GitHub Actions)
-   [ ] Retry / DLQ for message processing
-   [ ] Metrics and monitoring

------------------------------------------------------------------------

# Лицензия

MIT License