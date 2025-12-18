"""
Веб-сервер для приема ответов от n8n webhooks
"""
import asyncio
from aiohttp import web
from logger import bot_logger
from typing import Dict, Any


# Глобальное хранилище для ожидания ответов
# Структура: {request_id: {'event': asyncio.Event, 'response': str}}
pending_responses: Dict[str, Dict[str, Any]] = {}


async def handle_osebe_response(request):
    """Обработчик ответа от n8n для prompt_osebe"""
    return await handle_n8n_response(request, 'osebe')


async def handle_post_response(request):
    """Обработчик ответа от n8n для prompt_post"""
    return await handle_n8n_response(request, 'post')


async def handle_bluebutt_response(request):
    """Обработчик ответа от n8n для prompt_bluebutt"""
    return await handle_n8n_response(request, 'bluebutt')


async def handle_anons_response(request):
    """Обработчик ответа от n8n для prompt_anons"""
    return await handle_n8n_response(request, 'anons')


async def handle_prodaj_response(request):
    """Обработчик ответа от n8n для prompt_prodaj"""
    return await handle_n8n_response(request, 'prodaj')


async def handle_n8n_response(request, webhook_type: str):
    """
    Общий обработчик ответов от n8n
    
    Args:
        request: aiohttp request
        webhook_type: тип webhook (osebe, post, bluebutt, anons, prodaj)
    """
    try:
        # Логируем получение запроса
        bot_logger.info('WEBHOOK', 
                       f'Получен запрос от n8n ({webhook_type})', 
                       webhook_type=webhook_type)
        
        # Читаем данные из headers (n8n отправляет через headers)
        headers = request.headers
        
        # Получаем данные из headers
        telegram_id = headers.get('telegram-id') or headers.get('telegram_id')
        request_id = headers.get('request-id') or headers.get('request_id')
        response_text = headers.get('response')
        
        # Преобразуем telegram_id в int если это строка
        if telegram_id:
            try:
                telegram_id = int(telegram_id)
            except (ValueError, TypeError):
                bot_logger.error('WEBHOOK', f'Неверный формат telegram_id: {telegram_id}')
                return web.json_response({'status': 'error', 'message': 'Invalid telegram_id format'}, status=400)
        
        bot_logger.info('WEBHOOK', 
                       f'Данные из headers: telegram_id={telegram_id}, request_id={request_id}, response_len={len(response_text) if response_text else 0}',
                       telegram_id=telegram_id,
                       request_id=request_id)
        
        if not all([telegram_id, request_id, response_text]):
            bot_logger.error('WEBHOOK', 
                           f'Неполные данные от n8n ({webhook_type}). Headers: {dict(headers)}')
            return web.json_response({'status': 'error', 'message': 'Missing required headers: telegram-id, request-id, response'}, status=400)
        
        bot_logger.n8n_response_received(telegram_id, request_id, len(response_text))
        bot_logger.info('WEBHOOK', 
                       f'Получен ответ от n8n ({webhook_type})', 
                       telegram_id=telegram_id, 
                       request_id=request_id,
                       webhook_type=webhook_type)
        
        # Проверяем, ожидается ли этот ответ
        if request_id in pending_responses:
            pending_responses[request_id]['response'] = response_text
            pending_responses[request_id]['event'].set()
            bot_logger.info('WEBHOOK', 
                          f'Ответ передан обработчику ({webhook_type})', 
                          telegram_id=telegram_id, 
                          request_id=request_id)
        else:
            bot_logger.warning('WEBHOOK', 
                             f'Получен ответ для неожидаемого request_id ({webhook_type})', 
                             telegram_id=telegram_id, 
                             request_id=request_id)
        
        return web.json_response({'status': 'success'})
        
    except Exception as e:
        bot_logger.error('WEBHOOK', 
                        f'Ошибка обработки ответа от n8n ({webhook_type}): {str(e)}', 
                        error=e)
        return web.json_response({'error': str(e)}, status=500)


async def health_check(request):
    """Health check endpoint"""
    return web.json_response({'status': 'ok', 'service': 'pptbot-webhook-server'})


def create_app():
    """Создает aiohttp приложение"""
    app = web.Application()
    
    # Регистрируем endpoints для каждого типа webhook
    app.router.add_post('/webhook/response/osebe', handle_osebe_response)
    app.router.add_post('/webhook/response/post', handle_post_response)
    app.router.add_post('/webhook/response/bluebutt', handle_bluebutt_response)
    app.router.add_post('/webhook/response/anons', handle_anons_response)
    app.router.add_post('/webhook/response/prodaj', handle_prodaj_response)
    
    # Health check
    app.router.add_get('/health', health_check)
    
    return app


async def start_webhook_server(port: int = 8080):
    """
    Запускает webhook сервер
    
    Args:
        port: порт для запуска сервера
    """
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    bot_logger.info('WEBHOOK', f'🌐 Webhook сервер запущен на порту {port}')
    print(f"🌐 Webhook сервер запущен на порту {port}")
    print(f"   Endpoints для n8n:")
    print(f"   - POST http://localhost:{port}/webhook/response/osebe")
    print(f"   - POST http://localhost:{port}/webhook/response/post")
    print(f"   - POST http://localhost:{port}/webhook/response/bluebutt")
    print(f"   - POST http://localhost:{port}/webhook/response/anons")
    print(f"   - POST http://localhost:{port}/webhook/response/prodaj")
    
    return runner


async def wait_for_response(request_id: str, timeout: int = 180) -> str:
    """
    Ожидает ответ от n8n через webhook
    
    Args:
        request_id: ID запроса
        timeout: таймаут в секундах (по умолчанию 180 = 3 минуты)
        
    Returns:
        Текст ответа или None если таймаут
    """
    # Создаем Event для этого request_id
    event = asyncio.Event()
    pending_responses[request_id] = {
        'event': event,
        'response': None
    }
    
    try:
        # Ждем ответа с таймаутом
        await asyncio.wait_for(event.wait(), timeout=timeout)
        response = pending_responses[request_id]['response']
        return response
    except asyncio.TimeoutError:
        bot_logger.warning('WEBHOOK', f'Таймаут ожидания ответа от n8n', request_id=request_id)
        return None
    finally:
        # Очищаем запись
        if request_id in pending_responses:
            del pending_responses[request_id]

