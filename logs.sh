#!/bin/bash

# ============================================================
# 📊 СИСТЕМА ЛОГИРОВАНИЯ БОТА PPTbot
# ============================================================
# Использование:
#   ./logs.sh                    - показать меню
#   ./logs.sh user 123456789     - логи пользователя
#   ./logs.sh errors             - только ошибки
#   ./logs.sh warnings           - только предупреждения
#   ./logs.sh n8n                - взаимодействие с n8n
#   ./logs.sh posts              - создание постов
#   ./logs.sh publish            - публикация постов
#   ./logs.sh anons              - анонсы
#   ./logs.sh sales              - продающие посты
#   ./logs.sh voice              - голосовые сообщения
#   ./logs.sh reminders          - напоминания
#   ./logs.sh database           - запросы к БД
#   ./logs.sh today              - всё за сегодня
#   ./logs.sh live               - живые логи
#   ./logs.sh stats              - статистика из БД
#   ./logs.sh search "текст"     - поиск по тексту
# ============================================================

# Цвета для вывода
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Определяем способ запуска (Python процесс или Docker)
# По умолчанию используем поиск по процессу Python
LOG_SOURCE="python"
PROCESS_NAME="bot.py"

show_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  📊 $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

show_menu() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║          📊 СИСТЕМА ЛОГИРОВАНИЯ БОТА PPTbot             ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  1) 👤 Логи пользователя (по telegram_id)                ║"
    echo "║  2) ❌ Только ERROR                                      ║"
    echo "║  3) ⚠️  Только WARNING                                   ║"
    echo "║  4) 🤖 Взаимодействие с n8n                              ║"
    echo "║  5) 📝 Создание постов                                   ║"
    echo "║  6) 📤 Публикация поста-знакомства                       ║"
    echo "║  7) 📣 Анонсы                                            ║"
    echo "║  8) 💰 Продающие посты                                   ║"
    echo "║  9) 🎤 Голосовые сообщения                               ║"
    echo "║  10) 🔔 Напоминания                                      ║"
    echo "║  11) 💾 Запросы к базе данных                            ║"
    echo "║  12) 🎥 Отправка видео                                   ║"
    echo "║  13) 📅 Всё за сегодня                                   ║"
    echo "║  14) 🔴 Живые логи (Ctrl+C для выхода)                   ║"
    echo "║  15) 📈 Статистика из БД                                 ║"
    echo "║  16) 🔍 Поиск по тексту                                  ║"
    echo "║                                                          ║"
    echo "║  0) Выход                                                ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -n "Выберите опцию: "
}

# Функция получения логов (универсальная)
get_logs() {
    local lines=${1:-500}
    local filter=${2:-""}
    
    # Если бот запущен как Python процесс
    if pgrep -f "$PROCESS_NAME" > /dev/null; then
        # Читаем из stdout/stderr процесса или из файла логов если они ведутся
        if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
            tail -n $lines "logs/bot_$(date +%Y%m%d).log" | grep -E "$filter"
        else
            # Используем journalctl если бот запущен через systemd
            # Или просто читаем текущий вывод
            echo -e "${YELLOW}Внимание: Логи читаются из процесса. Для полноценного логирования настройте файловое логирование.${NC}"
        fi
    else
        echo -e "${RED}❌ Бот не запущен!${NC}"
        exit 1
    fi
}

# 1. Логи конкретного пользователя
logs_user() {
    local user_id=$1
    
    if [ -z "$user_id" ]; then
        echo -n "Введите telegram_id пользователя: "
        read user_id
    fi
    
    show_header "ЛОГИ ПОЛЬЗОВАТЕЛЯ $user_id"
    
    echo -e "${BLUE}📋 Данные из базы (подключитесь к Supabase для просмотра):${NC}"
    echo "SELECT * FROM users WHERE telegram_id = $user_id;"
    
    echo ""
    echo -e "${BLUE}📜 Последние действия в логах:${NC}"
    
    # Поиск по telegram_id в логах
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "telegram_id=$user_id" "logs/bot_$(date +%Y%m%d).log" | tail -50
    else
        echo -e "${YELLOW}Файл логов не найден. Проверьте настройки логирования.${NC}"
    fi
}

# 2. Только ошибки
logs_errors() {
    show_header "ОШИБКИ (ERROR)"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "ERROR" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 3. Только предупреждения
logs_warnings() {
    show_header "ПРЕДУПРЕЖДЕНИЯ (WARNING)"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "WARNING" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 4. Взаимодействие с n8n
logs_n8n() {
    show_header "ВЗАИМОДЕЙСТВИЕ С N8N"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep -E "N8N|request_id|prompt" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 5. Создание постов
logs_posts() {
    show_header "СОЗДАНИЕ ПОСТОВ"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "POSTS" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 6. Публикация поста-знакомства
logs_publish() {
    show_header "ПУБЛИКАЦИЯ ПОСТА-ЗНАКОМСТВА"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "PUBLISH" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 7. Анонсы
logs_anons() {
    show_header "АНОНСЫ"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "ANONS" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 8. Продающие посты
logs_sales() {
    show_header "ПРОДАЮЩИЕ ПОСТЫ"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "SALES" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 9. Голосовые сообщения
logs_voice() {
    show_header "ГОЛОСОВЫЕ СООБЩЕНИЯ"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "VOICE" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 10. Напоминания
logs_reminders() {
    show_header "НАПОМИНАНИЯ"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "REMINDER" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 11. Запросы к БД
logs_database() {
    show_header "ЗАПРОСЫ К БАЗЕ ДАННЫХ"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "DATABASE" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 12. Отправка видео
logs_video() {
    show_header "ОТПРАВКА ВИДЕО"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep "VIDEO" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 13. Логи за сегодня
logs_today() {
    local today=$(date +%Y-%m-%d)
    show_header "ВСЕ ЛОГИ ЗА $today"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        tail -200 "logs/bot_$(date +%Y%m%d).log"
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# 14. Живые логи
logs_live() {
    show_header "ЖИВЫЕ ЛОГИ (Ctrl+C для выхода)"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        tail -f "logs/bot_$(date +%Y%m%d).log"
    else
        echo -e "${YELLOW}Файл логов не найден. Создайте файл логирования в logger.py${NC}"
        echo "Раскомментируйте строки для file_handler в logger.py"
    fi
}

# 15. Статистика из БД
logs_stats() {
    show_header "СТАТИСТИКА ИЗ БАЗЫ ДАННЫХ"
    
    echo -e "${BLUE}Для просмотра статистики выполните следующие SQL-запросы в Supabase:${NC}"
    echo ""
    echo -e "${GREEN}📊 Пользователи по состояниям:${NC}"
    echo "SELECT state, COUNT(*) as count FROM users GROUP BY state ORDER BY count DESC;"
    echo ""
    echo -e "${GREEN}📝 Прогресс по постам:${NC}"
    echo "SELECT current_post_number, COUNT(*) as count FROM users WHERE current_post_number > 0 GROUP BY current_post_number ORDER BY current_post_number;"
    echo ""
    echo -e "${GREEN}✅ Завершившие этапы:${NC}"
    echo "SELECT COUNT(*) as completed FROM users WHERE state = 'final_step';"
    echo ""
    echo -e "${GREEN}📈 Общая статистика:${NC}"
    echo "SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN state = 'registered' THEN 1 END) as registered,
    COUNT(CASE WHEN channel_link IS NOT NULL THEN 1 END) as with_channels,
    COUNT(CASE WHEN blue_post_text IS NOT NULL THEN 1 END) as published_intro,
    COUNT(CASE WHEN sales_text IS NOT NULL THEN 1 END) as created_sales
FROM users;"
}

# 16. Поиск по тексту
logs_search() {
    local search_text=$1
    
    if [ -z "$search_text" ]; then
        echo -n "Введите текст для поиска: "
        read search_text
    fi
    
    show_header "ПОИСК: $search_text"
    
    if [ -f "logs/bot_$(date +%Y%m%d).log" ]; then
        grep -i "$search_text" "logs/bot_$(date +%Y%m%d).log" | tail -100
    else
        echo -e "${YELLOW}Файл логов не найден.${NC}"
    fi
}

# Главная логика
case "$1" in
    user)
        logs_user "$2"
        ;;
    errors)
        logs_errors
        ;;
    warnings)
        logs_warnings
        ;;
    n8n)
        logs_n8n
        ;;
    posts)
        logs_posts
        ;;
    publish)
        logs_publish
        ;;
    anons)
        logs_anons
        ;;
    sales)
        logs_sales
        ;;
    voice)
        logs_voice
        ;;
    reminders)
        logs_reminders
        ;;
    database)
        logs_database
        ;;
    video)
        logs_video
        ;;
    today)
        logs_today
        ;;
    live)
        logs_live
        ;;
    stats)
        logs_stats
        ;;
    search)
        logs_search "$2"
        ;;
    *)
        # Интерактивное меню
        while true; do
            show_menu
            read choice
            
            case $choice in
                1) logs_user ;;
                2) logs_errors ;;
                3) logs_warnings ;;
                4) logs_n8n ;;
                5) logs_posts ;;
                6) logs_publish ;;
                7) logs_anons ;;
                8) logs_sales ;;
                9) logs_voice ;;
                10) logs_reminders ;;
                11) logs_database ;;
                12) logs_video ;;
                13) logs_today ;;
                14) logs_live ;;
                15) logs_stats ;;
                16) logs_search ;;
                0) echo "До свидания!"; exit 0 ;;
                *) echo -e "${RED}Неверный выбор${NC}" ;;
            esac
            
            echo ""
            echo -n "Нажмите Enter для продолжения..."
            read
        done
        ;;
esac

