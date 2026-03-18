"""
Обработчики для публикации поста-знакомства на канале
"""
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import Database
from config import UserState, BLUE_BUTTON_QUESTIONS, BEST_LINKS_COUNT
import messages
from channel_helper import check_if_channel, check_bot_admin, publish_post_to_channel
from n8n_helper import generate_request_id, send_to_n8n, wait_for_n8n_response
from logger import bot_logger
from video_helper import send_video_safe

# Инициализация базы данных
db = Database()


async def delete_message_safe(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> bool:
    """
    Безопасно удаляет сообщение (не падает при ошибке)
    
    Args:
        context: Контекст бота
        chat_id: ID чата
        message_id: ID сообщения
        
    Returns:
        True если удалено, False если нет
    """
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        bot_logger.warning('SYSTEM', f'Не удалось удалить сообщение {message_id}: {str(e)}', telegram_id=chat_id)
        return False


async def handle_publish_myself(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Опубликую сам"
    """
    await query.edit_message_text(
        messages.PUBLISH_MYSELF_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Переходим к следующему этапу - создание анонсов
    await start_anons_flow(context, telegram_id)


async def handle_help_publish(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Помоги опубликовать"
    """
    db.update_user_state(telegram_id, UserState.WAITING_CHANNEL_LINK)
    
    await query.edit_message_text(
        messages.REQUEST_CHANNEL_LINK_MESSAGE,
        parse_mode=ParseMode.HTML
    )


async def process_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, channel_link: str) -> None:
    """
    Обрабатывает ссылку на канал
    """
    # Проверяем, является ли это каналом
    is_channel, username, channel_id = await check_if_channel(context.bot, channel_link)
    
    if not is_channel:
        await update.message.reply_text(
            messages.NOT_A_CHANNEL_ERROR,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Сохраняем данные канала
    db.save_channel_data(telegram_id, username, channel_id)
    db.update_user_state(telegram_id, UserState.WAITING_BOT_ADMIN)
    
    # Создаем кнопку
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_BOT_ADDED,
            callback_data='bot_added'
        )]
    ])
    
    # Отправляем инструкцию
    await update.message.reply_text(
        messages.ADD_BOT_ADMIN_INSTRUCTION,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def check_bot_admin_status(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Проверяет, является ли бот администратором канала
    """
    # Получаем данные пользователя
    user_data = db.get_user_by_telegram_id(telegram_id)
    
    if not user_data or not user_data.get('channel_id'):
        await query.edit_message_text(
            "❌ Ошибка: данные канала не найдены",
            parse_mode=ParseMode.HTML
        )
        return
    
    channel_id = user_data['channel_id']
    bot_id = context.bot.id
    
    # Проверяем права бота
    is_admin = await check_bot_admin(context.bot, channel_id, bot_id)
    
    if not is_admin:
        await query.edit_message_text(
            messages.BOT_NOT_ADMIN_ERROR,
            parse_mode=ParseMode.HTML
        )
        # Возвращаем к запросу ссылки
        db.update_user_state(telegram_id, UserState.WAITING_CHANNEL_LINK)
        return
    
    # Бот является админом - начинаем задавать вопросы
    db.update_user_state(telegram_id, UserState.ANSWERING_BLUE_QUESTIONS)
    
    await query.edit_message_text(
        "✅ Отлично! Бот добавлен администратором.\n\nТеперь ответьте на несколько вопросов для создания поста.",
        parse_mode=ParseMode.HTML
    )
    
    # Начинаем с первого вопроса
    await ask_blue_question(context, telegram_id, 1)


async def ask_blue_question(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, question_num: int) -> None:
    """
    Задает вопрос для создания поста с кнопкой
    """
    # Получаем текст вопроса
    question_texts = [
        messages.BLUE_BUTTON_QUESTION_1,
        messages.BLUE_BUTTON_QUESTION_2,
        messages.BLUE_BUTTON_QUESTION_3,
        messages.BLUE_BUTTON_QUESTION_4,
        messages.BLUE_BUTTON_QUESTION_5
    ]
    
    if question_num <= len(question_texts):
        await context.bot.send_message(
            chat_id=telegram_id,
            text=question_texts[question_num - 1],
            parse_mode=ParseMode.HTML
        )


async def process_blue_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, answer: str, question_num: int) -> None:
    """
    Обрабатывает ответ на вопрос для поста с кнопкой
    """
    # Получаем текущие ответы
    blue_data = db.get_blue_button_data(telegram_id)
    if not blue_data:
        blue_data = {'blue_answers': {}}
    
    blue_answers = blue_data.get('blue_answers', {})
    
    # Сохраняем ответ
    blue_answers[f'blueotvet{question_num}'] = answer
    db.save_blue_button_data(telegram_id, blue_answers=blue_answers)
    
    # Если это был последний вопрос - переходим к запросу ссылок
    if question_num >= BLUE_BUTTON_QUESTIONS:
        db.update_user_state(telegram_id, UserState.REQUESTING_BEST_LINKS)
        await request_best_link(context, telegram_id, 1)
    else:
        # Задаем следующий вопрос
        await ask_blue_question(context, telegram_id, question_num + 1)


async def request_best_link(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, link_num: int) -> None:
    """
    Запрашивает ссылку на лучший пост
    """
    if link_num == 1:
        # Первая ссылка - показываем вводное сообщение
        await context.bot.send_message(
            chat_id=telegram_id,
            text=messages.REQUEST_BEST_POSTS_LINKS.format(link_number=link_num),
            parse_mode=ParseMode.HTML
        )
    
    # Создаем кнопку "Пропустить"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_SKIP_LINK,
            callback_data='skip_link'
        )]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=f"🔗 <b>Ссылка {link_num} из {BEST_LINKS_COUNT}:</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def process_best_link(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, link: str, link_num: int) -> None:
    """
    Обрабатывает ссылку на лучший пост
    """
    # Получаем текущие ссылки
    blue_data = db.get_blue_button_data(telegram_id)
    if not blue_data:
        blue_data = {'best_links': {}}
    
    best_links = blue_data.get('best_links', {})
    
    # Сохраняем ссылку
    best_links[f'link{link_num}'] = link
    db.save_blue_button_data(telegram_id, best_links=best_links)
    
    # Если это была последняя ссылка - генерируем пост
    if link_num >= BEST_LINKS_COUNT:
        await generate_blue_button_post(update, context, telegram_id)
    else:
        # Запрашиваем следующую ссылку
        await request_best_link(context, telegram_id, link_num + 1)


async def handle_skip_link(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает пропуск ссылки
    """
    # Получаем текущие ссылки
    blue_data = db.get_blue_button_data(telegram_id)
    if not blue_data:
        blue_data = {'best_links': {}}
    
    best_links = blue_data.get('best_links', {})
    
    # Определяем номер текущей ссылки
    current_link_num = len(best_links) + 1
    
    # Сохраняем пустую ссылку
    best_links[f'link{current_link_num}'] = ""
    db.save_blue_button_data(telegram_id, best_links=best_links)
    
    await query.answer("Пропущено")
    
    # Если это была последняя ссылка - генерируем пост
    if current_link_num >= BEST_LINKS_COUNT:
        await generate_blue_button_post(query, context, telegram_id)
    else:
        # Запрашиваем следующую ссылку
        await request_best_link(context, telegram_id, current_link_num + 1)


async def generate_blue_button_post(update_or_query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Генерирует пост с кнопкой через n8n
    """
    db.update_user_state(telegram_id, UserState.PROCESSING_BLUE_POST)
    
    # Отправляем сообщение об обработке
    processing_msg = await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.PROCESSING_BLUE_BUTTON_POST,
        parse_mode=ParseMode.HTML
    )
    
    # Получаем данные
    blue_data = db.get_blue_button_data(telegram_id)
    
    if not blue_data:
        await processing_msg.edit_text(
            messages.BLUE_BUTTON_POST_ERROR,
            parse_mode=ParseMode.HTML
        )
        # Возвращаемся к вопросам
        db.update_user_state(telegram_id, UserState.ANSWERING_BLUE_QUESTIONS)
        await ask_blue_question(context, telegram_id, 1)
        return
    
    blue_answers = blue_data.get('blue_answers', {})
    best_links = blue_data.get('best_links', {})
    
    # Получаем промпт из БД
    prompt_template = db.get_prompt('prompt_bluebutt')
    
    if not prompt_template:
        prompt_template = "Создай пост на основе ответов: blueotvet1, blueotvet2, blueotvet3, blueotvet4, blueotvet5. Добавь ссылки: link1, link2, link3, link4, link5"
    
    # Подставляем ответы и ссылки в промпт
    prompt_text = prompt_template
    for i in range(1, BLUE_BUTTON_QUESTIONS + 1):
        answer = blue_answers.get(f'blueotvet{i}', '')
        prompt_text = prompt_text.replace(f'blueotvet{i}', answer)
    
    for i in range(1, BEST_LINKS_COUNT + 1):
        link = best_links.get(f'link{i}', '')
        prompt_text = prompt_text.replace(f'link{i}', link)
    
    # Генерируем request_id
    request_id = generate_request_id()
    
    # Отправляем в n8n (prompt_bluebutt - пост-знакомство)
    success = send_to_n8n(telegram_id, prompt_text, request_id, 'bluebutt')
    
    if not success:
        await processing_msg.edit_text(
            messages.BLUE_BUTTON_POST_ERROR,
            parse_mode=ParseMode.HTML
        )
        db.update_user_state(telegram_id, UserState.ANSWERING_BLUE_QUESTIONS)
        await ask_blue_question(context, telegram_id, 1)
        return
    
    # Ждем ответ от n8n через webhook
    n8n_response = await wait_for_n8n_response(
        telegram_id,
        request_id,
        180
    )
    
    if n8n_response:
        # Сохраняем текст поста
        db.save_blue_button_data(telegram_id, post_text=n8n_response)
        
        # Показываем текст
        await processing_msg.edit_text(
            messages.BLUE_BUTTON_POST_READY.format(post_text=n8n_response),
            parse_mode=ParseMode.HTML
        )
        
        # Переходим к выбору действия кнопки
        db.update_user_state(telegram_id, UserState.CHOOSING_BUTTON_ACTION)
        await show_button_action_choice(context, telegram_id)
    else:
        # Таймаут
        await processing_msg.edit_text(
            messages.BLUE_BUTTON_POST_ERROR,
            parse_mode=ParseMode.HTML
        )
        db.update_user_state(telegram_id, UserState.ANSWERING_BLUE_QUESTIONS)
        await ask_blue_question(context, telegram_id, 1)


async def show_button_action_choice(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Показывает выбор куда ведет кнопка
    """
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_TO_DM,
            callback_data='button_to_dm'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_TO_WEBSITE,
            callback_data='button_to_website'
        )]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.CHOOSE_BUTTON_ACTION_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_button_to_dm(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "В личные сообщения"
    """
    # Получаем username пользователя
    user = query.from_user
    username = user.username
    
    if not username:
        await query.edit_message_text(
            "❌ У вас не установлен username в Telegram. Пожалуйста, установите его в настройках.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Сохраняем данные
    button_url = f"https://t.me/{username}"
    db.save_blue_button_data(telegram_id, button_action='dm', button_url=button_url)
    
    await query.edit_message_text(
        "✅ Кнопка будет вести в ваши личные сообщения",
        parse_mode=ParseMode.HTML
    )
    
    # Переходим к выбору текста кнопки
    db.update_user_state(telegram_id, UserState.CHOOSING_BUTTON_TEXT)
    await show_button_text_choice(context, telegram_id)


async def handle_button_to_website(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "На сайт"
    """
    db.update_user_state(telegram_id, UserState.WAITING_WEBSITE_LINK)
    
    await query.edit_message_text(
        messages.REQUEST_WEBSITE_LINK,
        parse_mode=ParseMode.HTML
    )


async def process_website_link(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, link: str) -> None:
    """
    Обрабатывает ссылку на сайт
    """
    # Сохраняем ссылку
    db.save_blue_button_data(telegram_id, button_action='website', button_url=link)
    
    await update.message.reply_text(
        "✅ Ссылка сохранена",
        parse_mode=ParseMode.HTML
    )
    
    # Переходим к выбору текста кнопки
    db.update_user_state(telegram_id, UserState.CHOOSING_BUTTON_TEXT)
    await show_button_text_choice(context, telegram_id)


async def show_button_text_choice(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Показывает выбор текста кнопки
    """
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.BUTTON_TEXT_ZHM, callback_data='button_text_zhm')],
        [InlineKeyboardButton(messages.BUTTON_TEXT_NAPISAT, callback_data='button_text_napisat')],
        [InlineKeyboardButton(messages.BUTTON_TEXT_ZAPIS, callback_data='button_text_zapis')],
        [InlineKeyboardButton(messages.BUTTON_TEXT_SKIDKA, callback_data='button_text_skidka')],
        [InlineKeyboardButton(messages.BUTTON_TEXT_NEED_HELP, callback_data='button_text_help')],
        [InlineKeyboardButton(messages.BUTTON_TEXT_CUSTOM, callback_data='button_text_custom')]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.CHOOSE_BUTTON_TEXT_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_button_text_choice(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, callback_data: str) -> None:
    """
    Обрабатывает выбор текста кнопки
    """
    text_map = {
        'button_text_zhm': messages.BUTTON_TEXT_ZHM,
        'button_text_napisat': messages.BUTTON_TEXT_NAPISAT,
        'button_text_zapis': messages.BUTTON_TEXT_ZAPIS,
        'button_text_skidka': messages.BUTTON_TEXT_SKIDKA,
        'button_text_help': messages.BUTTON_TEXT_NEED_HELP
    }
    
    if callback_data == 'button_text_custom':
        # Запрашиваем свой текст
        db.update_user_state(telegram_id, UserState.WAITING_CUSTOM_BUTTON_TEXT)
        await query.edit_message_text(
            messages.REQUEST_CUSTOM_BUTTON_TEXT,
            parse_mode=ParseMode.HTML
        )
    else:
        # Сохраняем выбранный текст
        button_text = text_map.get(callback_data, messages.BUTTON_TEXT_ZHM)
        db.save_blue_button_data(telegram_id, button_text=button_text)
        
        await query.answer("Текст кнопки выбран")
        
        # Показываем предпросмотр
        await show_post_preview(context, telegram_id)


async def process_custom_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, text: str) -> None:
    """
    Обрабатывает свой текст кнопки
    """
    # Сохраняем текст
    db.save_blue_button_data(telegram_id, button_text=text)
    
    await update.message.reply_text(
        "✅ Текст кнопки сохранен",
        parse_mode=ParseMode.HTML
    )
    
    # Показываем предпросмотр
    await show_post_preview(context, telegram_id)


async def show_post_preview(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Показывает предпросмотр поста с кнопкой
    """
    db.update_user_state(telegram_id, UserState.PREVIEW_POST)
    
    # Получаем все данные
    blue_data = db.get_blue_button_data(telegram_id)
    
    if not blue_data:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="❌ Ошибка: данные не найдены",
            parse_mode=ParseMode.HTML
        )
        return
    
    post_text = blue_data.get('blue_post_text', '')
    button_text = blue_data.get('button_text', 'КНОПКА')
    button_url = blue_data.get('button_url', 'https://t.me/')
    
    # Создаем кнопку для предпросмотра
    preview_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_text, url=button_url)]
    ])
    
    # Отправляем предпросмотр
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.POST_PREVIEW_MESSAGE.format(post_text=post_text),
        reply_markup=preview_keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Кнопки подтверждения
    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.BUTTON_POST_OK, callback_data='post_ok')],
        [InlineKeyboardButton(messages.BUTTON_POST_NO, callback_data='post_no')]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text="Все верно?",
        reply_markup=confirm_keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_post_confirmation(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, confirmed: bool) -> None:
    """
    Обрабатывает подтверждение публикации поста
    """
    if not confirmed:
        # Начинаем заново с вопросов
        db.update_user_state(telegram_id, UserState.ANSWERING_BLUE_QUESTIONS)
        await query.edit_message_text(
            "🔄 Хорошо, давайте создадим пост заново!",
            parse_mode=ParseMode.HTML
        )
        await ask_blue_question(context, telegram_id, 1)
        return
    
    # Публикуем пост
    await query.edit_message_text(
        "⏳ Публикую пост на канале...",
        parse_mode=ParseMode.HTML
    )
    
    # Получаем данные
    user_data = db.get_user_by_telegram_id(telegram_id)
    blue_data = db.get_blue_button_data(telegram_id)
    
    if not user_data or not blue_data:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="❌ Ошибка: данные не найдены",
            parse_mode=ParseMode.HTML
        )
        return
    
    channel_id = user_data.get('channel_id')
    post_text = blue_data.get('blue_post_text', '')
    button_text = blue_data.get('button_text', '')
    button_url = blue_data.get('button_url', '')
    
    # Публикуем пост
    success, message_id = await publish_post_to_channel(
        context.bot,
        channel_id,
        post_text,
        button_text,
        button_url
    )
    
    if success:
        db.update_user_state(telegram_id, UserState.POST_PUBLISHED)
        await context.bot.send_message(
            chat_id=telegram_id,
            text=messages.POST_PUBLISHED_SUCCESS,
            parse_mode=ParseMode.HTML
        )
        
        # Переходим к созданию анонсов
        await start_anons_flow(context, telegram_id)
    else:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="❌ Ошибка при публикации поста. Попробуйте еще раз.",
            parse_mode=ParseMode.HTML
        )


# ============================================
# ФУНКЦИИ ДЛЯ СОЗДАНИЯ АНОНСОВ
# ============================================

async def start_anons_flow(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Начинает процесс создания анонсов
    """
    from config import VIDEO_LEARN6, VIDEO_LEARN6_FILE_ID

    # Отправляем сообщение о готовности канала
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.CHANNEL_READY_NEED_AUDIENCE,
        parse_mode=ParseMode.HTML
    )

    await send_video_safe(context.bot, telegram_id, VIDEO_LEARN6, file_id=VIDEO_LEARN6_FILE_ID)
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.LEARN6_SENT)
    
    # Создаем кнопки
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_WRITE_ANONS_MYSELF,
            callback_data='write_anons_myself'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_HELP_WRITE_ANONS,
            callback_data='help_write_anons'
        )]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.LEARN6_VIDEO_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_write_anons_myself(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Напишу анонс сам"
    """
    db.update_user_state(telegram_id, UserState.WRITE_ANONS_MYSELF)
    
    await query.edit_message_text(
        messages.WRITE_ANONS_MYSELF_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Переход к созданию продающего поста
    await start_sales_post_flow(context, telegram_id)


async def handle_help_write_anons(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Напиши анонс за меня"
    """
    db.update_user_state(telegram_id, UserState.CREATING_ANONS)
    
    await query.edit_message_text(
        "✅ Отлично! Давайте создадим анонс для вашего поста.",
        parse_mode=ParseMode.HTML
    )
    
    # Задаем первый вопрос
    await ask_anons_question(context, telegram_id, 1)


async def ask_anons_question(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, question_num: int) -> None:
    """
    Задает вопрос для создания анонса
    """
    if question_num == 1:
        question_text = messages.ANONS_QUESTION_1
    elif question_num == 2:
        question_text = messages.ANONS_QUESTION_2
    else:
        return
    
    db.update_user_state(telegram_id, UserState.ANSWERING_ANONS_QUESTIONS)
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=question_text,
        parse_mode=ParseMode.HTML
    )


async def process_anons_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, answer: str, question_num: int) -> None:
    """
    Обрабатывает ответ на вопрос для анонса
    """
    if question_num == 1:
        # Сохраняем первый ответ
        db.save_anons_data(telegram_id, anons1=answer)
        # Задаем второй вопрос
        await ask_anons_question(context, telegram_id, 2)
    elif question_num == 2:
        # Сохраняем второй ответ
        db.save_anons_data(telegram_id, anons2=answer)
        # Генерируем анонс
        await generate_anons_with_n8n(update, context, telegram_id)


async def generate_anons_with_n8n(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Генерирует анонс через n8n
    """
    db.update_user_state(telegram_id, UserState.PROCESSING_ANONS)
    
    # Отправляем сообщение об обработке
    processing_msg = await update.message.reply_text(
        messages.PROCESSING_ANONS_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Получаем данные
    anons_data = db.get_anons_data(telegram_id)
    
    if not anons_data or not anons_data.get('anons1') or not anons_data.get('anons2'):
        await processing_msg.edit_text(
            messages.ANONS_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаемся к первому вопросу
        await ask_anons_question(context, telegram_id, 1)
        return
    
    anons1 = anons_data['anons1']
    anons2 = anons_data['anons2']
    
    # Получаем промпт из БД
    prompt_template = db.get_prompt('prompt_anons')
    
    if not prompt_template:
        prompt_template = f"Создай анонс для поста на основе: О чем пост: anons1. Ссылка: anons2"
    
    # Подставляем ответы в промпт
    prompt_text = prompt_template.replace('anons1', anons1).replace('anons2', anons2)
    
    # Генерируем request_id
    request_id = generate_request_id()
    
    # Отправляем в n8n (prompt_anons - создание анонсов)
    success = send_to_n8n(telegram_id, prompt_text, request_id, 'anons')
    
    if not success:
        await processing_msg.edit_text(
            messages.ANONS_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        await ask_anons_question(context, telegram_id, 1)
        return
    
    # Ждем ответ от n8n через webhook
    n8n_response = await wait_for_n8n_response(
        telegram_id,
        request_id,
        180
    )
    
    if n8n_response:
        # Сохраняем готовый анонс
        db.save_anons_data(telegram_id, anons_text=n8n_response)
        db.update_user_state(telegram_id, UserState.ANONS_COMPLETED)
        
        # Показываем анонс (это важное сообщение)
        await processing_msg.edit_text(
            messages.ANONS_READY_MESSAGE.format(anons_text=n8n_response),
            parse_mode=ParseMode.HTML
        )
        
        # Удаляем ответ пользователя (не нужен больше)
        await delete_message_safe(context, telegram_id, update.message.message_id)
        
        # Автоматически переходим к созданию продающего поста
        await start_sales_post_flow(context, telegram_id)
    else:
        # Таймаут
        await processing_msg.edit_text(
            messages.ANONS_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        await ask_anons_question(context, telegram_id, 1)


# ============================================
# ФУНКЦИИ ДЛЯ СОЗДАНИЯ ПРОДАЮЩЕГО ПОСТА
# ============================================

async def start_sales_post_flow(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Начинает процесс создания продающего поста
    """
    from config import VIDEO_LEARN7, VIDEO_LEARN7_FILE_ID

    # Отправляем сообщение о готовности к продажам
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.READY_FOR_SALES_MESSAGE,
        parse_mode=ParseMode.HTML
    )

    await send_video_safe(context.bot, telegram_id, VIDEO_LEARN7, file_id=VIDEO_LEARN7_FILE_ID)
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.LEARN7_SENT)
    
    # Создаем кнопки
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_WRITE_SALES_MYSELF,
            callback_data='write_sales_myself'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_HELP_WRITE_SALES,
            callback_data='help_write_sales'
        )]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.LEARN7_VIDEO_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_write_sales_myself(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Напишу пост сам"
    """
    db.update_user_state(telegram_id, UserState.WRITE_SALES_MYSELF)
    
    await query.edit_message_text(
        messages.WRITE_SALES_MYSELF_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Переход к финальному шагу
    await show_final_step(context, telegram_id)


async def handle_help_write_sales(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Напиши продающий пост за меня"
    """
    # Обнуляем счетчик переписываний при начале создания нового поста
    db.save_sales_data(telegram_id, rewrite_count=0)
    db.update_user_state(telegram_id, UserState.CREATING_SALES_POST)
    
    await query.edit_message_text(
        "✅ Отлично! Давайте создадим продающий пост.",
        parse_mode=ParseMode.HTML
    )
    
    # Задаем первый вопрос
    await ask_sales_question(context, telegram_id, 1)


async def ask_sales_question(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, question_num: int) -> None:
    """
    Задает вопрос для создания продающего поста
    """
    if question_num == 1:
        question_text = messages.SALES_QUESTION_1
    elif question_num == 2:
        question_text = messages.SALES_QUESTION_2
    elif question_num == 3:
        question_text = messages.SALES_QUESTION_3
    else:
        return
    
    db.update_user_state(telegram_id, UserState.ANSWERING_SALES_QUESTIONS)
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=question_text,
        parse_mode=ParseMode.HTML
    )


async def process_sales_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, answer: str, question_num: int) -> None:
    """
    Обрабатывает ответ на вопрос для продающего поста
    """
    if question_num == 1:
        # Сохраняем первый ответ
        db.save_sales_data(telegram_id, prodaj1=answer)
        # Задаем второй вопрос
        await ask_sales_question(context, telegram_id, 2)
    elif question_num == 2:
        # Сохраняем второй ответ
        db.save_sales_data(telegram_id, prodaj2=answer)
        # Задаем третий вопрос
        await ask_sales_question(context, telegram_id, 3)
    elif question_num == 3:
        # Сохраняем третий ответ
        db.save_sales_data(telegram_id, prodaj3=answer)
        # Генерируем продающий пост
        await generate_sales_post_with_n8n(update, context, telegram_id)


async def generate_sales_post_with_n8n(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Генерирует продающий пост через n8n
    """
    db.update_user_state(telegram_id, UserState.PROCESSING_SALES_POST)
    
    # Отправляем сообщение об обработке
    processing_msg = await update.message.reply_text(
        messages.PROCESSING_SALES_POST_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Получаем данные
    sales_data = db.get_sales_data(telegram_id)
    
    if not sales_data or not sales_data.get('prodaj1') or not sales_data.get('prodaj2') or not sales_data.get('prodaj3'):
        await processing_msg.edit_text(
            messages.SALES_POST_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаемся к первому вопросу
        await ask_sales_question(context, telegram_id, 1)
        return
    
    prodaj1 = sales_data['prodaj1']
    prodaj2 = sales_data['prodaj2']
    prodaj3 = sales_data['prodaj3']
    
    # Получаем промпт из БД
    prompt_template = db.get_prompt('prompt_prodaj')
    
    if not prompt_template:
        prompt_template = f"Создай продающий пост на основе: Продукт: prodaj1. Проблема: prodaj2. Призыв: prodaj3"
    
    # Подставляем ответы в промпт
    prompt_text = prompt_template.replace('prodaj1', prodaj1).replace('prodaj2', prodaj2).replace('prodaj3', prodaj3)
    
    # Генерируем request_id
    request_id = generate_request_id()
    
    # Отправляем в n8n (prompt_prodaj - продающий пост)
    success = send_to_n8n(telegram_id, prompt_text, request_id, 'prodaj')
    
    if not success:
        await processing_msg.edit_text(
            messages.SALES_POST_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        await ask_sales_question(context, telegram_id, 1)
        return
    
    # Ждем ответ от n8n через webhook
    n8n_response = await wait_for_n8n_response(
        telegram_id,
        request_id,
        180
    )
    
    if n8n_response:
        # Сохраняем готовый продающий пост
        db.save_sales_data(telegram_id, sales_text=n8n_response)
        db.update_user_state(telegram_id, UserState.SALES_POST_READY)
        
        # Удаляем ответ пользователя (не нужен больше)
        await delete_message_safe(context, telegram_id, update.message.message_id)
        
        # Проверяем количество переписываний
        sales_data = db.get_sales_data(telegram_id)
        rewrite_count = sales_data.get('rewrite_count', 0) if sales_data else 0
        
        # Если это уже второй раз (после переписывания) - показываем без кнопок и переходим дальше
        if rewrite_count >= 1:
            message_text = messages.SALES_POST_REWRITTEN_MESSAGE.format(sales_text=n8n_response)
            # Показываем пост БЕЗ кнопок
            await processing_msg.edit_text(
                message_text,
                parse_mode=ParseMode.HTML
            )
            # Автоматически переходим к финальному шагу через 2 секунды
            await asyncio.sleep(2)
            await show_final_step(context, telegram_id)
        else:
            # Первый показ - даем возможность переписать
            message_text = messages.SALES_POST_READY_MESSAGE.format(sales_text=n8n_response)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    messages.BUTTON_REWRITE_SALES,
                    callback_data='rewrite_sales'
                )],
                [InlineKeyboardButton(
                    messages.BUTTON_TO_FINAL_STEP,
                    callback_data='to_final_step'
                )]
            ])
            # Показываем продающий пост с кнопками
            await processing_msg.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    else:
        # Таймаут
        await processing_msg.edit_text(
            messages.SALES_POST_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        await ask_sales_question(context, telegram_id, 1)


async def handle_rewrite_sales(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает нажатие кнопки "Переписать"
    """
    # Увеличиваем счетчик переписываний
    sales_data = db.get_sales_data(telegram_id)
    rewrite_count = sales_data.get('rewrite_count', 0) if sales_data else 0
    
    # Очищаем старые ответы для повторного ввода (используем пустые строки вместо None)
    db.save_sales_data(telegram_id, prodaj1='', prodaj2='', prodaj3='', rewrite_count=rewrite_count + 1)
    
    # Устанавливаем состояние ответа на вопросы (не REWRITING, а ANSWERING)
    db.update_user_state(telegram_id, UserState.ANSWERING_SALES_QUESTIONS)
    
    await query.edit_message_text(
        "🔄 Отлично! Давайте переработаем пост. Ответьте на вопросы еще раз.",
        parse_mode=ParseMode.HTML
    )
    
    # Задаем вопросы заново
    await ask_sales_question(context, telegram_id, 1)


async def handle_to_final_step(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает переход к финальному шагу
    """
    await query.edit_message_text(
        "✅ Отлично! Переходим к финальному шагу.",
        parse_mode=ParseMode.HTML
    )
    
    await show_final_step(context, telegram_id)


async def show_final_step(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Показывает финальные сообщения и завершает обучение
    """
    db.update_user_state(telegram_id, UserState.FINAL_STEP)
    
    # Отправляем три финальных сообщения по очереди
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.FINAL_STEP_MESSAGE_1,
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(2)
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.FINAL_STEP_MESSAGE_2,
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(2)
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.FINAL_STEP_MESSAGE_3,
        parse_mode=ParseMode.HTML
    )
    
    # Устанавливаем финальное состояние - обучение полностью завершено
    db.update_user_state(telegram_id, UserState.COMPLETED)
    
    bot_logger.info('USER', f'Пользователь завершил обучение', telegram_id=telegram_id)

