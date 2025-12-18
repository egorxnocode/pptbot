"""
Обработчики команд и сообщений бота
"""
import re
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import Database
from config import (
    UserState, VIDEO_LEARN1, VIDEO_LEARN2, VIDEO_LEARN3, VIDEO_LEARN4, TEMP_FOLDER,
    TOTAL_POSTS, QUESTIONS_PER_POST, MAX_POST_ATTEMPTS
)
import messages
from reminders import schedule_reminders, cancel_reminders
from openai_helper import transcribe_voice
from n8n_helper import generate_request_id, send_to_n8n, wait_for_n8n_response
from publish_handlers import (
    handle_publish_myself, handle_help_publish, process_channel_link,
    check_bot_admin_status, process_blue_answer, process_best_link,
    handle_skip_link, handle_button_to_dm, handle_button_to_website,
    process_website_link, handle_button_text_choice, process_custom_button_text,
    handle_post_confirmation,
    start_anons_flow, handle_write_anons_myself, handle_help_write_anons,
    process_anons_answer,
    start_sales_post_flow, handle_write_sales_myself, handle_help_write_sales,
    process_sales_answer, handle_rewrite_sales, handle_to_final_step
)
import asyncio
from logger import bot_logger


# Инициализация базы данных
db = Database()


def is_valid_email(email: str) -> bool:
    """
    Проверяет корректность email адреса
    
    Args:
        email: Email адрес для проверки
        
    Returns:
        True если email корректный, False если нет
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start
    Отправляет приветственное сообщение и запрашивает email
    """
    user = update.effective_user
    telegram_id = user.id
    
    bot_logger.user_start(telegram_id, user.username, user.first_name)
    
    # Проверяем, зарегистрирован ли пользователь
    user_data = db.get_user_by_telegram_id(telegram_id)
    
    if user_data:
        current_state = user_data.get('state', UserState.NEW)
        
        # Если пользователь уже прошел регистрацию
        if current_state in [UserState.REGISTERED, UserState.VIDEO_SENT, UserState.VIDEO_WATCHED]:
            await update.message.reply_text(
                "Вы уже зарегистрированы в системе!",
                parse_mode=ParseMode.HTML
            )
            return
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        messages.START_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Обновляем состояние пользователя
    if user_data:
        db.update_user_state(telegram_id, UserState.WAITING_EMAIL)
    
    # Сохраняем состояние в контексте
    context.user_data['state'] = UserState.WAITING_EMAIL


async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик ввода email
    Проверяет email в базе данных и регистрирует пользователя
    """
    user = update.effective_user
    telegram_id = user.id
    email_input = update.message.text.strip()
    
    # Проверяем текущее состояние пользователя
    user_state = context.user_data.get('state')
    
    # Если не в состоянии ожидания email, проверяем БД
    if user_state != UserState.WAITING_EMAIL:
        user_data = db.get_user_by_telegram_id(telegram_id)
        if not user_data or user_data.get('state') != UserState.WAITING_EMAIL:
            return
    
    # Проверяем корректность email
    if not is_valid_email(email_input):
        await update.message.reply_text(
            messages.INVALID_EMAIL,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Преобразуем email в нижний регистр
    email = email_input.lower()
    
    # Проверяем наличие email в базе данных
    if not db.check_email_exists(email):
        await update.message.reply_text(
            messages.EMAIL_NOT_FOUND,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Email найден - регистрируем пользователя
    db.update_user_telegram_id(email, telegram_id)
    db.update_user_state(telegram_id, UserState.REGISTERED)
    
    # Отправляем сообщение об успешной регистрации
    await update.message.reply_text(
        messages.REGISTRATION_SUCCESS,
        parse_mode=ParseMode.HTML
    )
    
    # Отправляем видео
    await send_video_and_button(update, context, telegram_id)


async def send_video_and_button(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Отправляет обучающее видео и кнопку для подтверждения просмотра
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Проверяем наличие видеофайла и отправляем если есть
    if os.path.exists(VIDEO_LEARN1):
        try:
            with open(VIDEO_LEARN1, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    supports_streaming=True
                )
        except Exception as e:
            bot_logger.error('VIDEO', f'Ошибка при отправке видео learn1.mp4: {str(e)}', 
                           telegram_id=telegram_id)
            # Продолжаем работу даже если не удалось отправить видео
    
    # Создаем inline кнопку
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_VIDEO_WATCHED,
            callback_data='video_watched'
        )]
    ])
    
    # Отправляем сообщение с кнопкой
    await update.message.reply_text(
        messages.VIDEO_SENT_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Обновляем состояние в БД
    db.update_user_state(telegram_id, UserState.VIDEO_SENT)
    db.update_video_sent_time(telegram_id)
    
    # Запускаем систему напоминаний
    await schedule_reminders(context, telegram_id)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик нажатия на inline кнопки
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    telegram_id = user.id
    
    # Обработка кнопки "Видео просмотрено"
    if query.data == 'video_watched':
        # Отменяем все запланированные напоминания
        cancel_reminders(context, telegram_id)
        
        # Обновляем состояние пользователя
        db.update_user_state(telegram_id, UserState.VIDEO_WATCHED)
        
        # Отправляем сообщение о завершении этапа
        await query.edit_message_text(
            messages.VIDEO_WATCHED_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        
        # Переходим к вопросу о канале
        await ask_about_channel(query, context, telegram_id)
    
    # Обработка кнопки "Нужно создать"
    elif query.data == 'need_create_channel':
        db.update_user_state(telegram_id, UserState.CHANNEL_CREATING)
        await send_channel_creation_instructions(query, context, telegram_id)
    
    # Обработка кнопки "Канал создан, едем дальше"
    elif query.data == 'channel_created':
        db.update_user_state(telegram_id, UserState.CHANNEL_CREATED)
        await send_learn3_video(query, context, telegram_id)
    
    # Обработка кнопки "Нужна помощь"
    elif query.data == 'need_help':
        db.update_user_state(telegram_id, UserState.WAITING_HELP)
        await handle_help_request(query, context, telegram_id)
    
    # Обработка кнопки "Едем дальше"
    elif query.data == 'continue_learning':
        db.update_user_state(telegram_id, UserState.CONTINUE_LEARNING)
        await handle_continue_learning(query, context, telegram_id)
    
    # Обработка кнопки "Напишу сам"
    elif query.data == 'write_myself':
        db.update_user_state(telegram_id, UserState.WRITE_MYSELF)
        await handle_write_myself(query, context, telegram_id)
    
    # Обработка кнопки "Напиши мне посты"
    elif query.data == 'write_posts':
        db.update_user_state(telegram_id, UserState.CREATING_POSTS)
        await start_creating_posts(query, context, telegram_id)
    
    # Обработка кнопки "Переписать"
    elif query.data == 'rewrite_post':
        await handle_rewrite_post(query, context, telegram_id)
    
    # Обработка кнопки "Написать следующий пост"
    elif query.data == 'next_post':
        await handle_next_post(query, context, telegram_id)
    
    # Обработка кнопок для публикации
    elif query.data == 'publish_myself':
        db.update_user_state(telegram_id, UserState.PUBLISH_MYSELF)
        await handle_publish_myself(query, context, telegram_id)
    
    elif query.data == 'help_publish':
        db.update_user_state(telegram_id, UserState.HELP_PUBLISH)
        await handle_help_publish(query, context, telegram_id)
    
    elif query.data == 'bot_added':
        await check_bot_admin_status(query, context, telegram_id)
    
    elif query.data == 'skip_link':
        await handle_skip_link(query, context, telegram_id)
    
    elif query.data == 'button_to_dm':
        await handle_button_to_dm(query, context, telegram_id)
    
    elif query.data == 'button_to_website':
        await handle_button_to_website(query, context, telegram_id)
    
    elif query.data.startswith('button_text_'):
        await handle_button_text_choice(query, context, telegram_id, query.data)
    
    elif query.data == 'post_ok':
        await handle_post_confirmation(query, context, telegram_id, True)
    
    elif query.data == 'post_no':
        await handle_post_confirmation(query, context, telegram_id, False)
    
    # Обработка кнопок для анонсов
    elif query.data == 'write_anons_myself':
        await handle_write_anons_myself(query, context, telegram_id)
    
    elif query.data == 'help_write_anons':
        await handle_help_write_anons(query, context, telegram_id)
    
    # Обработка кнопок для продающего поста
    elif query.data == 'write_sales_myself':
        await handle_write_sales_myself(query, context, telegram_id)
    
    elif query.data == 'help_write_sales':
        await handle_help_write_sales(query, context, telegram_id)
    
    elif query.data == 'rewrite_sales':
        await handle_rewrite_sales(query, context, telegram_id)
    
    elif query.data == 'to_final_step':
        await handle_to_final_step(query, context, telegram_id)


async def ask_about_channel(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Спрашивает пользователя о наличии телеграм канала
    
    Args:
        query: Query объект от callback
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.CHANNEL_QUESTION)
    
    # Создаем кнопки для выбора
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_CHANNEL_CREATED,
            callback_data='channel_created'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_NEED_CREATE_CHANNEL,
            callback_data='need_create_channel'
        )]
    ])
    
    # Отправляем вопрос о канале
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.CHANNEL_QUESTION_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def send_channel_creation_instructions(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Отправляет инструкцию по созданию канала (видео + текст)
    
    Args:
        query: Query объект от callback
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Отправляем вводное сообщение
    await query.edit_message_text(
        messages.CHANNEL_CREATION_INTRO,
        parse_mode=ParseMode.HTML
    )
    
    # Проверяем наличие видеофайла learn2.mp4
    if os.path.exists(VIDEO_LEARN2):
        # Отправляем видео
        with open(VIDEO_LEARN2, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=telegram_id,
                video=video_file,
                supports_streaming=True
            )
    else:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"❌ Ошибка: видеофайл не найден ({VIDEO_LEARN2})",
            parse_mode=ParseMode.HTML
        )
    
    # Отправляем текстовую инструкцию
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.CHANNEL_CREATION_TEXT_INSTRUCTION,
        parse_mode=ParseMode.HTML
    )
    
    # Создаем кнопку для подтверждения создания канала
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_CHANNEL_CREATED,
            callback_data='channel_created'
        )]
    ])
    
    # Отправляем сообщение с кнопкой
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.CHANNEL_CREATION_COMPLETE_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def send_learn3_video(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Отправляет видео learn3.mp4 после подтверждения создания канала
    
    Args:
        query: Query объект от callback
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Отправляем сообщение о готовности канала
    await query.edit_message_text(
        messages.CHANNEL_READY_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Проверяем наличие видеофайла learn3.mp4
    if os.path.exists(VIDEO_LEARN3):
        # Отправляем видео
        with open(VIDEO_LEARN3, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=telegram_id,
                video=video_file,
                supports_streaming=True
            )
    else:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"❌ Ошибка: видеофайл не найден ({VIDEO_LEARN3})",
            parse_mode=ParseMode.HTML
        )
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.LEARN3_SENT)
    
    # Создаем кнопки для выбора действия
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_NEED_HELP,
            callback_data='need_help'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_CONTINUE,
            callback_data='continue_learning'
        )]
    ])
    
    # Отправляем сообщение с кнопками
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.LEARN3_VIDEO_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_help_request(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает запрос на помощь
    Запрашивает информацию о пользователе
    
    Args:
        query: Query объект от callback
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.WAITING_HELP_ANSWER)
    
    # Запрашиваем информацию о пользователе
    await query.edit_message_text(
        messages.HELP_REQUEST_MESSAGE,
        parse_mode=ParseMode.HTML
    )


async def handle_continue_learning(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает продолжение обучения
    Переход к этапу наполнения канала
    
    Args:
        query: Query объект от callback
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.CONTINUE_LEARNING)
    
    # Отправляем сообщение о переходе к следующему этапу
    await query.edit_message_text(
        "🎉 <b>Отлично!</b>\n\nПереходим к следующему этапу!",
        parse_mode=ParseMode.HTML
    )
    
    # Переходим к этапу наполнения канала
    await send_fill_channel_step(context, telegram_id)


async def process_help_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_answer: str) -> None:
    """
    Обрабатывает ответ пользователя о себе и отправляет в n8n
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
        user_answer: Ответ пользователя (текст или транскрибированный голос)
    """
    user = update.effective_user
    telegram_id = user.id
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.PROCESSING_HELP)
    
    # Отправляем сообщение об обработке
    processing_msg = await update.message.reply_text(
        messages.PROCESSING_HELP_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Получаем промпт из БД
    prompt_template = db.get_prompt('prompt_osebe')
    
    if not prompt_template:
        # Если промпт не найден, используем дефолтный
        prompt_template = f"Пользователь рассказал о себе: otvet_osebe\n\nПомоги подобрать для него оптимальные варианты."
    
    # Подставляем ответ пользователя в промпт
    prompt_text = prompt_template.replace('otvet_osebe', user_answer)
    
    # Генерируем уникальный request_id
    request_id = generate_request_id()
    
    # Сохраняем запрос в БД
    db.save_n8n_request(telegram_id, request_id, user_answer)
    
    # Отправляем в n8n (prompt_osebe - рассказ о себе)
    success = send_to_n8n(telegram_id, prompt_text, request_id, 'osebe')
    
    if not success:
        await processing_msg.edit_text(
            messages.HELP_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаем в состояние WAITING_HELP
        db.update_user_state(telegram_id, UserState.WAITING_HELP)
        return
    
    # Ждем ответ от n8n (в отдельной корутине, чтобы не блокировать)
    n8n_response = await asyncio.to_thread(
        wait_for_n8n_response,
        db,
        telegram_id,
        request_id,
        180  # 3 минуты
    )
    
    if n8n_response:
        # Получили ответ от n8n
        db.update_user_state(telegram_id, UserState.HELP_COMPLETED)
        
        # Отправляем варианты пользователю
        await processing_msg.edit_text(
            messages.HELP_VARIANTS_MESSAGE.format(n8n_response=n8n_response),
            parse_mode=ParseMode.HTML
        )
        
        # Переходим к следующему этапу
        await send_fill_channel_step(context, telegram_id)
    else:
        # Таймаут - не получили ответ
        await processing_msg.edit_text(
            messages.HELP_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаем в состояние WAITING_HELP
        db.update_user_state(telegram_id, UserState.WAITING_HELP)


async def send_fill_channel_step(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Отправляет этап наполнения канала (learn4.mp4)
    
    Args:
        context: Контекст бота
        telegram_id: ID пользователя в Telegram
    """
    # Отправляем сообщение о наполнении канала
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.FILL_CHANNEL_INTRO_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Проверяем наличие видеофайла learn4.mp4
    if os.path.exists(VIDEO_LEARN4):
        # Отправляем видео
        with open(VIDEO_LEARN4, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=telegram_id,
                video=video_file,
                supports_streaming=True
            )
    else:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"❌ Ошибка: видеофайл не найден ({VIDEO_LEARN4})",
            parse_mode=ParseMode.HTML
        )
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.LEARN4_SENT)
    
    # Создаем кнопки для выбора
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_WRITE_POSTS,
            callback_data='write_posts'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_WRITE_MYSELF,
            callback_data='write_myself'
        )]
    ])
    
    # Отправляем сообщение с кнопками
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.LEARN4_VIDEO_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик голосовых сообщений
    Транскрибирует голос с помощью OpenAI Whisper
    """
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем состояние пользователя
    user_state = db.get_user_state(telegram_id)
    
    # Обрабатываем голос только если ждем ответ
    valid_states = [
        UserState.WAITING_HELP_ANSWER,
        UserState.ANSWERING_POST_QUESTIONS,
        UserState.ANSWERING_BLUE_QUESTIONS
    ]
    if user_state not in valid_states:
        return
    
    # Скачиваем голосовое сообщение
    voice = update.message.voice
    voice_file = await context.bot.get_file(voice.file_id)
    
    # Создаем папку для временных файлов если её нет
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    
    # Сохраняем голосовое сообщение
    voice_path = os.path.join(TEMP_FOLDER, f"{telegram_id}_{voice.file_id}.ogg")
    await voice_file.download_to_drive(voice_path)
    
    # Отправляем сообщение о транскрибации
    transcribing_msg = await update.message.reply_text(
        "🎤 Обрабатываю голосовое сообщение...",
        parse_mode=ParseMode.HTML
    )
    
    # Транскрибируем голос
    transcribed_text = transcribe_voice(voice_path)
    
    # Удаляем временный файл
    try:
        os.remove(voice_path)
    except:
        pass
    
    if transcribed_text:
        # Удаляем сообщение о транскрибации
        await transcribing_msg.delete()
        
        # Обрабатываем как текстовый ответ в зависимости от состояния
        if user_state == UserState.WAITING_HELP_ANSWER:
            await process_help_answer(update, context, transcribed_text)
        elif user_state == UserState.ANSWERING_POST_QUESTIONS:
            await process_post_question_answer(update, context, telegram_id, transcribed_text)
        elif user_state == UserState.ANSWERING_BLUE_QUESTIONS:
            blue_data = db.get_blue_button_data(telegram_id)
            if blue_data:
                question_num = len(blue_data.get('blue_answers', {})) + 1
            else:
                question_num = 1
            await process_blue_answer(update, context, telegram_id, transcribed_text, question_num)
    else:
        await transcribing_msg.edit_text(
            "❌ Не удалось распознать голосовое сообщение. Попробуйте еще раз или отправьте текстом.",
            parse_mode=ParseMode.HTML
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Общий обработчик текстовых сообщений
    Направляет обработку в зависимости от состояния пользователя
    """
    user = update.effective_user
    telegram_id = user.id
    
    # Получаем состояние пользователя
    user_state = context.user_data.get('state')
    
    # Если состояние не сохранено в контексте, проверяем БД
    if not user_state:
        user_data = db.get_user_by_telegram_id(telegram_id)
        if user_data:
            user_state = user_data.get('state', UserState.NEW)
        else:
            user_state = UserState.NEW
    
    # В зависимости от состояния вызываем нужный обработчик
    if user_state in [UserState.NEW, UserState.WAITING_EMAIL]:
        await handle_email(update, context)
    elif user_state == UserState.WAITING_HELP_ANSWER:
        # Обрабатываем ответ пользователя о себе
        user_answer = update.message.text.strip()
        await process_help_answer(update, context, user_answer)
    elif user_state == UserState.ANSWERING_POST_QUESTIONS:
        # Обрабатываем ответ на вопрос по посту
        user_answer = update.message.text.strip()
        await process_post_question_answer(update, context, telegram_id, user_answer)
    elif user_state == UserState.WAITING_CHANNEL_LINK:
        # Обрабатываем ссылку на канал
        channel_link = update.message.text.strip()
        await process_channel_link(update, context, telegram_id, channel_link)
    elif user_state == UserState.ANSWERING_BLUE_QUESTIONS:
        # Обрабатываем ответ на вопрос для поста с кнопкой
        user_answer = update.message.text.strip()
        # Определяем номер вопроса
        blue_data = db.get_blue_button_data(telegram_id)
        if blue_data:
            question_num = len(blue_data.get('blue_answers', {})) + 1
        else:
            question_num = 1
        await process_blue_answer(update, context, telegram_id, user_answer, question_num)
    elif user_state == UserState.REQUESTING_BEST_LINKS:
        # Обрабатываем ссылку на лучший пост
        link = update.message.text.strip()
        blue_data = db.get_blue_button_data(telegram_id)
        if blue_data:
            link_num = len(blue_data.get('best_links', {})) + 1
        else:
            link_num = 1
        await process_best_link(update, context, telegram_id, link, link_num)
    elif user_state == UserState.WAITING_WEBSITE_LINK:
        # Обрабатываем ссылку на сайт
        link = update.message.text.strip()
        await process_website_link(update, context, telegram_id, link)
    elif user_state == UserState.WAITING_CUSTOM_BUTTON_TEXT:
        # Обрабатываем свой текст кнопки
        text = update.message.text.strip()
        await process_custom_button_text(update, context, telegram_id, text)
    elif user_state == UserState.ANSWERING_ANONS_QUESTIONS:
        # Обрабатываем ответ на вопрос для анонса
        answer = update.message.text.strip()
        # Определяем номер вопроса
        anons_data = db.get_anons_data(telegram_id)
        if anons_data and anons_data.get('anons1'):
            question_num = 2
        else:
            question_num = 1
        await process_anons_answer(update, context, telegram_id, answer, question_num)
    elif user_state == UserState.ANSWERING_SALES_QUESTIONS:
        # Обрабатываем ответ на вопрос для продающего поста
        answer = update.message.text.strip()
        # Определяем номер вопроса
        sales_data = db.get_sales_data(telegram_id)
        if sales_data:
            if sales_data.get('prodaj1') and sales_data.get('prodaj2'):
                question_num = 3
            elif sales_data.get('prodaj1'):
                question_num = 2
            else:
                question_num = 1
        else:
            question_num = 1
        await process_sales_answer(update, context, telegram_id, answer, question_num)
    else:
        # Для других состояний можно добавить обработку позже
        pass


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПОСТАМИ
# ============================================

async def handle_write_myself(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает выбор "Напишу сам"
    """
    await query.edit_message_text(
        messages.WRITE_MYSELF_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Переходим к публикации поста-знакомства
    await start_publish_intro_post(context, telegram_id)


async def start_creating_posts(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Начинает процесс создания 5 постов
    """
    # Инициализируем прогресс: пост 1, вопрос 1, попытка 1
    db.update_user_post_progress(telegram_id, 1, 1, 1, {})
    
    # Отправляем приветственное сообщение
    await query.edit_message_text(
        messages.START_CREATING_POSTS_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Начинаем с первого поста
    await ask_post_question(context, telegram_id, 1, 1)


async def ask_post_question(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, post_num: int, question_num: int) -> None:
    """
    Задает вопрос по посту
    
    Args:
        context: Контекст бота
        telegram_id: ID пользователя
        post_num: Номер поста (1-5)
        question_num: Номер вопроса (1-3)
    """
    # Получаем данные поста из БД
    post_data = db.get_post_data(post_num)
    
    if not post_data:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"❌ Ошибка: данные для поста {post_num} не найдены в БД",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Если это первый вопрос - показываем тему поста
    if question_num == 1:
        topic = post_data.get('topic', f'Пост #{post_num}')
        await context.bot.send_message(
            chat_id=telegram_id,
            text=messages.POST_TOPIC_MESSAGE.format(post_number=post_num, topic=topic),
            parse_mode=ParseMode.HTML
        )
    
    # Получаем вопрос
    question_key = f'vopros_{question_num}'
    question_text = post_data.get(question_key, '')
    
    if not question_text:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"❌ Ошибка: вопрос {question_num} для поста {post_num} не найден",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.ANSWERING_POST_QUESTIONS)
    
    # Задаем вопрос
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.POST_QUESTION_MESSAGE.format(
            question_number=question_num,
            question=question_text
        ),
        parse_mode=ParseMode.HTML
    )


async def process_post_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, answer: str) -> None:
    """
    Обрабатывает ответ на вопрос по посту
    """
    # Получаем текущий прогресс
    progress = db.get_user_post_progress(telegram_id)
    
    if not progress:
        await update.message.reply_text(
            "❌ Ошибка: прогресс не найден",
            parse_mode=ParseMode.HTML
        )
        return
    
    current_post = progress['current_post_number']
    current_question = progress['current_question_number']
    attempt = progress['post_attempt']
    answers = progress['post_answers']
    
    # Сохраняем ответ
    answer_key = f'answer_{current_question}'
    answers[answer_key] = answer
    
    # Если это был последний вопрос - генерируем пост
    if current_question >= QUESTIONS_PER_POST:
        # Обновляем прогресс перед генерацией
        db.update_user_post_progress(telegram_id, current_post, current_question, attempt, answers)
        
        # Генерируем пост
        await generate_post_with_n8n(update, context, telegram_id, current_post, attempt, answers)
    else:
        # Переходим к следующему вопросу
        next_question = current_question + 1
        db.update_user_post_progress(telegram_id, current_post, next_question, attempt, answers)
        
        await ask_post_question(context, telegram_id, current_post, next_question)


async def generate_post_with_n8n(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, post_num: int, attempt: int, answers: dict) -> None:
    """
    Генерирует пост через n8n на основе ответов
    """
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.PROCESSING_POST)
    
    # Отправляем сообщение об обработке
    processing_msg = await update.message.reply_text(
        messages.PROCESSING_POST_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Получаем промпт для поста
    post_data = db.get_post_data(post_num)
    
    if not post_data:
        await processing_msg.edit_text(
            messages.POST_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаемся к первому вопросу
        db.update_user_post_progress(telegram_id, post_num, 1, attempt, {})
        await ask_post_question(context, telegram_id, post_num, 1)
        return
    
    prompt_template = post_data.get('prompt_post', '')
    
    # Подставляем ответы в промпт
    prompt_text = prompt_template
    for i in range(1, QUESTIONS_PER_POST + 1):
        answer_key = f'answer_{i}'
        answer_value = answers.get(answer_key, '')
        prompt_text = prompt_text.replace(f'vopros_{i}', answer_value)
    
    # Генерируем уникальный request_id
    request_id = generate_request_id()
    
    # Сохраняем запрос в БД
    db.save_n8n_request(telegram_id, request_id, str(answers))
    
    # Отправляем в n8n (prompt_post - создание постов)
    success = send_to_n8n(telegram_id, prompt_text, request_id, 'post')
    
    if not success:
        await processing_msg.edit_text(
            messages.POST_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаемся к первому вопросу
        db.update_user_post_progress(telegram_id, post_num, 1, attempt, {})
        await ask_post_question(context, telegram_id, post_num, 1)
        return
    
    # Ждем ответ от n8n
    n8n_response = await asyncio.to_thread(
        wait_for_n8n_response,
        db,
        telegram_id,
        request_id,
        180  # 3 минуты
    )
    
    if n8n_response:
        # Показываем результат
        await show_post_result(context, telegram_id, post_num, attempt, n8n_response, processing_msg)
    else:
        # Таймаут - возвращаемся к вопросам
        await processing_msg.edit_text(
            messages.POST_ERROR_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        # Возвращаемся к первому вопросу
        db.update_user_post_progress(telegram_id, post_num, 1, attempt, {})
        await ask_post_question(context, telegram_id, post_num, 1)


async def show_post_result(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, post_num: int, attempt: int, post_text: str, processing_msg) -> None:
    """
    Показывает результат сгенерированного поста
    """
    db.update_user_state(telegram_id, UserState.POST_RESULT_SHOWN)
    
    # Если это вторая попытка - показываем без кнопок
    if attempt >= MAX_POST_ATTEMPTS:
        await processing_msg.edit_text(
            messages.POST_RESULT_FINAL_MESSAGE.format(post_text=post_text),
            parse_mode=ParseMode.HTML
        )
        
        # Автоматически переходим к следующему посту
        if post_num < TOTAL_POSTS:
            next_post = post_num + 1
            db.update_user_post_progress(telegram_id, next_post, 1, 1, {})
            await ask_post_question(context, telegram_id, next_post, 1)
        else:
            # Все посты завершены
            db.update_user_state(telegram_id, UserState.ALL_POSTS_COMPLETED)
            await context.bot.send_message(
                chat_id=telegram_id,
                text=messages.ALL_POSTS_COMPLETED_MESSAGE,
                parse_mode=ParseMode.HTML
            )
    else:
        # Первая попытка - показываем с кнопками
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                messages.BUTTON_REWRITE_POST,
                callback_data='rewrite_post'
            )],
            [InlineKeyboardButton(
                messages.BUTTON_NEXT_POST,
                callback_data='next_post'
            )]
        ])
        
        await processing_msg.edit_text(
            messages.POST_RESULT_MESSAGE.format(post_text=post_text),
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


async def handle_rewrite_post(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает переписывание поста
    """
    # Получаем прогресс
    progress = db.get_user_post_progress(telegram_id)
    
    if not progress:
        await query.edit_message_text(
            "❌ Ошибка: прогресс не найден",
            parse_mode=ParseMode.HTML
        )
        return
    
    current_post = progress['current_post_number']
    attempt = progress['post_attempt']
    
    # Увеличиваем номер попытки
    new_attempt = attempt + 1
    
    # Сбрасываем ответы и начинаем заново
    db.update_user_post_progress(telegram_id, current_post, 1, new_attempt, {})
    
    await query.edit_message_text(
        "🔄 Хорошо, давайте попробуем еще раз!",
        parse_mode=ParseMode.HTML
    )
    
    # Начинаем заново задавать вопросы
    await ask_post_question(context, telegram_id, current_post, 1)


async def handle_next_post(query, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Обрабатывает переход к следующему посту
    """
    # Получаем прогресс
    progress = db.get_user_post_progress(telegram_id)
    
    if not progress:
        await query.edit_message_text(
            "❌ Ошибка: прогресс не найден",
            parse_mode=ParseMode.HTML
        )
        return
    
    current_post = progress['current_post_number']
    
    # Проверяем, есть ли еще посты
    if current_post >= TOTAL_POSTS:
        # Все посты завершены
        db.update_user_state(telegram_id, UserState.ALL_POSTS_COMPLETED)
        await query.edit_message_text(
            messages.ALL_POSTS_COMPLETED_MESSAGE,
            parse_mode=ParseMode.HTML
        )
        
        # Переходим к публикации поста-знакомства
        await start_publish_intro_post(context, telegram_id)
    else:
        # Переходим к следующему посту
        next_post = current_post + 1
        db.update_user_post_progress(telegram_id, next_post, 1, 1, {})
        
        await query.edit_message_text(
            f"✅ Отлично! Переходим к посту {next_post} из {TOTAL_POSTS}",
            parse_mode=ParseMode.HTML
        )
        
        # Начинаем с первого вопроса следующего поста
        await ask_post_question(context, telegram_id, next_post, 1)


# ============================================
# ФУНКЦИИ ДЛЯ ПУБЛИКАЦИИ ПОСТА-ЗНАКОМСТВА
# ============================================

async def start_publish_intro_post(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Начинает процесс публикации поста-знакомства
    """
    from config import VIDEO_LEARN5
    
    # Отправляем сообщение о публикации
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.PUBLISH_INTRO_POST_MESSAGE,
        parse_mode=ParseMode.HTML
    )
    
    # Проверяем наличие видео
    if os.path.exists(VIDEO_LEARN5):
        with open(VIDEO_LEARN5, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=telegram_id,
                video=video_file,
                supports_streaming=True
            )
    
    # Обновляем состояние
    db.update_user_state(telegram_id, UserState.LEARN5_SENT)
    
    # Создаем кнопки
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            messages.BUTTON_PUBLISH_MYSELF,
            callback_data='publish_myself'
        )],
        [InlineKeyboardButton(
            messages.BUTTON_HELP_PUBLISH,
            callback_data='help_publish'
        )]
    ])
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=messages.LEARN5_VIDEO_MESSAGE,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

