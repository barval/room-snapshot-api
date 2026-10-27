# Room Snapshot API v1.3

[English](README.md) | **Русский**

[![Python 3.15](https://img.shields.io/badge/python-3.15-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-%230db7ed.svg)](https://www.docker.com/)

Небольшой сервис, превращающий RTSP-камеры видеонаблюдения в простой HTTP API и
MCP-сервер. Другие проекты — скрипты, сайты, приложения и ИИ-агенты — обращаются к
нему вместо того, чтобы самим разбираться с RTSP-адресами и учётными данными камер.

## Возможности

- **HTTP API** для списка комнат, информации о комнате и JPEG-снимков.
- **MCP-сервер** (streamable HTTP), чтобы ИИ-агенты получали камеры готовыми инструментами.
- **Индивидуальные учётки на каждую камеру** вместо одного общего логина.
- **Аутентификация по API-ключу** на всех эндпоинтах (REST и MCP).
- **Параллельный захват**: запросы к разным камерам выполняются одновременно.
- **In-memory кэш снимков** с `ETag`/`304` и `Cache-Control`.
- **Локализованные имена комнат** (`ru`/`en`) с файлом переводов для каждой инсталляции.
- **Честная health-проверка**: живой TCP-опрос каждой камеры.
- Docker-образ, запуск от непривилегированного пользователя.

## Требования

- Docker и Docker Compose (рекомендуется), либо
- Python 3.15 и FFmpeg для локальной разработки.
- Сетевой доступ к RTSP-камерам.

## Быстрый старт

```bash
git clone git@gitea.prits.ru:barval-my/room-snapshot-api.git
cd room-snapshot-api

cp .env.example .env               # задайте API_KEY и RTSP_AUTH
cp config/cameras.conf.example config/cameras.conf
cp config/cameras.auth.example config/cameras.auth     # необязательные учётки камер
cp config/rooms.i18n.example.json config/rooms.i18n.json  # необязательные переводы

docker compose up -d
```

REST API доступен по адресу `http://localhost:5005`, MCP-сервер — по
`http://localhost:5006/mcp`.

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

Сервис работает **fail-closed**: если `API_KEY` пуст и `FLASK_DEBUG` не `true`,
он отказывается стартовать.

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
| GET | `/snapshot/<code>` | JPEG-снимок. Параметры: `width=<px>`, `fresh=1`, `lang=`. |
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
| `get_snapshot` | `room`, `width?`, `lang?` | JPEG-кадр как image-content. |
| `room_info` | `room`, `lang?` | Детали комнаты с маскированным URL. |
| `health` | — | Доступность камер и наличие ffmpeg. |

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

## Локализация

**Код** комнаты (`kuh`) — стабильный, языконезависимый идентификатор для URL, прав и
интеграций. Переводится только **подпись**. Порядок выбора языка: `?lang=` → заголовок
`Accept-Language` → `DEFAULT_LANG`. Формат `/rooms` остаётся `{code: name}`;
`/rooms/<code>` дополнительно содержит `names` со всеми переводами.

## Мониторинг

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/health | jq
```

`status` — `healthy`, `degraded` (часть камер недоступна) или `unhealthy` (ни одной).
HTTP-код остаётся 200, чтобы выключенная камера не перезапускала контейнер.
`docker compose logs -f` показывает JSON-логи.

## Docker

```bash
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
