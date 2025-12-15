"""
Модуль логирования для PPTbot
Подробная система логирования с категориями и уровнями
"""

import logging
import sys
from datetime import datetime
from typing import Optional, Any, Dict
from pathlib import Path


class BotLogger:
    """Класс для управления логированием бота"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        Инициализация логгера
        
        Args:
            log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = logging.getLogger("PPTbot")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Очищаем старые обработчики
        self.logger.handlers.clear()
        
        # Создаем форматтер
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(category)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный обработчик
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Файловый обработчик
        log_file = Path("logs") / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _log(self, level: str, category: str, message: str, **kwargs):
        """
        Внутренний метод логирования
        
        Args:
            level: Уровень (INFO, WARNING, ERROR)
            category: Категория лога
            message: Сообщение
            **kwargs: Дополнительные данные
        """
        extra_data = ' | '.join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
        full_message = f"{message}"
        if extra_data:
            full_message += f" | {extra_data}"
        
        log_method = getattr(self.logger, level.lower())
        log_method(full_message, extra={'category': category})
    
    # ============================================
    # ПОЛЬЗОВАТЕЛЬСКИЕ ДЕЙСТВИЯ
    # ============================================
    
    def user_start(self, telegram_id: int, username: Optional[str] = None, 
                   first_name: Optional[str] = None):
        """Пользователь запустил бота"""
        self._log('INFO', 'USER', f'👤 Пользователь запустил бота',
                  telegram_id=telegram_id, username=username, first_name=first_name)
    
    def user_registered(self, telegram_id: int, email: str):
        """Пользователь зарегистрирован"""
        self._log('INFO', 'USER', f'✅ Пользователь зарегистрирован',
                  telegram_id=telegram_id, email=email)
    
    def user_state_changed(self, telegram_id: int, old_state: str, new_state: str):
        """Изменение состояния пользователя"""
        self._log('INFO', 'USER', f'🔄 Состояние изменено: {old_state} → {new_state}',
                  telegram_id=telegram_id)
    
    def user_message(self, telegram_id: int, message_type: str, content_preview: str = ""):
        """Сообщение от пользователя"""
        self._log('INFO', 'USER', f'💬 Сообщение: {message_type}',
                  telegram_id=telegram_id, preview=content_preview[:50])
    
    def user_button_click(self, telegram_id: int, button_data: str):
        """Нажатие на кнопку"""
        self._log('INFO', 'USER', f'🔘 Нажата кнопка: {button_data}',
                  telegram_id=telegram_id)
    
    # ============================================
    # ВИДЕО И ОБУЧЕНИЕ
    # ============================================
    
    def video_sent(self, telegram_id: int, video_name: str):
        """Отправка видео"""
        self._log('INFO', 'VIDEO', f'🎥 Отправлено видео: {video_name}',
                  telegram_id=telegram_id)
    
    def video_watched(self, telegram_id: int, video_name: str):
        """Видео просмотрено"""
        self._log('INFO', 'VIDEO', f'👁️ Видео просмотрено: {video_name}',
                  telegram_id=telegram_id)
    
    # ============================================
    # РАБОТА С N8N
    # ============================================
    
    def n8n_request_sent(self, telegram_id: int, request_id: str, prompt_type: str):
        """Запрос отправлен в n8n"""
        self._log('INFO', 'N8N', f'📤 Запрос отправлен в n8n',
                  telegram_id=telegram_id, request_id=request_id, prompt=prompt_type)
    
    def n8n_response_received(self, telegram_id: int, request_id: str, 
                             response_length: int):
        """Ответ получен от n8n"""
        self._log('INFO', 'N8N', f'📥 Ответ получен от n8n',
                  telegram_id=telegram_id, request_id=request_id, 
                  length=f"{response_length} символов")
    
    def n8n_timeout(self, telegram_id: int, request_id: str, timeout: int):
        """Таймаут ожидания n8n"""
        self._log('WARNING', 'N8N', f'⏱️ Таймаут ожидания ответа от n8n',
                  telegram_id=telegram_id, request_id=request_id, 
                  timeout=f"{timeout}с")
    
    def n8n_error(self, telegram_id: int, error: str):
        """Ошибка при работе с n8n"""
        self._log('ERROR', 'N8N', f'❌ Ошибка n8n: {error}',
                  telegram_id=telegram_id)
    
    # ============================================
    # СОЗДАНИЕ ПОСТОВ
    # ============================================
    
    def post_question_asked(self, telegram_id: int, post_number: int, 
                           question_number: int):
        """Задан вопрос для поста"""
        self._log('INFO', 'POSTS', f'❓ Вопрос {question_number} для поста {post_number}',
                  telegram_id=telegram_id)
    
    def post_answer_received(self, telegram_id: int, post_number: int, 
                            question_number: int, answer_preview: str):
        """Получен ответ на вопрос"""
        self._log('INFO', 'POSTS', f'💭 Ответ на вопрос {question_number} поста {post_number}',
                  telegram_id=telegram_id, answer=answer_preview[:50])
    
    def post_generated(self, telegram_id: int, post_number: int, length: int):
        """Пост сгенерирован"""
        self._log('INFO', 'POSTS', f'✅ Пост {post_number} сгенерирован',
                  telegram_id=telegram_id, length=f"{length} символов")
    
    def post_rewrite_requested(self, telegram_id: int, post_number: int, 
                               attempt: int):
        """Запрошено переписывание поста"""
        self._log('INFO', 'POSTS', f'🔄 Переписывание поста {post_number} (попытка {attempt})',
                  telegram_id=telegram_id)
    
    def all_posts_completed(self, telegram_id: int):
        """Все 5 постов созданы"""
        self._log('INFO', 'POSTS', f'🎉 Все 5 постов созданы',
                  telegram_id=telegram_id)
    
    # ============================================
    # ПУБЛИКАЦИЯ ПОСТА-ЗНАКОМСТВА
    # ============================================
    
    def channel_link_received(self, telegram_id: int, channel_link: str):
        """Получена ссылка на канал"""
        self._log('INFO', 'PUBLISH', f'🔗 Получена ссылка на канал',
                  telegram_id=telegram_id, channel=channel_link)
    
    def bot_admin_check(self, telegram_id: int, is_admin: bool, channel_link: str):
        """Проверка прав администратора"""
        status = "✅ Есть права" if is_admin else "❌ Нет прав"
        self._log('INFO', 'PUBLISH', f'🔐 Проверка админа: {status}',
                  telegram_id=telegram_id, channel=channel_link)
    
    def intro_post_question(self, telegram_id: int, question_number: int):
        """Вопрос для поста-знакомства"""
        self._log('INFO', 'PUBLISH', f'❓ Вопрос {question_number}/5 для поста-знакомства',
                  telegram_id=telegram_id)
    
    def intro_post_generated(self, telegram_id: int, length: int):
        """Пост-знакомство сгенерирован"""
        self._log('INFO', 'PUBLISH', f'✅ Пост-знакомство сгенерирован',
                  telegram_id=telegram_id, length=f"{length} символов")
    
    def intro_post_published(self, telegram_id: int, channel_link: str):
        """Пост-знакомство опубликован"""
        self._log('INFO', 'PUBLISH', f'🎉 Пост-знакомство опубликован',
                  telegram_id=telegram_id, channel=channel_link)
    
    # ============================================
    # АНОНСЫ
    # ============================================
    
    def anons_question(self, telegram_id: int, question_number: int):
        """Вопрос для анонса"""
        self._log('INFO', 'ANONS', f'❓ Вопрос {question_number}/2 для анонса',
                  telegram_id=telegram_id)
    
    def anons_generated(self, telegram_id: int, length: int):
        """Анонс сгенерирован"""
        self._log('INFO', 'ANONS', f'✅ Анонс сгенерирован',
                  telegram_id=telegram_id, length=f"{length} символов")
    
    # ============================================
    # ПРОДАЮЩИЙ ПОСТ
    # ============================================
    
    def sales_question(self, telegram_id: int, question_number: int):
        """Вопрос для продающего поста"""
        self._log('INFO', 'SALES', f'❓ Вопрос {question_number}/3 для продающего поста',
                  telegram_id=telegram_id)
    
    def sales_post_generated(self, telegram_id: int, length: int):
        """Продающий пост сгенерирован"""
        self._log('INFO', 'SALES', f'✅ Продающий пост сгенерирован',
                  telegram_id=telegram_id, length=f"{length} символов")
    
    def sales_post_rewritten(self, telegram_id: int, rewrite_count: int):
        """Продающий пост переписан"""
        self._log('INFO', 'SALES', f'🔄 Продающий пост переписан (раз {rewrite_count})',
                  telegram_id=telegram_id)
    
    def final_step_reached(self, telegram_id: int):
        """Финальный шаг достигнут"""
        self._log('INFO', 'SALES', f'🎉 Пользователь завершил курс!',
                  telegram_id=telegram_id)
    
    # ============================================
    # ТРАНСКРИБАЦИЯ ГОЛОСОВЫХ
    # ============================================
    
    def voice_received(self, telegram_id: int, duration: int):
        """Получено голосовое сообщение"""
        self._log('INFO', 'VOICE', f'🎤 Получено голосовое ({duration}с)',
                  telegram_id=telegram_id)
    
    def voice_transcribed(self, telegram_id: int, text_preview: str):
        """Голосовое транскрибировано"""
        self._log('INFO', 'VOICE', f'📝 Транскрибировано',
                  telegram_id=telegram_id, text=text_preview[:50])
    
    def voice_error(self, telegram_id: int, error: str):
        """Ошибка транскрибации"""
        self._log('ERROR', 'VOICE', f'❌ Ошибка транскрибации: {error}',
                  telegram_id=telegram_id)
    
    # ============================================
    # НАПОМИНАНИЯ
    # ============================================
    
    def reminder_sent(self, telegram_id: int, reminder_number: int):
        """Отправлено напоминание"""
        self._log('INFO', 'REMINDER', f'🔔 Отправлено напоминание #{reminder_number}',
                  telegram_id=telegram_id)
    
    def reminder_scheduled(self, telegram_id: int, delay_minutes: int):
        """Напоминание запланировано"""
        self._log('INFO', 'REMINDER', f'⏰ Напоминание запланировано через {delay_minutes} мин',
                  telegram_id=telegram_id)
    
    # ============================================
    # БАЗА ДАННЫХ
    # ============================================
    
    def db_query(self, query_type: str, table: str, telegram_id: Optional[int] = None):
        """Запрос к БД"""
        self._log('INFO', 'DATABASE', f'💾 Запрос: {query_type} в {table}',
                  telegram_id=telegram_id)
    
    def db_error(self, error: str, table: str, telegram_id: Optional[int] = None):
        """Ошибка БД"""
        self._log('ERROR', 'DATABASE', f'❌ Ошибка БД в {table}: {error}',
                  telegram_id=telegram_id)
    
    # ============================================
    # ОШИБКИ И ПРЕДУПРЕЖДЕНИЯ
    # ============================================
    
    def warning(self, category: str, message: str, telegram_id: Optional[int] = None,
                **kwargs):
        """Общее предупреждение"""
        self._log('WARNING', category.upper(), f'⚠️ {message}',
                  telegram_id=telegram_id, **kwargs)
    
    def error(self, category: str, message: str, telegram_id: Optional[int] = None,
              error: Optional[Exception] = None, **kwargs):
        """Общая ошибка"""
        error_msg = str(error) if error else message
        self._log('ERROR', category.upper(), f'❌ {error_msg}',
                  telegram_id=telegram_id, **kwargs)
    
    def info(self, category: str, message: str, telegram_id: Optional[int] = None,
             **kwargs):
        """Общая информация"""
        self._log('INFO', category.upper(), message,
                  telegram_id=telegram_id, **kwargs)


# Создаем глобальный экземпляр логгера
bot_logger = BotLogger()

