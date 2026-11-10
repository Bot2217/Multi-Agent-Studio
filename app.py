"""Multi-Agent Studio — локальный интерфейс ролей, пайплайнов и каталога моделей."""

from __future__ import annotations

import html
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core.agent_runtime import AgentRuntime
from core.catalog import (
    BILLING_BADGE,
    format_price,
    is_free_option,
    load_models_catalog,
    missing_credentials,
    model_label,
    runnable_models,
    sorted_model_keys,
)
from core.icons import icon
from core.orchestrator import Orchestrator, load_config
from core.themes import (
    SCREENS,
    THEME_ORDER,
    THEMES,
    resolve_screen,
    resolve_theme,
    theme_stylesheet,
)
from core.ui_helpers import (
    KEY_NAMES,
    load_keys_from_env,
    load_user_settings,
    preset_paths,
    save_keys_to_env,
    save_user_settings,
)

KEY_LABELS = [
    ("Anthropic", "ANTHROPIC_API_KEY", "Claude"),
    ("OpenAI", "OPENAI_API_KEY", "GPT"),
    ("Google", "GOOGLE_API_KEY", "Gemini, есть free tier"),
    ("xAI", "XAI_API_KEY", "Grok"),
    ("DeepSeek", "DEEPSEEK_API_KEY", "DeepSeek"),
    ("Groq", "GROQ_API_KEY", "открытые модели Groq"),
    ("OpenRouter", "OPENROUTER_API_KEY", "модели :free"),
    ("Mistral", "MISTRAL_API_KEY", "Mistral и Codestral"),
    ("Cerebras", "CEREBRAS_API_KEY", "Cerebras"),
]

DEFAULT_WS = ROOT / "workspace"
BACKUPS = ROOT / "backups"
RESULTS = ROOT / "results"
for folder in (DEFAULT_WS, BACKUPS, RESULTS):
    folder.mkdir(exist_ok=True)

BILLING_FILTERS = [
    ("Все", "all"),
    ("Бесплатные", "free"),
    ("Платные", "paid"),
    ("Локальные", "local"),
    ("Цена unknown", "unknown"),
]


def inject_css() -> None:
    st.markdown(theme_stylesheet(st.session_state.get("theme")), unsafe_allow_html=True)


def slip(title: str, text: str) -> None:
    st.markdown(
        f'<div class="slip"><p class="kicker">{html.escape(title)}</p><p>{html.escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def step(number: str, title: str, hint: str = "", icon_name: str = "check") -> None:
    hint_html = f'<p class="step-hint">{html.escape(hint)}</p>' if hint else ""
    st.markdown(
        (
            '<div class="step">'
            f'<span class="step-no">{html.escape(number)}</span>'
            f"<div><h2>{icon(icon_name)}{html.escape(title)}</h2>{hint_html}</div></div>"
        ),
        unsafe_allow_html=True,
    )


def badge(billing: str) -> str:
    label = BILLING_BADGE.get(billing, billing or "Unknown")
    kind = billing if billing in BILLING_BADGE else "unknown"
    return f'<span class="badge badge-{kind}">{label}</span>'


def init_state(cfg: dict, user_set: dict, model_choices: list[str]) -> None:
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = load_keys_from_env()
    if "workspace_path" not in st.session_state:
        st.session_state.workspace_path = (
            user_set.get("workspace_path") or os.getenv("WORKSPACE_PATH") or str(DEFAULT_WS)
        )
    if "agent_overrides" not in st.session_state:
        agents_cfg = cfg.get("agents") or {}
        overrides = {}
        saved = user_set.get("agent_overrides") or {}
        for agent_id, agent_cfg in agents_cfg.items():
            overrides[agent_id] = {
                "enabled": agent_cfg.get("enabled", True),
                "model": agent_cfg.get("model", model_choices[0]),
                "temperature": float(agent_cfg.get("temperature", 0.2)),
            }
            if agent_id in saved:
                overrides[agent_id].update(saved[agent_id])
        st.session_state.agent_overrides = overrides
    pipelines = list((cfg.get("pipelines") or {}).keys()) or ["single"]
    if "pipeline_select" not in st.session_state:
        saved_pipe = user_set.get("pipeline") or cfg.get("default_pipeline", pipelines[0])
        st.session_state.pipeline_select = saved_pipe if saved_pipe in pipelines else pipelines[0]
    st.session_state.setdefault("max_steps", int(user_set.get("max_steps", 25)))
    st.session_state.setdefault("shell_timeout", int(user_set.get("shell_timeout", 120)))
    st.session_state.setdefault("keep_awake", bool(user_set.get("keep_awake", True)))
    st.session_state.setdefault("keep_display", bool(user_set.get("keep_display", False)))
    st.session_state.setdefault(
        "ollama_base",
        user_set.get("ollama_base") or os.getenv("OLLAMA_API_BASE") or "http://localhost:11434",
    )
    st.session_state.setdefault("last_run", None)
    st.session_state.setdefault("theme", resolve_theme(user_set.get("theme")))
    st.session_state.setdefault("screen", resolve_screen(user_set.get("screen")))
    os.environ["OLLAMA_API_BASE"] = str(st.session_state.ollama_base or "").strip()


def settings_payload() -> dict:
    return {
        "workspace_path": st.session_state.workspace_path,
        "pipeline": st.session_state.get("pipeline_select"),
        "agent_overrides": st.session_state.get("agent_overrides", {}),
        "max_steps": int(st.session_state.get("max_steps", 25)),
        "shell_timeout": int(st.session_state.get("shell_timeout", 120)),
        "keep_awake": bool(st.session_state.get("keep_awake", True)),
        "keep_display": bool(st.session_state.get("keep_display", False)),
        "ollama_base": st.session_state.get("ollama_base") or "http://localhost:11434",
        "theme": resolve_theme(st.session_state.get("theme")),
        "screen": resolve_screen(st.session_state.get("screen")),
    }


def persist() -> None:
    os.environ["OLLAMA_API_BASE"] = str(st.session_state.get("ollama_base") or "").strip()
    save_user_settings(settings_payload())


def workspace_dir() -> Path:
    raw = str(st.session_state.get("workspace_path") or "").strip()
    return Path(raw or DEFAULT_WS)


def render_theme_switch() -> None:
    current = resolve_theme(st.session_state.get("theme"))
    st.markdown('<p class="kicker">Оформление</p>', unsafe_allow_html=True)
    dots = "".join(
        f'<i style="background:{THEMES[theme_id]["bg"]};box-shadow:inset -8px 0 {THEMES[theme_id]["accent"]}"></i>'
        for theme_id in THEME_ORDER
    )
    st.markdown(f'<div class="palette" aria-hidden="true">{dots}</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    for index, theme_id in enumerate(THEME_ORDER):
        column = left if index % 2 == 0 else right
        with column:
            if st.button(
                THEMES[theme_id]["label"],
                key=f"pick_{theme_id}",
                type="primary" if theme_id == current else "secondary",
                use_container_width=True,
            ):
                st.session_state.theme = theme_id
                persist()
                st.rerun()
    st.caption(THEMES[current]["blurb"])


def render_nav() -> None:
    current = resolve_screen(st.session_state.get("screen"))
    columns = st.columns(len(SCREENS))
    for column, (screen_id, label) in zip(columns, SCREENS):
        with column:
            if st.button(
                label,
                key=f"nav_{screen_id}",
                type="primary" if screen_id == current else "secondary",
                use_container_width=True,
            ):
                st.session_state.screen = screen_id
                persist()
                st.rerun()


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="mast"><div class="mark">{icon("play", 22)}</div>'
            '<div><p class="kicker">Студия</p><strong>Агенты</strong></div></div>',
            unsafe_allow_html=True,
        )
        render_theme_switch()
        st.header("Ключи")
        filled = [
            label
            for label, env, _hint in KEY_LABELS
            if str(st.session_state.api_keys.get(env) or "").strip()
        ]
        empty = [label for label, env, _hint in KEY_LABELS if label not in filled]
        st.caption("Заданы: " + (", ".join(filled) if filled else "пока нет"))
        st.caption("Пусто: " + (", ".join(empty) if empty else "все заполнены"))
        with st.expander("Ввести ключи", expanded=not filled):
            st.caption(
                "Пароли не показываются. Пустое поле при сохранении старое значение не стирает."
            )
            for label, env, hint in KEY_LABELS:
                widget_key = f"k_{env}"
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = st.session_state.api_keys.get(env, "")
                st.session_state.api_keys[env] = st.text_input(
                    label,
                    type="password",
                    key=widget_key,
                    help=hint,
                )
            if st.button("Сохранить ключи", use_container_width=True):
                save_keys_to_env(
                    st.session_state.api_keys,
                    {
                        "WORKSPACE_PATH": str(workspace_dir()),
                        "OLLAMA_API_BASE": st.session_state.ollama_base,
                    },
                )
                persist()
                st.success("Ключи записаны в .env")
            if st.button("Перечитать .env", type="tertiary", use_container_width=True):
                st.session_state.api_keys = load_keys_from_env()
                for _label, env, _hint in KEY_LABELS:
                    st.session_state[f"k_{env}"] = st.session_state.api_keys.get(env, "")
                st.rerun()

        st.divider()
        with st.expander("Параметры запуска", expanded=False):
            _render_run_settings()


def _render_run_settings() -> None:
    st.slider(
        "Макс. шагов агента",
        5,
        80,
        key="max_steps",
        help="Сколько вызовов модели у одной роли.",
    )
    st.slider("Таймаут shell, сек", 10, 300, key="shell_timeout")
    st.checkbox(
        "Не давать системе уснуть",
        key="keep_awake",
        help="Блокирует idle-сон на время задачи. Настоящий сон с замороженным процессом здесь невозможен.",
    )
    st.checkbox("Держать экран включённым", key="keep_display")
    st.text_input(
        "Адрес Ollama",
        key="ollama_base",
        help="Нужен только для локальных моделей. Ключ API не требуется.",
    )
    if st.button("Сохранить настройки", use_container_width=True):
        persist()
        save_keys_to_env(
            st.session_state.api_keys,
            {
                "WORKSPACE_PATH": str(workspace_dir()),
                "OLLAMA_API_BASE": st.session_state.ollama_base,
            },
        )
        st.success("Настройки записаны в user_settings.json")


def render_header(catalog: dict, active_steps: list[str]) -> None:
    theme = THEMES[resolve_theme(st.session_state.get("theme"))]
    st.markdown(
        (
            '<div class="mast"><div class="mark" aria-hidden="true">МС</div><div>'
            f'<p class="kicker">{theme["kicker"]}</p>'
            "<h1>Multi-Agent Studio</h1>"
            '<p class="studio-lead">Сначала ключ слева, затем папка и задача, затем «Запустить».</p>'
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )
    render_nav()
    free_count = sum(1 for meta in catalog.values() if is_free_option(meta))
    known_keys = sum(
        1 for env in KEY_NAMES if str(st.session_state.api_keys.get(env) or "").strip()
    )
    folder = workspace_dir()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Моделей", len(catalog))
    col2.metric("Бесплатных вариантов", free_count)
    col3.metric("Ключей задано", f"{known_keys}/{len(KEY_LABELS)}")
    col4.metric("Активных ролей", len(active_steps) or 0)
    if folder.is_dir():
        st.caption(f"Папка проекта: {folder}")
    else:
        st.warning(f"Папки проекта ещё нет: {folder}. Создайте её в разделе «Запуск».")


def active_agent_ids(cfg: dict, steps: list[str]) -> list[str]:
    agents_cfg = cfg.get("agents") or {}
    active = []
    for agent_id in steps:
        override = st.session_state.agent_overrides.get(agent_id, {})
        enabled = override.get("enabled", agents_cfg.get(agent_id, {}).get("enabled", True))
        if enabled:
            active.append(agent_id)
    return active


def render_chain(cfg: dict, steps: list[str], catalog: dict) -> None:
    agents_cfg = cfg.get("agents") or {}
    parts = ['<div class="chain">']
    for index, agent_id in enumerate(steps):
        agent_cfg = agents_cfg.get(agent_id, {})
        override = st.session_state.agent_overrides.get(agent_id, {})
        enabled = override.get("enabled", agent_cfg.get("enabled", True))
        model_key = override.get("model") or agent_cfg.get("model") or ""
        meta = catalog.get(model_key) or {}
        name = agent_cfg.get("name", agent_id)
        model_name = meta.get("name") or model_key
        billing = badge(str(meta.get("billing") or "")) if meta else ""
        css = "chip" if enabled else "chip off"
        state = "" if enabled else " · выкл"
        parts.append(f'<span class="{css}">{name} · {model_name} {billing}{state}</span>')
        if index < len(steps) - 1:
            parts.append('<span class="arrow">→</span>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_run(cfg: dict, catalog: dict, pipelines: dict) -> None:
    folder_ready = workspace_dir().is_dir()
    task_ready = bool(str(st.session_state.get("task_text") or "").strip())
    done = 1 + int(folder_ready) + int(task_ready)
    st.markdown(
        '<div class="progress" aria-hidden="true">'
        + "".join(f'<span class="seg{" on" if index < done else ""}"></span>' for index in range(3))
        + "</div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.45, 1])
    with left:
        with st.container(key="card_folder"):
            _render_folder_card()
    with right:
        with st.container(key="card_status"):
            _render_status_card(cfg, catalog, pipelines, folder_ready)
    with st.container(key="card_pipeline"):
        pipeline_name, active = _render_pipeline_card(cfg, catalog, pipelines)
    with st.container(key="card_task"):
        _render_task_card(cfg, catalog, pipeline_name, active)


def _render_folder_card() -> None:
    step(
        "1",
        "Папка",
        "Агенты работают только внутри неё. Перед перезаписью делается backup.",
        "folder",
    )
    presets = preset_paths(DEFAULT_WS)
    columns = st.columns(min(4, max(len(presets), 1)))
    for index, (label, path) in enumerate(presets):
        with columns[index % len(columns)]:
            if st.button(label, key=f"ws_{index}", use_container_width=True):
                st.session_state.workspace_path = str(path)
                persist()
                st.rerun()
    st.text_input("Путь к папке", key="workspace_path")
    folder = workspace_dir()
    if st.button("Создать папку", use_container_width=True):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            st.success(f"Папка готова: {folder}")
        except OSError as exc:
            st.error(f"Не удалось создать папку: {exc}")
    if folder.is_dir():
        st.caption(f"Папка на месте: {folder}")
    else:
        st.warning("Такой папки нет. Создайте её или выберите другой путь.")


def _render_status_card(cfg: dict, catalog: dict, pipelines: dict, folder_ready: bool) -> None:
    step(" ", "Сейчас", "Что уже готово к запуску.", "check")
    known = sum(1 for env in KEY_NAMES if str(st.session_state.api_keys.get(env) or "").strip())
    pipe = st.session_state.get("pipeline_select") or ""
    steps = list((pipelines.get(pipe) or {}).get("steps") or [])
    active = active_agent_ids(cfg, steps)
    st.markdown(
        (
            f"<p>{icon('folder')} Папка: {'есть' if folder_ready else 'нет'}</p>"
            f"<p>{icon('key')} Ключей: {known} из {len(KEY_LABELS)}</p>"
            f"<p>{icon('users')} Активных ролей: {len(active)}</p>"
        ),
        unsafe_allow_html=True,
    )
    if known == 0:
        st.caption("Дальше: вставьте ключ в колонке слева. Для старта хватит Google.")


def _render_pipeline_card(cfg: dict, catalog: dict, pipelines: dict):
    step("2", "Пайплайн", "Включённые роли идут слева направо.", "users")
    pipe_names = list(pipelines.keys())
    if st.session_state.pipeline_select not in pipe_names:
        st.session_state.pipeline_select = pipe_names[0]
    pipeline_name = st.selectbox(
        "Режим",
        pipe_names,
        format_func=lambda name: f"{name} — {pipelines[name].get('description', '')}",
        key="pipeline_select",
    )
    steps = list(pipelines.get(pipeline_name, {}).get("steps") or ["developer"])
    render_chain(cfg, steps, catalog)
    active = active_agent_ids(cfg, steps)
    if not active:
        st.error(
            "В этом пайплайне нет включённых ролей. Откройте раздел «Агенты» слева и включите хотя бы одну."
        )
    else:
        missing = missing_credentials(
            model_keys_for(cfg, active), st.session_state.api_keys, catalog, cfg
        )
        if missing:
            bits = [f"{env} ({provider})" for _model, provider, env in missing]
            st.warning(
                "Нет ключа для: "
                + ", ".join(dict.fromkeys(bits))
                + ". Такой шаг будет пропущен. Локальный Ollama ключ не требует."
            )
    return pipeline_name, active


def _render_task_card(cfg: dict, catalog: dict, pipeline_name: str, active: list[str]) -> None:
    step("3", "Задача", "Одно предложение достаточно. Итог останется ниже.", "play")
    task = st.text_area(
        "Задача",
        height=150,
        placeholder="Например: создай hello.py, который печатает приветствие, и запусти его.",
        key="task_text",
    )
    run_clicked = st.button("Запустить", type="primary", use_container_width=True, key="launch_run")
    if run_clicked:
        execute_run(cfg, catalog, pipeline_name, task, active)

    last = st.session_state.last_run
    if not last:
        slip(
            "Следующий шаг",
            "Опишите задачу выше и нажмите «Запустить». Итог останется на этой странице.",
        )
        return
    with st.container(key="result_panel"):
        st.markdown('<p class="kicker">Результат</p>', unsafe_allow_html=True)
        st.caption(last.get("when") or "")
        if last.get("logs"):
            with st.expander("Журнал", expanded=bool(last.get("error"))):
                st.code("\n".join(last["logs"][-80:]), language="text")
        if last.get("error"):
            st.error(last["error"])
            if last.get("traceback"):
                with st.expander("Техническая подробность"):
                    st.code(last["traceback"], language="text")
        elif last.get("result"):
            st.markdown(last["result"])
            st.download_button(
                "Скачать отчёт",
                data=last.get("report") or last["result"],
                file_name=last.get("file_name") or "run.md",
                mime="text/markdown",
            )


def model_keys_for(cfg: dict, agent_ids: list[str]) -> list[str]:
    agents_cfg = cfg.get("agents") or {}
    keys = []
    for agent_id in agent_ids:
        override = st.session_state.agent_overrides.get(agent_id, {})
        keys.append(override.get("model") or agents_cfg.get(agent_id, {}).get("model") or "")
    return [key for key in keys if key]


def execute_run(cfg: dict, catalog: dict, pipeline_name: str, task: str, active: list[str]) -> None:
    persist()
    if not task.strip():
        st.error("Введите задачу. Пустой запрос запускать некуда.")
        return
    if not active:
        st.error("Включите хотя бы одну роль в этом пайплайне.")
        return
    folder = workspace_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        st.error(f"Папка проекта недоступна: {exc}")
        return
    st.session_state.workspace_path = str(folder)
    save_keys_to_env(
        st.session_state.api_keys,
        {"WORKSPACE_PATH": str(folder), "OLLAMA_API_BASE": st.session_state.ollama_base},
    )
    logs: list[str] = []
    log_box = st.empty()

    def log_fn(message: str) -> None:
        logs.append(str(message))
        log_box.code("\n".join(logs[-60:]), language="text")

    orchestrator = Orchestrator(
        workspace=str(folder),
        backup_dir=str(BACKUPS),
        api_keys=st.session_state.api_keys,
        config=cfg,
        max_steps=int(st.session_state.max_steps),
        shell_timeout=int(st.session_state.shell_timeout),
        log_fn=log_fn,
        overrides=st.session_state.agent_overrides,
        pipeline_name=pipeline_name,
    )
    power_runtime = None
    if st.session_state.keep_awake:
        power_runtime = AgentRuntime(
            workspace=str(folder),
            backup_dir=str(BACKUPS),
            model="ollama_chat/gemma4",
            api_key="ollama",
            allowed_tools=[],
            role_name="power",
        )
        log_fn(power_runtime.power.start("display" if st.session_state.keep_display else "system"))
    try:
        with st.spinner("Агенты работают…"):
            result = orchestrator.run(task.strip())
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = (
            f"# Задача\n\n{task.strip()}\n\n# Журнал\n\n"
            + "\n".join(logs)
            + f"\n\n# Результат\n\n{result}"
        )
        out = RESULTS / f"run_{stamp}.md"
        out.write_text(report, encoding="utf-8")
        st.session_state.last_run = {
            "when": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "logs": logs,
            "result": result,
            "report": report,
            "file_name": out.name,
            "error": "",
        }
    except Exception as exc:
        st.session_state.last_run = {
            "when": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "logs": logs,
            "result": "",
            "error": f"Запуск остановился: {exc}",
            "traceback": traceback.format_exc(),
        }
    finally:
        if power_runtime is not None:
            log_fn(power_runtime.power.stop())
            if st.session_state.last_run is not None:
                st.session_state.last_run["logs"] = logs


def render_agents(cfg: dict, catalog: dict, model_choices: list[str]) -> None:
    st.markdown(f"<h2>{icon('users')}Агенты</h2>", unsafe_allow_html=True)
    st.caption(
        "Бейдж Free tier значит, что у провайдера есть бесплатная квота, а цифра рядом — платный тариф за её пределами. "
        "Настройки пишутся в user_settings.json."
    )
    agents_cfg = cfg.get("agents") or {}
    recommendations = cfg.get("recommendations") or {}
    if not agents_cfg:
        st.info("В config/agents.yaml нет ролей.")
        return
    for agent_id, agent_cfg in agents_cfg.items():
        current = st.session_state.agent_overrides.get(agent_id, {})
        with st.expander(
            f"{agent_cfg.get('name', agent_id)} · {agent_id}", expanded=(agent_id == "developer")
        ):
            st.caption(agent_cfg.get("description", ""))
            col_on, col_model, col_temp = st.columns([1, 4, 2])
            with col_on:
                flag = f"en_{agent_id}"
                if flag not in st.session_state:
                    st.session_state[flag] = bool(
                        current.get("enabled", agent_cfg.get("enabled", True))
                    )
                enabled = st.checkbox("Включена", key=flag)
            with col_model:
                model_flag = f"model_{agent_id}"
                preferred = current.get("model") or agent_cfg.get("model") or model_choices[0]
                if (
                    model_flag not in st.session_state
                    or st.session_state[model_flag] not in model_choices
                ):
                    st.session_state[model_flag] = (
                        preferred if preferred in model_choices else model_choices[0]
                    )
                model_key = st.selectbox(
                    "Модель",
                    model_choices,
                    key=model_flag,
                    format_func=lambda key: model_label(key, catalog),
                )
            with col_temp:
                temp_flag = f"temp_{agent_id}"
                if temp_flag not in st.session_state:
                    st.session_state[temp_flag] = float(
                        current.get("temperature", agent_cfg.get("temperature", 0.2))
                    )
                temperature = st.slider("Температура", 0.0, 1.0, step=0.05, key=temp_flag)
            meta = catalog.get(model_key) or {}
            if meta:
                st.markdown(
                    badge(str(meta.get("billing") or "")) + " " + format_price(meta),
                    unsafe_allow_html=True,
                )
                if meta.get("availability") == "deprecated":
                    st.warning(meta.get("summary") or "Модель помечена как deprecated.")
                elif meta.get("price_status") == "unknown":
                    st.caption(
                        "Цена: unknown. Цифру не ставили, потому что официальный источник её не подтвердил."
                    )
                else:
                    st.caption(meta.get("price_note") or "")
            suggested = recommendations.get(agent_id) or []
            if suggested:
                st.caption(
                    "С чего начать: "
                    + ", ".join(model_label(item, catalog) for item in suggested if item in catalog)
                )
            st.session_state.agent_overrides[agent_id] = {
                "enabled": enabled,
                "model": model_key,
                "temperature": float(temperature),
            }
    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("Сохранить роли", use_container_width=True):
            persist()
            st.success("Роли сохранены.")
    with col_reset:
        if st.button("Вернуть модели из agents.yaml", type="tertiary", use_container_width=True):
            for agent_id, agent_cfg in agents_cfg.items():
                st.session_state.agent_overrides[agent_id] = {
                    "enabled": agent_cfg.get("enabled", True),
                    "model": agent_cfg.get("model", model_choices[0]),
                    "temperature": float(agent_cfg.get("temperature", 0.2)),
                }
                st.session_state[f"en_{agent_id}"] = bool(agent_cfg.get("enabled", True))
                chosen = agent_cfg.get("model", model_choices[0])
                st.session_state[f"model_{agent_id}"] = (
                    chosen if chosen in model_choices else model_choices[0]
                )
                st.session_state[f"temp_{agent_id}"] = float(agent_cfg.get("temperature", 0.2))
            persist()
            st.rerun()


def passes_billing(meta: dict, mode: str) -> bool:
    billing = meta.get("billing")
    if mode == "all":
        return True
    if mode == "free":
        return is_free_option(meta)
    if mode == "paid":
        return billing == "paid"
    if mode == "local":
        return billing == "local"
    if mode == "unknown":
        return meta.get("price_status") == "unknown"
    return True


def render_models(catalog: dict) -> None:
    st.markdown(f"<h2>{icon('grid')}Модели</h2>", unsafe_allow_html=True)
    st.markdown(
        "Цены сверены **9 ноября 2026** по страницам провайдеров и ответу API OpenRouter. "
        "Если цифры не было в источнике, стоит **unknown** — её не придумывали. "
        "Free tier у Gemini — это $0 в лимитах, а колонка цены показывает платный тариф после лимита."
    )
    providers = sorted({str(meta.get("provider") or "") for meta in catalog.values()})
    search_col, provider_col = st.columns(2)
    with search_col:
        search = st.text_input("Поиск", placeholder="Имя, провайдер или ID", key="model_search")
    with provider_col:
        if "provider_filter" not in st.session_state:
            st.session_state.provider_filter = providers
        else:
            st.session_state.provider_filter = [
                item for item in st.session_state.provider_filter if item in providers
            ] or providers
        chosen_providers = st.multiselect("Провайдеры", providers, key="provider_filter")
    billing_label = st.radio(
        "Доступ",
        [label for label, _mode in BILLING_FILTERS],
        horizontal=True,
        key="billing_filter",
    )
    mode = dict(BILLING_FILTERS)[billing_label]
    query = search.strip().lower()
    rows = []
    matched: list[tuple[str, dict]] = []
    for model_key, meta in catalog.items():
        if not passes_billing(meta, mode):
            continue
        if meta.get("provider") not in chosen_providers:
            continue
        haystack = " ".join(
            [
                model_key,
                str(meta.get("name") or ""),
                str(meta.get("provider") or ""),
                str(meta.get("litellm") or ""),
                str(meta.get("summary") or ""),
            ]
        ).lower()
        if query and query not in haystack:
            continue
        matched.append((model_key, meta))
        rows.append(
            {
                "Модель": meta.get("name"),
                "Провайдер": meta.get("provider"),
                "Доступ": BILLING_BADGE.get(meta.get("billing"), meta.get("billing")),
                "Цена, USD / 1M in → out": format_price(meta),
                "Контекст": meta.get("context"),
                "Статус": meta.get("availability"),
                "Проверено": meta.get("last_verified"),
            }
        )
    st.caption(f"Показано {len(rows)} из {len(catalog)}.")
    if not rows:
        slip("Пусто по фильтру", "Сбросьте поиск или верните доступ на «Все».")
        return
    render_sheet(rows)
    labels = {model_key: model_label(model_key, catalog) for model_key, _meta in matched}
    selected = st.selectbox("Карточка модели", list(labels), format_func=lambda key: labels[key])
    meta = catalog[selected]
    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
    st.markdown(
        badge(str(meta.get("billing") or "")) + f" **{meta.get('name')}** · {meta.get('provider')}",
        unsafe_allow_html=True,
    )
    st.markdown(meta.get("summary") or "")
    st.markdown(
        f"- **ID:** `{meta.get('litellm')}`\n"
        f"- **Цена:** {format_price(meta)}\n"
        f"- **Пояснение:** {meta.get('price_note')}\n"
        f"- **Контекст:** {meta.get('context')}\n"
        f"- **Для каких задач:** {meta.get('best_for')}\n"
        f"- **Статус:** {meta.get('availability')}\n"
        f"- **Источник:** {meta.get('source')}\n"
        f"- **Проверено:** {meta.get('last_verified')}"
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_sheet(rows: list[dict]) -> None:
    columns = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns)
        body.append(f"<tr>{cells}</tr>")
    st.markdown(
        (
            '<div class="sheet-wrap"><table class="sheet"><thead><tr>'
            f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
        ),
        unsafe_allow_html=True,
    )


def render_files() -> None:
    st.markdown(f"<h2>{icon('folder')}Файлы</h2>", unsafe_allow_html=True)
    folder = workspace_dir()
    st.caption(f"Корень: {folder}")
    if not folder.is_dir():
        st.warning("Папка проекта не найдена. Создайте её в разделе «Запуск».")
        return
    try:
        from tools.filesystem import WorkspaceFS

        filesystem = WorkspaceFS(folder, BACKUPS)
        entries = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    except Exception as exc:
        st.error(f"Не удалось прочитать папку: {exc}")
        return
    st.caption("Содержимое папки")
    st.code(filesystem.list_dir("."), language="text")
    if not entries:
        slip(
            "Папка пустая",
            "Запустите агента с задачей «создай файл» или положите файлы в эту папку сами.",
        )
    else:
        files = [item.name for item in entries if item.is_file()]
        if files:
            chosen = st.selectbox("Файл", files)
            if st.button("Прочитать файл"):
                show_file(filesystem, chosen)
        else:
            st.caption("Файлов для чтения нет, только папки.")
    custom = st.text_input("Или путь внутри папки", placeholder="src/main.py")
    if custom and st.button("Прочитать путь"):
        show_file(filesystem, custom.strip())


def show_file(filesystem, path: str) -> None:
    text = filesystem.read_file(path)
    if text.startswith(("File not found", "Not a file", "Path outside")):
        st.error(text)
    else:
        st.code(text, language="text")


def render_ssh() -> None:
    st.markdown(f"<h2>{icon('terminal')}SSH</h2>", unsafe_allow_html=True)
    st.warning(
        "Команда выполнится на указанном компьютере по SSH. Добавляйте только свои машины в локальной сети. "
        "Пароль в форму не входит: используйте ключ."
    )
    with st.form("ssh_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Имя устройства", value="device1")
            host = st.text_input("Хост", placeholder="192.168.1.10")
            command = st.text_input("Команда", value="uname -a")
        with col2:
            user = st.text_input("Пользователь", value="pi")
            port = st.number_input("Порт", value=22, min_value=1, max_value=65535)
            key_path = st.text_input("Путь к SSH-ключу", placeholder="~/.ssh/id_ed25519")
        submitted = st.form_submit_button("Выполнить по SSH", use_container_width=True)
    if not submitted:
        st.caption("Результат появится после отправки формы.")
        return
    if not host.strip() or not command.strip() or not name.strip():
        st.error("Нужны имя, хост и команда.")
        return
    from tools.remote import RemoteDevice, RemoteManager

    manager = RemoteManager()
    manager.add_device(
        RemoteDevice(
            name=name.strip(),
            host=host.strip(),
            user=user.strip() or "root",
            port=int(port),
            key_path=str(Path(key_path).expanduser()) if key_path.strip() else None,
        )
    )
    st.code(manager.run_ssh(name.strip(), command.strip()), language="text")


def render_help() -> None:
    st.markdown(f"<h2>{icon('help')}Справка</h2>", unsafe_allow_html=True)
    st.markdown(
        """
### Оформление
Слева три темы: Ночь, Бумага и Жар. Ночь включена по умолчанию. Выбор пишется в `user_settings.json` и остаётся после перезапуска.

### Как начать
1. Создайте ключ хотя бы одного бесплатного варианта: Google AI Studio для Gemini или OpenRouter для моделей с суффиксом `:free`.
2. Вставьте ключ слева и нажмите «Сохранить ключи».
3. В разделе «Запуск» оставьте пайплайн `code_only` и опишите задачу.

Роли по умолчанию смотрят на Gemini с free tier, так что одного ключа Google достаточно. Платные модели выбираются в разделе «Агенты».

### Где что лежит
| Что | Файл |
| --- | --- |
| Ключи | `.env` (не коммитится) |
| Роли, пайплайн, папка, тема | `user_settings.json` |
| Каталог, цены, источники | `config/models_catalog.yaml` |
| Промпты ролей | `config/agents.yaml` |
| Отчёты запусков | `results/` |

### Ollama
Локальные модели помечены **Local** и стоят $0 за токены API. Установите [Ollama](https://ollama.com/library), скачайте веса (`ollama pull gemma4`) и оставьте адрес `http://localhost:11434`.

### Безопасность
- Файловые инструменты не выходят из выбранной папки. Соседняя папка с тем же префиксом имени тоже снаружи.
- Перед перезаписью и удалением делается копия в `backups/`.
- Опасные шаблоны shell блокируются.
- SSH ходит только на хост, который вы явно указали в форме.

### Цены
Дата сверки указана у каждой модели. Провайдеры меняют прайс без предупреждения в этом репозитории. Если в карточке **unknown**, официальная цифра на момент сверки не подтверждалась.
        """
    )


def main() -> None:
    st.set_page_config(page_title="Multi-Agent Studio", page_icon="¶", layout="wide")
    cfg = (
        load_config(ROOT / "config" / "agents.yaml")
        if (ROOT / "config" / "agents.yaml").exists()
        else {}
    )
    catalog = load_models_catalog()
    runnable = runnable_models(catalog)
    model_choices = [key for key in sorted_model_keys(runnable)]
    if not model_choices:
        model_choices = ["gemini_38_flash"]
    user_set = load_user_settings()
    init_state(cfg, user_set, model_choices)
    inject_css()
    pipelines = cfg.get("pipelines") or {
        "single": {"steps": ["developer"], "description": "одна роль"}
    }
    pipe_name = st.session_state.pipeline_select
    steps = list((pipelines.get(pipe_name) or {}).get("steps") or ["developer"])
    render_sidebar()
    render_header(catalog, active_agent_ids(cfg, steps))
    screen = resolve_screen(st.session_state.get("screen"))
    if screen == "agents":
        render_agents(cfg, catalog, model_choices)
    elif screen == "models":
        render_models(catalog)
    elif screen == "files":
        render_files()
    elif screen == "ssh":
        render_ssh()
    elif screen == "help":
        render_help()
    else:
        render_run(cfg, catalog, pipelines)


if __name__ == "__main__":
    main()
