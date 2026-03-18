"""
Хелпер для отправки видео через Telegram Bot API.

Логика:
  1. Если в .env есть file_id — отправляем по file_id (без лимитов размера).
  2. Иначе — загружаем файл с диска и логируем полученный file_id,
     чтобы пользователь мог добавить его в .env.

Telegram ограничивает загрузку файлов через Bot API до 50 МБ.
Для первой загрузки файлов > 50 МБ сожмите видео с помощью ffmpeg:
  ffmpeg -i input.mp4 -vcodec libx264 -crf 28 -preset fast output.mp4
"""
import os
from logger import bot_logger


async def send_video_safe(
    bot,
    chat_id: int,
    video_path: str,
    file_id: str | None = None,
) -> None:
    """
    Отправляет видео пользователю.

    Args:
        bot: Telegram bot instance (context.bot)
        chat_id: ID чата/пользователя
        video_path: Путь к файлу на диске (fallback)
        file_id: Telegram file_id (если уже загружен ранее)
    """
    video_name = os.path.basename(video_path)
    env_key = 'VIDEO_' + video_name.replace('.mp4', '').upper() + '_FILE_ID'

    try:
        if file_id:
            await bot.send_video(
                chat_id=chat_id,
                video=file_id,
                supports_streaming=True,
            )
            return

        if not os.path.exists(video_path):
            bot_logger.warning('VIDEO', f'Файл не найден: {video_path}', telegram_id=chat_id)
            return

        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        bot_logger.info('VIDEO', f'Загружаем {video_name} ({size_mb:.1f} МБ)...', telegram_id=chat_id)

        with open(video_path, 'rb') as video_file:
            msg = await bot.send_video(
                chat_id=chat_id,
                video=video_file,
                supports_streaming=True,
            )

        if msg and msg.video:
            fid = msg.video.file_id
            bot_logger.info(
                'VIDEO',
                f'✅ {video_name} загружено. Добавьте в .env: {env_key}={fid}',
                telegram_id=chat_id,
            )

    except Exception as e:
        bot_logger.error('VIDEO', f'Ошибка при отправке {video_name}: {str(e)}', telegram_id=chat_id)
