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
| GET | `/api/v1/models/local` | статусы локальных моделей |

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

Пока рой исполняет прежний последовательный оркестратор. Окно Streamlit его и вызывает само: этот порт его не заменяет.
