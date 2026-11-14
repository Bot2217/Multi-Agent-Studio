"""Ulei studio: roles, pipelines, and the model catalog."""

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
from core.i18n import role_word, set_language, t
from core.orchestrator import load_config
from core.runner import RunJob
from core.themes import (
    LEGACY_APPEARANCE,
    PALETTE_ORDER,
    SCREEN_IDS,
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
    ("Google", "GOOGLE_API_KEY", "key.google"),
    ("OpenRouter", "OPENROUTER_API_KEY", "key.openrouter"),
    ("Anthropic", "ANTHROPIC_API_KEY", "key.anthropic"),
    ("OpenAI", "OPENAI_API_KEY", "key.openai"),
    ("xAI", "XAI_API_KEY", "key.xai"),
    ("DeepSeek", "DEEPSEEK_API_KEY", "key.deepseek"),
    ("Groq", "GROQ_API_KEY", "key.groq"),
    ("Mistral", "MISTRAL_API_KEY", "key.mistral"),
    ("Cerebras", "CEREBRAS_API_KEY", "key.cerebras"),
]

PIPELINE_IDS = ("code_only", "full", "research_code", "single")

BILLING_FILTERS = ("all", "free", "paid", "local")

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
    "ollama_base": "http://127.0.0.1:11434",
    "ollama_models_dir": "",
    "language": "auto",
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
    label = (
        t(f"billing.{billing}") if billing in BILLING_BADGE else (billing or t("billing.unknown"))
    )
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

EXAMPLE_KEYS = ("example.hello", "example.readme", "example.todo")


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
        return t("time.seconds", n=seconds)
    return t("time.minutes", m=seconds // 60, s=seconds % 60)


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
            f"<div><b>Улей</b><small>{html.escape(t('brand.studio'))}</small></div></div>",
            unsafe_allow_html=True,
        )
        for screen_id in SCREEN_IDS:
            st.button(
                t(f"nav.{screen_id}"),
                key=f"nav_{screen_id}",
                type="primary" if screen_id == current else "secondary",
                width="stretch",
                on_click=go,
                args=(screen_id,),
            )
        st.markdown(
            f'<p class="side-label">{html.escape(t("theme.label"))}</p>', unsafe_allow_html=True
        )

        def set_theme() -> None:
            st.session_state.theme = resolve_theme(st.session_state.get("w_theme"))
            persist()

        st.segmented_control(
            t("theme.label"),
            THEME_ORDER,
            default=resolve_theme(st.session_state.get("theme")),
            format_func=lambda item: t(f"theme.{item}"),
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
    eyebrow(t("chain.title"), f"{count} {role_word(count)}")
    items = []
    for index, agent_id in enumerate(active, 1):
        model_key = st.session_state.agent_overrides.get(agent_id, {}).get("model", "")
        meta = catalog.get(model_key) or {}
        name = html.escape(str(agents_cfg.get(agent_id, {}).get("name", agent_id)))
        model_name = html.escape(str(meta.get("name") or model_key))
        missing = model_key in no_key
        tag = f'<span class="tag quiet">{html.escape(t("chain.no_key"))}</span>' if missing else ""
        items.append(
            f'<li class="{"nokey" if missing else ""}"><span class="num">{index}</span>'
            f'<span class="who"><b>{name}</b><small>{model_name}</small></span>{tag}</li>'
        )
    if items:
        st.markdown(f'<ol class="steps">{"".join(items)}</ol>', unsafe_allow_html=True)
    else:
        empty(t("chain.all_off"))


def render_folder_picker() -> None:
    folder = workspace_dir()
    with st.popover(t("folder.button", name=folder.name or folder), width="stretch"):
        st.caption(t("folder.caption"))

        def set_path() -> None:
            st.session_state.workspace_path = st.session_state.w_workspace_path.strip()
            persist()

        st.text_input(
            t("folder.path"),
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
            shown = t("folder.preset_project") if label == "project" else label
            column.button(shown, key=f"ws_{label}", on_click=choose, args=(path,), width="stretch")
        if not folder.is_dir():
            st.caption(t("folder.missing"))


def render_run(cfg: dict, catalog: dict, pipelines: dict) -> None:
    job: RunJob | None = st.session_state.job
    busy = bool(job and job.running)
    free = sum(1 for meta in catalog.values() if is_free_option(meta))
    page_head(
        t("run.section"),
        t("run.title"),
        tags=((t("run.catalog_count", n=len(catalog)), True), (t("run.free_count", n=free), False)),
    )
    _steps, active = pipeline_steps(cfg, pipelines)
    model_keys = [st.session_state.agent_overrides[a]["model"] for a in active]
    missing = missing_credentials(model_keys, st.session_state.api_keys, catalog, cfg)
    no_key = {model_key for model_key, _provider, _env in missing}
    names = list(pipelines)

    left, right = st.columns([2, 1], gap="medium")
    with left, st.container(key="card_task"):
        eyebrow(t("run.task"))
        bound(
            st.text_area,
            t("run.task"),
            "task",
            save=False,
            height=120,
            placeholder=t("run.placeholder"),
            label_visibility="collapsed",
            disabled=busy,
        )
        if not str(st.session_state.task).strip() and not busy:
            for index, key in enumerate(EXAMPLE_KEYS):
                st.button(
                    t(key),
                    key=f"ex_{index}",
                    on_click=set_task,
                    args=(t(key),),
                    width="stretch",
                    help=t("run.use_example", text=t(key)),
                )
        mode_col, folder_col = st.columns([3, 2], vertical_alignment="bottom")
        with mode_col:

            def set_pipeline() -> None:
                st.session_state.pipeline = st.session_state.w_pipeline
                persist()

            st.selectbox(
                t("run.mode"),
                names,
                index=names.index(st.session_state.pipeline),
                format_func=lambda name: t(f"pipeline.{name}") if name in PIPELINE_IDS else name,
                key="w_pipeline",
                on_change=set_pipeline,
                disabled=busy,
                label_visibility="collapsed",
            )
        with folder_col:
            render_folder_picker()

        blocked = ""
        if not active:
            blocked = t("run.roles_off")
            st.warning(blocked + " " + t("run.roles_off_hint"))
        elif missing:
            envs = ", ".join(dict.fromkeys(env for _m, _p, env in missing))
            if len(no_key) == len(set(model_keys)):
                blocked = t("run.no_key_all")
                text = t("run.no_key_all_hint", envs=envs)
            else:
                text = t("run.no_key_some", envs=envs)
            note, action = st.columns([3, 1], vertical_alignment="center")
            note.warning(text)
            action.button(t("run.add_key"), on_click=go, args=("settings",), width="stretch")

        if st.button(
            t("run.start"),
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
            t("run.configure"),
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
                eyebrow(t("run.progress_title"))
                empty(t("run.progress_empty"))
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
        eyebrow(t("run.recent"), t("run.recent_hint"))
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
        eyebrow(t("run.files"), f"{folder.name}/")
        if files:
            rows = "".join(
                f'<div class="row">{svg("file")}<span class="name">{html.escape(name)}</span></div>'
                for name in files[:5]
            )
            st.markdown(f'<div class="rows">{rows}</div>', unsafe_allow_html=True)
            if len(files) > 5:
                st.caption(t("run.files_more", n=len(files) - 5))
            st.button(
                t("run.open_files"),
                on_click=go,
                args=("files",),
                type="tertiary",
            )
        else:
            st.caption(t("run.files_empty"))


def render_keys_card() -> None:
    keys = st.session_state.api_keys
    filled = [label for label, env, _hint in KEY_LABELS if str(keys.get(env) or "").strip()]
    shown = filled or [label for label, _env, _hint in KEY_LABELS[:2]]
    with st.container(key="card_keys"):
        eyebrow(t("run.keys"), t("run.keys_count", filled=len(filled), total=len(KEY_LABELS)))
        rows = []
        for label in shown:
            ok = label in filled
            rows.append(
                f'<div class="row"><span class="dot {"ok" if ok else ""}"></span>'
                f'<span class="label">{html.escape(label)}</span>'
                f'<span class="state {"ok" if ok else ""}">{html.escape(t("run.key_set") if ok else t("run.key_missing"))}</span></div>'
            )
        st.markdown(f'<div class="rows">{"".join(rows)}</div>', unsafe_allow_html=True)
        st.button(
            t("run.manage_keys"),
            on_click=go,
            args=("settings",),
            type="tertiary",
        )


def session_runtime():
    from core.ollama_runtime import OllamaRuntime

    runtime = st.session_state.get("ollama_runtime")
    custom = str(st.session_state.get("ollama_models_dir") or "").strip()
    base = str(st.session_state.get("ollama_base") or "http://127.0.0.1:11434").strip()
    if not isinstance(runtime, OllamaRuntime):
        runtime = OllamaRuntime(
            models_dir=Path(custom).expanduser() if custom else None,
            base_url=base,
        )
        st.session_state.ollama_runtime = runtime
        return runtime
    runtime.base_url = base.rstrip("/")
    if custom:
        runtime.set_models_dir(Path(custom).expanduser())
    return runtime


def local_model_names(cfg: dict) -> list[str]:
    from core.catalog import provider_of, resolve_model

    pipelines = cfg.get("pipelines") or {}
    _steps, active = pipeline_steps(cfg, pipelines)
    catalog = st.session_state.get("model_catalog") or {}
    names: list[str] = []
    for agent_id in active:
        key = st.session_state.agent_overrides.get(agent_id, {}).get("model", "")
        litellm = resolve_model(str(key), cfg, catalog)
        if provider_of(litellm) == "ollama" and "/" in litellm:
            names.append(litellm.split("/", 1)[1])
    return names


def start_run(cfg: dict) -> None:
    task = str(st.session_state.task or "").strip()
    if not task:
        st.session_state.last_run = {"outcome": "failed", "error": t("run.empty_task")}
        return
    folder = workspace_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        st.session_state.last_run = {"outcome": "failed", "error": t("run.folder_error", error=exc)}
        return
    local_names = local_model_names(cfg)
    if local_names:
        runtime = session_runtime()
        try:
            with st.spinner(t("run.starting_local")):
                runtime.ensure_running()
                for name in local_names:
                    runtime.warmup(name)
        except Exception as exc:
            from core.local_runtime import LocalRuntimeError

            message = exc.message if isinstance(exc, LocalRuntimeError) else str(exc)
            st.session_state.last_run = {"outcome": "failed", "error": message}
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
                        t("run.stopping"),
                        t("run.stopping_detail"),
                    )
                elif total:
                    status_line(
                        "live",
                        t("run.working", name=name),
                        t("run.step", index=index, total=total, elapsed=elapsed),
                    )
                else:
                    status_line("live", t("run.booting"), elapsed)
            action.button(
                t("run.stop"),
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
            status_line("ok", t("run.done"), detail)
        elif outcome == "stopped":
            status_line("", t("run.stopped"), detail)
        else:
            status_line("bad", t("run.failed"), detail)
        if last.get("error"):
            st.error(last["error"])
        if last.get("result"):
            st.markdown(last["result"])
        if last.get("traceback"):
            with st.expander(t("run.technical")):
                st.code(last["traceback"], language="text")
        if last.get("logs"):
            with st.expander(t("run.log")):
                st.code("\n".join(last["logs"][-200:]), language="text")
        if last.get("report"):
            left, right, _rest = st.columns([1, 1, 2])
            left.download_button(
                t("run.download"),
                data=last["report"],
                file_name=last.get("file_name") or "run.md",
                mime="text/markdown",
                width="stretch",
            )
            right.button(t("run.open_files"), on_click=go, args=("files",), width="stretch")


# ---------- agents ----------


def render_agents(cfg: dict, catalog: dict, model_choices: list[str]) -> None:
    page_head(t("agents.section"), t("agents.title"), t("agents.sub"))
    agents_cfg = cfg.get("agents") or {}
    if not agents_cfg:
        empty(t("agents.empty"))
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
                    t("agents.model"),
                    model_choices,
                    index=model_choices.index(current["model"]),
                    format_func=lambda item: str((catalog.get(item) or {}).get("name") or item),
                    key=key,
                    on_change=update,
                    args=(agent_id, "model", key),
                    label_visibility="collapsed",
                    help=t("agents.suggested", names=", ".join(suggested)) if suggested else None,
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
                    t("agents.temperature"),
                    0.0,
                    1.0,
                    value=float(current["temperature"]),
                    step=0.05,
                    key=key,
                    on_change=update,
                    args=(agent_id, "temperature", key),
                    help=t("agents.temperature_help"),
                )

    def reset() -> None:
        for agent_id, agent_cfg in agents_cfg.items():
            overrides[agent_id] = default_override(agent_cfg, model_choices)
            if overrides[agent_id]["model"] not in model_choices:
                overrides[agent_id]["model"] = model_choices[0]
            for prefix in ("w_on_", "w_model_", "w_temp_"):
                st.session_state.pop(prefix + agent_id, None)
        persist()

    st.button(t("agents.reset"), type="tertiary", on_click=reset)


# ---------- local models ----------


class _Transfer:
    def __init__(self, work) -> None:
        import threading

        self.message = t("run.booting")
        self.completed = 0
        self.total = 0
        self.error = ""
        self.outcome = "running"
        self._cancel = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(work,), daemon=True)
        self._thread.start()

    @property
    def running(self) -> bool:
        return self.outcome == "running"

    def cancel(self) -> None:
        self._cancel.set()

    def progress(self, status: str, completed: int, total: int) -> None:
        self.message = status or t("ollama.pulling")
        self.completed = completed
        self.total = total

    def _run(self, work) -> None:
        from core.local_runtime import LocalRuntimeError

        try:
            work(self.progress, self._cancel.is_set)
            self.outcome = "cancelled" if self._cancel.is_set() else "ok"
        except LocalRuntimeError as exc:
            self.error = exc.message
            self.outcome = "failed"
        except Exception as exc:
            self.error = str(exc) or t("ollama.download_failed")
            self.outcome = "failed"


def render_local() -> None:
    from core.local_runtime import (
        assess_fit,
        default_models_dir,
        format_bytes,
        load_library,
    )
    from core.ollama_runtime import asset_name

    runtime = session_runtime()
    probe = runtime.probe()
    page_head(
        t("local.section"),
        t("local.title"),
        t("local.sub"),
    )
    if probe.running:
        who = t("local.running_external") if probe.external else t("local.running_ours")
        status_line("ok", t("local.running"), who)
    elif probe.error:
        status_line("bad", "Ollama", t(f"ollama.{probe.error}"))
    elif probe.binary:
        status_line("live", t("local.installed"), t("local.installed_detail"))
    else:
        status_line("bad", t("local.missing"), t("local.missing_detail"))
    if probe.gpu_note:
        st.caption(probe.gpu_note)

    custom = str(st.session_state.get("ollama_models_dir") or "").strip()
    models_path = Path(custom).expanduser() if custom else default_models_dir()
    free = runtime.disk_free()
    ram = runtime.ram_free()
    st.caption(
        t("local.disk_line", path=models_path, free=format_bytes(free))
        + (
            t("local.ram_suffix", ram=format_bytes(ram))
            if ram is not None
            else t("local.disk_only_end")
        )
    )

    job = st.session_state.get("local_job")
    if job is not None and job.running:

        @st.fragment(run_every=0.6)
        def live_transfer() -> None:
            current = st.session_state.get("local_job")
            if current is None:
                return
            if not current.running:
                st.rerun()
            ratio = 0.0
            if current.total:
                ratio = min(1.0, current.completed / current.total)
            st.progress(ratio, text=current.message or t("local.downloading"))
            st.button(t("local.cancel"), on_click=current.cancel, key="cancel_local")

        live_transfer()
    elif job is not None and job.error:
        st.error(job.error)

    if not probe.running and not (job and job.running) and probe.error != "port_busy":
        if probe.binary:
            if st.button(t("local.start"), type="primary"):
                try:
                    runtime.ensure_running()
                except Exception as exc:
                    st.error(getattr(exc, "message", str(exc)))
                else:
                    st.rerun()
        elif st.button(t("local.install"), type="primary"):
            try:
                asset_name()
            except Exception as exc:
                st.error(str(exc))
            else:

                def work(progress, cancel):
                    runtime.install(progress, cancel)
                    runtime.ensure_running()

                st.session_state.local_job = _Transfer(work)
                st.rerun()

    installed = []
    if probe.running:
        try:
            installed = runtime.installed_models()
        except Exception as exc:
            st.error(str(exc))
    st.subheader(t("local.installed_heading"))
    if not installed:
        empty(t("local.none"))
    else:
        for model in installed:
            row, action = st.columns([4, 1], vertical_alignment="center")
            row.markdown(f"**{html.escape(model.name)}** · {format_bytes(model.size_bytes)}")
            if action.button(t("local.delete"), key=f"del_{model.name}"):
                try:
                    runtime.delete_model(model.name)
                    st.toast(t("local.deleted", name=model.name))
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    library = st.session_state.get("ollama_library")
    if library is None:
        cache = runtime.home / "library.html"

        def fetch() -> str:
            from urllib.request import Request, urlopen

            request = Request("https://ollama.com/library", headers={"User-Agent": "ulei"})
            with urlopen(request, timeout=4) as response:
                return response.read().decode("utf-8", errors="replace")

        library = load_library(fetch=fetch, cache=cache)
        st.session_state.ollama_library = library
    st.subheader(t("local.catalog"))
    st.caption(t("local.catalog_hint"))
    for model in library:
        with st.container(border=True):
            st.markdown(f"**{html.escape(model.name)}**")
            if model.summary:
                st.caption(model.summary)
            tags = [item.tag for item in model.tags] or ["latest"]
            tag = st.selectbox(
                t("local.tag"), tags, key=f"tag_{model.model_id}", label_visibility="collapsed"
            )
            chosen = next((item for item in model.tags if item.tag == tag), model.tags[0])
            fit = assess_fit(chosen.size_bytes, free, chosen.ram_bytes, ram)
            detail = format_bytes(chosen.size_bytes)
            if chosen.ram_bytes:
                detail += t("local.ram_about", size=format_bytes(chosen.ram_bytes))
            st.caption(detail)
            if fit.message:
                st.warning(fit.message)
            allow = True
            if fit.disk_ok and not fit.ram_ok:
                allow = st.checkbox(t("local.anyway"), key=f"anyway_{model.model_id}")
            reference = model.reference(tag)
            busy = bool(job and job.running)
            if st.button(
                t("local.install_model"),
                key=f"pull_{model.model_id}",
                disabled=busy or not fit.disk_ok or not allow or not probe.running,
            ):

                def work(progress, cancel, name=reference):
                    runtime.pull(name, progress, cancel)

                st.session_state.local_job = _Transfer(work)
                st.rerun()
            if not probe.running:
                st.caption(t("local.need_server"))

    with st.expander(t("local.log")):
        text = runtime.log_tail() or t("local.log_empty")
        st.code(text, language="text")


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
    page_head(t("models.section"), t("models.title"))
    verified = max((str(m.get("last_verified") or "") for m in catalog.values()), default="")
    st.markdown(
        f'<p class="lead">{html.escape(t("models.lead", date=verified))}</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([2, 3], vertical_alignment="bottom")
    query = left.text_input(
        t("models.search"), placeholder=t("models.search_placeholder"), label_visibility="collapsed"
    )
    choice = right.pills(
        t("models.access"),
        list(BILLING_FILTERS),
        default="all",
        format_func=lambda item: t(f"filter.{item}"),
        label_visibility="collapsed",
    )
    mode = choice or "all"
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
        empty(t("models.empty"))
        return
    rows = []
    for _key, meta in matched:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(meta.get('name')))}<br><small>{html.escape(str(meta.get('litellm')))}</small></td>"
            f"<td>{html.escape(str(meta.get('provider')))}</td>"
            f"<td>{badge(str(meta.get('billing') or ''))}</td>"
            f'<td class="num">{html.escape(format_price(meta).replace(t("price.suffix"), ""))}</td>'
            f'<td class="num">{html.escape(str(meta.get("context")))}</td>'
            "</tr>"
        )
    st.markdown(
        '<div class="sheet-wrap"><table class="sheet"><thead><tr>'
        "<th>"
        + "</th><th>".join(
            html.escape(t(key))
            for key in (
                "models.col_model",
                "models.col_provider",
                "models.col_access",
                "models.col_price",
                "models.col_context",
            )
        )
        + "</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.caption(t("models.shown", shown=len(matched), total=len(catalog)))
    with st.expander(t("models.details")):
        labels = {model_key: str(meta.get("name")) for model_key, meta in matched}
        selected = st.selectbox(
            t("models.col_model"),
            list(labels),
            format_func=labels.get,
            label_visibility="collapsed",
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
            f"- **{t('models.price_line')}:** {format_price(meta)}. {meta.get('price_note')}\n"
            f"- **{t('models.context_line')}:** {meta.get('context')}\n"
            f"- **{t('models.best_for')}:** {meta.get('best_for')}\n"
            f"- **{t('models.source_line')}:** {meta.get('source')} · {t('models.checked', date=meta.get('last_verified'))}"
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
    page_head(t("files.section"), t("files.title"))
    folder = workspace_dir()
    st.markdown(f'<p class="lead">{html.escape(str(folder))}</p>', unsafe_allow_html=True)
    if not folder.is_dir():
        empty(t("files.missing"))
        return
    try:
        files = list_files(folder)
    except OSError as exc:
        st.error(t("files.read_error", error=exc))
        return
    if not files:
        empty(t("files.empty"))
        return
    chosen = st.selectbox(t("files.file"), files, label_visibility="collapsed")
    if len(files) >= FILE_LIMIT:
        st.caption(t("files.limit", n=FILE_LIMIT))
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
    page_head(t("settings.section"), t("settings.title"))

    st.subheader(t("settings.appearance"))

    def set_palette() -> None:
        st.session_state.palette = resolve_palette(st.session_state.get("w_palette"))
        persist()

    st.segmented_control(
        t("settings.palette"),
        PALETTE_ORDER,
        default=resolve_palette(st.session_state.palette),
        format_func=lambda item: t(f"palette.{item}"),
        key="w_palette",
        on_change=set_palette,
        help=t("settings.palette_help"),
    )

    def set_language_choice() -> None:
        st.session_state.language = st.session_state.get("w_language") or "auto"
        set_language(st.session_state.language)
        persist()

    st.segmented_control(
        t("settings.language"),
        ("auto", "ru", "en"),
        default=st.session_state.get("language") or "auto",
        format_func=lambda item: t(f"lang.{item}"),
        key="w_language",
        on_change=set_language_choice,
        help=t("settings.language_help"),
    )

    st.subheader(t("settings.keys"))
    st.caption(t("settings.keys_help"))
    keys = st.session_state.api_keys
    with st.form("keys_form", border=False):
        columns = st.columns(2)
        entered = {}
        for index, (label, env, hint) in enumerate(KEY_LABELS):
            entered[env] = columns[index % 2].text_input(
                label, value=keys.get(env, ""), type="password", placeholder=t(hint)
            )
        if st.form_submit_button(t("settings.save_keys"), type="primary"):
            st.session_state.api_keys = {env: value.strip() for env, value in entered.items()}
            save_keys_to_env(st.session_state.api_keys)
            st.toast(t("settings.keys_saved"))
            st.rerun()

    st.subheader(t("settings.launch"))
    left, right = st.columns(2)
    with left:
        bound(
            st.slider,
            t("settings.max_steps"),
            "max_steps",
            min_value=5,
            max_value=80,
            help=t("settings.max_steps_help"),
        )
        bound(st.toggle, t("settings.keep_awake"), "keep_awake")
    with right:
        bound(
            st.slider,
            t("settings.shell_timeout"),
            "shell_timeout",
            min_value=10,
            max_value=300,
            help=t("settings.shell_timeout_help"),
        )
        bound(st.toggle, t("settings.keep_display"), "keep_display")
    bound(
        st.text_input,
        t("settings.ollama_base"),
        "ollama_base",
        help=t("settings.ollama_base_help"),
    )
    from core.local_runtime import default_models_dir

    custom = str(st.session_state.get("ollama_models_dir") or "").strip()
    models_path = Path(custom).expanduser() if custom else default_models_dir()
    bound(
        st.text_input,
        t("settings.ollama_dir"),
        "ollama_models_dir",
        help=t("settings.ollama_dir_help"),
    )
    st.caption(t("settings.ollama_dir_now", path=models_path))

    with st.expander(t("settings.ssh_check")):
        render_ssh()
    with st.expander(t("settings.help")):
        render_help()


def render_ssh() -> None:
    st.caption(t("ssh.caption"))
    with st.form("ssh_form", border=False):
        col1, col2 = st.columns(2)
        host = col1.text_input(t("ssh.host"), placeholder="192.168.1.10")
        user = col2.text_input(t("ssh.user"), value="pi")
        key_path = col1.text_input(t("ssh.key"), placeholder="~/.ssh/id_ed25519")
        port = col2.number_input(t("ssh.port"), value=22, min_value=1, max_value=65535)
        command = st.text_input(t("ssh.command"), value="uname -a")
        submitted = st.form_submit_button(t("ssh.run"))
    if not submitted:
        return
    if not host.strip() or not command.strip():
        st.error(t("ssh.need_both"))
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
    with st.spinner(t("ssh.connecting")):
        output = manager.run_ssh("check", command.strip())
    st.code(output, language="text")


def render_help() -> None:
    st.markdown(t("help.body"))


# ---------- entry ----------


def main() -> None:
    st.set_page_config(page_title="Улей", page_icon="⬡", layout="wide")
    config_path = ROOT / "config" / "agents.yaml"
    cfg = load_config(config_path) if config_path.exists() else {}
    user_set = load_user_settings()
    set_language(user_set.get("language", "auto"))
    catalog = load_models_catalog()
    try:
        from core.local_runtime import installed_catalog
        from core.ollama_runtime import OllamaRuntime

        custom = str(user_set.get("ollama_models_dir") or "").strip()
        base = str(user_set.get("ollama_base") or "http://127.0.0.1:11434")
        runtime = OllamaRuntime(
            models_dir=Path(custom).expanduser() if custom else None,
            base_url=base,
        )
        st.session_state.ollama_runtime = runtime
        if runtime.probe().running:
            catalog = {**catalog, **installed_catalog(runtime.installed_models())}
    except Exception:
        pass
    model_choices = sorted_model_keys(runnable_models(catalog)) or ["gemini_38_flash"]
    init_state(cfg, user_set, model_choices)
    set_language(st.session_state.get("language", "auto"))
    st.session_state.model_catalog = catalog
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
    elif screen == "local":
        render_local()
    elif screen == "files":
        render_files()
    elif screen == "settings":
        render_settings()
    else:
        render_run(cfg, catalog, pipelines)


if __name__ == "__main__":
    main()
