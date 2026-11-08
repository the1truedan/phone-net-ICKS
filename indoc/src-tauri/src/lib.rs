//! I.N-D.O.C.-T.R.I.N. 8-P.I.E.C.E.: a window over the P.A.P.E. receipt engine (scripts/pape/pape_receipt.py).
//! The engine is built into the app and written to ~/pape_scans/receipts/.engine/ on start. Everything runs on this
//! Mac: scanner -> OCR -> ledger CSVs. Nothing is uploaded.

use std::path::PathBuf;
use std::process::Command;

const ENGINE: &str = include_str!("../../../scripts/pape/pape_receipt.py");

fn home() -> PathBuf {
  PathBuf::from(std::env::var_os("HOME").unwrap_or_default())
}

fn out_dir() -> PathBuf {
  std::env::var_os("PAPE_RECEIPTS").map(PathBuf::from).unwrap_or_else(|| home().join("pape_scans").join("receipts"))
}

fn engine_path() -> Result<PathBuf, String> {
  let dir = out_dir().join(".engine");
  std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
  let p = dir.join("pape_receipt.py");
  if std::fs::read_to_string(&p).ok().as_deref() != Some(ENGINE) {
    std::fs::write(&p, ENGINE).map_err(|e| e.to_string())?;
  }
  Ok(p)
}

/// The P.A.P.E. toolbox Python (RapidOCR + OpenCV) if installed, else the system Python (Tesseract only).
fn python() -> PathBuf {
  let venv = home().join("models/pape_tools/.venv/bin/python");
  if venv.exists() { return venv; }
  for p in ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"] {
    if PathBuf::from(p).exists() { return PathBuf::from(p); }
  }
  PathBuf::from("python3")
}

fn engine(args: Vec<String>) -> Result<serde_json::Value, String> {
  let script = engine_path()?;
  let path = format!("/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin");
  let o = Command::new(python())
    .arg("-I")
    .arg(&script)
    .args(&args)
    .env("PATH", path)
    .output()
    .map_err(|e| format!("could not start the engine: {e}"))?;
  let text = String::from_utf8_lossy(&o.stdout);
  serde_json::from_str(&text).map_err(|_| {
    let err = String::from_utf8_lossy(&o.stderr);
    let tail: String = err.lines().rev().take(4).collect::<Vec<_>>().into_iter().rev().collect::<Vec<_>>().join("\n");
    format!("The engine stopped with an error.\n{tail}")
  })
}

async fn blocking(args: Vec<String>) -> Result<serde_json::Value, String> {
  tauri::async_runtime::spawn_blocking(move || engine(args)).await.map_err(|e| e.to_string())?
}

#[tauri::command]
async fn check() -> Result<serde_json::Value, String> { blocking(vec!["check".into()]).await }

#[tauri::command]
async fn scan(count: u32, model: Option<String>, verify: Option<bool>) -> Result<serde_json::Value, String> {
  let mut a = vec!["scan".to_string(), "--count".into(), count.to_string()];
  if verify.unwrap_or(false) { a.push("--verify".into()); }
  if let Some(m) = model.filter(|m| !m.is_empty()) { a.push("--model".into()); a.push(m); }
  blocking(a).await
}

#[tauri::command]
async fn read(paths: Vec<String>, redo: bool, model: Option<String>, verify: Option<bool>) -> Result<serde_json::Value, String> {
  let mut a = vec!["read".to_string()];
  if verify.unwrap_or(false) { a.push("--verify".into()); }
  if redo { a.push("--redo".into()); }
  if let Some(m) = model.filter(|m| !m.is_empty()) { a.push("--model".into()); a.push(m); }
  a.extend(paths);
  blocking(a).await
}

#[tauri::command]
async fn inbox() -> Result<serde_json::Value, String> { blocking(vec!["inbox".into()]).await }

#[tauri::command]
async fn ledger(limit: u32) -> Result<serde_json::Value, String> {
  blocking(vec!["ledger".into(), "--limit".into(), limit.to_string()]).await
}

#[tauri::command]
async fn recon() -> Result<serde_json::Value, String> { blocking(vec!["recon".into()]).await }

#[tauri::command]
async fn stores() -> Result<serde_json::Value, String> { blocking(vec!["stores".into()]).await }

#[tauri::command]
async fn report() -> Result<serde_json::Value, String> { blocking(vec!["report".into()]).await }

/// One receipt's saved record (receipt.json in its folder).
#[tauri::command]
fn receipt(folder: String) -> Result<serde_json::Value, String> {
  let p = PathBuf::from(&folder);
  if !p.starts_with(out_dir()) { return Err("not a receipt folder".into()); }
  let t = std::fs::read_to_string(p.join("receipt.json")).map_err(|e| e.to_string())?;
  serde_json::from_str(&t).map_err(|e| e.to_string())
}

/// A small picture of the cleaned scan, as a data: URL for the window.
#[tauri::command]
fn preview(folder: String) -> Result<String, String> {
  let p = PathBuf::from(&folder);
  if !p.starts_with(out_dir()) { return Err("not a receipt folder".into()); }
  let bytes = std::fs::read(p.join("preview.jpg")).map_err(|e| e.to_string())?;
  Ok(format!("data:image/jpeg;base64,{}", b64(&bytes)))
}

/// Show a folder or file in Finder (only inside the receipts folder).
#[tauri::command]
fn reveal(path: Option<String>) -> Result<(), String> {
  let p = path.map(PathBuf::from).unwrap_or_else(out_dir);
  if !p.starts_with(out_dir()) { return Err("outside the receipts folder".into()); }
  std::fs::create_dir_all(out_dir()).ok();
  let mut c = Command::new("open");
  if p.is_file() { c.arg("-R"); }
  c.arg(&p).status().map(|_| ()).map_err(|e| e.to_string())
}

fn b64(data: &[u8]) -> String {
  const T: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let mut s = String::with_capacity(data.len() * 4 / 3 + 4);
  for c in data.chunks(3) {
    let n = (c[0] as u32) << 16 | (*c.get(1).unwrap_or(&0) as u32) << 8 | *c.get(2).unwrap_or(&0) as u32;
    s.push(T[(n >> 18) as usize & 63] as char);
    s.push(T[(n >> 12) as usize & 63] as char);
    s.push(if c.len() > 1 { T[(n >> 6) as usize & 63] as char } else { '=' });
    s.push(if c.len() > 2 { T[n as usize & 63] as char } else { '=' });
  }
  s
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .runtime(tauri_runtime_wry::Wry::default())
    .invoke_handler(tauri::generate_handler![check, scan, read, inbox, ledger, report, recon, stores, receipt, preview, reveal])
    .run(tauri::generate_context!())
    .expect("error while starting the scan app");
}
