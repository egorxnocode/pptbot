"""
Модуль для работы с каналами Telegram
Проверка и публикация постов
"""
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.constants import ParseMode
from logger import bot_logger


async def check_if_channel(bot: Bot, channel_link: str) -> tuple[bool, str, int]:
    """
    Проверяет, является ли ссылка каналом
    
    Args:
        bot: Объект бота
        channel_link: Ссылка на канал
        
    Returns:
        (is_channel, username, channel_id)
    """
    try:
        # Извлекаем username из ссылки
        if '@' in channel_link:
            username = channel_link.split('@')[1].strip()
        elif 't.me/' in channel_link:
            username = channel_link.split('t.me/')[1].strip().rstrip('/')
        else:
            username = channel_link.strip()
        
        # Добавляем @ если нет
        if not username.startswith('@'):
            username = f'@{username}'
        
        # Пытаемся получить информацию о канале
        chat = await bot.get_chat(username)
        
        # Проверяем, что это канал
        if chat.type == 'channel':
            return True, username, chat.id
        else:
            return False, username, 0
            
    except TelegramError as e:
        bot_logger.error('PUBLISH', f'Ошибка проверки канала: {str(e)}', channel=channel_link)
        return False, "", 0


async def check_bot_admin(bot: Bot, channel_id: int, bot_id: int) -> bool:
    """
    Проверяет, является ли бот администратором канала
    
    Args:
        bot: Объект бота
        channel_id: ID канала
        bot_id: ID бота
        
    Returns:
        True если бот админ, False если нет
    """
    try:
        # Получаем список администраторов
        admins = await bot.get_chat_administrators(channel_id)
        
        # Проверяем, есть ли бот в списке
        for admin in admins:
            if admin.user.id == bot_id:
                # Проверяем права на публикацию
                if admin.can_post_messages or admin.status == 'creator':
                    return True
        
        return False
        
    except TelegramError as e:
        bot_logger.error('PUBLISH', f'Ошибка проверки прав бота: {str(e)}', channel_id=channel_id)
        return False


async def publish_post_to_channel(
    bot: Bot,
    channel_id: int,
    post_text: str,
    button_text: str,
    button_url: str
) -> tuple[bool, int]:
    """
    Публикует пост на канале с кнопкой
    
    Args:
        bot: Объект бота
        channel_id: ID канала
        post_text: Текст поста
        button_text: Текст кнопки
        button_url: URL кнопки
        
    Returns:
        (success, message_id)
    """
    try:
        # Создаем кнопку
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(button_text, url=button_url)]
        ])
        
        # Публикуем пост
        message = await bot.send_message(
            chat_id=channel_id,
            text=post_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Закрепляем пост
        await bot.pin_chat_message(
            chat_id=channel_id,
            message_id=message.message_id,
            disable_notification=True
        )
        
        return True, message.message_id
        
    except TelegramError as e:
        bot_logger.error('PUBLISH', f'Ошибка публикации поста: {str(e)}', channel_id=channel_id)
        return False, 0

