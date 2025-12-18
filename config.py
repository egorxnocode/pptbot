"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Supabase настройки
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_TABLE = os.getenv('SUPABASE_TABLE', 'users')
SUPABASE_PROMPTS_TABLE = os.getenv('SUPABASE_PROMPTS_TABLE', 'prompts')
SUPABASE_N8N_RESPONSES_TABLE = os.getenv('SUPABASE_N8N_RESPONSES_TABLE', 'n8n_responses')
SUPABASE_POSTS_TABLE = os.getenv('SUPABASE_POSTS_TABLE', 'posts')

# OpenAI настройки
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# n8n настройки - отдельный webhook для каждого типа запроса
N8N_WEBHOOK_OSEBE = os.getenv('N8N_WEBHOOK_OSEBE')  # Для prompt_osebe (рассказ о себе)
N8N_WEBHOOK_POST = os.getenv('N8N_WEBHOOK_POST')  # Для prompt_post (создание постов)
N8N_WEBHOOK_BLUEBUTT = os.getenv('N8N_WEBHOOK_BLUEBUTT')  # Для prompt_bluebutt (пост-знакомство)
N8N_WEBHOOK_ANONS = os.getenv('N8N_WEBHOOK_ANONS')  # Для prompt_anons (анонсы)
N8N_WEBHOOK_PRODAJ = os.getenv('N8N_WEBHOOK_PRODAJ')  # Для prompt_prodaj (продающий пост)

# Папка для медиафайлов
MEDIA_FOLDER = 'media'

# Видеофайлы
VIDEO_LEARN1 = os.path.join(MEDIA_FOLDER, 'learn1.mp4')
VIDEO_LEARN2 = os.path.join(MEDIA_FOLDER, 'learn2.mp4')
VIDEO_LEARN3 = os.path.join(MEDIA_FOLDER, 'learn3.mp4')
VIDEO_LEARN4 = os.path.join(MEDIA_FOLDER, 'learn4.mp4')
VIDEO_LEARN5 = os.path.join(MEDIA_FOLDER, 'learn5.mp4')
VIDEO_LEARN6 = os.path.join(MEDIA_FOLDER, 'learn6.mp4')
VIDEO_LEARN7 = os.path.join(MEDIA_FOLDER, 'learn7.mp4')

# Папка для временных файлов (голосовые сообщения)
TEMP_FOLDER = 'temp'

# Порт для webhook сервера (прием ответов от n8n)
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8080'))

# Состояния пользователя
class UserState:
    """Состояния пользователя в боте"""
    NEW = 'new'  # Новый пользователь
    WAITING_EMAIL = 'waiting_email'  # Ожидает ввода email
    REGISTERED = 'registered'  # Зарегистрирован, email подтвержден
    VIDEO_SENT = 'video_sent'  # Видео отправлено, ожидает просмотра
    VIDEO_WATCHED = 'video_watched'  # Видео просмотрено, нажал кнопку
    CHANNEL_QUESTION = 'channel_question'  # Вопрос о наличии канала
    CHANNEL_CREATING = 'channel_creating'  # Создает канал (получил инструкцию)
    CHANNEL_CREATED = 'channel_created'  # Канал создан
    LEARN3_SENT = 'learn3_sent'  # Видео learn3 отправлено
    WAITING_HELP = 'waiting_help'  # Нажал "Нужна помощь"
    WAITING_HELP_ANSWER = 'waiting_help_answer'  # Ожидает ответ о себе (текст/голос)
    PROCESSING_HELP = 'processing_help'  # Обработка запроса через n8n
    HELP_COMPLETED = 'help_completed'  # Помощь получена
    CONTINUE_LEARNING = 'continue_learning'  # Продолжает обучение
    LEARN4_SENT = 'learn4_sent'  # Видео learn4 отправлено
    CHOOSING_POSTS_OPTION = 'choosing_posts_option'  # Выбирает вариант с постами
    WRITE_MYSELF = 'write_myself'  # Выбрал "Напишу сам"
    CREATING_POSTS = 'creating_posts'  # Создает посты с помощью AI
    ANSWERING_POST_QUESTIONS = 'answering_post_questions'  # Отвечает на вопросы по посту
    PROCESSING_POST = 'processing_post'  # Обработка поста через n8n
    POST_RESULT_SHOWN = 'post_result_shown'  # Показан результат поста
    ALL_POSTS_COMPLETED = 'all_posts_completed'  # Все 5 постов созданы
    # Состояния для публикации поста-знакомства
    LEARN5_SENT = 'learn5_sent'  # Видео learn5 отправлено
    PUBLISH_MYSELF = 'publish_myself'  # Выбрал "Опубликую сам"
    HELP_PUBLISH = 'help_publish'  # Выбрал "Помоги опубликовать"
    WAITING_CHANNEL_LINK = 'waiting_channel_link'  # Ожидает ссылку на канал
    WAITING_BOT_ADMIN = 'waiting_bot_admin'  # Ожидает добавления бота админом
    ANSWERING_BLUE_QUESTIONS = 'answering_blue_questions'  # Отвечает на 5 вопросов
    REQUESTING_BEST_LINKS = 'requesting_best_links'  # Запрашиваем ссылки на посты
    PROCESSING_BLUE_POST = 'processing_blue_post'  # Обработка поста с кнопкой
    CHOOSING_BUTTON_ACTION = 'choosing_button_action'  # Выбирает куда ведет кнопка
    WAITING_WEBSITE_LINK = 'waiting_website_link'  # Ожидает ссылку на сайт
    CHOOSING_BUTTON_TEXT = 'choosing_button_text'  # Выбирает текст кнопки
    WAITING_CUSTOM_BUTTON_TEXT = 'waiting_custom_button_text'  # Ожидает свой текст кнопки
    PREVIEW_POST = 'preview_post'  # Предпросмотр поста
    POST_PUBLISHED = 'post_published'  # Пост опубликован
    # Состояния для создания анонсов
    LEARN6_SENT = 'learn6_sent'  # Видео learn6 отправлено
    WRITE_ANONS_MYSELF = 'write_anons_myself'  # Выбрал "Напишу сам"
    CREATING_ANONS = 'creating_anons'  # Создает анонс с AI
    ANSWERING_ANONS_QUESTIONS = 'answering_anons_questions'  # Отвечает на вопросы для анонса
    PROCESSING_ANONS = 'processing_anons'  # Обработка анонса через n8n
    ANONS_COMPLETED = 'anons_completed'  # Анонс создан
    # Состояния для создания продающего поста
    LEARN7_SENT = 'learn7_sent'  # Видео learn7 отправлено
    WRITE_SALES_MYSELF = 'write_sales_myself'  # Выбрал "Напишу сам"
    CREATING_SALES_POST = 'creating_sales_post'  # Создает продающий пост с AI
    ANSWERING_SALES_QUESTIONS = 'answering_sales_questions'  # Отвечает на вопросы для продающего поста
    PROCESSING_SALES_POST = 'processing_sales_post'  # Обработка продающего поста через n8n
    SALES_POST_READY = 'sales_post_ready'  # Продающий пост готов
    REWRITING_SALES_POST = 'rewriting_sales_post'  # Переписывание продающего поста
    FINAL_STEP = 'final_step'  # Финальный шаг
    COMPLETED = 'completed'  # Полностью завершил обучение

# Время для напоминаний (в секундах)
REMINDER_1_DELAY = 10 * 60  # 10 минут
REMINDER_2_DELAY = 60 * 60  # 1 час
REMINDER_3_DELAY = 24 * 60 * 60  # 24 часа

# Константы для создания постов
TOTAL_POSTS = 5  # Всего постов для создания
QUESTIONS_PER_POST = 3  # Вопросов на каждый пост
MAX_POST_ATTEMPTS = 2  # Максимум попыток переписать пост

# Константы для публикации поста с кнопкой
BLUE_BUTTON_QUESTIONS = 5  # Количество вопросов для поста с кнопкой
BEST_LINKS_COUNT = 5  # Количество ссылок на лучшие посты

