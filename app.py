"""Multi-Agent Studio"""
from __future__ import annotations
import os, sys
from datetime import datetime
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core.agent_runtime import AgentRuntime
from core.orchestrator import Orchestrator, load_config, KEY_ENV
from core.ui_helpers import (
    load_keys_from_env, save_keys_to_env, load_user_settings, save_user_settings,
    load_models_catalog, model_label, preset_paths, SETTINGS_PATH, ENV_PATH,
)

KEY_LABELS = [("Anthropic","ANTHROPIC_API_KEY"),("OpenAI","OPENAI_API_KEY"),("Google","GOOGLE_API_KEY"),("xAI","XAI_API_KEY"),("DeepSeek","DEEPSEEK_API_KEY")]
DEFAULT_WS = ROOT / "workspace"
BACKUPS, RESULTS = ROOT / "backups", ROOT / "results"
for d in (DEFAULT_WS, BACKUPS, RESULTS): d.mkdir(exist_ok=True)

st.set_page_config(page_title="Agent Studio", page_icon="🤖", layout="wide")
cfg = load_config(ROOT / "config" / "agents.yaml") if (ROOT/"config"/"agents.yaml").exists() else {}
CATALOG = load_models_catalog()
MODELS_MAP = dict(cfg.get("models") or {})
for mk, meta in CATALOG.items():
    if mk not in MODELS_MAP and meta.get("litellm"):
        MODELS_MAP[mk] = meta["litellm"]
MODEL_CHOICES = list(MODELS_MAP.keys()) or ["claude_sonnet_45"]
PIPELINES = cfg.get("pipelines") or {"single": {"steps": ["developer"], "description": "one"}}
AGENTS_CFG = cfg.get("agents") or {}
RECS = cfg.get("recommendations") or {}
user_set = load_user_settings()

if "api_keys" not in st.session_state:
    st.session_state.api_keys = load_keys_from_env()
if "workspace_path" not in st.session_state:
    st.session_state.workspace_path = user_set.get("workspace_path") or os.getenv("WORKSPACE_PATH") or str(DEFAULT_WS)
if "agent_overrides" not in st.session_state:
    ov = {}
    for aid, ac in AGENTS_CFG.items():
        ov[aid] = {"enabled": ac.get("enabled", True), "model": ac.get("model", MODEL_CHOICES[0]), "temperature": float(ac.get("temperature", 0.2))}
    for aid, s in (user_set.get("agent_overrides") or {}).items():
        if aid in ov: ov[aid].update(s)
    st.session_state.agent_overrides = ov
if "pipeline_select" not in st.session_state:
    st.session_state.pipeline_select = user_set.get("pipeline") or cfg.get("default_pipeline", "code_only")

def persist():
    save_user_settings({"workspace_path": st.session_state.workspace_path, "pipeline": st.session_state.get("pipeline_select"), "agent_overrides": st.session_state.get("agent_overrides", {})})

def fmt(k): return model_label(k, CATALOG, MODELS_MAP)

with st.sidebar:
    st.header("🔑 API-ключи")
    for label, env in KEY_LABELS:
        st.session_state.api_keys[env] = st.text_input(label, value=st.session_state.api_keys.get(env,""), type="password", key=f"k_{env}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 Ключи", use_container_width=True):
            save_keys_to_env(st.session_state.api_keys, {"WORKSPACE_PATH": st.session_state.workspace_path}); persist(); st.success("OK")
    with c2:
        if st.button("🔄 .env", use_container_width=True):
            st.session_state.api_keys = load_keys_from_env(); st.rerun()
    st.divider()
    st.header("⚙️ Параметры")
    max_steps = st.slider("Макс. шагов", 5, 80, 25)
    shell_timeout = st.slider("Таймаут shell", 10, 300, 120)
    keep_awake = st.checkbox("Не уходить в сон", value=True)
    keep_display = st.checkbox("Держать экран", value=False)
    if st.button("💾 Все настройки", use_container_width=True):
        persist(); save_keys_to_env(st.session_state.api_keys, {"WORKSPACE_PATH": st.session_state.workspace_path})
        st.success(f"→ {SETTINGS_PATH.name}")

st.title("🤖 Multi-Agent Studio")
st.caption("start.bat = git pull + запуск · настройки ролей в user_settings.json")
tab_run, tab_agents, tab_models, tab_fs, tab_remote, tab_help = st.tabs(["▶️ Запуск","👥 Агенты","📚 Модели","📁 Файлы","🌐 SSH","❓ Справка"])

with tab_run:
    st.subheader("💻 Workspace")
    presets = preset_paths(DEFAULT_WS)
    cols = st.columns(min(4, len(presets)))
    for i,(label,path) in enumerate(presets):
        with cols[i % len(cols)]:
            if st.button(label, key=f"ws_{i}", use_container_width=True):
                st.session_state.workspace_path = str(path); persist(); st.rerun()
    w1,w2 = st.columns([4,1])
    with w1:
        wp = st.text_input("Путь", value=st.session_state.workspace_path)
        st.session_state.workspace_path = wp.strip() or str(DEFAULT_WS)
    with w2:
        st.write(""); st.write("")
        if st.button("📁 Создать", use_container_width=True):
            try: Path(st.session_state.workspace_path).mkdir(parents=True, exist_ok=True); st.success("OK")
            except Exception as e: st.error(str(e))
    p = Path(st.session_state.workspace_path)
    st.success(f"✓ `{p}`") if p.is_dir() else st.warning("Папки нет")

    st.subheader("🔗 Пайплайн")
    pipe_names = list(PIPELINES.keys())
    cur = st.session_state.pipeline_select if st.session_state.pipeline_select in pipe_names else pipe_names[0]
    pipeline_name = st.selectbox("Режим", pipe_names, index=pipe_names.index(cur), format_func=lambda n: f"{n} — {PIPELINES[n].get('description','')}", key="pipeline_select")
    steps = PIPELINES.get(pipeline_name,{}).get("steps",["developer"])
    active = [s for s in steps if st.session_state.agent_overrides.get(s,{}).get("enabled", AGENTS_CFG.get(s,{}).get("enabled", True))]
    st.info("Цепочка: **" + " → ".join(active) + "**" if active else "Нет активных агентов")

    task = st.text_area("Задача", height=140, placeholder="Создай hello.py и запусти")
    run_btn = st.button("🚀 Запустить", type="primary", use_container_width=True)
    log_box, result_box = st.empty(), st.empty()
    if run_btn:
        persist()
        if not task.strip(): st.error("Введите задачу")
        elif not active: st.error("Включите агентов")
        else:
            Path(st.session_state.workspace_path).mkdir(parents=True, exist_ok=True)
            save_keys_to_env(st.session_state.api_keys, {"WORKSPACE_PATH": st.session_state.workspace_path})
            logs = []
            def log_fn(m):
                logs.append(m); log_box.code("\n".join(logs[-60:]), language="text")
            orch = Orchestrator(workspace=st.session_state.workspace_path, backup_dir=str(BACKUPS), api_keys=st.session_state.api_keys, config=cfg, max_steps=max_steps, shell_timeout=shell_timeout, log_fn=log_fn, overrides=st.session_state.agent_overrides, pipeline_name=pipeline_name)
            power_rt = None
            if keep_awake:
                power_rt = AgentRuntime(workspace=st.session_state.workspace_path, backup_dir=str(BACKUPS), model="openai/gpt-4o-mini", api_key=st.session_state.api_keys.get("OPENAI_API_KEY") or "x", allowed_tools=[], role_name="power")
                log_fn(power_rt.power.start("display" if keep_display else "system"))
            try:
                with st.spinner("Агенты..."):
                    result = orch.run(task.strip())
                result_box.markdown("### Результат\n\n"+result)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out = RESULTS / f"run_{ts}.md"
                out.write_text(f"# Задача\n\n{task}\n\n# Лог\n\n"+"\n".join(logs)+f"\n\n# Результат\n\n{result}", encoding="utf-8")
                st.download_button("📥 Отчёт", data=out.read_text(encoding="utf-8"), file_name=out.name)
            except Exception as e:
                st.exception(e)
            finally:
                if keep_awake and power_rt: log_fn(power_rt.power.stop())

with tab_agents:
    st.caption("🟢 FREE = free tier у провайдера. Сохраняется в user_settings.json")
    for aid, ac in AGENTS_CFG.items():
        cur = st.session_state.agent_overrides.get(aid, {})
        with st.expander(f"{ac.get('name',aid)} (`{aid}`)", expanded=(aid=="developer")):
            st.caption(ac.get("description",""))
            c1,c2,c3 = st.columns([1,3,1])
            with c1: enabled = st.checkbox("Вкл", value=bool(cur.get("enabled", ac.get("enabled", True))), key=f"en_{aid}")
            with c2:
                dm = cur.get("model") or ac.get("model") or MODEL_CHOICES[0]
                if dm not in MODEL_CHOICES: dm = MODEL_CHOICES[0]
                model_key = st.selectbox("Модель", MODEL_CHOICES, index=MODEL_CHOICES.index(dm), key=f"model_{aid}", format_func=fmt)
            with c3: temp = st.slider("Temp", 0.0, 1.0, float(cur.get("temperature", ac.get("temperature", 0.2))), 0.05, key=f"temp_{aid}")
            meta = CATALOG.get(model_key) or {}
            if meta.get("free_tier"): st.success(f"🟢 {meta.get('summary','')}")
            elif meta: st.caption(f"💰 {meta.get('price_note','')} · {meta.get('summary','')}")
            rec = RECS.get(aid) or []
            if rec: st.info("⭐ " + ", ".join(fmt(r) for r in rec if r in MODELS_MAP))
            st.session_state.agent_overrides[aid] = {"enabled": enabled, "model": model_key, "temperature": temp}
    if st.button("💾 Сохранить роли"):
        persist(); st.success("OK")

with tab_models:
    st.markdown("Ориентир окт 2026. **🟢 FREE** = квотный free tier (лимиты RPM/RPD).")
    only_free = st.checkbox("Только FREE", value=False)
    for mk, meta in CATALOG.items():
        if only_free and not meta.get("free_tier"): continue
        badge = "🟢 FREE" if meta.get("free_tier") else "💰 paid"
        with st.expander(f"{meta.get('name',mk)} — {badge} · {meta.get('provider','')}"):
            st.markdown(f"- **id:** `{meta.get('litellm', MODELS_MAP.get(mk,mk))}`\n- **Контекст:** {meta.get('context','—')}\n- **Цена:** {meta.get('price_note','—')}\n- **Для:** {meta.get('best_for','—')}\n\n{meta.get('summary','')}")
    st.markdown("""
| Провайдер | FREE | Ключ |
|-----------|------|------|
| Google AI Studio | Gemini Flash / Lite / иногда Pro | GOOGLE_API_KEY |
| DeepSeek | часто грант, потом очень дёшево | DEEPSEEK_API_KEY |
| OpenAI / Anthropic / xAI | обычно только paid | свои ключи |
""")

with tab_fs:
    st.caption(f"`{st.session_state.workspace_path}`")
    try:
        from tools.filesystem import WorkspaceFS
        Path(st.session_state.workspace_path).mkdir(parents=True, exist_ok=True)
        fs = WorkspaceFS(st.session_state.workspace_path, BACKUPS)
        st.code(fs.list_dir("."), language="text")
        path = st.text_input("Файл", value="")
        if path and st.button("Читать"): st.code(fs.read_file(path), language="text")
    except Exception as e: st.error(str(e))

with tab_remote:
    c1,c2,c3 = st.columns(3)
    with c1: r_name=st.text_input("Имя", value="device1"); r_host=st.text_input("Host", value="192.168.1.10")
    with c2: r_user=st.text_input("User", value="pi"); r_port=st.number_input("Port", value=22, min_value=1, max_value=65535)
    with c3: r_key=st.text_input("SSH key", value=""); r_cmd=st.text_input("Cmd", value="uname -a")
    if st.button("SSH run"):
        from tools.remote import RemoteManager, RemoteDevice
        rm = RemoteManager(); rm.add_device(RemoteDevice(name=r_name, host=r_host, user=r_user, port=int(r_port), key_path=r_key or None))
        st.code(rm.run_ssh(r_name, r_cmd), language="text")

with tab_help:
    st.markdown("""
### Windows: двойной клик `start.bat`
1. git pull  2. зависимости  3. streamlit

### Сохранение
| Что | Файл |
|-----|------|
| Ключи | `.env` |
| Роли / модели / pipeline / workspace | `user_settings.json` |

Оба файла в `.gitignore`.
""")
