"""
Модуль для работы с n8n webhook
Отправка запросов и получение ответов
"""
import requests
import uuid
import time
from typing import Optional, Dict, Any
from config import N8N_WEBHOOK_URL
from logger import bot_logger


def generate_request_id() -> str:
    """
    Генерирует уникальный request_id
    
    Returns:
        Уникальный UUID строка
    """
    return str(uuid.uuid4())


def send_to_n8n(telegram_id: int, prompt_text: str, request_id: str) -> bool:
    """
    Отправляет данные в n8n через webhook
    
    Args:
        telegram_id: ID пользователя в Telegram
        prompt_text: Текст промпта для отправки
        request_id: Уникальный ID запроса
        
    Returns:
        True если запрос отправлен успешно, False если нет
    """
    try:
        payload = {
            "telegram_id": telegram_id,
            "request_id": request_id,
            "prompt": prompt_text
        }
        
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            bot_logger.n8n_request_sent(telegram_id, request_id, prompt_text[:50])
            return True
        else:
            bot_logger.error('N8N', f'HTTP {response.status_code}', telegram_id=telegram_id, 
                           request_id=request_id, url=N8N_WEBHOOK_URL)
            return False
            
    except Exception as e:
        bot_logger.n8n_error(telegram_id, str(e))
        bot_logger.error('N8N', f'Ошибка подключения: {str(e)}', telegram_id=telegram_id, 
                        url=N8N_WEBHOOK_URL)
        return False


def wait_for_n8n_response(
    db,
    telegram_id: int,
    request_id: str,
    timeout: int = 180
) -> Optional[str]:
    """
    Ожидает ответ от n8n (проверяет БД каждые 5 секунд)
    
    Args:
        db: Объект базы данных
        telegram_id: ID пользователя в Telegram
        request_id: ID запроса
        timeout: Время ожидания в секундах (по умолчанию 180 = 3 минуты)
        
    Returns:
        Ответ от n8n или None если ответ не получен
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Проверяем наличие ответа в БД
        response = db.get_n8n_response(telegram_id, request_id)
        
        if response:
            bot_logger.n8n_response_received(telegram_id, request_id, len(response))
            return response
        
        # Ждем 5 секунд перед следующей проверкой
        time.sleep(5)
    
    bot_logger.n8n_timeout(telegram_id, request_id, timeout)
    return None

