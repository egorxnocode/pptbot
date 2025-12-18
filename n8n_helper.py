"""
Модуль для работы с n8n webhook
Отправка запросов и получение ответов через прямые webhooks
"""
import requests
import uuid
from typing import Optional
from config import (
    N8N_WEBHOOK_OSEBE,
    N8N_WEBHOOK_POST,
    N8N_WEBHOOK_BLUEBUTT,
    N8N_WEBHOOK_ANONS,
    N8N_WEBHOOK_PRODAJ
)
from logger import bot_logger
import webhook_server


def generate_request_id() -> str:
    """
    Генерирует уникальный request_id
    
    Returns:
        Уникальный UUID строка
    """
    return str(uuid.uuid4())


def send_to_n8n(telegram_id: int, text: str, request_id: str, webhook_type: str) -> bool:
    """
    Отправляет данные в n8n через webhook
    
    Args:
        telegram_id: ID пользователя в Telegram
        text: Текст для отправки (промпт или ответ пользователя)
        request_id: Уникальный ID запроса
        webhook_type: Тип webhook ('osebe', 'post', 'bluebutt', 'anons', 'prodaj')
        
    Returns:
        True если запрос отправлен успешно, False если нет
    """
    # Определяем URL webhook в зависимости от типа
    webhook_urls = {
        'osebe': N8N_WEBHOOK_OSEBE,
        'post': N8N_WEBHOOK_POST,
        'bluebutt': N8N_WEBHOOK_BLUEBUTT,
        'anons': N8N_WEBHOOK_ANONS,
        'prodaj': N8N_WEBHOOK_PRODAJ
    }
    
    # Проверяем, что тип webhook валидный
    if webhook_type not in webhook_urls:
        bot_logger.error('N8N', f'Неизвестный тип webhook: {webhook_type}', telegram_id=telegram_id)
        return False
    
    # Получаем URL
    webhook_url = webhook_urls.get(webhook_type)
    if not webhook_url:
        bot_logger.error('N8N', 
                        f'Переменная окружения для webhook "{webhook_type}" не установлена. '
                        f'Проверьте N8N_WEBHOOK_{webhook_type.upper()} в .env файле', 
                        telegram_id=telegram_id)
        return False
    
    try:
        payload = {
            "telegram_id": telegram_id,
            "text": text,
            "request_id": request_id
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            bot_logger.n8n_request_sent(telegram_id, request_id, text[:50])
            bot_logger.info('N8N', f'Запрос отправлен на {webhook_type}', telegram_id=telegram_id, 
                          request_id=request_id, webhook_type=webhook_type)
            return True
        else:
            bot_logger.error('N8N', f'HTTP {response.status_code}', telegram_id=telegram_id, 
                           request_id=request_id, url=webhook_url, webhook_type=webhook_type)
            return False
            
    except Exception as e:
        bot_logger.n8n_error(telegram_id, str(e))
        bot_logger.error('N8N', f'Ошибка подключения: {str(e)}', telegram_id=telegram_id, 
                        url=webhook_url, webhook_type=webhook_type)
        return False


async def wait_for_n8n_response(
    telegram_id: int,
    request_id: str,
    timeout: int = 180
) -> Optional[str]:
    """
    Ожидает ответ от n8n через webhook
    
    Args:
        telegram_id: ID пользователя в Telegram
        request_id: ID запроса
        timeout: Время ожидания в секундах (по умолчанию 180 = 3 минуты)
        
    Returns:
        Ответ от n8n или None если ответ не получен
    """
    response = await webhook_server.wait_for_response(request_id, timeout)
    
    if not response:
        bot_logger.n8n_timeout(telegram_id, request_id, timeout)
    
    return response

