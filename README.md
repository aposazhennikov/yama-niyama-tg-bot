# 🕊️ Yoga Bot - Telegram Bot for Daily Yoga Principles

Многоязычный телеграм-бот для ежедневной рассылки принципов йоги. Поддерживает русский и английский языки. Отправляет каждый день случайно выбранный принцип из 10 основных принципов йоги (ямы и ниямы) в указанное пользователем время с учетом часового пояса. Каждый пользователь получает свой уникальный случайный принцип.

## ✨ Возможности

- 🌐 **Многоязычность** - русский и английский языки
- 📅 **Ежедневная рассылка** принципов йоги в удобное время
- 🖼️ **Изображения принципов** - каждый принцип отправляется с соответствующей картинкой
- 🌍 **Поддержка часовых поясов** (IANA timezone)
- 📵 **Пропуск дней недели** (например, выходных)
- 🔄 **Случайная отправка** принципов с возможными повторениями
- 📋 **Постоянное меню** - удобный доступ ко всем функциям
- ⚙️ **Изменение настроек** - возможность изменить язык, время и часовой пояс после регистрации
- 💌 **Система обратной связи** - пользователи могут оставлять отзывы
- 🧹 **Автоочистка диалога** - старые сообщения удаляются для чистого интерфейса
- 🛡️ **Защита от спама** - ограничения по частоте отправки отзывов и размеру файлов
- 👨‍💼 **Админ панель** для управления и статистики
- 💬 **Администрирование отзывов** - просмотр статистики и списка отзывов
- 📊 **Мониторинг** через healthcheck и Prometheus metrics
- 🐳 **Docker** готовность для легкого деплоя
- 🔍 **Интеграция Sentry** для отслеживания ошибок

## 🏗️ Архитектура

```
yoga_bot/
├── bot/                 # исходный код
│   ├── main.py         # точка входа
│   ├── scheduler.py    # планировщик рассылки
│   ├── handlers.py     # обработчики команд
│   ├── storage.py      # работа с JSON хранилищем
│   ├── utils.py        # утилиты и форматирование
│   └── principles.json # принципы йоги
├── Dockerfile          
├── docker-compose.yml  
├── requirements.txt    
└── README.md          
```

## 🚀 Быстрый старт

### 1. Подготовка

1. Создайте бота в [@BotFather](https://t.me/BotFather) и получите `BOT_TOKEN`
2. Узнайте свой Telegram ID (можно через [@userinfobot](https://t.me/userinfobot))

### 2. Создание .env файла

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here

# Admin User IDs (comma-separated)
ADMIN_IDS=123456789,987654321

# Optional: Sentry DSN for error tracking
SENTRY_DSN=

# Optional: Data directory path
DATA_DIR=data

# Optional: HTTP server port for healthcheck
HTTP_PORT=8080

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: Environment name for Sentry
ENVIRONMENT=production
```

### 3. Запуск через Docker

```bash
# Запуск приложения
docker compose up -d

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down
```

### 4. Проверка работы

- Healthcheck: `http://localhost:8080/healthz`
- Метрики: `http://localhost:8080/metrics`
- Статистика: `http://localhost:8080/stats`

## 📱 Команды пользователя

| Команда | Описание |
|---------|----------|
| `/start` | Подписаться на рассылку |
| `/stop` | Отписаться от рассылки |
| `/settings` | Показать текущие настройки |
| `/test` | Получить тестовое сообщение |

## 👨‍💼 Команды администратора

| Команда | Описание |
|---------|----------|
| `/next [user_id]` | Показать случайный принцип для пользователя |
| `/add <текст>` | Добавить новый принцип |
| `/stats` | Статистика бота |
| `/broadcast <сообщение>` | Рассылка всем активным пользователям |

## 🔧 Настройка пользователя

При выполнении `/start` бот проведет через 4 шага настройки:

1. **Выбор языка** - русский или английский
2. **Часовой пояс** - в формате IANA (например: `Europe/Moscow`)
3. **Время отправки** - в формате ЧЧ:ММ (например: `08:00`)
4. **Пропускаемые дни** - номера дней недели через запятую (0=Пн, 6=Вс)

### Примеры часовых поясов:
- `Europe/Moscow` - Москва
- `Asia/Tashkent` - Ташкент
- `Europe/Kiev` - Киев
- `Asia/Almaty` - Алматы
- `UTC` - UTC время

## 📊 Мониторинг

### Health Check
```bash
curl http://localhost:8080/healthz
```

Ответ:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0",
  "telegram_connected": true,
  "scheduler_running": true,
  "principles_loaded": 10
}
```

### Prometheus Metrics
```bash
curl http://localhost:8080/metrics
```

Доступные метрики:
- `yoga_bot_uptime_seconds` - время работы бота
- `yoga_bot_users_total` - общее количество пользователей
- `yoga_bot_active_users` - активные пользователи
- `yoga_bot_messages_sent_total` - отправлено сообщений
- `yoga_bot_scheduled_jobs` - запланированные задания

## 🏭 Production деплой

### Docker Compose (рекомендуется)

```bash
# Создание .env файла
cp .env.example .env
# Отредактируйте .env

# Запуск
docker compose up -d

# Мониторинг
docker compose logs -f yoga-bot
```

### Systemd Unit File

Создайте `/etc/systemd/system/yoga-bot.service`:

```ini
[Unit]
Description=Yoga Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/yoga-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

### Helm Chart (Kubernetes)

```yaml
# values.yaml
replicaCount: 1

image:
  repository: yoga-bot
  tag: "latest"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

ingress:
  enabled: false

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: false

env:
  BOT_TOKEN: "your-token"
  API_ID: "123456"
  API_HASH: "your-hash"
  ADMIN_IDS: "123456789"

persistence:
  enabled: true
  storageClass: ""
  size: 1Gi
```

## 🔍 Troubleshooting

### Проблемы с запуском

1. **Проверьте переменные окружения**:
   ```bash
   docker compose config
   ```

2. **Проверьте логи**:
   ```bash
   docker compose logs yoga-bot
   ```

3. **Проверьте healthcheck**:
   ```bash
   curl http://localhost:8080/healthz
   ```

### Ошибки Telegram

- **FloodWaitError** - автоматически обрабатывается с ожиданием
- **ChatWriteForbiddenError** - пользователь заблокировал бота (автоматически деактивируется)

### Проблемы с часовыми поясами

Убедитесь, что используете корректные IANA timezone:
```bash
python -c "import pytz; print(pytz.all_timezones)"
```

## 🧪 Разработка

### Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
cp .env.example .env

# Запуск
python -m bot.main
```

### Структура данных

Данные хранятся в JSON файлах в директории `data/`:

- `users.json` - настройки пользователей
- `sent_logs.json` - логи отправленных сообщений  
- `bot_session.session` - сессия Telegram

### Добавление принципов

Принципы хранятся в `bot/principles.json`:

```json
{
  "id": 11,
  "name": "Новый принцип",
  "emoji": "🧘",
  "short_description": "Краткое описание",
  "description": "Подробное описание принципа",
  "practice_tip": "Совет по практике"
}
```

## 📈 Roadmap

- [ ] Веб-интерфейс для администрирования
- [ ] Поддержка MySQL/PostgreSQL
- [ ] Персонализированные рекомендации
- [ ] Статистика прогресса пользователей
- [ ] Интеграция с календарем
- [ ] Поддержка медиа-контента
- [ ] Мультиязычность

## 🤝 Contributing

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📄 License

Этот проект распространяется под лицензией MIT. Подробности в файле `LICENSE`.

## 🎮 Команды бота

### Пользовательские команды

- `/start` - Начать использование бота (выбор языка, настройка времени, часового пояса и дней пропуска)
- `/menu` - Показать главное меню со всеми опциями
- `/settings` - Посмотреть текущие настройки и изменить их
- `/test` - Получить тестовое сообщение с принципом йоги
- `/stop` - Остановить рассылку и отписаться от бота

### Меню бота

Бот предоставляет удобное постоянное меню:
- ⚙️ **Настройки** - изменение языка, времени, часового пояса и дней пропуска
- 🧪 **Тест** - получить тестовый принцип
- ℹ️ **О боте** - информация о функционале
- 💌 **Обратная связь** - оставить отзыв разработчикам
- ❌ **Отписаться** - прекратить рассылку

### Админские команды

- `/next` - Показать случайный принцип для пользователя
- `/add <текст>` - Добавить новый принцип (пока не реализовано)
- `/stats` - Показать статистику бота
- `/broadcast <сообщение>` - Разослать сообщение всем активным пользователям
- `/feedback_stats` - Статистика отзывов пользователей
- `/feedback_list [лимит]` - Показать последние отзывы (по умолчанию 10, максимум 50)

### Система обратной связи

- **Ограничения**: максимум 1000 символов на отзыв
- **Rate limiting**: один отзыв каждые 10 минут
- **Защита от спама**: контроль размера файлов (лимит 10 МБ)
- **Уведомления**: админы получают уведомления о новых отзывах

## 🙏 Благодарности

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram bot library
- [APScheduler](https://github.com/agronholm/apscheduler) - планировщик задач
- [Pydantic](https://github.com/pydantic/pydantic) - валидация данных
- Источники принципов йоги

## 📞 Поддержка

Если у вас есть вопросы или проблемы:

1. Проверьте [Issues](https://github.com/your-repo/yoga-bot/issues)
2. Создайте новый Issue с подробным описанием
3. Используйте метки для категоризации проблемы

---

Made with ❤️ for yoga practitioners 