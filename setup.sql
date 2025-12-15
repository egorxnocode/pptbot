-- ============================================
-- SQL ЗАПРОСЫ ДЛЯ НАСТРОЙКИ БАЗЫ ДАННЫХ SUPABASE
-- ============================================
-- Просто скопируйте и вставьте весь этот файл в SQL Editor в Supabase

-- ============================================
-- 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
-- ============================================

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  telegram_id BIGINT UNIQUE,
  state TEXT DEFAULT 'new',
  video_sent_at TIMESTAMP,
  -- Поля для работы с постами
  current_post_number INT DEFAULT 1,
  current_question_number INT DEFAULT 1,
  post_attempt INT DEFAULT 1,
  post_answers JSONB,
  -- Поля для публикации поста с кнопкой
  channel_username TEXT,
  channel_id BIGINT,
  blue_answers JSONB,
  best_links JSONB,
  button_action TEXT,
  button_url TEXT,
  button_text TEXT,
  blue_post_text TEXT,
  -- Данные для анонсов
  anons1 TEXT,
  anons2 TEXT,
  anons_text TEXT,
  -- Данные для продающего поста
  prodaj1 TEXT,
  prodaj2 TEXT,
  prodaj3 TEXT,
  sales_text TEXT,
  rewrite_count INT DEFAULT 0,
  -- Служебные поля
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_state ON users(state);

-- ============================================
-- 2. ТАБЛИЦА ПРОМПТОВ
-- ============================================

CREATE TABLE IF NOT EXISTS prompts (
  id BIGSERIAL PRIMARY KEY,
  prompt_name TEXT UNIQUE NOT NULL,
  prompt_text TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Добавляем промпт для помощи "О себе"
-- ОТРЕДАКТИРУЙ ЭТОТ ПРОМПТ ПОД СВОИ НУЖДЫ!
INSERT INTO prompts (prompt_name, prompt_text) VALUES (
  'prompt_osebe',
  'Пользователь рассказал о себе: otvet_osebe

Проанализируй информацию и подбери для него оптимальные варианты ниш для телеграм канала.
Предложи 3-5 конкретных идей с кратким описанием каждой.'
) ON CONFLICT (prompt_name) DO NOTHING;

-- Добавляем промпт для поста с кнопкой
-- ОТРЕДАКТИРУЙ ЭТОТ ПРОМПТ ПОД СВОИ НУЖДЫ!
INSERT INTO prompts (prompt_name, prompt_text) VALUES (
  'prompt_bluebutt',
  'Создай пост-знакомство для телеграм канала на основе ответов:

Проблема: blueotvet1
Аудитория: blueotvet2
Уникальная ценность: blueotvet3
Результат: blueotvet4
Призыв к действию: blueotvet5

Добавь в конце ссылки на лучшие посты (если они есть):
link1
link2
link3
link4
link5

Пост должен быть вовлекающим и мотивирующим к подписке.'
) ON CONFLICT (prompt_name) DO NOTHING;

-- Добавляем промпт для анонсов
-- ОТРЕДАКТИРУЙ ЭТОТ ПРОМПТ ПОД СВОИ НУЖДЫ!
INSERT INTO prompts (prompt_name, prompt_text) VALUES (
  'prompt_anons',
  'Создай привлекательный анонс для телеграм поста на основе следующей информации:

О чем пост: anons1
Ссылка на пост: anons2

Анонс должен быть коротким, цепляющим и мотивировать перейти по ссылке.
Используй эмодзи для привлекательности.
Длина анонса: 100-150 слов.'
) ON CONFLICT (prompt_name) DO NOTHING;

-- Добавляем промпт для продающего поста
-- ОТРЕДАКТИРУЙ ЭТОТ ПРОМПТ ПОД СВОИ НУЖДЫ!
INSERT INTO prompts (prompt_name, prompt_text) VALUES (
  'prompt_prodaj',
  'Создай продающий пост для телеграм канала на основе следующей информации:

Продукт/услуга: prodaj1
Проблема, которую решает: prodaj2
Призыв к действию: prodaj3

Пост должен быть убедительным, показывать ценность предложения и мотивировать к действию.
Используй эмодзи для привлекательности.
Структура: проблема → решение → выгоды → призыв к действию.
Длина: 200-300 слов.'
) ON CONFLICT (prompt_name) DO NOTHING;

-- ============================================
-- 3. ТАБЛИЦА ОТВЕТОВ ОТ N8N
-- ============================================

CREATE TABLE IF NOT EXISTS n8n_responses (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT NOT NULL,
  request_id TEXT UNIQUE NOT NULL,
  user_answer TEXT NOT NULL,
  n8n_response TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_request_id ON n8n_responses(request_id);
CREATE INDEX IF NOT EXISTS idx_telegram_id_n8n ON n8n_responses(telegram_id);
CREATE INDEX IF NOT EXISTS idx_status ON n8n_responses(status);

-- ============================================
-- 4. ТАБЛИЦА ПОСТОВ (ВОПРОСЫ И ПРОМПТЫ)
-- ============================================

CREATE TABLE IF NOT EXISTS posts (
  id BIGSERIAL PRIMARY KEY,
  post_number INT UNIQUE NOT NULL,
  topic TEXT NOT NULL,
  vopros_1 TEXT NOT NULL,
  vopros_2 TEXT NOT NULL,
  vopros_3 TEXT NOT NULL,
  prompt_post TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Добавляем 5 постов с примерами вопросов и промптов
-- ОТРЕДАКТИРУЙ ЭТИ ДАННЫЕ ПОД СВОИ НУЖДЫ!

INSERT INTO posts (post_number, topic, vopros_1, vopros_2, vopros_3, prompt_post) VALUES
(
  1,
  'Знакомство с аудиторией',
  'Кто ваша целевая аудитория? (возраст, интересы, проблемы)',
  'Какую главную ценность вы хотите донести до подписчиков?',
  'Какой стиль общения предпочитаете? (формальный, дружеский, экспертный)',
  'Создай пост-знакомство для телеграм канала на основе следующей информации:

Целевая аудитория: vopros_1
Главная ценность: vopros_2
Стиль общения: vopros_3

Пост должен быть приветственным, вызывающим доверие и побуждающим к подписке.'
),
(
  2,
  'Решение проблемы аудитории',
  'Какая главная проблема вашей аудитории?',
  'Как ваш продукт/услуга решает эту проблему?',
  'Приведите пример успешного решения этой проблемы',
  'Создай пост для телеграм канала о решении проблемы:

Проблема аудитории: vopros_1
Решение: vopros_2
Пример: vopros_3

Пост должен показать экспертность и вызвать желание узнать больше.'
),
(
  3,
  'Образовательный контент',
  'Какую тему вы хотите раскрыть в обучающем посте?',
  'Какие 3 главных совета вы можете дать по этой теме?',
  'Какой призыв к действию добавить в конце?',
  'Создай образовательный пост для телеграм канала:

Тема: vopros_1
Советы: vopros_2
Призыв к действию: vopros_3

Пост должен быть структурированным, легким для восприятия и ценным.'
),
(
  4,
  'История успеха / Кейс',
  'Опишите ситуацию клиента ДО работы с вами',
  'Что было сделано для достижения результата?',
  'Каким был результат ПОСЛЕ?',
  'Создай пост-кейс для телеграм канала:

Ситуация ДО: vopros_1
Что было сделано: vopros_2
Результат ПОСЛЕ: vopros_3

Пост должен вдохновлять и показывать конкретные результаты.'
),
(
  5,
  'Призыв к действию / Оффер',
  'Какое действие вы хотите, чтобы совершила аудитория?',
  'Какую выгоду получит пользователь от этого действия?',
  'Есть ли ограничение по времени или бонус?',
  'Создай продающий пост для телеграм канала:

Желаемое действие: vopros_1
Выгода для пользователя: vopros_2
Ограничение/бонус: vopros_3

Пост должен мотивировать к действию и создавать срочность.'
)
ON CONFLICT (post_number) DO NOTHING;

-- ============================================
-- ГОТОВО!
-- ============================================
-- Все таблицы созданы и заполнены примерами.
-- Не забудьте отредактировать:
-- 1. Промпт 'prompt_osebe' в таблице prompts
-- 2. Промпт 'prompt_bluebutt' в таблице prompts
-- 3. Все 5 постов в таблице posts (вопросы и промпты)
-- 4. 5 вопросов для поста с кнопкой в файле messages.py (BLUE_BUTTON_QUESTION_1-5)

