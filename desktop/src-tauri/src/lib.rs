use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_updater::UpdaterExt;

struct Backend(Mutex<Option<CommandChild>>);

const RU_JSON: &str = include_str!("../../../locales/ru.json");
const EN_JSON: &str = include_str!("../../../locales/en.json");

fn saved_language() -> Option<&'static str> {
    let mut paths = Vec::new();
    if let Ok(dir) = std::env::var("MAS_DATA_DIR") {
        paths.push(std::path::PathBuf::from(dir).join("user_settings.json"));
    }
    if let Ok(appdata) = std::env::var("APPDATA") {
        paths.push(
            std::path::PathBuf::from(appdata)
                .join("ulei")
                .join("user_settings.json"),
        );
    }
    if let Some(home) = std::env::var_os("HOME") {
        let home = std::path::PathBuf::from(home);
        paths.push(
            home.join("Library")
                .join("Application Support")
                .join("ulei")
                .join("user_settings.json"),
        );
        paths.push(
            home.join(".local")
                .join("share")
                .join("ulei")
                .join("user_settings.json"),
        );
    }
    paths.push(std::path::PathBuf::from("user_settings.json"));
    for path in paths {
        let Ok(text) = std::fs::read_to_string(path) else {
            continue;
        };
        let Ok(value) = serde_json::from_str::<serde_json::Value>(&text) else {
            continue;
        };
        match value.get("language").and_then(|item| item.as_str()) {
            Some("ru") => return Some("ru"),
            Some("en") => return Some("en"),
            _ => {}
        }
    }
    None
}

fn ui_language() -> &'static str {
    if let Some(lang) = saved_language() {
        return lang;
    }
    let raw = std::env::var("LC_ALL")
        .or_else(|_| std::env::var("LANG"))
        .unwrap_or_default();
    if raw.to_lowercase().starts_with("en") {
        "en"
    } else {
        "ru"
    }
}

fn tr(key: &str) -> String {
    fn lookup(raw: &str, key: &str) -> Option<String> {
        let value: serde_json::Value = serde_json::from_str(raw).ok()?;
        value.get(key).and_then(|item| item.as_str()).map(str::to_string)
    }
    let primary = if ui_language() == "en" { EN_JSON } else { RU_JSON };
    lookup(primary, key)
        .or_else(|| lookup(RU_JSON, key))
        .unwrap_or_else(|| key.to_string())
}

fn free_port() -> u16 {
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("free port");
    let port = listener.local_addr().expect("port").port();
    drop(listener);
    port
}

fn probe(client: &reqwest::blocking::Client, url: &str) -> bool {
    client
        .get(url)
        .send()
        .map(|response| response.status().is_success())
        .unwrap_or(false)
}

fn api_json_path() -> std::path::PathBuf {
    if let Ok(dir) = std::env::var("MAS_DATA_DIR") {
        return std::path::PathBuf::from(dir).join("api.json");
    }
    #[cfg(windows)]
    {
        let base = std::env::var("APPDATA").unwrap_or_else(|_| ".".into());
        return std::path::PathBuf::from(base).join("ulei").join("api.json");
    }
    #[cfg(target_os = "macos")]
    {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
        return std::path::PathBuf::from(home)
            .join("Library")
            .join("Application Support")
            .join("ulei")
            .join("api.json");
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let base = std::env::var("XDG_DATA_HOME").unwrap_or_else(|_| {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
            format!("{home}/.local/share")
        });
        std::path::PathBuf::from(base).join("ulei").join("api.json")
    }
}

fn engine_token() -> Option<String> {
    let text = std::fs::read_to_string(api_json_path()).ok()?;
    let value: serde_json::Value = serde_json::from_str(&text).ok()?;
    let token = value.get("token")?.as_str()?.trim();
    if token.is_empty() { None } else { Some(token.to_string()) }
}

fn probe_engine(client: &reqwest::blocking::Client, url: &str) -> bool {
    let Some(token) = engine_token() else {
        return false;
    };
    client
        .get(url)
        .header("authorization", format!("Bearer {token}"))
        .send()
        .map(|response| response.status().is_success())
        .unwrap_or(false)
}

/// Streamlit health, then the engine health. The window still opens when the
/// engine stays quiet, after a short extra wait.
fn wait_until_ready(port: u16, api_port: u16) -> (bool, bool) {
    let page = format!("http://127.0.0.1:{port}/_stcore/health");
    let engine = format!("http://127.0.0.1:{api_port}/api/v1/health");
    let Ok(client) = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
    else {
        return (false, false);
    };
    let mut page_ok = false;
    let mut engine_ok = false;
    let mut page_since: Option<u32> = None;
    for tick in 0..120u32 {
        if !page_ok && probe(&client, &page) {
            page_ok = true;
            page_since = Some(tick);
        }
        if !engine_ok && probe_engine(&client, &engine) {
            engine_ok = true;
        }
        if page_ok && engine_ok {
            return (true, true);
        }
        if page_ok && page_since.is_some_and(|start| tick.saturating_sub(start) >= 15) {
            return (true, false);
        }
        std::thread::sleep(Duration::from_secs(1));
    }
    (page_ok, engine_ok)
}

fn set_status(window: &tauri::WebviewWindow, text: &str) {
    let quoted = serde_json::to_string(text).unwrap_or_else(|_| "\"\"".into());
    let _ = window.eval(&format!(
        "const node = document.getElementById('status'); if (node) node.textContent = {quoted};"
    ));
}

fn spawn_backend(
    app: &tauri::AppHandle,
    port: u16,
    api_port: u16,
) -> Result<CommandChild, String> {
    let sidecar = app
        .shell()
        .sidecar("ulei-backend")
        .map_err(|err| err.to_string())?
        .args([
            "--port",
            &port.to_string(),
            "--api-port",
            &api_port.to_string(),
        ])
        .set_process_group(true);
    let (mut rx, child) = sidecar.spawn().map_err(|err| err.to_string())?;
    // If the window is killed outright, the job closes and takes the sidecar with it.
    // Otherwise NSIS cannot replace ulei-backend.exe on the next install.
    #[cfg(windows)]
    attach_kill_on_job_close(child.pid());
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                    eprintln!("ulei-backend: {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Error(err) => eprintln!("ulei-backend error: {err}"),
                CommandEvent::Terminated(payload) => {
                    eprintln!("ulei-backend exited: {payload:?}");
                }
                _ => {}
            }
        }
    });
    Ok(child)
}

fn offer_update(app: &tauri::AppHandle) {
    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        let Ok(updater) = handle.updater() else {
            return;
        };
        let Ok(Some(update)) = updater.check().await else {
            return;
        };
        let install = handle
            .dialog()
            .message(tr("desktop.update_message"))
            .title("Улей")
            .buttons(MessageDialogButtons::OkCancelCustom(
                tr("desktop.update_install"),
                tr("desktop.update_later"),
            ))
            .blocking_show();
        if !install {
            return;
        }
        // The installer also stops this copy. Releasing the sidecar first
        // avoids the NSIS "file is open for writing" dialog.
        kill_backend(&handle);
        if update.download_and_install(|_, _| {}, || {}).await.is_ok() {
            handle.request_restart();
        } else {
            handle
                .dialog()
                .message(tr("desktop.update_failed"))
                .title("Улей")
                .blocking_show();
        }
    });
}

fn boot(app: tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        set_status(&window, &tr("desktop.starting"));
    }
    let port = free_port();
    let api_port = free_port();
    let child = match spawn_backend(&app, port, api_port) {
        Ok(child) => child,
        Err(err) => {
            eprintln!("sidecar: {err}");
            if let Some(window) = app.get_webview_window("main") {
                set_status(&window, &tr("desktop.start_failed"));
            }
            return;
        }
    };
    app.manage(Backend(Mutex::new(Some(child))));
    let (page_ok, engine_ok) = wait_until_ready(port, api_port);
    if !page_ok {
        if let Some(window) = app.get_webview_window("main") {
            set_status(&window, &tr("desktop.no_answer"));
        }
        return;
    }
    if !engine_ok {
        eprintln!("engine healthcheck failed on {api_port}");
        if let Some(window) = app.get_webview_window("main") {
            set_status(&window, &tr("desktop.engine_down"));
        }
    }
    if let Some(window) = app.get_webview_window("main") {
        let url = format!("http://127.0.0.1:{port}/");
        if let Ok(parsed) = url.parse() {
            let _ = window.navigate(parsed);
        }
    }
    offer_update(&app);
}

fn kill_backend(app: &tauri::AppHandle) {
    let Some(state) = app.try_state::<Backend>() else {
        return;
    };
    if let Some(child) = state.0.lock().ok().and_then(|mut slot| slot.take()) {
        let pid = child.pid();
        let _ = child.kill();
        wait_for_exit(pid, Duration::from_secs(5));
    }
}

#[cfg(windows)]
fn wait_for_exit(pid: u32, timeout: Duration) {
    const SYNCHRONIZE: u32 = 0x0010_0000;
    unsafe {
        let handle = OpenProcess(SYNCHRONIZE, 0, pid);
        if handle.is_null() {
            return;
        }
        let millis = u32::try_from(timeout.as_millis()).unwrap_or(u32::MAX);
        WaitForSingleObject(handle, millis);
        CloseHandle(handle);
    }
}

#[cfg(not(windows))]
fn wait_for_exit(_pid: u32, _timeout: Duration) {}

#[cfg(windows)]
fn attach_kill_on_job_close(pid: u32) {
    const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION: i32 = 9;
    const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x2000;
    const PROCESS_SET_QUOTA: u32 = 0x0100;
    const PROCESS_TERMINATE: u32 = 0x0001;

    #[repr(C)]
    struct BasicLimit {
        per_process_user_time: i64,
        per_job_user_time: i64,
        limit_flags: u32,
        minimum_working_set_size: usize,
        maximum_working_set_size: usize,
        active_process_limit: u32,
        affinity: usize,
        priority_class: u32,
        scheduling_class: u32,
    }
    #[repr(C)]
    struct ExtendedLimit {
        basic: BasicLimit,
        io_counters: [u64; 6],
        process_memory: usize,
        job_memory: usize,
        peak_process_memory: usize,
        peak_job_memory: usize,
    }

    unsafe {
        let job = CreateJobObjectW(std::ptr::null_mut(), std::ptr::null());
        if job.is_null() {
            return;
        }
        let mut limits = std::mem::zeroed::<ExtendedLimit>();
        limits.basic.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let set = SetInformationJobObject(
            job,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            &limits as *const ExtendedLimit as *mut std::ffi::c_void,
            std::mem::size_of::<ExtendedLimit>() as u32,
        );
        if set == 0 {
            CloseHandle(job);
            return;
        }
        let process = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, pid);
        if process.is_null() {
            CloseHandle(job);
            return;
        }
        let assigned = AssignProcessToJobObject(job, process);
        CloseHandle(process);
        if assigned == 0 {
            CloseHandle(job);
            return;
        }
        // Keep the handle until this process exits. Closing it now would kill
        // the sidecar immediately; process teardown closes it and the sidecar
        // dies with this install instead of surviving as an orphan.
        keep_job_handle(job);
    }
}

#[cfg(windows)]
fn keep_job_handle(job: *mut std::ffi::c_void) {
    static JOBS: Mutex<Vec<usize>> = Mutex::new(Vec::new());
    if let Ok(mut jobs) = JOBS.lock() {
        jobs.push(job as usize);
    }
}

#[cfg(windows)]
#[link(name = "kernel32")]
extern "system" {
    fn CreateJobObjectW(attrs: *mut std::ffi::c_void, name: *const u16) -> *mut std::ffi::c_void;
    fn SetInformationJobObject(
        job: *mut std::ffi::c_void,
        class: i32,
        info: *mut std::ffi::c_void,
        length: u32,
    ) -> i32;
    fn AssignProcessToJobObject(job: *mut std::ffi::c_void, process: *mut std::ffi::c_void) -> i32;
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> *mut std::ffi::c_void;
    fn WaitForSingleObject(handle: *mut std::ffi::c_void, millis: u32) -> u32;
    fn CloseHandle(handle: *mut std::ffi::c_void) -> i32;
}

fn watch_signals(app: tauri::AppHandle) {
    #[cfg(unix)]
    tauri::async_runtime::spawn(async move {
        use tokio::signal::unix::{signal, SignalKind};
        let Ok(mut term) = signal(SignalKind::terminate()) else {
            return;
        };
        let Ok(mut interrupt) = signal(SignalKind::interrupt()) else {
            return;
        };
        tokio::select! {
            _ = term.recv() => {}
            _ = interrupt.recv() => {}
        }
        kill_backend(&app);
        app.exit(0);
    });
    #[cfg(not(unix))]
    drop(app);
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build());
    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }));
    }
    builder
        .setup(|app| {
            let handle = app.handle().clone();
            std::thread::spawn(move || boot(handle));
            watch_signals(app.handle().clone());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Ulei")
        .run(|app, event| {
            if matches!(
                event,
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. }
            ) {
                kill_backend(app);
            }
        });
}
