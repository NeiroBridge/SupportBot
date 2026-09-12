# NeiroBridge Support Bot

Telegram-бот первой линии студии [NeiroBridge](https://neirobridge.ru): собирает заявку на диагностику или обращение в поддержку и отправляет карточку в канал оператора.

Это учебный пайплайн incoming lids, переписанный под реальный сценарий студии и демо для заказчиков.

## Что делает бот

После `/start` клиент выбирает режим:

- **Новая заявка / диагностика** — квалификация лида: имя, контакт, компания, тип запроса, задача, текущие инструменты, срок.
- **Поддержка по проекту** — имя, контакт, проект, суть проблемы, когда началось, где проявляется, приоритет.

Дальше бот ведёт короткий диалог через LLM, умеет вытащить несколько полей из одного сообщения и отвечает на базовые вопросы о студии без выдуманных цен и телефонов.

Когда обязательные поля режима собраны, карточка уходит в Telegram-чат оператора, а клиент получает подтверждение.

## Куда слать заявки

Лучший вариант для демо и работы — **закрытый канал** `NeiroBridge | Заявки`.

Почему канал, а не личка:

- личные сообщения не смешиваются с заявками;
- лента чистая, её можно показать заказчику;
- позже можно добавить коллегу, не переписывая бота;
- история обращений не теряется в общем чате.

Как настроить:

1. Создайте закрытый канал.
2. Добавьте бота администратором с правом публиковать сообщения.
3. Откройте канал в [web.telegram.org](https://web.telegram.org), скопируйте число после `#` и поставьте минус в начале. Для канала это обычно `-100...`.
4. Пропишите ID в `OPERATOR_CHAT_ID`.

Для самого первого теста можно временно указать свой user id — бот напишет заявку вам в личку. Для демо заказчикам переключитесь на канал.

## Стек

- Python 3.12, aiogram 3
- LLM через [ProxyAPI](https://proxyapi.ru), модель `gpt-4o-mini`
- SQLite для сессий
- Docker + Docker Compose

Контакты, которые бот имеет право называть:

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
```

Если с сервера не открывается `api.telegram.org`, укажите Cloudflare Worker в `TELEGRAM_API_URL` — как в DeskMate.

```powershell
python main.py
```

Проверка без Telegram:

```powershell
pytest
```

## Docker

```powershell
docker compose up -d --build
docker compose logs -f
```

Сессии хранятся в volume `supportbot-data`. После перезапуска контейнера диалог не сбрасывается.

## Деплой на VPS

На сервере должны быть Docker и Docker Compose. Затем:

```bash
git clone https://github.com/NeiroBridge/neirobridge-support-bot.git
cd neirobridge-support-bot
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
```

Проверьте `/start`, оба режима и появление карточки в канале оператора.

## Команды

- `/start` — приветствие и выбор режима
- `/help` — коротко про сценарии и контакты
- `/reset` — сброс сессии

## Структура

```text
bot/          обработчики Telegram и клавиатуры
core/         настройки, логи, схемы заявки
services/     LLM, SQLite, workflow, отправка оператору
docs/         отчёт по домашнему заданию
```

## Домашнее задание

Краткий отчёт: [docs/HOMEWORK.md](docs/HOMEWORK.md)
