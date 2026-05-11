# Public_Learn

# Telegram-бот с элементами геймификации для поддержки индивидуального процесса обучения

## Краткое описание

Проект представляет собой адаптивную образовательную систему в формате Telegram-бота. Бот регистрирует пользователя, помогает выбрать тему, выдаёт учебные задания, проверяет ответы, адаптирует сложность следующих заданий, начисляет опыт, уровни, достижения, поддерживает серии активности и квесты. Дополнительно реализован REST API на FastAPI для служебных операций и аналитики.

## Возможности бота

- регистрация Telegram-пользователя при первом запуске;
- хранение профиля пользователя и прогресса в PostgreSQL;
- выбор темы обучения;
- адаптивная выдача заданий сложности 1-5;
- проверка `numeric_answer`, `text_answer`, `single_choice`;
- объяснение ошибок;
- XP, уровни, ежедневные серии, достижения и квесты;
- пользовательское и техническое логирование;
- REST API для интеграций и аналитики;
- Redis-кэширование сгенерированных заданий.

## Архитектура проекта

Проект разделён на слои: `routes/handlers`, `services`, `repositories`, `models`, `schemas`, `domain`. Telegram handlers не работают напрямую с БД и не содержат основной бизнес-логики.

```text
app/
  main.py
  bot/
    main.py
    handlers/
    keyboards/
    middlewares/
  api/
    deps.py
    routes/
  core/
  models/
  schemas/
  repositories/
  services/
  domain/
alembic/
scripts/seed_data.py
tests/
docker-compose.yml
Dockerfile
.env.example
pyproject.toml
```

## Описание модулей

- `AdaptiveService` — профиль освоения, сложность, повторение темы.
- `ContentGenerationService` — шаблонная или YandexGPT-генерация задач и Redis-кэш.
- `YandexGPTContentService` — обращение к Yandex Foundation Models API, разбор JSON и валидация задания.
- `CodeCheckService` — безопасная проверка Python-кода по тест-кейсам с timeout.
- `AnswerCheckService` — проверка числовых, текстовых и single-choice ответов.
- `GamificationService` — XP, уровни, серии, достижения, квесты.
- `AnalyticsService` — статистика пользователя и агрегированная аналитика.
- `LoggingService` и repositories logs — пользовательские и технические события.

## Адаптивный алгоритм

`mastery_level = correct_count / attempts_count`, при `attempts_count = 0` значение равно `0`. Сложность от 1 до 5. Правильный быстрый ответ при высоком освоении повышает сложность. Ошибка при низком освоении или большой доле ошибок снижает сложность. Если пользователь давно не занимался или часто ошибается, сервис считает тему требующей повторения.

## Геймификация

XP за ответ: попытка `2 XP`, правильный ответ `+10 XP`, неправильный `+3 XP`, бонус сложности `difficulty * 2 XP`. Уровень: `level = xp // 100 + 1`.

Достижения: первый правильный ответ, 10 заданий, 5 правильных ответов, серия 3 дня, освоение темы 80%+. Квесты: ежедневный на 3 задания, недельный на 20 заданий, тематический на 5 заданий.

## База данных

Основные таблицы: `user_profile`, `topic`, `task`, `mastery_profile`, `task_log`, `gamification_log`, `achievement`, `user_achievement`, `quest`, `user_quest`, `technical_log`.

## Генерация заданий через YandexGPT

По умолчанию проект использует надёжную шаблонную генерацию:

```env
CONTENT_GENERATION_MODE=template
```

Чтобы включить YandexGPT, укажите в `.env`:

```env
CONTENT_GENERATION_MODE=yandexgpt
YANDEXGPT_FOLDER_ID=your_yandex_cloud_folder_id
YANDEXGPT_API_KEY=your_yandex_cloud_api_key
YANDEXGPT_MODEL=yandexgpt-lite
```

Вместо API-ключа можно использовать IAM-токен:

```env
YANDEXGPT_IAM_TOKEN=your_iam_token
```

Если заданы оба значения, приоритет имеет `YANDEXGPT_IAM_TOKEN`. Сервис просит модель вернуть строгий JSON с полями `task_type`, `difficulty`, `question_text`, `correct_answer`, `options`, `explanation`, а для заданий на код также `starter_code` и `test_cases`. Ответ валидируется: тип задания должен быть одним из `single_choice`, `text_answer`, `numeric_answer`, `code_answer`; сложность — от 1 до 5; у `single_choice` должно быть 4 варианта и правильный ответ среди них; у `code_answer` должны быть тест-кейсы.

Если YandexGPT недоступен, вернул некорректный JSON или не заполнены ключи, бот автоматически использует шаблонный генератор. Поэтому включение нейросети не ломает выдачу заданий.

### Контекстная генерация по датасету

Проект использует не RAG/few-shot подход: темы ЕГЭ и авторские
задания хранятся в базе, а при генерации YandexGPT получает:

- название выбранной темы;
- теорию из `Topic.description`;
- несколько примеров заданий из `Task` по этой теме;
- требуемую сложность и строгий JSON-формат ответа.

Количество примеров настраивается:

```env
YANDEXGPT_FEW_SHOT_EXAMPLES=3
```

## Задания на код

Тип `code_answer` позволяет ученику отправлять Python-код. Задание хранит стартовый шаблон и тест-кейсы:

```json
{
  "starter_code": "def add(a, b):\n    pass",
  "test_cases": [
    {"input": [2, 3], "expected": 5},
    {"input": [-1, 1], "expected": 0}
  ]
}
```

`CodeCheckService` сначала проверяет код через AST и запрещает опасные конструкции (`import`, `open`, `eval`, `exec`, сетевые/системные вызовы), затем запускает решение в отдельном процессе с timeout и проверяет функцию на тестах. В прототипе это безопаснее прямого `exec` в основном приложении; для production-версии рекомендуется вынести проверку в отдельный sandbox-контейнер.

## Запуск без Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:create_app --factory --reload
```

Запуск Telegram-бота:

```bash
python -m app.bot.main
```

## Запуск через Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Docker Compose запускает сразу несколько сервисов:

- `postgres` — база данных;
- `redis` — кэш и временное состояние текущих заданий;
- `app` — FastAPI REST API;
- `bot` — Telegram-бот на aiogram.

После запуска откройте Telegram и отправьте боту `/start`. Отдельно выполнять
`python -m app.bot.main` в Docker больше не нужно.

В Docker Compose приложение должно работать через PostgreSQL. Если в логах Alembic
появляется `Context impl SQLiteImpl`, значит контейнер получил SQLite URL вместо
PostgreSQL. Внутри Docker нельзя использовать `localhost` для базы данных:
`localhost` указывает на контейнер приложения, а не на контейнер PostgreSQL.
Используйте имя сервиса `postgres`:

```env
DATABASE_URL=postgresql+asyncpg://bot_user:bot_password@postgres:5432/telegram_learning_bot
REDIS_URL=redis://redis:6379/0
```

## Миграции

```bash
alembic revision --autogenerate -m "initial migration"
alembic upgrade head
alembic downgrade -1
```

## Резервное копирование данных пользователей

Данные PostgreSQL сохраняются в Docker volume `postgres_data`, поэтому обычные
команды `docker compose stop`, `docker compose restart` и `docker compose down`
не удаляют пользователей, прогресс, XP, квесты и логи. Данные удаляются при:

```bash
docker compose down -v
```

Чтобы защититься от потери volume при переносе сервера или очистке Docker,
используйте резервные копии PostgreSQL.

Создать backup:

```bash
./scripts/backup_postgres.sh
```

Файл появится в папке:

```text
backups/
```

Например:

```text
backups/telegram_learning_bot_20260502_201500.dump
```

Папка `backups/` добавлена в `.gitignore`: дампы базы не попадут в Git, потому
что там могут быть персональные данные пользователей.

Восстановить backup:

```bash
./scripts/restore_postgres.sh backups/telegram_learning_bot_20260502_201500.dump
```

Перед восстановлением PostgreSQL-контейнер должен быть запущен:

```bash
docker compose up -d postgres
```

Для ручного backup без скрипта:

```bash
docker compose run --rm -v "$PWD/backups:/backups" postgres \
  sh -c 'PGPASSWORD=bot_password pg_dump -h postgres -U bot_user -d telegram_learning_bot -Fc -f /backups/manual.dump'
```

## Заполнение начальными данными

```bash
python scripts/seed_data.py
```

Скрипт добавляет базовые темы, достижения и квесты, а также расширенный
датасет ЕГЭ профильной математики 2026 из файла:

```text
data/ege_profile_math_2026.json
```

В этом файле темы ЕГЭ загружаются в `Topic`, теория хранится в
`Topic.description`, а практические задания загружаются в `Task`.
Раздел `/theory` в боте показывает теорию по выбранной пользователем теме.


## Команды бота

`/start`, `/help`, `/profile`, `/topics`, `/task`, `/quests`, `/achievements`, `/stats`, `/theory`.

## Примеры API-запросов

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/tasks/next?user_id=1&topic_id=1"
curl -X POST http://localhost:8000/tasks/answer   -H "Content-Type: application/json"   -d '{"user_id":1,"task_id":1,"answer":"30","answer_time_seconds":12.5}'
curl http://localhost:8000/analytics/users/1/progress
curl http://localhost:8000/analytics/summary
```

## Тесты

```bash
pytest
```

Покрыты: числовые и текстовые ответы, XP, уровни, серия активности, mastery, повышение/снижение сложности, квесты, достижения, `/health`.

## Форматирование

```bash
black app tests scripts
ruff check app tests scripts
```


- spaced repetition;
- A/B-тестирование адаптивных стратегий.
