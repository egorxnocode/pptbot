"""
Модуль для работы с базой данных Supabase
"""
from supabase import create_client, Client
from config import (
    SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE, 
    SUPABASE_PROMPTS_TABLE, SUPABASE_N8N_RESPONSES_TABLE,
    SUPABASE_POSTS_TABLE, UserState
)
from typing import Optional, Dict, Any
from datetime import datetime


class Database:
    """Класс для работы с базой данных Supabase"""
    
    def __init__(self):
        """Инициализация подключения к Supabase"""
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.table_name = SUPABASE_TABLE
        self.prompts_table = SUPABASE_PROMPTS_TABLE
        self.n8n_responses_table = SUPABASE_N8N_RESPONSES_TABLE
        self.posts_table = SUPABASE_POSTS_TABLE
    
    def check_email_exists(self, email: str) -> bool:
        """
        Проверяет наличие email в базе данных
        
        Args:
            email: Email адрес (будет преобразован в нижний регистр)
            
        Returns:
            True если email найден, False если нет
        """
        email = email.lower()
        try:
            response = self.client.table(self.table_name)\
                .select("email")\
                .eq("email", email)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            bot_logger.db_error(str(e), 'users')
            return False
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по Telegram ID
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Словарь с данными пользователя или None
        """
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("telegram_id", telegram_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            bot_logger.db_error(str(e), 'users', telegram_id=telegram_id)
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по email
        
        Args:
            email: Email адрес (будет преобразован в нижний регистр)
            
        Returns:
            Словарь с данными пользователя или None
        """
        email = email.lower()
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("email", email)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            bot_logger.db_error(str(e), 'users')
            return None
    
    def update_user_telegram_id(self, email: str, telegram_id: int) -> bool:
        """
        Обновляет Telegram ID для пользователя с указанным email
        
        Args:
            email: Email адрес (будет преобразован в нижний регистр)
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если обновление успешно, False если нет
        """
        email = email.lower()
        try:
            self.client.table(self.table_name)\
                .update({"telegram_id": telegram_id})\
                .eq("email", email)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def update_user_state(self, telegram_id: int, state: str) -> bool:
        """
        Обновляет состояние пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            state: Новое состояние (из класса UserState)
            
        Returns:
            True если обновление успешно, False если нет
        """
        try:
            self.client.table(self.table_name)\
                .update({
                    "state": state,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def update_video_sent_time(self, telegram_id: int) -> bool:
        """
        Сохраняет время отправки видео для системы напоминаний
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если обновление успешно, False если нет
        """
        try:
            self.client.table(self.table_name)\
                .update({
                    "video_sent_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def get_user_state(self, telegram_id: int) -> Optional[str]:
        """
        Получает текущее состояние пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Строка с состоянием или None
        """
        user = self.get_user_by_telegram_id(telegram_id)
        if user:
            return user.get('state', UserState.NEW)
        return None
    
    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Получает промпт из таблицы prompts
        
        Args:
            prompt_name: Название промпта (например, 'prompt_osebe')
            
        Returns:
            Текст промпта или None
        """
        try:
            response = self.client.table(self.prompts_table)\
                .select("prompt_text")\
                .eq("prompt_name", prompt_name)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0].get('prompt_text')
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "prompts")
            return None
    
    def save_n8n_request(self, telegram_id: int, request_id: str, user_answer: str) -> bool:
        """
        Сохраняет запрос к n8n в базе данных
        
        Args:
            telegram_id: ID пользователя в Telegram
            request_id: ID запроса
            user_answer: Ответ пользователя о себе
            
        Returns:
            True если сохранение успешно, False если нет
        """
        try:
            self.client.table(self.n8n_responses_table)\
                .insert({
                    "telegram_id": telegram_id,
                    "request_id": request_id,
                    "user_answer": user_answer,
                    "n8n_response": None,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat()
                })\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "n8n_responses")
            return False
    
    def save_n8n_response(self, request_id: str, n8n_response: str) -> bool:
        """
        Сохраняет ответ от n8n в базе данных
        Этот метод будет вызван через webhook от n8n
        
        Args:
            request_id: ID запроса
            n8n_response: Ответ от n8n
            
        Returns:
            True если сохранение успешно, False если нет
        """
        try:
            self.client.table(self.n8n_responses_table)\
                .update({
                    "n8n_response": n8n_response,
                    "status": "completed",
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("request_id", request_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "n8n_responses")
            return False
    
    def get_n8n_response(self, telegram_id: int, request_id: str) -> Optional[str]:
        """
        Получает ответ от n8n из базы данных
        
        Args:
            telegram_id: ID пользователя в Telegram
            request_id: ID запроса
            
        Returns:
            Ответ от n8n или None если ответ еще не получен
        """
        try:
            response = self.client.table(self.n8n_responses_table)\
                .select("n8n_response, status")\
                .eq("telegram_id", telegram_id)\
                .eq("request_id", request_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                if data.get('status') == 'completed':
                    return data.get('n8n_response')
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "n8n_responses")
            return None
    
    def get_post_data(self, post_number: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные для поста (вопросы и промпт)
        
        Args:
            post_number: Номер поста (1-5)
            
        Returns:
            Словарь с данными поста или None
        """
        try:
            response = self.client.table(self.posts_table)\
                .select("*")\
                .eq("post_number", post_number)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "posts")
            return None
    
    def update_user_post_progress(
        self,
        telegram_id: int,
        current_post: int,
        current_question: int,
        attempt: int,
        answers: Optional[Dict] = None
    ) -> bool:
        """
        Обновляет прогресс создания постов пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            current_post: Текущий номер поста (1-5)
            current_question: Текущий номер вопроса (1-3)
            attempt: Номер попытки (1-2)
            answers: Словарь с ответами на вопросы
            
        Returns:
            True если обновление успешно, False если нет
        """
        try:
            update_data = {
                "current_post_number": current_post,
                "current_question_number": current_question,
                "post_attempt": attempt,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if answers is not None:
                import json
                update_data["post_answers"] = json.dumps(answers)
            
            self.client.table(self.table_name)\
                .update(update_data)\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def get_user_post_progress(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает прогресс создания постов пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Словарь с прогрессом или None
        """
        try:
            response = self.client.table(self.table_name)\
                .select("current_post_number, current_question_number, post_attempt, post_answers")\
                .eq("telegram_id", telegram_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                # Парсим JSON с ответами
                if data.get('post_answers'):
                    import json
                    data['post_answers'] = json.loads(data['post_answers'])
                else:
                    data['post_answers'] = {}
                return data
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return None
    
    def save_channel_data(self, telegram_id: int, channel_username: str, channel_id: int) -> bool:
        """
        Сохраняет данные канала пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            channel_username: Username канала
            channel_id: ID канала
            
        Returns:
            True если сохранение успешно, False если нет
        """
        try:
            self.client.table(self.table_name)\
                .update({
                    "channel_username": channel_username,
                    "channel_id": channel_id,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def save_blue_button_data(
        self,
        telegram_id: int,
        blue_answers: Optional[Dict] = None,
        best_links: Optional[Dict] = None,
        button_action: Optional[str] = None,
        button_url: Optional[str] = None,
        button_text: Optional[str] = None,
        post_text: Optional[str] = None
    ) -> bool:
        """
        Сохраняет данные для поста с кнопкой
        
        Args:
            telegram_id: ID пользователя
            blue_answers: Ответы на 5 вопросов (blueotvet1-5)
            best_links: Ссылки на лучшие посты (link1-5)
            button_action: Действие кнопки (dm/website)
            button_url: URL кнопки
            button_text: Текст кнопки
            post_text: Текст поста от n8n
            
        Returns:
            True если успешно, False если нет
        """
        try:
            import json
            update_data = {"updated_at": datetime.utcnow().isoformat()}
            
            if blue_answers is not None:
                update_data["blue_answers"] = json.dumps(blue_answers)
            if best_links is not None:
                update_data["best_links"] = json.dumps(best_links)
            if button_action is not None:
                update_data["button_action"] = button_action
            if button_url is not None:
                update_data["button_url"] = button_url
            if button_text is not None:
                update_data["button_text"] = button_text
            if post_text is not None:
                update_data["blue_post_text"] = post_text
            
            self.client.table(self.table_name)\
                .update(update_data)\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def get_blue_button_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные для поста с кнопкой
        
        Args:
            telegram_id: ID пользователя
            
        Returns:
            Словарь с данными или None
        """
        try:
            response = self.client.table(self.table_name)\
                .select("blue_answers, best_links, button_action, button_url, button_text, blue_post_text")\
                .eq("telegram_id", telegram_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                import json
                # Парсим JSON поля
                if data.get('blue_answers'):
                    data['blue_answers'] = json.loads(data['blue_answers'])
                else:
                    data['blue_answers'] = {}
                
                if data.get('best_links'):
                    data['best_links'] = json.loads(data['best_links'])
                else:
                    data['best_links'] = {}
                
                return data
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return None
    
    def save_anons_data(
        self,
        telegram_id: int,
        anons1: Optional[str] = None,
        anons2: Optional[str] = None,
        anons_text: Optional[str] = None
    ) -> bool:
        """
        Сохраняет данные для анонса
        
        Args:
            telegram_id: ID пользователя
            anons1: Ответ на вопрос "О чем пост"
            anons2: Ссылка на пост
            anons_text: Готовый текст анонса
            
        Returns:
            True если успешно, False если нет
        """
        try:
            update_data = {"updated_at": datetime.utcnow().isoformat()}
            
            if anons1 is not None:
                update_data["anons1"] = anons1
            if anons2 is not None:
                update_data["anons2"] = anons2
            if anons_text is not None:
                update_data["anons_text"] = anons_text
            
            self.client.table(self.table_name)\
                .update(update_data)\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def get_anons_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные анонса
        
        Args:
            telegram_id: ID пользователя
            
        Returns:
            Словарь с данными или None
        """
        try:
            response = self.client.table(self.table_name)\
                .select("anons1, anons2, anons_text")\
                .eq("telegram_id", telegram_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return None
    
    def save_sales_data(
        self,
        telegram_id: int,
        prodaj1: Optional[str] = None,
        prodaj2: Optional[str] = None,
        prodaj3: Optional[str] = None,
        sales_text: Optional[str] = None,
        rewrite_count: Optional[int] = None
    ) -> bool:
        """
        Сохраняет данные для продающего поста
        
        Args:
            telegram_id: ID пользователя
            prodaj1: Ответ на вопрос 1 (что продаете)
            prodaj2: Ответ на вопрос 2 (какую проблему решает)
            prodaj3: Ответ на вопрос 3 (призыв к действию)
            sales_text: Готовый текст продающего поста
            rewrite_count: Количество переписываний
            
        Returns:
            True если успешно, False если нет
        """
        try:
            update_data = {"updated_at": datetime.utcnow().isoformat()}
            
            if prodaj1 is not None:
                update_data["prodaj1"] = prodaj1
            if prodaj2 is not None:
                update_data["prodaj2"] = prodaj2
            if prodaj3 is not None:
                update_data["prodaj3"] = prodaj3
            if sales_text is not None:
                update_data["sales_text"] = sales_text
            if rewrite_count is not None:
                update_data["rewrite_count"] = rewrite_count
            
            self.client.table(self.table_name)\
                .update(update_data)\
                .eq("telegram_id", telegram_id)\
                .execute()
            return True
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return False
    
    def get_sales_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные продающего поста
        
        Args:
            telegram_id: ID пользователя
            
        Returns:
            Словарь с данными или None
        """
        try:
            response = self.client.table(self.table_name)\
                .select("prodaj1, prodaj2, prodaj3, sales_text, rewrite_count")\
                .eq("telegram_id", telegram_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            bot_logger.db_error(str(e), "users")
            return None

