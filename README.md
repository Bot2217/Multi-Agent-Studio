# 🤖 Agent Studio

Локальный агент уровня **Claude Code** на вашем ПК:

- читает / пишет / удаляет файлы (перед изменением — **резервная копия**)
- выполняет **bash / cmd**
- подключается по **SSH** к другим устройствам в локальной сети
- **не даёт компьютеру уснуть** на время работы
- режим «экран может погаснуть, CPU работает» (не полный S3-сон)

---

## Быстрый старт

```bash
cd agent_studio
pip install -r requirements.txt
cp .env.example .env
# вставьте API-ключи в .env

# UI
streamlit run app.py
# или
./run.sh

# CLI без браузера
python cli.py "Создай hello.py и запусти его"
```

Workspace по умолчанию: `./workspace`  
Бэкапы: `./backups`

---

## Возможности

| Модуль | Описание |
|--------|----------|
| **Filesystem** | list, read, write, append, delete, move, copy, search. Всё ограничено workspace. Delete/write → backup |
| **Shell** | Любая команда shell с таймаутом и deny-list опасных паттернов |
| **Remote (LAN)** | SSH: добавить устройство → выполнить команду. Нужен `ssh` или `paramiko` |
| **Power** | Не уходить в idle-sleep (`wakepy` / native API). Display on/off отдельно |

### Про «работу в режиме сна»

| Режим | Что происходит |
|-------|----------------|
| Keep-awake ON, экран ON | ПК и монитор не спят |
| Keep-awake ON, экран OFF | CPU работает, монитор может погаснуть |
| Полный Sleep / Hibernate (S3/S4) | Процессы **останавливаются** — агент не может работать |

Полный сон ОС замораживает процессы. Реалистичный вариант «работать ночью» = **не давать системе уснуть**, опционально гасить только экран.

---

## Архитектура

```
agent_studio/
├── app.py                 # Streamlit UI
├── cli.py                 # Терминальный запуск
├── core/agent_runtime.py  # Цикл агента + вызов LLM + tools
├── tools/
│   ├── filesystem.py      # FS + backups
│   ├── shell.py           # bash/cmd
│   ├── remote.py          # SSH LAN
│   └── power.py           # keep-awake
├── workspace/             # рабочая папка агента
├── backups/               # автоматические копии
└── results/               # отчёты запусков
```

Агент вызывает инструменты через JSON-блоки ` ```tool {...} ``` ` в ответе модели (работает с любым LLM через LiteLLM).

---

## Безопасность

1. Пути только внутри `workspace` (иначе `PermissionError`)
2. Перед overwrite / delete — копия в `backups/`
3. Shell deny-list: `rm -rf /`, `mkfs`, shutdown/reboot и т.п.
4. SSH только на явно добавленные хосты
5. Ключи API — в `.env` или в UI (сессия браузера)

---

## Удалённые устройства

В задаче агенту можно написать:

```
Добавь устройство name=nas host=192.168.1.50 user=admin key_path=/home/me/.ssh/id_rsa
и выполни на нём df -h
```

Или проверить SSH во вкладке UI «Удалённые устройства».

На целевой машине должен быть включён SSH-сервер и доступ по ключу/паролю в вашей LAN.

---

## Требования

- Python 3.10+
- API-ключ хотя бы одного провайдера
- Опционально: `wakepy` (keep-awake), OpenSSH client, `paramiko`
