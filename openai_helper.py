"""
Модуль для работы с OpenAI API
Транскрибация голосовых сообщений
"""
import os
from openai import OpenAI
from config import OPENAI_API_KEY
from logger import bot_logger


# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe_voice(audio_file_path: str) -> str:
    """
    Транскрибирует голосовое сообщение с помощью OpenAI Whisper
    
    Args:
        audio_file_path: Путь к аудиофайлу
        
    Returns:
        Транскрибированный текст или None в случае ошибки
    """
    try:
        with open(audio_file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Указываем русский язык
            )
        
        return transcript.text
    
    except Exception as e:
        bot_logger.error('VOICE', f'Ошибка транскрибации: {str(e)}', file=audio_file_path)
        return None

