# Контракт улья, версия 1

Это договор между будущим движком (FastAPI) и новым интерфейсом. Сейчас окно на Streamlit эти события ещё не шлёт. Поля версии `1` не переименовываются: ломающее изменение — это версия `2`.

Схемы: [ulei-contract-v1.schema.json](ulei-contract-v1.schema.json). Модели Pydantic: `contracts/v1.py`.

Сгенерировать TypeScript (не входит в сборку):

```bash
npx --yes json-schema-to-typescript docs/contracts/ulei-contract-v1.schema.json -o ulei-contract-v1.d.ts
```

Обновить JSON Schema после правки моделей:

```bash
python -m contracts.export_schema
```

Все кадры стрима несут `"version": "1"` и `"type"`.

## Сущности

Агент — роль. `model` — id из каталога или `ollama_chat/<имя>`.

```json
{
  "id": "developer",
  "name": "Разработчик",
  "description": "Пишет и правит код",
  "enabled": true,
  "model": "ollama_chat/llama3.2:3b",
  "temperature": 0.2
}
```

Рой — команда в порядке шагов. `steps` — id агентов.

```json
{
  "id": "code_only",
  "name": "Быстро: код и ревью",
  "steps": ["developer", "reviewer"]
}
```

Задача — то, что попросил человек.

```json
{
  "id": "task_01",
  "text": "Добавь hello.py и запусти его",
  "pipeline": "code_only",
  "workspace": "C:/Users/me/proj"
}
```

Сообщение — один ход внутри запуска, не кадр стрима.

```json
{
  "role": "agent",
  "author": "developer",
  "text": "Файл записан.",
  "created_at": "2026-11-14T06:00:00"
}
```

Локальная модель — статус загрузки или запуска. `progress` от 0 до 1, если известен.

```json
{
  "version": "1",
  "name": "llama3.2:3b",
  "state": "downloading",
  "progress": 0.4,
  "completed": 800000000,
  "total": 2000000000,
  "size_bytes": null,
  "message": "pulling manifest"
}
```

`state`: `missing`, `downloading`, `installed`, `starting`, `running`, `error`.

## События стрима

Порядок одного запуска: `start`, затем `step` и `log` (и `error`, если шаг сломался), в конце ровно один `done`.

`start` — улей принял задачу.

```json
{
  "version": "1",
  "type": "start",
  "task_id": "task_01",
  "pipeline": "code_only",
  "agents": ["developer", "reviewer"]
}
```

`step` — очередь дошла до роли. `index` с 1.

```json
{
  "version": "1",
  "type": "step",
  "task_id": "task_01",
  "index": 1,
  "total": 2,
  "agent_id": "developer",
  "title": "Разработчик"
}
```

`log` — строка журнала. `agent_id` пустой, если строка про весь запуск.

```json
{
  "version": "1",
  "type": "log",
  "task_id": "task_01",
  "agent_id": "developer",
  "text": "пишу hello.py"
}
```

`error` — шаг или запуск сломался. Запуск после этого всё равно заканчивается `done` с `outcome: "failed"`.

```json
{
  "version": "1",
  "type": "error",
  "task_id": "task_01",
  "agent_id": "developer",
  "code": "model_not_found",
  "message": "Такой модели нет в библиотеке Ollama."
}
```

`done` — конец. `outcome`: `ok`, `stopped`, `failed`.

```json
{
  "version": "1",
  "type": "done",
  "task_id": "task_01",
  "outcome": "ok",
  "result": "hello.py печатает приветствие."
}
```

Клиент различает кадры по полю `type` и не должен падать на неизвестном `type` будущей версии: такой кадр можно пропустить, если `version` не `"1"`.
