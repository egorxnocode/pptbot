#!/bin/bash

echo "========================================"
echo "🔍 Проверка статуса бота"
echo "========================================"
echo ""

echo "1. Статус контейнера:"
docker ps -a | grep pptbot
echo ""

echo "2. Последние 50 строк логов:"
docker logs --tail 50 pptbot-telegram-bot 2>&1
echo ""

echo "3. Переменные окружения (первые символы):"
docker exec pptbot-telegram-bot env | grep -E "TELEGRAM|SUPABASE|OPENAI|N8N" | sed 's/=.*/=***/'
echo ""

echo "========================================"
echo "✅ Проверка завершена"
echo "========================================"












