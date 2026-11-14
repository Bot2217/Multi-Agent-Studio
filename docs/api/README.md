# Локальный движок, версия 1

Рядом со Streamlit sidecar поднимает FastAPI на `127.0.0.1`. Порт выбирает окно Tauri и передаёт его как `--api-port`. В каталоге данных появляется `api.json`:

```json
{"port": 8765, "health": "http://127.0.0.1:8765/api/v1/health"}
```

Проверка с той же машины: `GET /api/v1/health` → `{"status":"ok","version":"1","service":"ulei"}`. Окно само опрашивает этот адрес перед тем, как открыть студию. Если движок молчит, студия всё равно открывается: старый экран не зависит от этого порта. Порт записан в `api.json`.

Схемы сущностей и кадров — в [контракте v1](../contracts/README.md). Кадр стрима — JSON этой схемы, без лишних полей.

## Запросы

База: `http://127.0.0.1:<api-port>`.

| Метод | Путь | Ответ |
| --- | --- | --- |
| GET | `/api/v1/agents` | список агентов |
| GET | `/api/v1/swarms` | список роёв (`steps` — id агентов по порядку) |
| POST | `/api/v1/tasks` | задача, код 201 |
| POST | `/api/v1/tasks/{id}/run` | код 202, ссылки на стрим |
| POST | `/api/v1/tasks/{id}/cancel` | код 202 |
| GET | `/api/v1/tasks/{id}/events` | SSE, по кадру на строку `data:` |
| WS | `/api/v1/tasks/{id}/stream` | те же кадры JSON |
| GET | `/api/v1/models/catalog` | поиск по библиотеке: `q`, `quant`, `max_gb`, `max_ram_gb`, `max_vram_gb`, `fits` |
| GET | `/api/v1/models/local` | статусы локальных моделей |
| POST | `/api/v1/models/local/{name}/pull` | начать скачивание |
| POST | `/api/v1/models/local/{name}/pause` | пауза (`state: paused`) |
| POST | `/api/v1/models/local/{name}/resume` | продолжить |
| POST | `/api/v1/models/local/{name}/cancel` | отменить |

Создать задачу:

```json
{"text": "Добавь hello.py", "pipeline": "code_only", "workspace": "C:/Users/me/proj"}
```

Неизвестный `pipeline` — код 400, `unknown_pipeline`. Повторный запуск живой задачи — код 409, `already_running`.

Тело запуска необязательно. `timeout_s` — секунды на весь запуск. По истечении приходит `error` с `code: "timeout"` и затем `done` с `outcome: "failed"`. Отмена даёт `done` с `outcome: "stopped"`.

## Как читать стрим

Порядок одного запуска: `start`, затем `step` и `log`, при сбое ещё `error`, в конце ровно один `done`. Подписчик, который пришёл позже, получает уже прошедшие кадры и ждёт `done`, если его ещё не было.

SSE:

```text
data: {"version":"1","type":"start","task_id":"task_0001","pipeline":"single","agents":["developer"]}

data: {"version":"1","type":"done","task_id":"task_0001","outcome":"ok","result":"готово"}
```

WebSocket шлёт тот же JSON одним сообщением на кадр и закрывается после `done`.

Запуск идёт через движок v2. Роли из одного `waves` в `config/agents.yaml` работают одновременно; без `waves` каждый шаг ждёт предыдущий, как раньше. Если у роли локальная модель (`ollama_chat/...`), движок сначала поднимает Ollama и, если это не вышло, шлёт `error` с кодом среды (`binary_missing`, `port_busy`, …) и `done` с `outcome: "failed"`. Окно Streamlit по-прежнему вызывает старый оркестратор и от этого порта не зависит.

Каталог — теги из `config/ollama_library.yaml`. У каждого есть размер, квантизация и оценка RAM/VRAM. `fits=true` оставляет только те, что влезают в свободный диск, память и, если она известна, видеопамять. Цифры ориентировочные.
