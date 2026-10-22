"""Multi-Agent Studio UI — keys persist to local .env"""
from __future__ import annotations
import os, sys, re
from datetime import datetime
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)

from core.agent_runtime import AgentRuntime
from core.orchestrator import Orchestrator, load_config, KEY_ENV

KEY_LABELS = [
    ("Anthropic", "ANTHROPIC_API_KEY"),
    ("OpenAI", "OPENAI_API_KEY"),
    ("Google", "GOOGLE_API_KEY"),
    ("xAI", "XAI_API_KEY"),
    ("DeepSeek", "DEEPSEEK_API_KEY"),
]
KEY_NAMES = [env for _, env in KEY_LABELS]


def load_keys_from_env() -> dict[str, str]:
    load_dotenv(ENV_PATH, override=True)
    return {k: os.getenv(k, "") or "" for k in KEY_NAMES}


def save_keys_to_env(keys: dict[str, str]) -> str:
    """Write API keys into .env without wiping other variables."""
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line_st = line.strip()
            if not line_st or line_st.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            existing[k] = v
    for k, v in keys.items():
        if v is not None and str(v).strip():
            existing[k] = str(v).strip()
        elif k in existing and not (v and str(v).strip()):
            # keep old value if user cleared the field accidentally? or remove?
            # keep previous if new is empty
            pass
    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    # refresh process env
    for k, v in existing.items():
        os.environ[k] = v
    return str(ENV_PATH)


st.set_page_config(page_title="Agent Studio", page_icon="🤖", layout="wide")
WORKSPACE, BACKUPS, RESULTS = ROOT / "workspace", ROOT / "backups", ROOT / "results"
for d in (WORKSPACE, BACKUPS, RESULTS):
    d.mkdir(exist_ok=True)

@st.cache_data
def get_cfg():
    try:
        return load_config(ROOT / "config" / "agents.yaml")
    except Exception as e:
        return {"error": str(e)}

cfg = get_cfg()
MODELS_MAP = cfg.get("models") or {
    "claude_sonnet": "anthropic/claude-sonnet-4-5",
    "gpt41": "openai/gpt-4.1",
    "grok": "xai/grok-4",
}
MODEL_CHOICES = list(MODELS_MAP.keys())
PIPELINES = cfg.get("pipelines") or {"single": {"steps": ["developer"], "description": "one"}}
AGENTS_CFG = cfg.get("agents") or {}
RECS = cfg.get("recommendations") or {}

with st.sidebar:
    st.header("🔑 API-ключи")
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = load_keys_from_env()

    for label, env in KEY_LABELS:
        st.session_state.api_keys[env] = st.text_input(
            label,
            value=st.session_state.api_keys.get(env, ""),
            type="password",
            key=f"k_{env}",
        )

    c_save, c_info = st.columns([1, 1])
    with c_save:
        if st.button("💾 Сохранить ключи", use_container_width=True):
            path = save_keys_to_env(st.session_state.api_keys)
            st.session_state["_keys_saved"] = path
            st.success("Сохранено")
    with c_info:
        if st.button("🔄 Из .env", use_container_width=True):
            st.session_state.api_keys = load_keys_from_env()
            st.rerun()

    if st.session_state.get("_keys_saved"):
        st.caption(f"Файл: `{ENV_PATH.name}` (не попадает в git)")

    # auto-save when any non-empty key is present and differs from file
    if st.checkbox("Автосохранение ключей", value=True, key="auto_save_keys"):
        disk = load_keys_from_env()
        cur = {k: (st.session_state.api_keys.get(k) or "").strip() for k in KEY_NAMES}
        if any(cur[k] and cur[k] != (disk.get(k) or "") for k in KEY_NAMES):
            save_keys_to_env(st.session_state.api_keys)

    st.divider()
    workspace_path = st.text_input("Workspace", value=str(WORKSPACE))
    max_steps = st.slider("Макс. шагов на агента", 5, 80, 25)
    shell_timeout = st.slider("Таймаут shell", 10, 300, 120)
    keep_awake = st.checkbox("Не давать ПК уснуть", value=True)
    keep_display = st.checkbox("Держать экран", value=False)

st.title("🤖 Multi-Agent Studio")
st.caption("Роли · оркестратор · свои ключи · файлы / shell / SSH")
tab_run, tab_agents, tab_fs, tab_remote, tab_help = st.tabs(
    ["▶️ Запуск", "👥 Агенты", "📁 Файлы", "🌐 SSH", "❓ Справка"]
)

with tab_agents:
    st.subheader("Роли и модели")
    if "agent_overrides" not in st.session_state:
        st.session_state.agent_overrides = {}
    for aid, ac in AGENTS_CFG.items():
        with st.expander(f"{ac.get('name', aid)} (`{aid}`)", expanded=(aid == "developer")):
            st.caption(ac.get("description", ""))
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                enabled = st.checkbox("Вкл", value=bool(ac.get("enabled", True)), key=f"en_{aid}")
            with c2:
                dm = ac.get("model", "claude_sonnet")
                if dm not in MODEL_CHOICES:
                    dm = MODEL_CHOICES[0]
                model_key = st.selectbox(
                    "Модель",
                    MODEL_CHOICES,
                    index=MODEL_CHOICES.index(dm),
                    key=f"model_{aid}",
                    format_func=lambda k: f"{k} → {MODELS_MAP.get(k, k)}",
                )
            with c3:
                temp = st.slider(
                    "Temp", 0.0, 1.0, float(ac.get("temperature", 0.2)), 0.05, key=f"temp_{aid}"
                )
            rec = RECS.get(aid) or []
            if rec:
                st.info("⭐ Рекомендуется: " + ", ".join(f"{r} ({MODELS_MAP.get(r, r)})" for r in rec))
            tools = ac.get("tools")
            st.caption(
                "Инструменты: "
                + ("нет (план)" if tools == [] else (", ".join(tools) if tools else "все"))
            )
            st.session_state.agent_overrides[aid] = {
                "enabled": enabled,
                "model": model_key,
                "temperature": temp,
            }
    st.divider()
    pipe_names = list(PIPELINES.keys())
    default_pipe = cfg.get("default_pipeline", "full")
    if default_pipe not in pipe_names:
        default_pipe = pipe_names[0] if pipe_names else "single"
    pipeline_name = st.selectbox(
        "Пайплайн",
        pipe_names,
        index=pipe_names.index(default_pipe) if default_pipe in pipe_names else 0,
        format_func=lambda n: f"{n}: {PIPELINES[n].get('description', '')}",
        key="pipeline_select",
    )
    steps = PIPELINES.get(pipeline_name, {}).get("steps", [])
    active = [
        s
        for s in steps
        if st.session_state.agent_overrides.get(s, {}).get(
            "enabled", AGENTS_CFG.get(s, {}).get("enabled", True)
        )
    ]
    st.success("Цепочка: " + " → ".join(active) if active else "Нет активных агентов")

with tab_run:
    pipeline_name = st.session_state.get("pipeline_select", cfg.get("default_pipeline", "full"))
    steps = PIPELINES.get(pipeline_name, {}).get("steps", ["developer"])
    active = [
        s
        for s in steps
        if st.session_state.get("agent_overrides", {}).get(s, {}).get(
            "enabled", AGENTS_CFG.get(s, {}).get("enabled", True)
        )
    ]
    st.markdown(f"**Пайплайн:** `{pipeline_name}` · **Цепочка:** {' → '.join(active) or '—'}")
    task = st.text_area(
        "Задача",
        height=150,
        placeholder="Создай hello.py, запусти, сохрани вывод в result.txt",
    )
    run_btn = st.button("🚀 Запустить команду агентов", type="primary", use_container_width=True)
    log_box, result_box = st.empty(), st.empty()
    if run_btn:
        if not task.strip():
            st.error("Введите задачу")
        elif not active:
            st.error("Включите агентов на вкладке «Агенты»")
        else:
            # ensure keys on disk before run
            save_keys_to_env(st.session_state.api_keys)
            logs = []

            def log_fn(msg):
                logs.append(msg)
                log_box.code("\n".join(logs[-60:]), language="text")

            orch = Orchestrator(
                workspace=workspace_path,
                backup_dir=str(BACKUPS),
                api_keys=st.session_state.api_keys,
                config=cfg,
                max_steps=max_steps,
                shell_timeout=shell_timeout,
                log_fn=log_fn,
                overrides=st.session_state.get("agent_overrides", {}),
                pipeline_name=pipeline_name,
            )
            power_rt = None
            if keep_awake:
                power_rt = AgentRuntime(
                    workspace=workspace_path,
                    backup_dir=str(BACKUPS),
                    model="openai/gpt-4o",
                    api_key=st.session_state.api_keys.get("OPENAI_API_KEY") or "x",
                    allowed_tools=[],
                    role_name="power",
                )
                log_fn(power_rt.power.start("display" if keep_display else "system"))
            try:
                with st.spinner("Агенты работают..."):
                    result = orch.run(task.strip())
                result_box.markdown("### Результат\n\n" + result)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out = RESULTS / f"run_{ts}.md"
                out.write_text(
                    f"# Задача\n\n{task}\n\n# Лог\n\n"
                    + "\n".join(logs)
                    + f"\n\n# Результат\n\n{result}",
                    encoding="utf-8",
                )
                st.download_button(
                    "📥 Скачать отчёт",
                    data=out.read_text(encoding="utf-8"),
                    file_name=out.name,
                )
            except Exception as e:
                st.exception(e)
            finally:
                if keep_awake and power_rt:
                    log_fn(power_rt.power.stop())

with tab_fs:
    st.subheader("Workspace")
    try:
        from tools.filesystem import WorkspaceFS

        fs = WorkspaceFS(workspace_path, BACKUPS)
        st.code(fs.list_dir("."), language="text")
        path = st.text_input("Файл", value="")
        if path and st.button("Читать"):
            st.code(fs.read_file(path), language="text")
    except Exception as e:
        st.error(str(e))

with tab_remote:
    st.subheader("SSH")
    c1, c2, c3 = st.columns(3)
    with c1:
        r_name = st.text_input("Имя", value="device1")
        r_host = st.text_input("Host", value="192.168.1.10")
    with c2:
        r_user = st.text_input("User", value="pi")
        r_port = st.number_input("Port", value=22, min_value=1, max_value=65535)
    with c3:
        r_key = st.text_input("SSH key", value="")
        r_cmd = st.text_input("Cmd", value="uname -a")
    if st.button("SSH run"):
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
### Роли
| Роль | Задача | Tools |
|------|--------|-------|
| Менеджер | План | нет |
| Исследователь | Факты | read/search |
| Архитектор | Структура | read |
| Разработчик | Код/shell/SSH | все |
| Ревьюер | Проверка | read+shell |
| Тестировщик | Тесты | read+shell |

### Пайплайны
- **full** — manager → researcher → architect → developer → reviewer
- **code_only** — developer → reviewer
- **research_code** — researcher → developer → reviewer
- **single** — developer

### Ключи
Вставленные API-ключи сохраняются в локальный файл `.env` (он в `.gitignore` и не уходит на GitHub).
Кнопка **Сохранить ключи** или автосохранение / при запуске задачи.

Конфиг: `config/agents.yaml`. CLI: `python cli.py --pipeline code_only "задача"`
"""
    )
