#!/usr/bin/env python3
"""
Скрипт для однократной загрузки видео в Telegram и получения file_id.

Запуск:
    python upload_videos.py YOUR_CHAT_ID

Ваш chat_id можно узнать через @userinfobot в Telegram.

После запуска скрипт выведет строки для .env файла, например:
    VIDEO_LEARN1_FILE_ID=BAACAgIAAxkBAAI...

Добавьте эти строки в /opt/pptbot/.env и перезапустите бота.
Бот будет отправлять видео по file_id без ограничения 50 МБ.

ВАЖНО: файлы > 50 МБ нужно предварительно сжать:
    ffmpeg -i media/learn1.mp4 -vcodec libx264 -crf 28 -preset fast media/learn1.mp4.tmp
    mv media/learn1.mp4.tmp media/learn1.mp4
"""
import asyncio
import os
import sys

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

VIDEOS = [
    ('VIDEO_LEARN1_FILE_ID', 'media/learn1.mp4'),
    ('VIDEO_LEARN2_FILE_ID', 'media/learn2.mp4'),
    ('VIDEO_LEARN3_FILE_ID', 'media/learn3.mp4'),
    ('VIDEO_LEARN4_FILE_ID', 'media/learn4.mp4'),
    ('VIDEO_LEARN5_FILE_ID', 'media/learn5.mp4'),
    ('VIDEO_LEARN6_FILE_ID', 'media/learn6.mp4'),
    ('VIDEO_LEARN7_FILE_ID', 'media/learn7.mp4'),
]


async def upload_all(chat_id: str) -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('❌ TELEGRAM_BOT_TOKEN не установлен в .env')
        sys.exit(1)

    bot = Bot(token=token)
    print('\n🎬 Загрузка видео в Telegram...\n')
    results = []

    for env_key, video_path in VIDEOS:
        existing = os.getenv(env_key)
        if existing:
            print(f'✅ {env_key} уже установлен, пропускаем')
            results.append(f'{env_key}={existing}')
            continue

        if not os.path.exists(video_path):
            print(f'⚠️  {video_path} не найден, пропускаем')
            continue

        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f'📤 Загружаем {video_path} ({size_mb:.1f} МБ)...')

        if size_mb > 50:
            print(f'❌ {video_path} ({size_mb:.1f} МБ) превышает лимит 50 МБ.')
            print(f'   Сожмите файл:')
            print(f'   ffmpeg -i {video_path} -vcodec libx264 -crf 28 -preset fast {video_path}.tmp && mv {video_path}.tmp {video_path}\n')
            continue

        try:
            with open(video_path, 'rb') as f:
                msg = await bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    supports_streaming=True,
                )
            file_id = msg.video.file_id
            print(f'✅ Загружено! {env_key}={file_id}\n')
            results.append(f'{env_key}={file_id}')
        except Exception as e:
            print(f'❌ Ошибка: {e}\n')

    if results:
        print('\n' + '=' * 60)
        print('Добавьте в /opt/pptbot/.env:')
        print('=' * 60)
        for line in results:
            print(line)
        print('=' * 60)
        print('\nЗатем перезапустите бота: docker compose restart bot')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Использование: python upload_videos.py YOUR_CHAT_ID')
        print('Ваш chat_id: напишите @userinfobot в Telegram')
        sys.exit(1)

    asyncio.run(upload_all(sys.argv[1]))
