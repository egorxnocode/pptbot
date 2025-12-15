"""
Главный файл телеграм бота
"""
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import TELEGRAM_BOT_TOKEN, MEDIA_FOLDER, TEMP_FOLDER
from handlers import start_command, button_callback, handle_text_message, handle_voice_message
from logger import bot_logger


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
    # Проверяем наличие токена
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен!")
        print("Создайте файл .env и добавьте ваш токен бота")
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

