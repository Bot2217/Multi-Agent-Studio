use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_updater::UpdaterExt;

struct Backend(Mutex<Option<CommandChild>>);

fn free_port() -> u16 {
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("free port");
    let port = listener.local_addr().expect("port").port();
    drop(listener);
    port
}

fn wait_until_ready(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{port}/_stcore/health");
    let Ok(client) = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
    else {
        return false;
    };
    for _ in 0..120 {
        if let Ok(response) = client.get(&url).send() {
            if response.status().is_success() {
                return true;
            }
        }
        std::thread::sleep(Duration::from_secs(1));
    }
    false
}

fn set_status(window: &tauri::WebviewWindow, text: &str) {
    let quoted = serde_json::to_string(text).unwrap_or_else(|_| "\"\"".into());
    let _ = window.eval(&format!(
        "const node = document.getElementById('status'); if (node) node.textContent = {quoted};"
    ));
}

fn spawn_backend(app: &tauri::AppHandle, port: u16) -> Result<CommandChild, String> {
    let sidecar = app
        .shell()
        .sidecar("ulei-backend")
        .map_err(|err| err.to_string())?
        .args(["--port", &port.to_string()])
        .set_process_group(true);
    let (mut rx, child) = sidecar.spawn().map_err(|err| err.to_string())?;
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
            .message("Доступно обновление. Установить и перезапустить?")
            .title("Улей")
            .buttons(MessageDialogButtons::OkCancelCustom(
                "Установить и перезапустить".into(),
                "Позже".into(),
            ))
            .blocking_show();
        if !install {
            return;
        }
        if update.download_and_install(|_, _| {}, || {}).await.is_ok() {
            handle.request_restart();
        }
    });
}

fn boot(app: tauri::AppHandle) {
    let port = free_port();
    let child = match spawn_backend(&app, port) {
        Ok(child) => child,
        Err(err) => {
            eprintln!("sidecar: {err}");
            if let Some(window) = app.get_webview_window("main") {
                set_status(&window, "Не удалось запустить Улей.");
            }
            return;
        }
    };
    app.manage(Backend(Mutex::new(Some(child))));
    if !wait_until_ready(port) {
        if let Some(window) = app.get_webview_window("main") {
            set_status(
                &window,
                "Улей не ответил. Закройте окно и запустите ещё раз.",
            );
        }
        return;
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
        let _ = child.kill();
    }
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
        .expect("error while building Улей")
        .run(|app, event| {
            if matches!(
                event,
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. }
            ) {
                kill_backend(app);
            }
        });
}
