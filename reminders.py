"""
Система напоминаний для пользователей
"""
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import REMINDER_1_DELAY, REMINDER_2_DELAY, REMINDER_3_DELAY, UserState
from database import Database
import messages


# Инициализация базы данных
db = Database()


async def send_reminder(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, reminder_text: str) -> None:
    """
    Отправляет напоминание пользователю
    
    Args:
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
        reminder_text: Текст напоминания
    """
    # Проверяем состояние пользователя
    user_state = db.get_user_state(telegram_id)
    
    # Отправляем напоминание только если пользователь еще не нажал кнопку
    if user_state == UserState.VIDEO_SENT:
        try:
            # Добавляем inline кнопку к напоминанию
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    messages.BUTTON_VIDEO_WATCHED,
                    callback_data='video_watched'
                )]
            ])
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text=reminder_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            bot_logger.error('REMINDER', f'Ошибка при отправке напоминания #{reminder_number}', 
                           telegram_id=telegram_id, error=str(e))


async def send_reminder_1(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет первое напоминание (через 10 минут)
    """
    job = context.job
    telegram_id = job.data
    await send_reminder(context, telegram_id, messages.REMINDER_1)


async def send_reminder_2(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет второе напоминание (через 1 час)
    """
    job = context.job
    telegram_id = job.data
    await send_reminder(context, telegram_id, messages.REMINDER_2)


async def send_reminder_3(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет третье напоминание (через 24 часа)
    """
    job = context.job
    telegram_id = job.data
    await send_reminder(context, telegram_id, messages.REMINDER_3)


async def schedule_reminders(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Планирует отправку всех напоминаний для пользователя
    
    Args:
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    job_queue = context.job_queue
    
    # Отменяем существующие напоминания для этого пользователя (если есть)
    cancel_reminders(context, telegram_id)
    
    # Планируем 1-е напоминание (через 10 минут)
    job_queue.run_once(
        send_reminder_1,
        when=REMINDER_1_DELAY,
        data=telegram_id,
        name=f"reminder_1_{telegram_id}"
    )
    
    # Планируем 2-е напоминание (через 1 час)
    job_queue.run_once(
        send_reminder_2,
        when=REMINDER_2_DELAY,
        data=telegram_id,
        name=f"reminder_2_{telegram_id}"
    )
    
    # Планируем 3-е напоминание (через 24 часа)
    job_queue.run_once(
        send_reminder_3,
        when=REMINDER_3_DELAY,
        data=telegram_id,
        name=f"reminder_3_{telegram_id}"
    )
    
    bot_logger.reminder_scheduled(telegram_id, REMINDER_1_DELAY // 60)
    bot_logger.info('REMINDER', f'Запланировано 3 напоминания: {REMINDER_1_DELAY//60}м, {REMINDER_2_DELAY//60}м, {REMINDER_3_DELAY//3600}ч',
                   telegram_id=telegram_id)


def cancel_reminders(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Отменяет все запланированные напоминания для пользователя
    
    Args:
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    job_queue = context.job_queue
    
    # Получаем все задачи для данного пользователя
    jobs_to_remove = [
        f"reminder_1_{telegram_id}",
        f"reminder_2_{telegram_id}",
        f"reminder_3_{telegram_id}"
    ]
    
    # Удаляем каждую задачу
    for job_name in jobs_to_remove:
        current_jobs = job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
    
    bot_logger.info('REMINDER', f'Отменены все напоминания', telegram_id=telegram_id)

