# Room Snapshot API v1.4

[English](README.md) | **Русский**

[![Python 3.15](https://img.shields.io/badge/python-3.15-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-%230db7ed.svg)](https://www.docker.com/)
[![MCP](https://img.shields.io/badge/MCP-streamable%20HTTP-blueviolet.svg)](https://modelcontextprotocol.io/)

Небольшой сервис, превращающий RTSP-камеры видеонаблюдения в простой HTTP API и
MCP-сервер. Другие проекты — скрипты, сайты, приложения и ИИ-агенты — обращаются к
нему вместо того, чтобы самим разбираться с RTSP-адресами и учётными данными камер.

Поставляется с [навыком для агента](skills/README.md): Claude Code, Cursor и другие
агенты могут сами установить и использовать сервис.

## Возможности

- **HTTP API** для списка комнат, информации о комнате и JPEG-снимков.
- **MCP-сервер** (streamable HTTP и stdio), чтобы ИИ-агенты получали камеры готовыми инструментами.
- **Навык для агента**, который умеет разворачивать сервис и пользоваться им из Claude Code, Cursor и других агентов.
- **Индивидуальные учётки на каждую камеру** вместо одного общего логина.
- **Аутентификация по API-ключу** на всех эндпоинтах (REST и MCP).
- **Параллельный захват**: запросы к разным камерам выполняются одновременно.
- **In-memory кэш снимков** с `ETag`/`304` и `Cache-Control`.
- **Локализованные имена комнат** (`ru`/`en`) с файлом переводов для каждой инсталляции.
- **Честная health-проверка**: живой TCP-опрос каждой камеры.
- **Установка одной командой**: `./install.sh` готовит конфигурацию и запускает Docker.
- Docker-образ, запуск от непривилегированного пользователя.

## Требования

- Docker и Docker Compose (рекомендуется), либо
- Python 3.15 и FFmpeg для локальной разработки.
- Сетевой доступ к RTSP-камерам.

## Тестированное оборудование

Сервис протестирован на IP-камерах видеонаблюдения **TP-Link Tapo C100, C200 и
C500** по RTSP. Другие камеры работают, если ffmpeg умеет читать их поток;
заметки по настройке Tapo (аккаунт камеры, пути `/stream1` и `/stream2`) — в
[`skills/room-snapshot/references/cameras.md`](skills/room-snapshot/references/cameras.md).

## Быстрый старт

Одна команда создаёт `.env` со сгенерированным API-ключом, копирует шаблоны
конфигурации, собирает образ и ждёт, пока API станет здоровым:

```bash
git clone git@gitea.prits.ru:barval-my/room-snapshot-api.git
cd room-snapshot-api
./install.sh
```

Затем внесите камеры в `config/cameras.conf` и перезапустите:

```bash
docker compose restart api mcp
```

Либо вручную:

```bash
cp .env.example .env               # задайте API_KEY и RTSP_AUTH
cp config/cameras.conf.example config/cameras.conf
cp config/cameras.auth.example config/cameras.auth     # необязательные учётки камер
cp config/rooms.i18n.example.json config/rooms.i18n.json  # необязательные переводы

docker compose up -d --build
```

REST API доступен по адресу `http://localhost:5005`, MCP-сервер — по
`http://localhost:5006/mcp`.

## Навык для агента

В репозитории есть самодостаточный навык
[`skills/room-snapshot/`](skills/room-snapshot/SKILL.md). Он покрывает два случая:

- **развёртывание** — агент проверяет предпосылки, запускает `./install.sh`,
  добавляет камеры, проверяет эндпоинты и регистрирует MCP-сервер;
- **использование** — агенту дают базовый URL и API-ключ, и он только читает
  список комнат, снимает кадры и сообщает состояние камер.

```bash
mkdir -p ~/.claude/skills
cp -r skills/room-snapshot ~/.claude/skills/
```

Другие агенты и smoke-тест описаны в [`skills/README.md`](skills/README.md).
Навык распространяется по MIT, как и весь проект, и публикуется бесплатно.

## Инсталляционные файлы

Набор камер, их имена и учётные данные у каждой инсталляции свои и **никогда не
хранятся в git**. Отслеживаются только шаблоны `*.example`; реальные файлы лежат в
`config/` и не попадают в Docker-образ (монтируются томом).

| Файл | Назначение | Формат |
|------|-----------|--------|
| `config/cameras.conf` | Список камер | `code=ip:port/path:name` |
| `config/cameras.auth` | Учётки камер (необязательно) | `code=user:password` |
| `config/rooms.i18n.json` | Локализованные имена (необязательно) | `{"kuh": {"ru": "Кухня", "en": "Kitchen"}}` |

- Камера без записи в `cameras.auth` использует общий `RTSP_AUTH`.
- Камера вообще без учётных данных получает URL без логина.
- Если `rooms.i18n.json` отсутствует, берутся имена из `cameras.conf`.

## Конфигурация (`.env`)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `API_KEY` | Общий API-ключ для REST и MCP. Обязателен. | — |
| `RTSP_AUTH` | Общие учётки камер `user:password`. | `` |
| `CORS_ORIGINS` | Список разрешённых origin через запятую; пусто — cross-origin запрещён. | `` |
| `DEFAULT_LANG` | Язык имён комнат по умолчанию (`en` или `ru`). | `en` |
| `SNAPSHOT_CACHE_TTL` | Время жизни кэша снимка, секунды. | `5` |
| `SNAPSHOT_TIMEOUT` | Таймаут захвата ffmpeg, секунды. | `15` |
| `MCP_PORT` | Порт MCP-сервера. | `8000` |
| `FLASK_DEBUG` | Режим отладки (никогда в проде). | `false` |
| `SECRET_KEY` | Секрет сессий Flask. | — |
| `HOST`, `PORT` | Адрес/порт (dev-сервер). | `0.0.0.0`, `5000` |
| `CONFIG_DIR` | Каталог с инсталляционными файлами. | `/app/config` |
| `CAMERAS_CONF` | Переопределить путь к `cameras.conf`. | `<CONFIG_DIR>/cameras.conf` |
| `CAMERAS_AUTH` | Переопределить путь к `cameras.auth`. | `<CONFIG_DIR>/cameras.auth` |
| `ROOMS_I18N` | Переопределить путь к `rooms.i18n.json`. | `<CONFIG_DIR>/rooms.i18n.json` |

Сервис работает **fail-closed**: если `API_KEY` пуст и `FLASK_DEBUG` не `true`,
он отказывается стартовать.

Dev-сервер запускается командой `python -m app.app` (использует `HOST`/`PORT`); в Docker
порт задаётся командой gunicorn.

## Аутентификация

Каждому запросу нужен общий ключ — либо заголовок `X-API-Key`, либо
`Authorization: Bearer <key>`:

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/rooms
```

Отсутствующий или неверный ключ возвращает `401 {"error": "Unauthorized"}`.

## Эндпоинты REST

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/info` | Метаданные API и список эндпоинтов. |
| GET | `/rooms` | `{code: name}` для всех комнат (язык через `?lang=` / `Accept-Language`). |
| GET | `/rooms/<code>` | Детали комнаты: `name`, `names`, `ip`, `stream`, маскированный `url`. |
| GET | `/snapshot/<code>` | JPEG-снимок. Параметры: `width=<px>`, `fresh=1`. |
| GET | `/health` | Живая доступность камер; всегда HTTP 200. |

Ответы со снимком содержат `ETag` и `Cache-Control`; при `If-None-Match` вернётся
`304 Not Modified`. `?fresh=1` обходит кэш и обновляет его.

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/snapshot/kuh?width=640 -o kuh.jpg
```

## MCP-сервер

ИИ-агенты подключаются по **streamable HTTP** к `http://host:5006/mcp`, используя тот
же `API_KEY` (заголовок `X-API-Key` или `Authorization: Bearer`).

Инструменты:

| Инструмент | Аргументы | Возвращает |
|-----------|-----------|------------|
| `list_rooms` | `lang?` | Код комнаты → локализованное имя. |
| `get_snapshot` | `room`, `width?` | JPEG-кадр как image-content. |
| `room_info` | `room`, `lang?` | Детали комнаты с маскированным URL. |
| `health` | — | Доступность камер и наличие ffmpeg. |

Неизвестная комната и сбой захвата возвращаются как ошибка инструмента с понятным
текстом, чтобы агент мог объяснить проблему, а не показать пустоту.

Пример конфигурации MCP-клиента (транспорт-URL):

```json
{
  "mcpServers": {
    "room-snapshot": {
      "url": "http://localhost:5006/mcp",
      "headers": { "X-API-Key": "your-api-key" }
    }
  }
}
```

Claude Code:

```bash
claude mcp add --transport http room-snapshot http://localhost:5006/mcp \
  --header "X-API-Key: your-api-key"
```

Клиенты без поддержки удалённого HTTP могут запускать сервер локально по stdio;
канал локальный и доверенный, поэтому API-ключ не нужен:

```bash
python -m app.mcp_server --stdio
```

```json
{
  "mcpServers": {
    "room-snapshot": {
      "command": "python",
      "args": ["-m", "app.mcp_server", "--stdio"],
      "cwd": "/path/to/room-snapshot-api"
    }
  }
}
```

## Локализация

**Код** комнаты (`kuh`) — стабильный, языконезависимый идентификатор для URL, прав и
интеграций. Переводится только **подпись**. Порядок выбора языка: `?lang=` → заголовок
`Accept-Language` → `DEFAULT_LANG`. Формат `/rooms` остаётся `{code: name}`;
`/rooms/<code>` дополнительно содержит `names` со всеми переводами.

Поскольку по умолчанию язык `en`, существующим русскоязычным клиентам (например FLAI)
нужно отправлять `Accept-Language: ru` или `?lang=ru`, чтобы и дальше получать русские
подписи.

## Мониторинг

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/health | jq
```

`status` — `healthy`, `degraded` (часть камер недоступна) или `unhealthy` (ни одной).
HTTP-код остаётся 200, чтобы выключенная камера не перезапускала контейнер.
`docker compose logs -f` показывает JSON-логи.

## Docker

```bash
./install.sh               # первый запуск: конфигурация, ключ, сборка, старт, health-проверка
docker compose build
docker compose up -d      # api на :5005, mcp на :5006
docker compose down
```

## Разработка

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

CI запускает `ruff` и `pytest` на каждый push (`.gitea/workflows/ci.yml`).

## Безопасность

- Учётные данные лежат в `config/cameras.auth` и `.env`, а не в git и не в образе.
- Все эндпоинты требуют API-ключ; без него сервис не стартует.
- Запросы к разным камерам выполняются параллельно; один медленный поток не блокирует остальные.
- В проде используйте HTTPS и обратный прокси; учётные данные камер URL-кодируются и
  маскируются в ответах API и логах.

## Планы развития

- Live-стримы MJPEG / WebSocket
- Автообнаружение камер по ONVIF
- Веб-интерфейс просмотра
- Запись архива
- Метрики Prometheus

## Лицензия

MIT — см. [LICENSE](LICENSE). Русский перевод: [LICENSE-ru](LICENSE-ru).
