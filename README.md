# NeiroBridge Support Bot

Telegram-бот первой линии студии [NeiroBridge](https://neirobridge.ru). Собирает заявку на диагностику или обращение в поддержку и отправляет карточку в канал оператора.

Живой бот: [@neirobridge_support_bot](https://t.me/neirobridge_support_bot)

## Что делает бот

После `/start` клиент выбирает режим:

- **Новая заявка / диагностика** — имя, контакт, компания, тип запроса, задача, текущие инструменты, срок.
- **Поддержка по проекту** — имя, контакт, проект, суть проблемы, когда началось, где проявляется, приоритет.

Бот ведёт короткий диалог, умеет вытащить несколько полей из одного сообщения и отвечает на базовые вопросы о студии. Цены, почту и телефон не выдумывает.

Когда обязательные поля режима собраны, карточка уходит оператору, клиент получает подтверждение.

## Стек

- Python 3.12, aiogram 3
- LLM через [ProxyAPI](https://proxyapi.ru), модель `gpt-4o-mini`
- SQLite для сессий
- Docker + Docker Compose

Контакты, которые бот называет:

- сайт: https://neirobridge.ru
- Telegram: https://t.me/neirobridge_ai
- канал кейсов: https://t.me/neirobridge_cases

## Быстрый старт

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Заполните `.env`:

```env
TELEGRAM_BOT_TOKEN=
OPERATOR_CHAT_ID=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
TELEGRAM_API_URL=
```

Если с сервера не открывается `api.telegram.org`, укажите Cloudflare Worker в `TELEGRAM_API_URL`.

```powershell
python main.py
```

## Docker

```bash
docker compose up -d --build
docker compose logs -f
```

Сессии хранятся в volume `supportbot-data` и переживают перезапуск контейнера.

## Деплой на VPS

```bash
git clone https://github.com/NeiroBridge/SupportBot.git
cd SupportBot
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
```

## Команды

- `/start` — приветствие и выбор режима
- `/help` — сценарии и контакты
- `/reset` — новая заявка

## Структура

```text
bot/          обработчики Telegram и клавиатуры
core/         настройки, логи, схемы заявки
services/     LLM, SQLite, workflow, отправка оператору
```
