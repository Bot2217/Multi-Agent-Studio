"""
Agent Studio — локальный агент уровня Claude Code.
Файлы + backup, shell, SSH по локальной сети, keep-awake.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# project root on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from core.agent_runtime import AgentRuntime

st.set_page_config(
    page_title="Agent Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- defaults ----------
WORKSPACE = ROOT / "workspace"
BACKUPS = ROOT / "backups"
RESULTS = ROOT / "results"
WORKSPACE.mkdir(exist_ok=True)
BACKUPS.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)

MODELS = {
    "Claude Sonnet": "anthropic/claude-sonnet-4-5",
    "Claude Opus": "anthropic/claude-opus-4",
    "GPT-4.1": "openai/gpt-4.1",
    "GPT-4o": "openai/gpt-4o",
    "Gemini 2.5 Pro": "gemini/gemini-2.5-pro",
    "Grok 4": "xai/grok-4",
    "DeepSeek": "deepseek/deepseek-chat",
}

KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def provider_of(model_id: str) -> str:
    if model_id.startswith("anthropic"):
        return "anthropic"
    if model_id.startswith("openai"):
        return "openai"
    if model_id.startswith("gemini"):
        return "gemini"
    if model_id.startswith("xai"):
        return "xai"
    if model_id.startswith("deepseek"):
        return "deepseek"
    return "openai"


# ---------- sidebar ----------
with st.sidebar:
    st.header("🔑 API-ключи")
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = {
            k: os.getenv(k, "")
            for k in [
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "GOOGLE_API_KEY",
                "XAI_API_KEY",
                "DEEPSEEK_API_KEY",
            ]
        }

    for label, env in [
        ("Anthropic", "ANTHROPIC_API_KEY"),
        ("OpenAI", "OPENAI_API_KEY"),
        ("Google", "GOOGLE_API_KEY"),
        ("xAI", "XAI_API_KEY"),
        ("DeepSeek", "DEEPSEEK_API_KEY"),
    ]:
        st.session_state.api_keys[env] = st.text_input(
            label, value=st.session_state.api_keys[env], type="password", key=f"k_{env}"
        )

    st.divider()
    st.header("⚙️ Агент")
    model_name = st.selectbox("Модель", list(MODELS.keys()), index=0)
    model_id = MODELS[model_name]
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    max_steps = st.slider("Макс. шагов", 5, 80, 40)
    shell_timeout = st.slider("Таймаут shell (сек)", 10, 300, 120)

    st.divider()
    st.header("💻 Workspace")
    workspace_path = st.text_input("Путь workspace", value=str(WORKSPACE))
    st.caption(f"Бэкапы: {BACKUPS}")

    st.divider()
    st.header("🔋 Питание")
    keep_awake = st.checkbox("Не давать ПК уснуть во время работы", value=True)
    keep_display = st.checkbox("Держать экран включённым", value=False)
    st.caption(
        "«Работа в режиме сна» = система не засыпает, экран может погаснуть "
        "(если галочка экрана выключена). Полный S3-сон останавливает процессы."
    )

# ---------- main ----------
st.title("🤖 Agent Studio")
st.caption(
    "Локальный агент: файлы с бэкапами · shell · SSH по LAN · keep-awake"
)

tab_run, tab_fs, tab_remote, tab_help = st.tabs(
    ["Запуск", "Файлы workspace", "Удалённые устройства", "Справка"]
)

with tab_run:
    task = st.text_area(
        "Задача",
        height=160,
        placeholder=(
            "Пример:\n"
            "Создай в workspace скрипт hello.py, который печатает Hello, "
            "запусти его через shell и сохрани вывод в result.txt"
        ),
    )
    col_a, col_b = st.columns([1, 3])
    with col_a:
        run_btn = st.button("🚀 Запустить агента", type="primary", use_container_width=True)

    log_box = st.empty()
    result_box = st.empty()

    if run_btn:
        if not task.strip():
            st.error("Введите задачу")
        else:
            prov = provider_of(model_id)
            env_key = KEY_ENV.get(prov, "OPENAI_API_KEY")
            api_key = st.session_state.api_keys.get(env_key) or os.getenv(env_key)
            if not api_key:
                st.error(f"Нет API-ключа для {prov} ({env_key})")
            else:
                logs: list[str] = []

                def log_fn(msg: str):
                    logs.append(msg)
                    log_box.code("\n".join(logs[-40:]), language="text")

                runtime = AgentRuntime(
                    workspace=workspace_path,
                    backup_dir=str(BACKUPS),
                    model=model_id,
                    api_key=api_key,
                    temperature=temperature,
                    max_steps=max_steps,
                    shell_timeout=shell_timeout,
                    log_fn=log_fn,
                )

                power_msg = ""
                if keep_awake:
                    mode = "display" if keep_display else "system"
                    power_msg = runtime.power.start(mode)
                    log_fn(power_msg)

                try:
                    with st.spinner("Агент работает..."):
                        result = runtime.run(task.strip())
                    result_box.markdown("### Результат")
                    result_box.markdown(result)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out = RESULTS / f"run_{ts}.md"
                    out.write_text(f"# Задача\n\n{task}\n\n# Лог\n\n" + "\n".join(logs) + f"\n\n# Результат\n\n{result}", encoding="utf-8")
                    st.download_button("📥 Скачать отчёт", data=out.read_text(encoding="utf-8"), file_name=out.name)
                except Exception as e:
                    st.exception(e)
                finally:
                    if keep_awake:
                        log_fn(runtime.power.stop())

with tab_fs:
    st.subheader("Содержимое workspace")
    if st.button("Обновить список"):
        st.session_state["_fs_refresh"] = True
    try:
        from tools.filesystem import WorkspaceFS
        fs = WorkspaceFS(workspace_path, BACKUPS)
        st.code(fs.list_dir("."), language="text")
        path = st.text_input("Прочитать файл", value="")
        if path and st.button("Читать"):
            st.code(fs.read_file(path), language="text")
    except Exception as e:
        st.error(str(e))

with tab_remote:
    st.subheader("Устройства в локальной сети (SSH)")
    st.markdown(
        "Агент может сам вызывать `remote_add` / `remote_run`. "
        "Здесь можно заранее проверить подключение."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        r_name = st.text_input("Имя", value="device1")
        r_host = st.text_input("Host / IP", value="192.168.1.10")
    with c2:
        r_user = st.text_input("User", value="pi")
        r_port = st.number_input("Port", value=22, min_value=1, max_value=65535)
    with c3:
        r_key = st.text_input("SSH key path (опционально)", value="")
        r_cmd = st.text_input("Команда", value="uname -a")

    if st.button("Выполнить по SSH"):
        from tools.remote import RemoteManager, RemoteDevice
        rm = RemoteManager()
        rm.add_device(
            RemoteDevice(
                name=r_name,
                host=r_host,
                user=r_user,
                port=int(r_port),
                key_path=r_key or None,
            )
        )
        st.code(rm.run_ssh(r_name, r_cmd), language="text")

with tab_help:
    st.markdown(
        """
### Возможности

| Функция | Как работает |
|---------|----------------|
| Чтение / запись / удаление файлов | Только внутри workspace; перед изменением/удалением — **backup** в `backups/` |
| Shell / bash / cmd | `run_shell`, таймаут, блок опасных паттернов |
| Другие устройства в LAN | SSH: `remote_add` + `remote_run` (нужен OpenSSH или paramiko) |
| Не уходить в сон | `power_start` / галочка в сайдбаре (wakepy / native API) |
| «Режим сна» | Система **не** засыпает, экран может погаснуть. Полный sleep (S3) останавливает процессы — агент там не работает |

### Безопасность

- Пути ограничены workspace (и extra roots, если добавите)
- Перед overwrite/delete — копия в `backups/`
- Опасные shell-команды режутся deny-list
- SSH только на явно добавленные хосты

### Запуск из терминала (без UI)

```bash
python cli.py "Создай файл test.txt с текстом hello"
```
        """
    )
