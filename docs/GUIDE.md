# Справочник Multi-Agent Studio

Локальное приложение на Streamlit. Роли идут по пайплайну, модели вызываются через LiteLLM, ключи остаются в `.env`.

Короткий запуск описан в [README](../README.md). Здесь подробности.

## Содержание

- [Установка и неполадки](#install)
- [Ключи API](#keys)
- [Каталог моделей](#catalog)
- [Агенты](#agents)
- [Файлы](#files)
- [SSH](#ssh)
- [Темы](#themes)
- [Настройки](#settings)
- [Разработка и CI](#dev)

<a id="install"></a>

## Установка и неполадки

Нужен Python 3. Команда `python` или, на Windows, `py` должна быть в `PATH`.

### Windows

1. Установите [Git](https://git-scm.com/download/win) и Python 3.
2. Клонируйте репозиторий и запустите `start.bat`.

`start.bat` делает три шага: `git pull`, виртуальное окружение `.venv`, установка зависимостей, затем Streamlit. Только подготовка, без окна:

```bat
start.bat setup
```

Git хранит `start.bat` в UTF-8, а при `git clone` и `git pull` записывает рабочую копию в кодировке CP866 и с концами строк CRLF. Это кодировка русской консоли. `cmd.exe` делит batch-файл по паре CR+LF. Если в файле только LF, на каждой строке теряется байт: `echo` превращается в `cho` или `ho`, `https` в `ttps`, кириллица в `�нимание`. Виртуальное окружение при этом не создаётся, хотя глобальный Streamlit может всё равно запуститься.

Поэтому:

1. Клонируйте репозиторий. Не скачивайте ZIP с GitHub: в архиве нет преобразования `.gitattributes`, и `start.bat` приходит с LF.
2. Не пересохраняйте `start.bat` как UTF-8 и не добавляйте `chcp 65001`. После этой команды парсер cmd путает байты и символы.
3. Если архив уже распакован, запустите студию вручную:

   ```bat
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m streamlit run app.py
   ```

Сообщение «The system cannot find the path specified» на `.venv\Scripts\activate.bat` значит, что окружение не создалось. Сначала должен отработать `python -m venv`.

### macOS и Linux

```bash
git clone https://github.com/Bot2217/Multi-Agent-Studio.git
cd Multi-Agent-Studio
chmod +x start.sh
./start.sh
```

`start.sh` и `run.sh` остаются с окончаниями LF. Так и должно быть: для bash CRLF ломает shebang.

### Без скрипта и из командной строки

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Один запуск без окна:

```bash
python cli.py --pipeline code_only "Создай hello.py и запусти"
```

Ключи CLI читаются из `.env`.

<a id="keys"></a>

## Ключи API

Скопируйте `.env.example` в `.env` или вставьте ключи в разделе «Настройки» и нажмите «Сохранить ключи». Пустое поле при сохранении удаляет ключ из `.env`. Файл `.env` не коммитится.

| Переменная | Провайдер | Зачем |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Google AI Studio | Gemini. У части моделей есть free tier |
| `OPENROUTER_API_KEY` | OpenRouter | модели `:free` и роутер `openrouter/free` |
| `ANTHROPIC_API_KEY` | Anthropic | Claude. Бесплатного API нет |
| `OPENAI_API_KEY` | OpenAI | GPT. Бесплатного API нет |
| `XAI_API_KEY` | xAI | Grok |
| `DEEPSEEK_API_KEY` | DeepSeek | `deepseek-flash` и `deepseek-v4-pro` |
| `GROQ_API_KEY` | Groq | GPT-OSS и Qwen |
| `MISTRAL_API_KEY` | Mistral | Small, Large, Codestral |
| `CEREBRAS_API_KEY` | Cerebras | GPT-OSS и Qwen. Цена токена в каталоге unknown |
| `OLLAMA_API_BASE` | Ollama | локальные модели. Ключ не нужен. По умолчанию `http://localhost:11434` |

Если для выбранной модели ключа нет, шаг пропускается и это написано в итоге. Локальный Ollama ключ не требует.

Не отправляйте в бесплатные API то, что нельзя отдавать провайдеру. У free tier Google контент может использоваться для улучшения продуктов. У части бесплатных маршрутов OpenRouter условия другие. Это указано в карточке модели.

<a id="catalog"></a>

## Каталог моделей

Список в приложении, раздел «Модели». Источник данных: `config/models_catalog.yaml`. Цены сверены 9 ноября 2026. Провайдер может изменить прайс раньше, чем обновится файл.

| Бейдж | Что это |
| --- | --- |
| Free | $0 за токены API |
| Free tier | Есть бесплатная квота. В таблице рядом платный standard, когда квота кончилась |
| Paid | Платный API, USD за 1M токенов входа и выхода |
| Local | Веса на вашем компьютере через Ollama. $0 за токены API |
| unknown | Официальную цифру на дату сверки подтвердить не удалось |

Для Gemini указан standard-тариф. У GPT-6 и Grok длинный контекст дороже короткого: оговорка в `price_note`. У DeepSeek в таблице off-peak цена без кэша, в пиковые часы она удваивается. У Claude Haiku 5.5 промпт длиннее 100k токенов тарифицируется выше. Где окно контекста в источнике не названо числом, стоит unknown.

Mistral Moderation 2 бесплатная, но это классификатор, не чат. В список ролей она не попадает.

Локальные теги нужно скачать, например `ollama pull gemma4`. Карточки: [ollama.com/library](https://ollama.com/library).

| Модель | Провайдер | ID | Доступ | Цена, USD / 1M in → out | Контекст | Проверено |
| --- | --- | --- | --- | --- | --- | --- |
| Gemini 2.5 Flash-Lite | Google | `gemini/gemini-2.5-flash-lite` | Free tier | $0.10 / $0.40 за 1M (paid); free tier $0 | unknown | 2026-11-09 |
| Gemini 2.5 Flash | Google | `gemini/gemini-2.5-flash` | Free tier | $0.30 / $2.50 за 1M (paid); free tier $0 | 1M | 2026-11-09 |
| Gemini 2.5 Pro | Google | `gemini/gemini-2.5-pro` | Free tier | $1.25 / $10 за 1M (paid); free tier $0 | unknown | 2026-11-09 |
| Gemini 3.5 Flash-Lite | Google | `gemini/gemini-3.5-flash-lite` | Free tier | $0.30 / $2.50 за 1M (paid); free tier $0 | unknown | 2026-11-09 |
| Gemini 3.8 Flash | Google | `gemini/gemini-3.8-flash` | Free tier | $0.75 / $3.75 за 1M (paid); free tier $0 | unknown | 2026-11-09 |
| Gemini 4 Argon | Google | `gemini/gemini-4-argon` | Paid | $2 / $10 за 1M | unknown | 2026-11-09 |
| GPT-4o mini | OpenAI | `openai/gpt-4o-mini` | Paid | $0.15 / $0.60 за 1M | 128K | 2026-11-09 |
| GPT-4o | OpenAI | `openai/gpt-4o` | Paid | $2.50 / $10 за 1M | 128K | 2026-11-09 |
| GPT-4.1 | OpenAI | `openai/gpt-4.1` | Paid | $2 / $8 за 1M | 1 047 576 | 2026-11-09 |
| GPT-5 mini | OpenAI | `openai/gpt-5-mini` | Paid | $0.25 / $2 за 1M | 400K | 2026-11-09 |
| GPT-5 | OpenAI | `openai/gpt-5` | Paid | $1.25 / $10 за 1M | 400K | 2026-11-09 |
| GPT-6 Luna | OpenAI | `openai/gpt-6-luna` | Paid | $0.10 / $0.50 за 1M | 1.05M | 2026-11-09 |
| GPT-6.1 Terra | OpenAI | `openai/gpt-6.1-terra` | Paid | $1 / $5 за 1M | 1.05M | 2026-11-09 |
| GPT-6.1 Sol | OpenAI | `openai/gpt-6.1-sol` | Paid | $2 / $10 за 1M | 1.05M | 2026-11-09 |
| GPT-6 Astra | OpenAI | `openai/gpt-6-astra` | Paid | $10 / $50 за 1M | 1.05M | 2026-11-09 |
| Claude Haiku 4.5 | Anthropic | `anthropic/claude-haiku-4-5` | Paid | $1 / $5 за 1M | unknown | 2026-11-09 |
| Claude Sonnet 4.5 | Anthropic | `anthropic/claude-sonnet-4-5` | Paid | $3 / $15 за 1M | unknown | 2026-11-09 |
| Claude Opus 4.5 | Anthropic | `anthropic/claude-opus-4-5` | Paid | $5 / $25 за 1M | unknown | 2026-11-09 |
| Claude Haiku 5.5 | Anthropic | `anthropic/claude-haiku-5-5` | Paid | $0.10 / $0.50 за 1M | 1M | 2026-11-09 |
| Claude Sonnet 5.5 | Anthropic | `anthropic/claude-sonnet-5-5` | Paid | $2 / $10 за 1M | 1M | 2026-11-09 |
| Claude Opus 5.5 | Anthropic | `anthropic/claude-opus-5-5` | Paid | $4 / $20 за 1M | 1M | 2026-11-09 |
| Claude Fable 5.2 | Anthropic | `anthropic/claude-fable-5-2` | Paid | $8 / $40 за 1M | 1M | 2026-11-09 |
| Grok 4.7 | xAI | `xai/grok-4.7` | Paid | $2 / $6 за 1M | 500K | 2026-11-09 |
| Grok 4.5 | xAI | `xai/grok-4.5` | Paid | $2 / $6 за 1M | 500K | 2026-11-09 |
| Grok 4.3 | xAI | `xai/grok-4.3` | Paid | $1.25 / $2.50 за 1M | 1M | 2026-11-09 |
| Grok Build 0.1 | xAI | `xai/grok-build-0.1` | Paid | $1 / $2 за 1M | 256K | 2026-11-09 |
| DeepSeek Flash | DeepSeek | `deepseek/deepseek-flash` | Paid | $0.15 / $0.60 за 1M | 1M | 2026-11-09 |
| DeepSeek V4 Pro | DeepSeek | `deepseek/deepseek-v4-pro` | Paid | $0.66 / $1.98 за 1M | 1M | 2026-11-09 |
| GPT-OSS 20B (Groq) | Groq | `groq/openai/gpt-oss-20b` | Paid | $0.075 / $0.30 за 1M | 131 072 | 2026-11-09 |
| GPT-OSS 120B (Groq) | Groq | `groq/openai/gpt-oss-120b` | Paid | $0.15 / $0.60 за 1M | 131 072 | 2026-11-09 |
| Qwen 3.8 27B (Groq) | Groq | `groq/qwen/qwen3.8-27b` | Paid | $0.80 / $4 за 1M | 131 072 | 2026-11-09 |
| Mistral Small 4 | Mistral | `mistral/mistral-small-2603` | Paid | $0.15 / $0.60 за 1M | 256K | 2026-11-09 |
| Mistral Large 4 | Mistral | `mistral/mistral-large-4` | Paid | $0.70 / $2.10 за 1M | 1M | 2026-11-09 |
| Codestral | Mistral | `mistral/codestral-2508` | Paid | $0.30 / $0.90 за 1M | 128K | 2026-11-09 |
| Mistral Moderation 2 | Mistral | `mistral/mistral-moderation-2603` | Free | $0 / $0 за 1M | 128K | 2026-11-09 |
| GPT-OSS 120B (Cerebras) | Cerebras | `cerebras/gpt-oss-120b` | Paid | unknown | 131K paid / 65K trial | 2026-11-09 |
| Qwen 3.8 27B (Cerebras) | Cerebras | `cerebras/qwen-3.8-27b` | Paid | unknown | 128K paid / 64K trial | 2026-11-09 |
| Nemotron 3 Ultra (free) | OpenRouter | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | Free | $0 / $0 за 1M | 1 000 000 | 2026-11-09 |
| Nemotron 3.5 Lightning (free) | OpenRouter | `openrouter/nvidia/nemotron-3.5-lightning:free` | Free | $0 / $0 за 1M | 1 000 000 | 2026-11-09 |
| Nemotron 3.5 Super VL (free) | OpenRouter | `openrouter/nvidia/nemotron-3.5-super-vl:free` | Free | $0 / $0 за 1M | 1 000 000 | 2026-11-09 |
| Nemotron 3 Nano Omni (free) | OpenRouter | `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | Free | $0 / $0 за 1M | 256 000 | 2026-11-09 |
| Gemma 4 31B (free) | OpenRouter | `openrouter/google/gemma-4-31b-it:free` | Free | $0 / $0 за 1M | 262 144 | 2026-11-09 |
| Gemma 4 26B A4B (free) | OpenRouter | `openrouter/google/gemma-4-26b-a4b-it:free` | Free | $0 / $0 за 1M | 262 144 | 2026-11-09 |
| North Mini Code (free) | OpenRouter | `openrouter/cohere/north-mini-code:free` | Free | $0 / $0 за 1M | 256 000 | 2026-11-09 |
| Flint v1 (free) | OpenRouter | `openrouter/recursive/flint-v1.0:free` | Free | $0 / $0 за 1M | 262 144 | 2026-11-09 |
| Xing4.0 29B (free) | OpenRouter | `openrouter/xingchen-agi/xing4.0-29b-a4b:free` | Free | $0 / $0 за 1M | 262 144 | 2026-11-09 |
| Dots3-Note Preview (free) | OpenRouter | `openrouter/dots-studio/dots-3-note-preview:free` | Free | $0 / $0 за 1M | 512 000 | 2026-11-09 |
| LFM3 1.7B (free) | OpenRouter | `openrouter/liquid/lfm-3-1.7b:free` | Free | $0 / $0 за 1M | 262 144 | 2026-11-09 |
| LFM 2.5 2.6B (free) | OpenRouter | `openrouter/liquid/lfm-2.5-2.6b:free` | Free | $0 / $0 за 1M | 65 536 | 2026-11-09 |
| OpenRouter Free Router | OpenRouter | `openrouter/openrouter/free` | Free | $0 / $0 за 1M | 200 000 | 2026-11-09 |
| Crouton Alpha | OpenRouter | `openrouter/stealth/crouton-alpha` | Free | $0 / $0 за 1M | 1 048 576 | 2026-11-09 |
| Gemma 4 (Ollama) | Ollama | `ollama_chat/gemma4` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| Llama 3.2 (Ollama) | Ollama | `ollama_chat/llama3.2` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| Qwen 3 (Ollama) | Ollama | `ollama_chat/qwen3` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| Qwen 3.5 (Ollama) | Ollama | `ollama_chat/qwen3.5` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| Qwen 2.5 Coder (Ollama) | Ollama | `ollama_chat/qwen2.5-coder` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| DeepSeek R1 (Ollama) | Ollama | `ollama_chat/deepseek-r1` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| Phi-4 (Ollama) | Ollama | `ollama_chat/phi4` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |
| Mistral (Ollama) | Ollama | `ollama_chat/mistral` | Local | $0 / $0 за 1M | unknown | 2026-11-09 |

<a id="agents"></a>

## Агенты

Раздел «Агенты». У роли есть выключатель, модель и температура. Подсказка «С чего начать» берётся из `config/agents.yaml`. Кнопка «Сохранить роли» пишет выбор в `user_settings.json`. «Вернуть модели из agents.yaml» сбрасывает переопределения.

| Роль | По умолчанию | Задача |
| --- | --- | --- |
| Менеджер | Gemini 3.8 Flash | разбить задачу и собрать итог, без инструментов |
| Исследователь | Gemini 2.5 Flash | читать файлы и собирать факты |
| Архитектор | Gemini 2.5 Pro | план файлов и интерфейсов |
| Разработчик | Gemini 3.8 Flash | код, shell, при необходимости SSH |
| Ревьюер | Gemini 2.5 Pro | замечания по коду |
| Тестировщик | Gemini 2.5 Flash-Lite | выключен, пока не включите |

Пайплайн выбирается в «Запуск». По умолчанию `code_only`.

| Пайплайн | Шаги |
| --- | --- |
| `full` | менеджер, исследователь, архитектор, разработчик, ревьюер |
| `code_only` | разработчик, ревьюер |
| `research_code` | исследователь, разработчик, ревьюер |
| `single` | разработчик |

Промпты ролей лежат в `config/agents.yaml`. Каталог цен побеждает, если алиас модели в yaml разошёлся с `models_catalog.yaml`.

<a id="files"></a>

## Файлы

Раздел «Файлы» показывает выбранную папку. Агенты читают и пишут только внутри неё. Соседняя папка с тем же префиксом имени (`workspace` и `workspace_evil`) тоже снаружи.

Перед перезаписью и удалением копия кладётся в `backups/`.

Shell режет опасные шаблоны: `rm` по `/` и домашним каталогам, `curl` или `wget` в shell, Windows `del /s`, `rd /s` и `format` диска. Это ограничитель, не песочница. Кнопка «Остановить» прерывает такую команду (группа процессов) и перестаёт ждать ответ модели, который уже отправлен провайдеру.

<a id="ssh"></a>

## SSH

Раздел «SSH» выполняет команду на компьютере, который вы указали. Добавляйте только свои машины. Пароль форма не спрашивает: укажите путь к ключу. Пустые имя, хост или команда не отправляются.

<a id="themes"></a>

## Темы

Тема и палитра выбираются отдельно и пишутся в `user_settings.json`.

- **Тема** — переключатель в боковой колонке: «Авто» (как в системе), «Светлая», «Тёмная». По умолчанию «Авто».
- **Палитра** — в «Настройках», блок «Оформление». По умолчанию «Графит».

| Палитра | Характер |
| --- | --- |
| Графит | уголь `#0d0e12` и лаймовый акцент в тёмной теме, светло-серый фон и зелёный акцент в светлой |
| Тёплая | исходные цвета студии: бумага и красный акцент в светлой теме, тёмная мастерская с латунью в тёмной |

Старые значения темы открываются так: `night` и `pine` — тёмная «Графит», `paper` — светлая «Тёплая», `ember` и `kiln` — тёмная «Тёплая». После первого запуска в `user_settings.json` записываются уже новые `theme` и `palette`.

Текст набран Inter, код и ID моделей — JetBrains Mono. Размер заголовка задаётся через `clamp()`. Отступы 16 и 24 px, скругление 12–20 px.

<a id="settings"></a>

## Настройки

| Что | Куда |
| --- | --- |
| Ключи | `.env` |
| Роли, режим, папка, тема, палитра, ползунки | `user_settings.json` |
| Промпты и порядок ролей | `config/agents.yaml` |
| Цены и ID моделей | `config/models_catalog.yaml` |
| Отчёты запусков | `results/` |
| Копии перед удалением и перезаписью | `backups/` |

Раздел «Настройки», блок «Запуск»: шагов на одну роль, лимит на команду, запрет ухода в сон, адрес Ollama. Изменения сохраняются сразу.

Сон на время задачи только блокирует idle-сон. Настоящий сон с замороженным процессом здесь невозможен.

<a id="dev"></a>

## Разработка и CI

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
ruff format --check .
ruff check .
pytest -q
```

GitHub Actions на Ubuntu гоняет те же три команды. Отдельный job на `windows-latest` выполняет `start.bat setup` и проверяет, что в `.venv` импортируется Streamlit.

Чтобы добавить модель:

1. Допишите запись в `config/models_catalog.yaml`: ID, провайдер, `billing`, цена входа и выхода за 1M или `price_status: unknown`, `source`, `last_verified`.
2. Не ставьте цену по памяти. Если страницы нет или цифры нет, пишите `unknown`.
3. Если есть и free tier, и платный тариф, `billing: freemium`, а в полях цены платный standard.
4. Запустите проверки выше. Тест каталога сверяет обязательные поля и требует, чтобы имя и ID модели были в этом справочнике.
