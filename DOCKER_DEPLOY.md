# 🐳 Развертывание бота в Docker

## Быстрый старт

### 1. Подготовка

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
nano .env
```

Заполните переменные:
- `TELEGRAM_BOT_TOKEN` - токен от @BotFather
- `SUPABASE_URL` - URL вашего Supabase (например: https://xxxxx.supabase.co)
- `SUPABASE_KEY` - Anon key из Supabase Settings → API
- `OPENAI_API_KEY` - ключ OpenAI API
- `N8N_WEBHOOK_URL` - URL вашего n8n webhook

### 2. Добавьте медиафайлы

Поместите видеофайлы в папку `media/`:
- `learn1.mp4`
- `learn2.mp4`
- `learn3.mp4`
- `learn4.mp4`
- `learn5.mp4`
- `learn6.mp4`
- `learn7.mp4`

### 3. Запуск бота

```bash
# Собрать и запустить
docker-compose up -d

# Или через docker build
docker build -t pptbot .
docker run -d --name pptbot-bot --env-file .env \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/temp:/app/temp \
  pptbot
```

### 4. Проверка работы

```bash
# Просмотр логов
docker-compose logs -f bot

# Или
docker logs -f pptbot-telegram-bot

# Статус контейнера
docker-compose ps

# Или
docker ps | grep pptbot
```

## Управление

### Остановка бота

```bash
docker-compose stop
# или
docker stop pptbot-telegram-bot
```

### Перезапуск бота

```bash
docker-compose restart
# или
docker restart pptbot-telegram-bot
```

### Остановка и удаление

```bash
docker-compose down
# или
docker stop pptbot-telegram-bot && docker rm pptbot-telegram-bot
```

### Обновление бота

```bash
# Остановить
docker-compose down

# Пересобрать образ
docker-compose build --no-cache

# Запустить
docker-compose up -d
```

## Логи

### Просмотр логов

```bash
# В реальном времени
docker-compose logs -f bot

# Последние 100 строк
docker-compose logs --tail=100 bot

# Логи за последние 10 минут
docker-compose logs --since=10m bot
```

### Логи в файлах

Логи также сохраняются в папке `logs/`:

```bash
# Просмотр логов за сегодня
tail -f logs/bot_$(date +%Y%m%d).log

# Использование скрипта logs.sh
./logs.sh live
```

## Подключение к сети с Supabase и n8n

Если ваш Supabase и n8n находятся в той же Docker сети:

1. Раскомментируйте в `docker-compose.yml`:

```yaml
networks:
  - external-network

networks:
  external-network:
    external: true
    name: your-network-name  # Имя вашей сети
```

2. В `.env` используйте имена контейнеров:

```bash
SUPABASE_URL=http://supabase-kong:8000
N8N_WEBHOOK_URL=http://n8n:5678/webhook/pptbot
```

## Отладка

### Войти в контейнер

```bash
docker exec -it pptbot-telegram-bot /bin/bash
```

### Проверить переменные окружения

```bash
docker exec pptbot-telegram-bot env | grep -E "TELEGRAM|SUPABASE|N8N"
```

### Проверить файлы

```bash
# Медиафайлы
docker exec pptbot-telegram-bot ls -la /app/media

# Логи
docker exec pptbot-telegram-bot ls -la /app/logs
```

### Пересоздать контейнер

```bash
docker-compose down
docker-compose up -d --force-recreate
```

## Troubleshooting

### Бот не запускается

1. Проверьте логи:
```bash
docker logs pptbot-telegram-bot
```

2. Проверьте переменные окружения в `.env`

3. Убедитесь, что порты не заняты

### Не подключается к Supabase

1. Проверьте URL и ключ в `.env`
2. Если Supabase в той же сети Docker - используйте имя контейнера
3. Если на другом сервере - укажите полный URL

### Не подключается к n8n

1. Проверьте доступность n8n:
```bash
docker exec pptbot-telegram-bot curl -I http://your-n8n:5678
```

2. Убедитесь, что webhook настроен в n8n

### Нет медиафайлов

```bash
# Проверить монтирование
docker inspect pptbot-telegram-bot | grep -A 10 Mounts

# Добавить файлы и перезапустить
docker-compose restart
```

## Советы по продакшену

1. **Используйте restart: unless-stopped** (уже настроено)
2. **Настройте логирование** - логи автоматически ротируются по дням
3. **Мониторинг**: используйте healthcheck (настроен в docker-compose)
4. **Бэкапы**: регулярно делайте бэкап папок `media/` и `logs/`
5. **Обновления**: перед обновлением делайте бэкап

## Автозапуск при перезагрузке сервера

Docker Compose с `restart: unless-stopped` автоматически запустит бота после перезагрузки сервера.

Проверка:

```bash
# Перезагрузить сервер
sudo reboot

# После перезагрузки проверить
docker ps | grep pptbot
```

## Systemd сервис (альтернатива)

Если хотите управлять через systemd:

```bash
# Создать сервис
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
# Включить и запустить
sudo systemctl enable pptbot
sudo systemctl start pptbot
sudo systemctl status pptbot
```

