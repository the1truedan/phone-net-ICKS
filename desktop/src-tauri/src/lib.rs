mod ask;
mod scan;
mod check;
mod pull;

/// "Check my computer" screen: read-only tool and phone detection.
#[tauri::command]
fn check_computer() -> Vec<check::CheckRow> {
  check::run_checks()
}

/// Read-only phone checks (installed apps, readable text counts).
#[tauri::command]
async fn check_phone() -> Result<Vec<check::CheckRow>, String> {
  tauri::async_runtime::spawn_blocking(check::phone_checks).await.map_err(|e| e.to_string())
}

/// Optional speaker-names setup checks (Python, pyannote, Hugging Face token presence).
#[tauri::command]
async fn check_speakers(python: Option<String>) -> Result<Vec<check::CheckRow>, String> {
  tauri::async_runtime::spawn_blocking(move || check::speaker_checks(python)).await.map_err(|e| e.to_string())
}

/// On click only: ask Hugging Face whether the saved token works and the speaker model's terms are accepted.
#[tauri::command]
async fn check_hf(python: Option<String>) -> Result<Vec<check::CheckRow>, String> {
  tauri::async_runtime::spawn_blocking(move || check::hf_access(python)).await.map_err(|e| e.to_string())
}

/// Phones ready over USB (serial shown to the page only as its last 4 characters).
#[tauri::command]
async fn list_phones() -> Result<Vec<scan::Device>, String> {
  tauri::async_runtime::spawn_blocking(scan::devices).await.map_err(|e| e.to_string())
}

/// Read-only, metadata-only scan of one phone; saves dates/counts/sizes to ~/phone-net-ICKS/scans.
#[tauri::command]
async fn scan_phone(serial: String) -> Result<scan::Scan, String> {
  tauri::async_runtime::spawn_blocking(move || scan::scan(&serial)).await.map_err(|e| e.to_string())?
}

/// Open an https link in the normal browser.
#[tauri::command]
fn open_external(url: String) -> Result<(), String> {
  check::open_external(&url)
}

/// Local Ollama models for the chat page.
#[tauri::command]
async fn ollama_models() -> Result<Vec<String>, String> {
  tauri::async_runtime::spawn_blocking(ask::models).await.map_err(|e| e.to_string())?
}

/// "Ask my records": search the folder, then ask the local model with the matching lines.
#[tauri::command]
async fn ask_records(folder: String, model: String, question: String) -> Result<ask::Answer, String> {
  tauri::async_runtime::spawn_blocking(move || ask::ask(&folder, &model, &question))
    .await
    .map_err(|e| e.to_string())?
}

/// The owner's pull workflows (from ~/phone-net-ICKS/pulls.json): connected?, last pull, running?
#[tauri::command]
async fn pull_jobs() -> Result<Vec<pull::PullJob>, String> {
  tauri::async_runtime::spawn_blocking(pull::jobs).await.map_err(|e| e.to_string())?
}

/// Start one pull: the owner's own script, continuing from the last pull's time.
#[tauri::command]
async fn pull_start(id: String) -> Result<String, String> {
  tauri::async_runtime::spawn_blocking(move || pull::start(&id)).await.map_err(|e| e.to_string())?
}

/// Progress of a pull folder, read from its PULL_LOG.txt.
#[tauri::command]
async fn pull_progress(folder: String) -> Result<pull::Progress, String> {
  tauri::async_runtime::spawn_blocking(move || pull::progress(&folder)).await.map_err(|e| e.to_string())?
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .runtime(tauri_runtime_wry::Wry::default())
    .setup(|app| {
      // plug-in auto-pull (only does anything when ~/phone-net-ICKS/pulls.json lists the phone)
      std::thread::spawn(pull::watch);
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![check_computer, check_phone, check_speakers, check_hf, list_phones, scan_phone, open_external, ollama_models, ask_records, pull_jobs, pull_start, pull_progress])
    .run(tauri::generate_context!())
    .expect("error while building tauri application");
}
