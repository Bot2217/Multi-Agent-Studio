"""Multi-Agent Studio — локальный интерфейс ролей, пайплайнов и каталога моделей."""

from __future__ import annotations

import html
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    ROOT = Path(getattr(sys, "_MEIPASS"))
sys.path.insert(0, str(ROOT))

from core.paths import data_root

DATA = data_root()
load_dotenv(DATA / ".env")

from core.catalog import (
    BILLING_BADGE,
    format_price,
    is_free_option,
    load_models_catalog,
    missing_credentials,
    runnable_models,
    sorted_model_keys,
)
from core.orchestrator import load_config
from core.runner import RunJob
from core.themes import (
    LEGACY_APPEARANCE,
    PALETTE_LABELS,
    PALETTE_ORDER,
    SCREENS,
    THEME_LABELS,
    THEME_ORDER,
    migrate_appearance,
    resolve_palette,
    resolve_screen,
    resolve_theme,
    theme_stylesheet,
)
from core.ui_helpers import (
    load_keys_from_env,
    load_user_settings,
    preset_paths,
    save_keys_to_env,
    save_user_settings,
)

KEY_LABELS = [
    ("Google", "GOOGLE_API_KEY", "Gemini, есть бесплатная квота"),
    ("OpenRouter", "OPENROUTER_API_KEY", "модели с суффиксом :free"),
    ("Anthropic", "ANTHROPIC_API_KEY", "Claude"),
    ("OpenAI", "OPENAI_API_KEY", "GPT"),
    ("xAI", "XAI_API_KEY", "Grok"),
    ("DeepSeek", "DEEPSEEK_API_KEY", "DeepSeek"),
    ("Groq", "GROQ_API_KEY", "открытые модели на Groq"),
    ("Mistral", "MISTRAL_API_KEY", "Mistral и Codestral"),
    ("Cerebras", "CEREBRAS_API_KEY", "Cerebras"),
]

PIPELINE_LABELS = {
    "code_only": "Быстро: код и ревью",
    "full": "Полный цикл",
    "research_code": "Исследование и код",
    "single": "Один разработчик",
}

BILLING_FILTERS = {
    "Все": "all",
    "Бесплатные": "free",
    "Платные": "paid",
    "Локальные": "local",
}

DEFAULT_WS = DATA / "workspace"
BACKUPS = DATA / "backups"
RESULTS = DATA / "results"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
FILE_LIMIT = 300

SETTING_DEFAULTS = {
    "max_steps": 25,
    "shell_timeout": 120,
    "keep_awake": True,
    "keep_display": False,
    "ollama_base": "http://localhost:11434",
}


# ---------- state ----------


def init_state(cfg: dict, user_set: dict, model_choices: list[str]) -> None:
    state = st.session_state
    if "api_keys" not in state:
        state.api_keys = load_keys_from_env()
    if "workspace_path" not in state:
        state.workspace_path = (
            user_set.get("workspace_path") or os.getenv("WORKSPACE_PATH") or str(DEFAULT_WS)
        )
    if "agent_overrides" not in state:
        saved = user_set.get("agent_overrides") or {}
        overrides = {}
        for agent_id, agent_cfg in (cfg.get("agents") or {}).items():
            overrides[agent_id] = default_override(agent_cfg, model_choices)
            if isinstance(saved.get(agent_id), dict):
                overrides[agent_id].update(saved[agent_id])
            if overrides[agent_id]["model"] not in model_choices:
                overrides[agent_id]["model"] = model_choices[0]
        state.agent_overrides = overrides
    pipelines = list((cfg.get("pipelines") or {}).keys()) or ["single"]
    if state.get("pipeline") not in pipelines:
        saved_pipe = user_set.get("pipeline") or cfg.get("default_pipeline")
        state.pipeline = saved_pipe if saved_pipe in pipelines else pipelines[0]
    for name, fallback in SETTING_DEFAULTS.items():
        if name not in state:
            saved_value = user_set.get(name)
            state[name] = fallback if saved_value is None else type(fallback)(saved_value)
    state.setdefault("task", "")
    state.setdefault("job", None)
    state.setdefault("last_run", None)
    theme, palette = migrate_appearance(user_set.get("theme"), user_set.get("palette"))
    state.setdefault("theme", theme)
    state.setdefault("palette", palette)
    state.setdefault("screen", resolve_screen(user_set.get("screen")))
    os.environ["OLLAMA_API_BASE"] = str(state.ollama_base or "").strip()
    if str(user_set.get("theme") or "").strip().lower() in LEGACY_APPEARANCE:
        state.theme = theme
        state.palette = palette
        persist()


def default_override(agent_cfg: dict, model_choices: list[str]) -> dict:
    return {
        "enabled": bool(agent_cfg.get("enabled", True)),
        "model": agent_cfg.get("model", model_choices[0]),
        "temperature": float(agent_cfg.get("temperature", 0.2)),
    }


def persist() -> None:
    state = st.session_state
    os.environ["OLLAMA_API_BASE"] = str(state.get("ollama_base") or "").strip()
    payload = {
        "workspace_path": state.workspace_path,
        "pipeline": state.get("pipeline"),
        "agent_overrides": state.get("agent_overrides", {}),
        "theme": resolve_theme(state.get("theme")),
        "palette": resolve_palette(state.get("palette")),
        "screen": resolve_screen(state.get("screen")),
    }
    for name, fallback in SETTING_DEFAULTS.items():
        payload[name] = state.get(name, fallback)
    save_user_settings(payload)


def bound(widget, label: str, name: str, save: bool = True, **kwargs):
    """A widget whose value lives in session_state[name] and survives leaving the screen."""
    widget_key = f"w_{name}"

    def sync() -> None:
        st.session_state[name] = st.session_state[widget_key]
        if save:
            persist()

    return widget(label, value=st.session_state[name], key=widget_key, on_change=sync, **kwargs)


def go(screen: str) -> None:
    st.session_state.screen = screen
    persist()


def workspace_dir() -> Path:
    raw = str(st.session_state.get("workspace_path") or "").strip()
    return Path(raw or DEFAULT_WS).expanduser()


# ---------- small pieces ----------


def badge(billing: str) -> str:
    label = BILLING_BADGE.get(billing, billing or "Unknown")
    kind = billing if billing in BILLING_BADGE else "unknown"
    return f'<span class="badge badge-{kind}">{html.escape(label)}</span>'


def empty(text: str) -> None:
    st.markdown(f'<div class="empty">{html.escape(text)}</div>', unsafe_allow_html=True)


def status_line(kind: str, title: str, detail: str = "") -> None:
    small = f"<small>{html.escape(detail)}</small>" if detail else ""
    st.markdown(
        f'<p class="status"><span class="dot {kind}"></span>{html.escape(title)} {small}</p>',
        unsafe_allow_html=True,
    )


ICONS = {
    "file": "M7 3h7l5 5v13H7zM14 3v5h5",
    "clock": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M12 7v5l3 2",
}

EXAMPLES = [
    "Создай hello.py, который печатает приветствие, и запусти его",
    "Напиши README.md с описанием файлов в этой папке",
    "Найди в коде все TODO и собери их в todo.md",
]


def svg(name: str, size: int = 18) -> str:
    return (
        f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{ICONS[name]}"></path></svg>'
    )


def eyebrow(text: str, tag: str = "") -> None:
    extra = f'<span class="tag quiet">{html.escape(tag)}</span>' if tag else ""
    st.markdown(
        f'<div class="card-head"><p class="eyebrow">{html.escape(text)}</p>{extra}</div>',
        unsafe_allow_html=True,
    )


def page_head(section: str, title: str, sub: str = "", tags: tuple = ()) -> None:
    """Page header: small section label, title, optional line and tags [(text, quiet)]."""
    sub_html = f'<p class="sub">{html.escape(sub)}</p>' if sub else ""
    tags_html = "".join(
        f'<span class="tag{" quiet" if quiet else ""}">{html.escape(text)}</span>'
        for text, quiet in tags
    )
    st.markdown(
        f'<div class="page-head"><div><p class="eyebrow">{html.escape(section)}</p>'
        f"<h1>{html.escape(title)}</h1>{sub_html}</div>"
        f'<div class="tags">{tags_html}</div></div>',
        unsafe_allow_html=True,
    )


def set_task(text: str) -> None:
    st.session_state.task = text
    st.session_state.pop("w_task", None)


def recent_runs(limit: int = 4) -> list[tuple[str, str]]:
    """(when, task) of the latest saved reports, newest first, without repeats."""
    runs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in sorted(RESULTS.glob("run_*.md"), reverse=True)[:40]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[:8]
        except OSError:
            continue
        task = next((ln.strip() for ln in lines[1:] if ln.strip() and not ln.startswith("#")), "")
        if not task or task in seen:
            continue
        seen.add(task)
        stamp = path.stem.removeprefix("run_")
        try:
            when = datetime.strptime(stamp, "%Y%m%d_%H%M%S").strftime("%d.%m %H:%M")
        except ValueError:
            when = stamp
        runs.append((when, task))
        if len(runs) >= limit:
            break
    return runs


def duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} с"
    return f"{seconds // 60} мин {seconds % 60} с"


# ---------- sidebar ----------


def render_sidebar() -> None:
    current = resolve_screen(st.session_state.get("screen"))
    with st.sidebar:
        st.markdown(
            '<div class="brand"><svg aria-hidden="true" width="32" height="32" viewBox="0 0 32 32">'
            '<path fill="#c2f24e" d="M16 4.2 21.2 7.2v6L16 16.2 10.8 13.2v-6z"/>'
            '<path fill="#e0a15a" d="M22.4 8.4 27.6 11.4v6l-5.2 3-5.2-3v-6z"/>'
            '<path fill="#9be0b8" d="M9.6 8.4 14.8 11.4v6l-5.2 3-5.2-3v-6z"/>'
            '<path fill="#eef0f4" d="M16 15.6 21.2 18.6v6L16 27.6 10.8 24.6v-6z"/>'
            "</svg>"
            "<div><b>Улей</b><small>студия</small></div></div>",
            unsafe_allow_html=True,
        )
        for screen_id, label in SCREENS:
            st.button(
                label,
                key=f"nav_{screen_id}",
                type="primary" if screen_id == current else "secondary",
                width="stretch",
                on_click=go,
                args=(screen_id,),
            )
        st.markdown('<p class="side-label">Тема</p>', unsafe_allow_html=True)

        def set_theme() -> None:
            st.session_state.theme = resolve_theme(st.session_state.get("w_theme"))
            persist()

        st.segmented_control(
            "Тема",
            THEME_ORDER,
            default=resolve_theme(st.session_state.get("theme")),
            format_func=lambda item: THEME_LABELS[item],
            key="w_theme",
            on_change=set_theme,
            label_visibility="collapsed",
        )


# ---------- run ----------


def pipeline_steps(cfg: dict, pipelines: dict) -> tuple[list[str], list[str]]:
    """All steps of the chosen pipeline and the ones that are switched on."""
    steps = list((pipelines.get(st.session_state.pipeline) or {}).get("steps") or ["developer"])
    overrides = st.session_state.agent_overrides
    active = [step for step in steps if overrides.get(step, {}).get("enabled", True)]
    return steps, active


def render_chain(cfg: dict, active: list[str], catalog: dict, no_key: set[str]) -> None:
    agents_cfg = cfg.get("agents") or {}
    count = len(active)
    word = "роль" if count == 1 else "роли" if 2 <= count <= 4 else "ролей"
    eyebrow("Цепочка", f"{count} {word}")
    items = []
    for index, agent_id in enumerate(active, 1):
        model_key = st.session_state.agent_overrides.get(agent_id, {}).get("model", "")
        meta = catalog.get(model_key) or {}
        name = html.escape(str(agents_cfg.get(agent_id, {}).get("name", agent_id)))
        model_name = html.escape(str(meta.get("name") or model_key))
        missing = model_key in no_key
        tag = '<span class="tag quiet">нет ключа</span>' if missing else ""
        items.append(
            f'<li class="{"nokey" if missing else ""}"><span class="num">{index}</span>'
            f'<span class="who"><b>{name}</b><small>{model_name}</small></span>{tag}</li>'
        )
    if items:
        st.markdown(f'<ol class="steps">{"".join(items)}</ol>', unsafe_allow_html=True)
    else:
        empty("Все роли выключены.")


def render_folder_picker() -> None:
    folder = workspace_dir()
    with st.popover(f"Папка: {folder.name or folder}", width="stretch"):
        st.caption("Агенты читают и пишут файлы только в этой папке.")

        def set_path() -> None:
            st.session_state.workspace_path = st.session_state.w_workspace_path.strip()
            persist()

        st.text_input(
            "Путь",
            value=st.session_state.workspace_path,
            key="w_workspace_path",
            on_change=set_path,
        )

        def choose(path: Path) -> None:
            st.session_state.workspace_path = str(path)
            st.session_state.pop("w_workspace_path", None)
            persist()

        presets = preset_paths(DEFAULT_WS)
        for column, (label, path) in zip(st.columns(len(presets)), presets):
            column.button(label, key=f"ws_{label}", on_click=choose, args=(path,), width="stretch")
        if not folder.is_dir():
            st.caption("Такой папки ещё нет — она будет создана при запуске.")


def render_run(cfg: dict, catalog: dict, pipelines: dict) -> None:
    job: RunJob | None = st.session_state.job
    busy = bool(job and job.running)
    free = sum(1 for meta in catalog.values() if is_free_option(meta))
    page_head(
        "Запуск",
        "Что сделать?",
        tags=((f"{len(catalog)} моделей в каталоге", True), (f"{free} бесплатных", False)),
    )
    _steps, active = pipeline_steps(cfg, pipelines)
    model_keys = [st.session_state.agent_overrides[a]["model"] for a in active]
    missing = missing_credentials(model_keys, st.session_state.api_keys, catalog, cfg)
    no_key = {model_key for model_key, _provider, _env in missing}
    names = list(pipelines)

    left, right = st.columns([2, 1], gap="medium")
    with left, st.container(key="card_task"):
        eyebrow("Задача")
        bound(
            st.text_area,
            "Задача",
            "task",
            save=False,
            height=120,
            placeholder="Опишите, что нужно сделать. Одного предложения достаточно.",
            label_visibility="collapsed",
            disabled=busy,
        )
        if not str(st.session_state.task).strip() and not busy:
            for index, text in enumerate(EXAMPLES):
                st.button(
                    text,
                    key=f"ex_{index}",
                    on_click=set_task,
                    args=(text,),
                    width="stretch",
                    help="Подставить пример: " + text,
                )
        mode_col, folder_col = st.columns([3, 2], vertical_alignment="bottom")
        with mode_col:

            def set_pipeline() -> None:
                st.session_state.pipeline = st.session_state.w_pipeline
                persist()

            st.selectbox(
                "Режим",
                names,
                index=names.index(st.session_state.pipeline),
                format_func=lambda name: PIPELINE_LABELS.get(name, name),
                key="w_pipeline",
                on_change=set_pipeline,
                disabled=busy,
                label_visibility="collapsed",
            )
        with folder_col:
            render_folder_picker()

        blocked = ""
        if not active:
            blocked = "В этом режиме выключены все роли."
            st.warning(blocked + " Включите хотя бы одну в разделе «Агенты».")
        elif missing:
            envs = ", ".join(dict.fromkeys(env for _m, _p, env in missing))
            if len(no_key) == len(set(model_keys)):
                blocked = "Нет ключа ни для одной модели."
                text = f"Чтобы запустить, нужен ключ: {envs}. У Google AI Studio он бесплатный."
            else:
                text = f"Нет ключа {envs} — роли с пунктиром будут пропущены."
            note, action = st.columns([3, 1], vertical_alignment="center")
            note.warning(text)
            action.button("Добавить ключ", on_click=go, args=("settings",), width="stretch")

        if st.button(
            "Запустить",
            type="primary",
            width="stretch",
            key="launch_run",
            disabled=busy or bool(blocked),
        ):
            start_run(cfg)
            st.rerun()

    with right, st.container(key="card_chain"):
        render_chain(cfg, active, catalog, no_key)
        st.button(
            "Настроить роли",
            on_click=go,
            args=("agents",),
            type="tertiary",
        )

    left, right = st.columns([2, 1], gap="medium")
    with left:
        if st.session_state.job is not None:
            render_progress()
        elif st.session_state.last_run:
            render_result()
        else:
            with st.container(key="card_idle"):
                eyebrow("Ход работы")
                empty("Здесь появятся журнал и результат запуска.")
        if not busy:
            render_history()
    with right:
        render_files_card()
        render_keys_card()


def render_history() -> None:
    runs = recent_runs()
    if not runs:
        return
    with st.container(key="card_history"):
        eyebrow("Недавние задачи", "нажмите, чтобы повторить")
        for index, (when, task) in enumerate(runs):
            st.button(
                f"{when} · {task}",
                key=f"hist_{index}",
                on_click=set_task,
                args=(task,),
                width="stretch",
                help=task,
            )


def render_files_card() -> None:
    folder = workspace_dir()
    with st.container(key="card_files"):
        try:
            files = list_files(folder) if folder.is_dir() else []
        except OSError:
            files = []
        eyebrow("Файлы", f"{folder.name}/")
        if files:
            rows = "".join(
                f'<div class="row">{svg("file")}<span class="name">{html.escape(name)}</span></div>'
                for name in files[:5]
            )
            st.markdown(f'<div class="rows">{rows}</div>', unsafe_allow_html=True)
            if len(files) > 5:
                st.caption(f"и ещё {len(files) - 5}")
            st.button(
                "Открыть файлы",
                on_click=go,
                args=("files",),
                type="tertiary",
            )
        else:
            st.caption("Пока пусто. Перед каждой перезаписью сохраняется копия в backups/.")


def render_keys_card() -> None:
    keys = st.session_state.api_keys
    filled = [label for label, env, _hint in KEY_LABELS if str(keys.get(env) or "").strip()]
    shown = filled or [label for label, _env, _hint in KEY_LABELS[:2]]
    with st.container(key="card_keys"):
        eyebrow("Ключи API", f"{len(filled)} из {len(KEY_LABELS)}")
        rows = []
        for label in shown:
            ok = label in filled
            rows.append(
                f'<div class="row"><span class="dot {"ok" if ok else ""}"></span>'
                f'<span class="label">{html.escape(label)}</span>'
                f'<span class="state {"ok" if ok else ""}">{"задан" if ok else "не задан"}</span></div>'
            )
        st.markdown(f'<div class="rows">{"".join(rows)}</div>', unsafe_allow_html=True)
        st.button(
            "Управлять ключами",
            on_click=go,
            args=("settings",),
            type="tertiary",
        )


def start_run(cfg: dict) -> None:
    task = str(st.session_state.task or "").strip()
    if not task:
        st.session_state.last_run = {"outcome": "failed", "error": "Опишите задачу — поле пустое."}
        return
    folder = workspace_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        st.session_state.last_run = {"outcome": "failed", "error": f"Папка недоступна: {exc}"}
        return
    persist()
    st.session_state.last_run = None
    st.session_state.job = RunJob(
        task=task,
        results_dir=RESULTS,
        keep_awake=bool(st.session_state.keep_awake),
        keep_display=bool(st.session_state.keep_display),
        workspace=str(folder),
        backup_dir=str(BACKUPS),
        api_keys=dict(st.session_state.api_keys),
        config=cfg,
        max_steps=int(st.session_state.max_steps),
        shell_timeout=int(st.session_state.shell_timeout),
        overrides={k: dict(v) for k, v in st.session_state.agent_overrides.items()},
        pipeline_name=st.session_state.pipeline,
    ).start()


def render_progress() -> None:
    job: RunJob | None = st.session_state.job
    if job is None:
        return

    @st.fragment(run_every=1.0)
    def live() -> None:
        current: RunJob | None = st.session_state.job
        if current is None:
            return
        if not current.running:
            finish_run(current)
            st.rerun()
        index, total, name = current.step
        elapsed = duration((datetime.now() - current.started).total_seconds())
        with st.container(key="live_panel"):
            head, action = st.columns([4, 1], vertical_alignment="center")
            with head:
                if current.stopping:
                    status_line(
                        "live",
                        "Останавливаю…",
                        "прерываю команду; ответ модели, который уже ушёл, не жду",
                    )
                elif total:
                    status_line("live", f"{name} работает", f"шаг {index} из {total} · {elapsed}")
                else:
                    status_line("live", "Запускаю…", elapsed)
            action.button(
                "Остановить",
                key="stop_run",
                on_click=current.stop,
                disabled=current.stopping,
                width="stretch",
            )
            st.code("\n".join(current.logs[-14:]) or "…", language="text")

    live()


def result_body(result: str) -> str:
    """The report without its two technical header lines; the saved file keeps them."""
    lines = result.splitlines()
    while lines and (lines[0].startswith("# ") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines)


def finish_run(job: RunJob) -> None:
    seconds = ((job.finished or job.started) - job.started).total_seconds()
    st.session_state.last_run = {
        "outcome": job.outcome,
        "when": f"{job.started:%H:%M}",
        "took": duration(seconds),
        "logs": list(job.logs),
        "result": result_body(job.result),
        "report": job.report(),
        "error": job.error,
        "traceback": job.traceback,
        "file_name": job.report_path.name if job.report_path else "run.md",
    }
    st.session_state.job = None


def render_result() -> None:
    last = st.session_state.last_run
    if not last or st.session_state.job is not None:
        return
    outcome = last.get("outcome")
    with st.container(key="result_panel"):
        detail = " · ".join(bit for bit in (last.get("when"), last.get("took")) if bit)
        if outcome == "ok":
            status_line("ok", "Готово", detail)
        elif outcome == "stopped":
            status_line("", "Остановлено", detail)
        else:
            status_line("bad", "Не получилось", detail)
        if last.get("error"):
            st.error(last["error"])
        if last.get("result"):
            st.markdown(last["result"])
        if last.get("traceback"):
            with st.expander("Техническая подробность"):
                st.code(last["traceback"], language="text")
        if last.get("logs"):
            with st.expander("Журнал"):
                st.code("\n".join(last["logs"][-200:]), language="text")
        if last.get("report"):
            left, right, _rest = st.columns([1, 1, 2])
            left.download_button(
                "Скачать отчёт",
                data=last["report"],
                file_name=last.get("file_name") or "run.md",
                mime="text/markdown",
                width="stretch",
            )
            right.button("Открыть файлы", on_click=go, args=("files",), width="stretch")


# ---------- agents ----------


def render_agents(cfg: dict, catalog: dict, model_choices: list[str]) -> None:
    page_head("Агенты", "Роли и модели", "У каждой роли своя модель. Изменения сохраняются сразу.")
    agents_cfg = cfg.get("agents") or {}
    if not agents_cfg:
        empty("В config/agents.yaml нет ролей.")
        return
    recommendations = cfg.get("recommendations") or {}
    overrides = st.session_state.agent_overrides

    def update(agent_id: str, field: str, widget_key: str) -> None:
        overrides[agent_id][field] = st.session_state[widget_key]
        persist()

    agent_ids = list(agents_cfg)
    for start in range(0, len(agent_ids), 3):
        for column, agent_id in zip(st.columns(3, gap="medium"), agent_ids[start : start + 3]):
            agent_cfg = agents_cfg[agent_id]
            current = overrides[agent_id]
            with column, st.container(key=f"card_{agent_id}"):
                key = f"w_on_{agent_id}"
                st.toggle(
                    str(agent_cfg.get("name", agent_id)),
                    value=bool(current["enabled"]),
                    key=key,
                    on_change=update,
                    args=(agent_id, "enabled", key),
                )
                st.caption(agent_cfg.get("description", ""))
                key = f"w_model_{agent_id}"
                suggested = [
                    str((catalog.get(item) or {}).get("name") or item)
                    for item in recommendations.get(agent_id) or []
                    if item in catalog
                ]
                st.selectbox(
                    "Модель",
                    model_choices,
                    index=model_choices.index(current["model"]),
                    format_func=lambda item: str((catalog.get(item) or {}).get("name") or item),
                    key=key,
                    on_change=update,
                    args=(agent_id, "model", key),
                    label_visibility="collapsed",
                    help=("Подходят: " + ", ".join(suggested)) if suggested else None,
                )
                meta = catalog.get(current["model"]) or {}
                if meta:
                    st.markdown(
                        badge(str(meta.get("billing") or ""))
                        + f'<span class="tag quiet">{html.escape(format_price(meta))}</span>',
                        unsafe_allow_html=True,
                    )
                key = f"w_temp_{agent_id}"
                st.slider(
                    "Температура",
                    0.0,
                    1.0,
                    value=float(current["temperature"]),
                    step=0.05,
                    key=key,
                    on_change=update,
                    args=(agent_id, "temperature", key),
                    help="Ниже — строже и предсказуемее, выше — свободнее.",
                )

    def reset() -> None:
        for agent_id, agent_cfg in agents_cfg.items():
            overrides[agent_id] = default_override(agent_cfg, model_choices)
            if overrides[agent_id]["model"] not in model_choices:
                overrides[agent_id]["model"] = model_choices[0]
            for prefix in ("w_on_", "w_model_", "w_temp_"):
                st.session_state.pop(prefix + agent_id, None)
        persist()

    st.button("Вернуть как было", type="tertiary", on_click=reset)


# ---------- models ----------


def passes_billing(meta: dict, mode: str) -> bool:
    if mode == "free":
        return is_free_option(meta)
    if mode == "paid":
        return meta.get("billing") == "paid"
    if mode == "local":
        return meta.get("billing") == "local"
    return True


def render_models(catalog: dict) -> None:
    page_head("Модели", "Каталог и цены")
    verified = max((str(m.get("last_verified") or "") for m in catalog.values()), default="")
    st.markdown(
        f'<p class="lead">Цены в долларах за 1M токенов, вход / выход. Сверено {html.escape(verified)}. '
        "У Free tier показан платный тариф после бесплатной квоты.</p>",
        unsafe_allow_html=True,
    )
    left, right = st.columns([2, 3], vertical_alignment="bottom")
    query = left.text_input(
        "Поиск", placeholder="Название, провайдер или ID", label_visibility="collapsed"
    )
    choice = right.pills(
        "Доступ", list(BILLING_FILTERS), default="Все", label_visibility="collapsed"
    )
    mode = BILLING_FILTERS.get(choice or "Все", "all")
    needle = query.strip().lower()
    matched = []
    for model_key, meta in catalog.items():
        if not passes_billing(meta, mode):
            continue
        haystack = " ".join(
            str(meta.get(field) or "") for field in ("name", "provider", "litellm", "summary")
        )
        if needle and needle not in (model_key + " " + haystack).lower():
            continue
        matched.append((model_key, meta))
    if not matched:
        empty("Ничего не нашлось. Измените запрос или верните фильтр на «Все».")
        return
    rows = []
    for _key, meta in matched:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(meta.get('name')))}<br><small>{html.escape(str(meta.get('litellm')))}</small></td>"
            f"<td>{html.escape(str(meta.get('provider')))}</td>"
            f"<td>{badge(str(meta.get('billing') or ''))}</td>"
            f'<td class="num">{html.escape(format_price(meta).replace(" за 1M", ""))}</td>'
            f'<td class="num">{html.escape(str(meta.get("context")))}</td>'
            "</tr>"
        )
    st.markdown(
        '<div class="sheet-wrap"><table class="sheet"><thead><tr>'
        "<th>Модель</th><th>Провайдер</th><th>Доступ</th><th>Цена</th><th>Контекст</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Показано {len(matched)} из {len(catalog)}.")
    with st.expander("Подробности о модели"):
        labels = {model_key: str(meta.get("name")) for model_key, meta in matched}
        selected = st.selectbox(
            "Модель", list(labels), format_func=labels.get, label_visibility="collapsed"
        )
        meta = catalog[selected]
        st.markdown(
            badge(str(meta.get("billing") or ""))
            + f" **{html.escape(str(meta.get('name')))}** · {html.escape(str(meta.get('provider')))}",
            unsafe_allow_html=True,
        )
        st.markdown(meta.get("summary") or "")
        st.markdown(
            f"- **ID:** `{meta.get('litellm')}`\n"
            f"- **Цена:** {format_price(meta)}. {meta.get('price_note')}\n"
            f"- **Контекст:** {meta.get('context')}\n"
            f"- **Для чего:** {meta.get('best_for')}\n"
            f"- **Источник:** {meta.get('source')} · проверено {meta.get('last_verified')}"
        )


# ---------- files ----------


def list_files(folder: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            found.append(str((Path(current) / name).relative_to(folder)))
            if len(found) >= FILE_LIMIT:
                return found
    return found


def render_files() -> None:
    page_head("Файлы", "Папка проекта")
    folder = workspace_dir()
    st.markdown(f'<p class="lead">{html.escape(str(folder))}</p>', unsafe_allow_html=True)
    if not folder.is_dir():
        empty("Папки ещё нет. Она появится после первого запуска.")
        return
    try:
        files = list_files(folder)
    except OSError as exc:
        st.error(f"Не удалось прочитать папку: {exc}")
        return
    if not files:
        empty("Папка пустая. Файлы появятся здесь, когда агенты их создадут.")
        return
    chosen = st.selectbox("Файл", files, label_visibility="collapsed")
    if len(files) >= FILE_LIMIT:
        st.caption(f"Показаны первые {FILE_LIMIT} файлов.")
    from tools.filesystem import WorkspaceFS

    try:
        text = WorkspaceFS(folder, BACKUPS).read_file(chosen)
    except (OSError, PermissionError) as exc:
        st.error(str(exc))
        return
    suffix = Path(chosen).suffix.lower().lstrip(".")
    language = {"py": "python", "js": "javascript", "ts": "typescript", "md": "markdown"}.get(
        suffix, suffix if suffix in {"json", "yaml", "toml", "html", "css", "sql"} else "text"
    )
    st.code(text, language=language)


# ---------- settings ----------


def render_settings() -> None:
    page_head("Настройки", "Ключи и параметры")

    st.subheader("Оформление")

    def set_palette() -> None:
        st.session_state.palette = resolve_palette(st.session_state.get("w_palette"))
        persist()

    st.segmented_control(
        "Палитра",
        PALETTE_ORDER,
        default=resolve_palette(st.session_state.palette),
        format_func=lambda item: PALETTE_LABELS[item],
        key="w_palette",
        on_change=set_palette,
        help="«Графит» — тёмно-серые тона с ярким акцентом, «Тёплая» — исходные цвета студии.",
    )

    st.subheader("Ключи API")
    st.caption(
        "Хватит одного. Ключи лежат в файле .env рядом с программой и никуда не отправляются, "
        "кроме самого провайдера."
    )
    keys = st.session_state.api_keys
    with st.form("keys_form", border=False):
        columns = st.columns(2)
        entered = {}
        for index, (label, env, hint) in enumerate(KEY_LABELS):
            entered[env] = columns[index % 2].text_input(
                label, value=keys.get(env, ""), type="password", placeholder=hint
            )
        if st.form_submit_button("Сохранить ключи", type="primary"):
            st.session_state.api_keys = {env: value.strip() for env, value in entered.items()}
            save_keys_to_env(st.session_state.api_keys)
            st.toast("Ключи сохранены")
            st.rerun()

    st.subheader("Запуск")
    left, right = st.columns(2)
    with left:
        bound(
            st.slider,
            "Шагов на одну роль",
            "max_steps",
            min_value=5,
            max_value=80,
            help="Сколько раз роль может обратиться к модели за один запуск.",
        )
        bound(st.toggle, "Не давать компьютеру уснуть", "keep_awake")
    with right:
        bound(
            st.slider,
            "Лимит на команду, сек",
            "shell_timeout",
            min_value=10,
            max_value=300,
            help="Команда агента в терминале прерывается, если идёт дольше.",
        )
        bound(st.toggle, "Держать экран включённым", "keep_display")
    bound(
        st.text_input,
        "Адрес Ollama",
        "ollama_base",
        help="Нужен только для локальных моделей.",
    )

    with st.expander("Проверить SSH-подключение"):
        render_ssh()
    with st.expander("Справка"):
        render_help()


def render_ssh() -> None:
    st.caption("Команда выполнится на указанном компьютере. Вход по ключу, пароль не спрашивается.")
    with st.form("ssh_form", border=False):
        col1, col2 = st.columns(2)
        host = col1.text_input("Хост", placeholder="192.168.1.10")
        user = col2.text_input("Пользователь", value="pi")
        key_path = col1.text_input("Путь к SSH-ключу", placeholder="~/.ssh/id_ed25519")
        port = col2.number_input("Порт", value=22, min_value=1, max_value=65535)
        command = st.text_input("Команда", value="uname -a")
        submitted = st.form_submit_button("Выполнить")
    if not submitted:
        return
    if not host.strip() or not command.strip():
        st.error("Нужны хост и команда.")
        return
    from tools.remote import RemoteDevice, RemoteManager

    manager = RemoteManager()
    manager.add_device(
        RemoteDevice(
            name="check",
            host=host.strip(),
            user=user.strip() or "root",
            port=int(port),
            key_path=str(Path(key_path).expanduser()) if key_path.strip() else None,
        )
    )
    with st.spinner("Подключаюсь…"):
        output = manager.run_ssh("check", command.strip())
    st.code(output, language="text")


def render_help() -> None:
    st.markdown(
        """
**С чего начать.** Получите бесплатный ключ в Google AI Studio или OpenRouter, вставьте его выше
и сохраните. Затем откройте «Запуск», опишите задачу и нажмите «Запустить».

**Локальные модели.** Установите [Ollama](https://ollama.com/library), скачайте веса
(`ollama pull gemma4`) и выберите модель с пометкой Local в разделе «Агенты». Ключ не нужен.

**Где что лежит**

| Что | Файл |
| --- | --- |
| Ключи | `.env` |
| Выбранные модели, режим, папка, тема | `user_settings.json` |
| Каталог моделей и цены | `config/models_catalog.yaml` |
| Промпты ролей и режимы | `config/agents.yaml` |
| Отчёты запусков | `results/` |
| Копии файлов перед изменением | `backups/` |

**Безопасность.** Файловые инструменты агентов не выходят из выбранной папки, перед перезаписью и
удалением делается копия. Команды в терминале стартуют в этой папке, не видят ваших ключей API и
проходят через список запрещённых шаблонов — но это страховка, а не песочница: запускайте агентов
в папке, которую не жалко, и не давайте им задач от имени администратора.
"""
    )


# ---------- entry ----------


def main() -> None:
    st.set_page_config(page_title="Улей", page_icon="⬡", layout="wide")
    config_path = ROOT / "config" / "agents.yaml"
    cfg = load_config(config_path) if config_path.exists() else {}
    catalog = load_models_catalog()
    model_choices = sorted_model_keys(runnable_models(catalog)) or ["gemini_38_flash"]
    init_state(cfg, load_user_settings(), model_choices)
    st.markdown(
        theme_stylesheet(st.session_state.theme, st.session_state.palette), unsafe_allow_html=True
    )
    pipelines = cfg.get("pipelines") or {"single": {"steps": ["developer"]}}
    render_sidebar()
    screen = resolve_screen(st.session_state.screen)
    if screen == "agents":
        render_agents(cfg, catalog, model_choices)
    elif screen == "models":
        render_models(catalog)
    elif screen == "files":
        render_files()
    elif screen == "settings":
        render_settings()
    else:
        render_run(cfg, catalog, pipelines)


if __name__ == "__main__":
    main()
