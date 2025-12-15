# 🐳 Развертывание PPTbot в Docker

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Управление контейнером](#управление-контейнером)
3. [Просмотр логов](#просмотр-логов)
4. [Подключение к существующим сервисам](#подключение-к-существующим-сервисам)
5. [Troubleshooting](#troubleshooting)
6. [Автозапуск](#автозапуск)

---

## 🚀 Быстрый старт

### Шаг 1: Подготовка окружения

```bash
# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать переменные
nano .env
```

Заполните обязательные переменные:

```bash
# Telegram Bot Token от @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# URL вашего Supabase
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI API Key
OPENAI_API_KEY=sk-...

# URL вашего n8n webhook
N8N_WEBHOOK_URL=http://your-server:5678/webhook/pptbot
```

### Шаг 2: Добавление медиафайлов

Поместите обучающие видео в папку `media/`:

```bash
media/
├── learn1.mp4  # Первое обучающее видео
├── learn2.mp4  # Создание канала
├── learn3.mp4  # Следующий урок
├── learn4.mp4  # Наполнение канала
├── learn5.mp4  # Публикация поста
├── learn6.mp4  # Создание анонсов
└── learn7.mp4  # Продающие посты
```

### Шаг 3: Запуск

```bash
# Собрать и запустить контейнер
docker-compose up -d

# Проверить статус
docker-compose ps

# Проверить логи
docker-compose logs -f bot
```

Готово! Бот запущен и работает в фоновом режиме.

---

## 🎮 Управление контейнером

### Основные команды

```bash
# Запустить бота
docker-compose up -d

# Остановить бота
docker-compose stop

# Перезапустить бота
docker-compose restart

# Остановить и удалить контейнер
docker-compose down

# Проверить статус
docker-compose ps
```

### Обновление бота

После изменения кода:

```bash
# Остановить и удалить контейнер
docker-compose down

# Пересобрать образ (без кеша)
docker-compose build --no-cache

# Запустить заново
docker-compose up -d
```

### Альтернативные команды Docker

Если не используете docker-compose:

```bash
# Собрать образ
docker build -t pptbot .

# Запустить контейнер
docker run -d \
  --name pptbot-bot \
  --env-file .env \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/temp:/app/temp \
  --restart unless-stopped \
  pptbot

# Управление
docker stop pptbot-bot       # Остановить
docker start pptbot-bot      # Запустить
docker restart pptbot-bot    # Перезапустить
docker rm pptbot-bot         # Удалить
```

---

## 📜 Просмотр логов

### Docker Compose

```bash
# Логи в реальном времени
docker-compose logs -f bot

# Последние 100 строк
docker-compose logs --tail=100 bot

# Логи за последний час
docker-compose logs --since=1h bot

# Логи за сегодня
docker-compose logs --since=$(date +%Y-%m-%d) bot
```

### Docker напрямую

```bash
# Логи в реальном времени
docker logs -f pptbot-telegram-bot

# Последние строки
docker logs --tail=100 pptbot-telegram-bot
```

### Файлы логов

Логи также сохраняются в папке `logs/`:

```bash
# Просмотр логов за сегодня
tail -f logs/bot_$(date +%Y%m%d).log

# Использование скрипта
./logs.sh live
./logs.sh errors
./logs.sh user 123456789
```

---

## 🔗 Подключение к существующим сервисам

### Если Supabase и n8n на другом сервере

В `.env` укажите полные URL:

```bash
SUPABASE_URL=https://your-project.supabase.co
N8N_WEBHOOK_URL=https://your-n8n-domain.com/webhook/pptbot
```

### Если Supabase и n8n в той же Docker сети

#### 1. Узнайте имя сети

```bash
# Посмотреть все сети
docker network ls

# Посмотреть контейнеры в сети
docker network inspect network-name
```

#### 2. Подключите бота к сети

Раскомментируйте в `docker-compose.yml`:

```yaml
services:
  bot:
    # ... остальное
    networks:
      - external-network

networks:
  external-network:
    external: true
    name: your-network-name  # Имя вашей сети
```

#### 3. Используйте имена контейнеров

В `.env`:

```bash
# Используйте имена контейнеров вместо localhost
SUPABASE_URL=http://supabase-kong:8000
N8N_WEBHOOK_URL=http://n8n:5678/webhook/pptbot
```

#### 4. Перезапустите

```bash
docker-compose down
docker-compose up -d
```

---

## 🔧 Troubleshooting

### Бот не запускается

**Проверьте логи:**

```bash
docker logs pptbot-telegram-bot
```

**Проверьте переменные окружения:**

```bash
docker exec pptbot-telegram-bot env | grep -E "TELEGRAM|SUPABASE|N8N"
```

**Проверьте, что .env файл существует:**

```bash
ls -la .env
cat .env
```

### Нет медиафайлов

**Проверьте монтирование:**

```bash
docker exec pptbot-telegram-bot ls -la /app/media
```

**Проверьте права доступа:**

```bash
ls -la media/
chmod 755 media/
chmod 644 media/*.mp4
```

### Не подключается к Supabase

**Проверьте доступность:**

```bash
docker exec pptbot-telegram-bot curl -I $SUPABASE_URL
```

**Если в той же сети - проверьте имя контейнера:**

```bash
docker network inspect your-network-name | grep supabase
```

### Не подключается к n8n

**Проверьте доступность:**

```bash
docker exec pptbot-telegram-bot curl -I $N8N_WEBHOOK_URL
```

**Проверьте webhook в n8n:**
- Откройте n8n
- Проверьте, что workflow активен
- Проверьте URL webhook

### Войти в контейнер для отладки

```bash
# Войти в bash
docker exec -it pptbot-telegram-bot /bin/bash

# Внутри контейнера можно:
ls -la                          # Посмотреть файлы
python -c "import telegram"     # Проверить импорты
env                             # Проверить переменные
curl https://api.telegram.org   # Проверить интернет
```

### Контейнер постоянно перезапускается

```bash
# Проверить статус
docker ps -a | grep pptbot

# Посмотреть последние логи
docker logs --tail=50 pptbot-telegram-bot

# Запустить без перезапуска для отладки
docker run --rm -it --env-file .env \
  -v $(pwd)/media:/app/media \
  pptbot python bot.py
```

---

## ⚙️ Автозапуск

### Docker Compose (рекомендуется)

В `docker-compose.yml` уже настроено:

```yaml
restart: unless-stopped
```

Это означает:
- ✅ Автозапуск после перезагрузки сервера
- ✅ Автоматический перезапуск при сбое
- ❌ НЕ перезапускается, если вы остановили вручную

### Проверка после перезагрузки сервера

```bash
# Перезагрузить сервер
sudo reboot

# После перезагрузки (через SSH)
docker ps | grep pptbot
docker logs pptbot-telegram-bot
```

### Systemd сервис (опционально)

Если хотите управлять через systemd:

```bash
sudo nano /etc/systemd/system/pptbot.service
```

```ini
[Unit]
Description=PPTbot Telegram Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/PPTbot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Активировать
sudo systemctl daemon-reload
sudo systemctl enable pptbot
sudo systemctl start pptbot

# Управление
sudo systemctl status pptbot
sudo systemctl restart pptbot
sudo systemctl stop pptbot
```

---

## 📊 Мониторинг

### Статус контейнера

```bash
# Краткий статус
docker ps | grep pptbot

# Подробная информация
docker inspect pptbot-telegram-bot

# Использование ресурсов
docker stats pptbot-telegram-bot
```

### Health check

Контейнер настроен с health check:

```bash
# Проверить здоровье
docker inspect --format='{{.State.Health.Status}}' pptbot-telegram-bot
```

### Просмотр метрик

```bash
# CPU, память, сеть
docker stats --no-stream pptbot-telegram-bot

# Размер контейнера
docker ps -s | grep pptbot
```

---

## 🛡️ Безопасность

### Рекомендации

1. **Не коммитьте .env в Git**
   - Уже добавлен в `.gitignore`

2. **Используйте сильные пароли**
   - Для PostgreSQL
   - Для JWT секрета

3. **Ограничьте доступ к портам**
   - Используйте firewall
   - Открывайте только необходимые порты

4. **Регулярно обновляйте образы**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

5. **Мониторинг логов на ошибки**
   ```bash
   ./logs.sh errors
   ```

---

## 📦 Бэкапы

### Что бэкапить

1. **Переменные окружения:**
   ```bash
   cp .env .env.backup
   ```

2. **Медиафайлы:**
   ```bash
   tar -czf media_backup.tar.gz media/
   ```

3. **Логи (опционально):**
   ```bash
   tar -czf logs_backup.tar.gz logs/
   ```

### Восстановление

```bash
# Распаковать медиафайлы
tar -xzf media_backup.tar.gz

# Восстановить .env
cp .env.backup .env

# Перезапустить
docker-compose up -d
```

---

## 🎯 Советы по продакшену

1. ✅ Используйте `restart: unless-stopped`
2. ✅ Настройте мониторинг (Prometheus + Grafana)
3. ✅ Настройте алерты на ошибки
4. ✅ Регулярные бэкапы
5. ✅ Мониторинг дискового пространства
6. ✅ Ротация логов (уже настроена)
7. ✅ Используйте HTTPS для Supabase и n8n
8. ✅ Ограничьте доступ к серверу

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `docker logs pptbot-telegram-bot`
2. Проверьте переменные: `docker exec pptbot-telegram-bot env`
3. Проверьте файлы: `docker exec pptbot-telegram-bot ls -la /app`
4. Используйте скрипт: `./logs.sh errors`

