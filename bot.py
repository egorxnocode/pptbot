"""
Главный файл телеграм бота
"""
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import (
    TELEGRAM_BOT_TOKEN, MEDIA_FOLDER, TEMP_FOLDER,
    SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY,
    N8N_WEBHOOK_OSEBE, N8N_WEBHOOK_POST, N8N_WEBHOOK_BLUEBUTT,
    N8N_WEBHOOK_ANONS, N8N_WEBHOOK_PRODAJ
)
from handlers import start_command, button_callback, handle_text_message, handle_voice_message
from logger import bot_logger


def check_environment():
    """Проверяет наличие всех необходимых переменных окружения"""
    missing_vars = []
    
    # Обязательные переменные
    required_vars = {
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_KEY': SUPABASE_KEY,
        'OPENAI_API_KEY': OPENAI_API_KEY,
        'N8N_WEBHOOK_OSEBE': N8N_WEBHOOK_OSEBE,
        'N8N_WEBHOOK_POST': N8N_WEBHOOK_POST,
        'N8N_WEBHOOK_BLUEBUTT': N8N_WEBHOOK_BLUEBUTT,
        'N8N_WEBHOOK_ANONS': N8N_WEBHOOK_ANONS,
        'N8N_WEBHOOK_PRODAJ': N8N_WEBHOOK_PRODAJ
    }
    
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)
    
    if missing_vars:
        print("❌ Ошибка: Не установлены следующие переменные окружения:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Создайте файл .env и добавьте все необходимые переменные")
        print("   Пример можно посмотреть в .env.example")
        return False
    
    print("✅ Все переменные окружения настроены")
    return True


def create_folders():
    """Создает необходимые папки если их нет"""
    # Создаем папку для логов
    logs_folder = "logs"
    if not os.path.exists(logs_folder):
        os.makedirs(logs_folder)
        print(f"✅ Создана папка для логов: {logs_folder}")
    
    if not os.path.exists(MEDIA_FOLDER):
        os.makedirs(MEDIA_FOLDER)
        print(f"✅ Создана папка для медиафайлов: {MEDIA_FOLDER}")
        bot_logger.info('SYSTEM', f'Создана папка {MEDIA_FOLDER}')
    
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
        print(f"✅ Создана папка для временных файлов: {TEMP_FOLDER}")
        bot_logger.info('SYSTEM', f'Создана папка {TEMP_FOLDER}')


def main():
    """Запуск бота"""
    # Проверяем все переменные окружения
    if not check_environment():
        return
    
    # Создаем необходимые папки
    create_folders()
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    
    # Регистрируем обработчик callback кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрируем обработчик голосовых сообщений
    application.add_handler(MessageHandler(
        filters.VOICE,
        handle_voice_message
    ))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))
    
    # Запускаем бота
    print("🤖 Бот запущен и готов к работе!")
    print("Нажмите Ctrl+C для остановки бота")
    
    # Запускаем polling
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        bot_logger.info('SYSTEM', '⏹️ Бот остановлен пользователем')
        print("\n⏹️ Бот остановлен")
    except Exception as e:
        bot_logger.error('SYSTEM', f'Критическая ошибка при запуске бота: {str(e)}')
        print(f"\n❌ Критическая ошибка: {e}")
        raise

