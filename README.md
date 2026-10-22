# Multi-Agent Studio

Локальная мультиагентная система с оркестратором, своими API-ключами и инструментами уровня Claude Code.

## Возможности

- **Роли**: менеджер, исследователь, архитектор, разработчик, ревьюер, тестировщик
- **Пайплайны**: full / code_only / research_code / single
- **Модели на роль**: Claude, GPT, Gemini, Grok, DeepSeek (через LiteLLM)
- **Рекомендации моделей** в UI (⭐)
- Файлы с **backup**, shell, SSH по LAN, keep-awake

## Быстрый старт

```bash
git clone https://github.com/Bot2217/Multi-Agent-Studio.git
cd Multi-Agent-Studio
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # вставьте ключи
streamlit run app.py
```

CLI:

```bash
python cli.py --pipeline code_only "Создай hello.py и запусти"
```

## Конфигурация

Файл `config/agents.yaml`:

- `agents` — роли, промпты, tools, model, temperature, enabled
- `models` — алиасы → litellm id
- `recommendations` — рекомендуемые модели по ролям
- `pipelines` — порядок шагов

В UI вкладка **«Агенты и роли»**: вкл/выкл, модель, temperature.

## Обновление с GitHub

```bash
git pull origin main
```

## Безопасность

- Работа только внутри `workspace/`
- Backup перед overwrite/delete
- Deny-list опасных shell-команд
- SSH только на явно добавленные хосты
