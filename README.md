# GlassHouse Live

Публичная бета AI-реалити-шоу: один общий сезон «Вилла», четыре автономных
персонажа, бесплатное влияние зрителей, русский и английский интерфейс.
Голос открывает возможность, но не определяет согласие или результат.

## Быстрый запуск — Docker, без LLM

Из корня этого репозитория (`public-show-work`):

```bash
cp .env.example .env
docker compose up --build
```

Откройте <http://localhost:8000>, создайте аккаунт и перейдите в «Эфир».
На предстоящую серию доступны 3 бесплатных очка: их можно разделить между целями.
Следующая серия выходит через 120 секунд. В режиме `development` авторизованному
зрителю доступна кнопка «Запустить серию». Архив и профиль показывают результат
и собственные голоса. Переключатель RU / EN сохраняет язык в профиле.

Compose запускает PostgreSQL 16, API и отдельный worker. API перед стартом
применяет Alembic-миграции и идемпотентно создаёт первый сезон с seed 42.
Worker стартует после готовности API. LLM по умолчанию выключен; ключ не нужен.
Состояние, голоса, аккаунты, сессии, журнал и recaps сохраняются в volume `pgdata`.

```bash
docker compose restart api worker       # история сохранится
docker compose logs --tail=50 api worker
docker compose down                    # останавливает, сохраняя volume
```

`docker compose down -v` удаляет базу и историю — для обычного перезапуска
эта команда не нужна. PostgreSQL не публикует порт наружу; API доступен только
на loopback хоста. Контейнеры приложения работают без root, с read-only файловой
системой и временным `/tmp`.

## Локальная разработка — SQLite

Python 3.11 или новее. Docker не требуется:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

В `.env` замените адрес базы на `DATABASE_URL=sqlite:///./glasshouse.db`.
Затем:

```bash
alembic upgrade head
python -m glasshouse.live.worker --init
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Во втором терминале, в том же окружении и каталоге:

```bash
python -m glasshouse.live.worker
```

`--init` создаёт первый сезон без сброса существующего; API также делает это при
старте. `python -m glasshouse.live.worker --once` обрабатывает каждый наступивший
сезон не более одного раза и завершается; если время тика ещё не пришло, изменений
нет. Подходит для cron. После простоя worker не проигрывает всю очередь пропущенных
тиков: следующая серия назначается относительно времени завершения текущей.

Для локального PostgreSQL укажите URL вида
`postgresql+psycopg://USER:PASSWORD@localhost:5432/glasshouse` и выполните те же
команды миграции, API и worker. Старые URL `postgresql+asyncpg://` автоматически
приводятся к синхронному psycopg для нового сервисного слоя.

## OpenRouter — необязательный рассказчик

В `.env` задайте:

```dotenv
LLM_ENABLED=true
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL_NARRATOR=provider/model-id
OPENROUTER_MODEL_NARRATOR_FALLBACKS=provider/backup-model-id
OPENROUTER_SITE_URL=https://your-site.example
OPENROUTER_APP_NAME=GlassHouse Live
```

Модели выбираете вы; используйте модель, поддерживающую строгий JSON Schema.
В проекте нет жёстко заданной платной модели. Для Docker примените изменения:

```bash
docker compose up -d --force-recreate api worker
```

Адаптер использует OpenAI Python SDK, `https://openrouter.ai/api/v1`,
`chat.completions.create`, `response_format=json_schema` со `strict=true`,
`extra_body.models` и `provider.require_parameters=true`. Дополнительные
заголовки: `HTTP-Referer`, `X-OpenRouter-Title`.

В бете рассказчик работает как **ограниченный редактор**: выбирает формулировки
из авторских вариантов уже разрешённого события. Текст проверяется по строгой
схеме и списку допустимых вариантов, поэтому модель не может дописать новый факт,
диалог, интимное действие или согласие персонажа. Это сознательно ограничивает
творческую свободу. Механика всегда детерминирована и никогда не вызывает LLM.

Не более одного внешнего запроса на содержательный тик; HTTP-повторы отключены,
перебор моделей выполняет OpenRouter внутри запроса. Тики отдыха не вызывают LLM.
При выключенном LLM, отсутствии ключа/модели, таймауте, отказе или неверном ответе
публикуется локальный шаблон. В `llm_runs` сохраняются статус, роль, модели,
usage/cost при наличии, latency и тип ошибки — без ключа и полного prompt.

Для одного общего сезона narration создаётся на `SEASON_LOCALE` (по умолчанию ru).
Другой язык всегда доступен как полноценный детерминированный перевод, без второго
LLM-вызова. Смена языка зрителем не меняет мир и не инициирует платный запрос.

Официальная спецификация: [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs),
[model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks).

## Переменные окружения

| Переменная | Назначение / значение по умолчанию |
|---|---|
| `APP_ENV` | `development`, `test` или `production`; только development включает ручные тики |
| `DATABASE_URL` | В примере PostgreSQL в Compose; без переменной — локальный SQLite |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL в Compose; должен совпадать с паролем в URL |
| `SESSION_SECRET` | В development локальное значение по умолчанию; в production обязательный случайный секрет от 32 символов |
| `TICK_INTERVAL_SECONDS` | 120 реальных секунд между сериями; минимум 5 |
| `WORKER_POLL_SECONDS` | 5 секунд между проверками очереди |
| `SEASON_LOCALE` | `ru` или `en`; применяется при создании сезона |
| `LLM_ENABLED` | `false`; включает только публичного рассказчика |
| `OPENROUTER_API_KEY` | Секретный ключ; необязателен |
| `OPENROUTER_MODEL_NARRATOR` | ID основной модели; пустой по умолчанию |
| `OPENROUTER_MODEL_NARRATOR_FALLBACKS` | ID резервных моделей через запятую |
| `OPENROUTER_SITE_URL` | Необязательный HTTP-Referer |
| `OPENROUTER_APP_NAME` | `GlassHouse Live`, заголовок X-OpenRouter-Title |
| `LLM_MAX_CALLS_PER_TICK` | 1; допустимы только 0 или 1 |
| `LLM_MAX_OUTPUT_TOKENS_PER_TICK` | 600; диапазон 64–2000 |
| `LLM_MAX_INPUT_CHARS` | 12000; контекст длиннее лимита приводит к шаблонному recap |
| `LLM_TIMEOUT_SECONDS` | 15; диапазон 1–60 |

Не добавляйте `.env` и ключи в git. Для публичного размещения задайте
`APP_ENV=production`, собственные пароль БД и `SESSION_SECRET`; используйте HTTPS
через reverse proxy. Secure cookie намеренно не работает по обычному HTTP в
production. Секрет можно сгенерировать командой
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Настройте резервное копирование PostgreSQL. Пример рассчитан на локальную бету;
публичная инфраструктура HTTPS, резервных копий и внешнего rate limiting зависит
от выбранного хостинга. Без доверенной настройки proxy приложение использует
реальный адрес соединения и игнорирует поддельный X-Forwarded-For.

## API и безопасность

OpenAPI: <http://localhost:8000/docs>. Доступны:

| Метод и путь | Назначение |
|---|---|
| `GET /public/season` | Общее публичное состояние и последний recap |
| `GET /public/goals` | Активные цели (список) |
| `GET /public/influence` | Цели, предстоящий тик, остаток очков; `null` для гостя |
| `GET /public/timeline`, `/public/recaps` | Публичные эпизоды, `page`, `limit`, `from_tick` |
| `GET /public/session` | CSRF-токен и признак входа, без user id/email |
| `POST /public/votes` | Голос текущего пользователя с CSRF и idempotency key |
| `GET /health` | Жив ли процесс |
| `GET /ready` | Доступна ли БД, применена ли миграция, существует ли сезон |
| `POST /public/dev/ticks` | Только development, вход + CSRF + `expected_revision` |

Публичные представления поддерживают `?lang=ru` / `?lang=en`.
Список timeline теперь содержит локализованные `Episode` и метаданные пагинации;
его формат расширен по сравнению с in-memory прототипом. Путь сохранён.

После регистрации/входа через HTML-форму API использует ту же session cookie.
Получите `csrf_token` из `/public/session` и передайте его в `X-CSRF-Token`:

```json
{
  "story_goal_id": "goal:1:conversation",
  "tick": 1,
  "influence_points": 2,
  "request_id": "a-unique-request-id-123456"
}
```

ID и tick берите из актуальных целей. `viewer_id` больше не принимается.
Повтор того же `request_id` с тем же телом возвращает предыдущий результат без
повторного списания. Другое тело с тем же ключом даёт 409. Голос за закрытый тик,
конфликт revision и исчерпанный бюджет также дают 409. Ошибки имеют поля `code`,
`message` и не отражают секретный пользовательский ввод.

Пароли хешируются Argon2id. Cookie: HttpOnly, SameSite=Lax, Secure в production;
срок сессии 7 дней. В БД хранится только хеш случайного session token. Выход
отзывает сессию на сервере; после входа меняются session token и CSRF.
Все формы POST защищены CSRF. Login ограничен по адресу и нормализованному email,
регистрация — по адресу, голосование — по аккаунту. Счётчики в БД общие для
процессов; worker удаляет истёкшие сессии и старые счётчики. Входные тела ограничены
16 KiB, включая chunked-запросы. HTMX поставляется локально; страницы имеют CSP,
автоэкранирование Jinja и не требуют CDN.

Старый debug API вынесен в `apps.api.debug:app`, никогда не подключается к Live
и отказывается стартовать при `APP_ENV=production`. Для локального исследования:

```bash
APP_ENV=development uvicorn apps.api.debug:app --host 127.0.0.1 --port 8001
```

Это отдельное состояние в памяти; оно не управляет сезоном Live и содержит
приватные сведения симулятора. Существующие тесты этого адаптера сохранены,
изменён только импорт точки входа.

## Хранение и детерминизм

`src/glasshouse/live/` содержит сервисный слой, SQLAlchemy-модели, worker,
аутентификацию, переводы и рассказчика. `apps/api/` — HTTP-слой и Jinja/CSS/HTMX.
Миграция 002 добавляет `users`, `seasons`, `show_events`, `viewer_votes`,
`viewer_budgets`, `public_recaps`, `llm_runs`, `auth_sessions`, `rate_limits`.
Миграция 001 сохранена с совместимыми типами для SQLite; расширение pgvector для
используемых float arrays больше не требуется.

Каждая мутация делает условный UPDATE сезона по `revision`. Только победившая
транзакция изменяет snapshot, добавляет события и recaps. Тик, журнал, recap,
LLM-аудит и следующее время фиксируются одним commit. Конкурентный worker с
устаревшей revision не исполняет тик. Голоса используют ту же блокировку строки;
бюджет защищён условным UPDATE и CHECK `0 <= spent <= 3`. Журнал дополнительно
защищён триггерами от UPDATE/DELETE. Snapshot и журнал внутренние, не публичные.

Сохранены цепочка World Truth → perception → Knowledge → Claims → Beliefs,
причинные ссылки, границы и взаимное согласие персонажей. Seed, snapshot и
последовательность голосов воспроизводят механическую историю. Narration —
отдельная публичная проекция, она не изменяет snapshot и replay. Один тик равен
120 игровым минутам; реальный интервал публикации настраивается отдельно.

```bash
alembic upgrade head
python scripts/run_simulation.py --hours 48 --seed 42
```

Миграции при масштабировании API запускайте один раз как отдельный deployment
step, затем стартуйте процессы через `uvicorn apps.api.main:app`. Несколько
worker-процессов допустимы: защиту обеспечивает БД. SQLite предназначен для
разработки и тестов, PostgreSQL — основной режим.

## Проверки

```bash
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -m "not evaluation" -q -p no:cacheprovider
ruff check .
```

Новые тесты проверяют миграции, восстановление, atomic rollback, конкуренцию,
worker `--once`, аккаунты, отзыв сессий, CSRF, бюджет/идемпотентность, локализацию,
HTML-путь, отсутствие приватных данных, OpenRouter contract и fallback. Во всех
не-evaluation тестах реальные сетевые соединения запрещены fixture; OpenRouter
проверяется подставным клиентом. Прежние evaluation-тесты остаются отдельными и
не запускаются этими командами.

Для изолированного smoke-теста на PostgreSQL запущенного Compose:

```bash
docker compose exec api python scripts/smoke_postgres.py
```

Он создаёт временную схему с уникальным именем, проверяет миграции, конкурентные
операции, восстановление и откат и удаляет только эту схему; сезон приложения
не затрагивается.

## Границы Public Beta

- Один общий сезон и фиксированные персонажи/сюжетные категории; нет редактора
  пользовательских промптов, персонажей или произвольного контента.
- Нет ставок, платежей, криптовалюты, призов и вывода очков; влияние бесплатно.
- Нет откровенного контента; романтическая возможность требует взаимного согласия.
- Нет OAuth, подтверждения email, восстановления пароля и защиты от всех форм
  создания множества аккаунтов. Ограничения попыток — базовая защита беты.
- Narrator выбирает безопасные авторские формулировки, а не пишет свободный сценарий.
- Интерфейс обновляется каждые 15 секунд через HTMX; голос обновляет свой блок сразу.
- Snapshot включает историю симулятора и со временем растёт. Долгие сезоны,
  архивирование, удержание данных и нагрузочное тестирование — следующий этап.
- После принятия голоса исход не гарантирован. Отказ персонажа полноценен и
  не штрафуется. Имена профилей никогда не передаются LLM.
