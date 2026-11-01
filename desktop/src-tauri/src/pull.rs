//! "Pull new files": run the owner's existing pull scripts from the app and show their progress.
//!
//! The scripts stay the source of truth (they already hash, dedupe and log custody). The app only:
//! 1. reads the owner's list of pulls from ~/phone-net-ICKS/pulls.json (never in the repo),
//! 2. works out SINCE from the newest earlier folder's custody_log.txt and the next folder letter for today,
//! 3. starts the script in the background, and
//! 4. reads that folder's PULL_LOG.txt (the same lines the on-phone status page reads).
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Deserialize)]
struct Cfg {
  pulls: Vec<CfgPull>,
  /// Optional: path to phone_status.py; when set, Pull also puts a progress page on the phone's own screen.
  status_page: Option<String>,
}

#[derive(Deserialize, Clone)]
struct CfgPull {
  id: String,
  name: String,
  serial: String,
  script: String,
  /// Folder prefix the script writes to; today's date and a letter are appended (…_delta_2026-11-01a).
  dest_prefix: String,
}

#[derive(Serialize)]
pub struct PullJob {
  pub id: String,
  pub name: String,
  pub serial_tail: String,
  pub connected: bool,
  /// Read from the phone itself when connected (maker + model), so a mix-up shows.
  pub model: Option<String>,
  pub last_folder: Option<String>,
  pub since: Option<String>,
  pub running_folder: Option<String>,
}

#[derive(Serialize)]
pub struct Step {
  pub label: String,
  pub done: u64,
  pub total: u64,
}

#[derive(Serialize)]
pub struct Progress {
  pub folder: String,
  pub steps: Vec<Step>,
  pub finished: bool,
  pub summary: String,
}

fn home() -> PathBuf {
  PathBuf::from(std::env::var("HOME").unwrap_or_default())
}

fn expand(p: &str) -> PathBuf {
  match p.strip_prefix("~/") {
    Some(rest) => home().join(rest),
    None => PathBuf::from(p),
  }
}

fn cfg_path() -> PathBuf {
  home().join("phone-net-ICKS").join("pulls.json")
}

fn load_cfg() -> Result<Cfg, String> {
  let p = cfg_path();
  let txt = fs::read_to_string(&p).map_err(|_| format!("No pull list yet. Copy pulls.json.example to {}", p.display()))?;
  serde_json::from_str(&txt).map_err(|e| format!("pulls.json: {e}"))
}

fn load() -> Result<Vec<CfgPull>, String> {
  Ok(load_cfg()?.pulls)
}

/// Progress page on the phone itself: start phone_status.py for this folder, then (once the phone is unlocked)
/// route its port over the USB cable, keep the screen awake while plugged in, and open the page in Chrome.
fn phone_screen(status_page: &Path, folder: &str, title: &str, serial: &str) {
  const SH: &str = r#"pkill -f phone_status.py; sleep 1
nohup python3 "$1" --root "$2" --title "$3" --next "🎙️ New recordings go to the quick pass next. Nothing else to do." >/dev/null 2>&1 &
until adb -s "$4" shell dumpsys trust 2>/dev/null | grep -q deviceLocked=0; do sleep 5; done
adb -s "$4" reverse tcp:8799 tcp:8799; adb -s "$4" shell svc power stayon usb
adb -s "$4" shell am start -a android.intent.action.VIEW -d http://localhost:8799/ com.android.chrome"#;
  let _ = Command::new("/bin/bash")
    .args(["-c", SH, "_"])
    .arg(status_page)
    .args([folder, title, serial])
    .env("PATH", format!("/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{}", std::env::var("PATH").unwrap_or_default()))
    .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
    .spawn();
}

/// Folders that start with the prefix, sorted by name (dates and letters sort in time order).
fn folders(prefix: &str) -> Vec<PathBuf> {
  let pre = expand(prefix);
  let (dir, stem) = match (pre.parent(), pre.file_name()) {
    (Some(d), Some(s)) => (d.to_path_buf(), s.to_string_lossy().to_string()),
    _ => return vec![],
  };
  let mut v: Vec<PathBuf> = fs::read_dir(&dir)
    .map(|rd| {
      rd.flatten()
        .filter(|e| e.file_name().to_string_lossy().starts_with(&stem) && e.path().is_dir())
        .map(|e| e.path())
        .collect()
    })
    .unwrap_or_default();
  v.sort();
  v
}

/// Time of the last pull = the start of the last custody line ("YYYY-MM-DD HH:MM").
fn since_of(folder: &Path) -> Option<String> {
  let txt = fs::read_to_string(folder.join("custody_log.txt")).ok()?;
  let line = txt.lines().filter(|l| l.len() >= 16).last()?;
  let s = &line[..16];
  (s.as_bytes()[4] == b'-' && s.as_bytes()[10] == b' ').then(|| s.to_string())
}

fn adb() -> String {
  for p in ["/opt/homebrew/bin/adb", "/usr/local/bin/adb", "/usr/bin/adb"] {
    if Path::new(p).exists() {
      return p.to_string();
    }
  }
  "adb".to_string()
}

fn connected(serial: &str) -> bool {
  Command::new(adb())
    .arg("devices")
    .output()
    .map(|o| String::from_utf8_lossy(&o.stdout).lines().any(|l| l.starts_with(serial) && l.ends_with("device")))
    .unwrap_or(false)
}

fn model(serial: &str) -> Option<String> {
  let get = |prop: &str| {
    Command::new(adb()).args(["-s", serial, "shell", "getprop", prop]).output().ok()
      .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).filter(|s| !s.is_empty())
  };
  let m = get("ro.product.model")?;
  Some(match get("ro.product.manufacturer") {
    Some(maker) if !m.to_lowercase().starts_with(&maker.to_lowercase()) => format!("{} {}", maker[..1].to_uppercase() + &maker[1..], m),
    _ => m,
  })
}

fn today() -> String {
  Command::new("date").arg("+%F").output().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default()
}

/// A folder is running when it has a PULL_LOG.txt and no finish line yet.
fn running(folder: &Path) -> bool {
  fs::read_to_string(folder.join("PULL_LOG.txt")).map(|t| !t.contains("phase1 done")).unwrap_or(false)
}

pub fn jobs() -> Result<Vec<PullJob>, String> {
  Ok(load()?
    .into_iter()
    .map(|c| {
      let fs_ = folders(&c.dest_prefix);
      // the newest folder that finished is the "last pull"; a newer unfinished one is "running"
      let last = fs_.iter().rev().find(|f| f.join("custody_log.txt").exists()).cloned();
      let run = fs_.last().filter(|f| running(f)).cloned();
      PullJob {
        serial_tail: c.serial.chars().rev().take(4).collect::<String>().chars().rev().collect(),
        connected: connected(&c.serial),
        model: if connected(&c.serial) { model(&c.serial) } else { None },
        since: last.as_deref().and_then(since_of),
        last_folder: last.map(|p| p.display().to_string()),
        running_folder: run.map(|p| p.display().to_string()),
        id: c.id,
        name: c.name,
      }
    })
    .collect())
}

pub fn start(id: &str) -> Result<String, String> {
  let c = load()?.into_iter().find(|c| c.id == id).ok_or("unknown pull")?;
  let fs_ = folders(&c.dest_prefix);
  if let Some(r) = fs_.last().filter(|f| running(f)) {
    return Err(format!("Already running: {}", r.display()));
  }
  let last = fs_.iter().rev().find(|f| f.join("custody_log.txt").exists()).ok_or("No earlier pull folder to continue from")?;
  let since = since_of(last).ok_or("Could not read the time of the last pull")?;
  let day = today();
  let used: Vec<String> = fs_.iter().map(|p| p.display().to_string()).collect();
  let letter = ('a'..='z')
    .find(|l| !used.iter().any(|u| u.ends_with(&format!("{day}{l}"))))
    .ok_or("No folder letter left for today")?;
  let script = expand(&c.script);
  if !script.exists() {
    return Err(format!("Script not found: {}", script.display()));
  }
  Command::new("/bin/bash")
    .arg(&script)
    .arg(letter.to_string())
    .env("SINCE", &since)
    .env("PULL_SERIAL", &c.serial)
    .env("PULL_DEST_PREFIX", expand(&c.dest_prefix))
    .env("PATH", format!("/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{}", std::env::var("PATH").unwrap_or_default()))
    .stdin(Stdio::null())
    .stdout(Stdio::null())
    .stderr(Stdio::null())
    .spawn()
    .map_err(|e| e.to_string())?;
  let folder = format!("{}{day}{letter}", expand(&c.dest_prefix).display());
  if let Some(sp) = load_cfg()?.status_page.map(|p| expand(&p)).filter(|p| p.exists()) {
    let who = model(&c.serial).unwrap_or_else(|| c.name.clone());
    phone_screen(&sp, &folder, &format!("{who} · new since {since}"), &c.serial);
  }
  Ok(folder)
}

pub fn progress(folder: &str) -> Result<Progress, String> {
  let log = fs::read_to_string(Path::new(folder).join("PULL_LOG.txt")).unwrap_or_default();
  let mut steps = vec![];
  for (key, label) in [("sms", "💬 Texts"), ("mms", "🖼️ Picture messages"), ("call_log/calls", "📞 Calls")] {
    let tag = format!("content://{key} rows=");
    if let Some(n) = log.lines().filter_map(|l| l.split_once(&tag).map(|(_, n)| n.trim().to_string())).last() {
      let n: u64 = n.parse().unwrap_or(0);
      steps.push(Step { label: label.into(), done: n, total: n });
    }
  }
  let finished = log.contains("phase1 done");
  if let Some((k, t)) = log.lines().filter_map(|l| l.split_once("new files ").and_then(|(_, r)| r.split_once('/'))).last() {
    let t: u64 = t.trim().parse().unwrap_or(0);
    let k: u64 = if finished { t } else { k.trim().parse().unwrap_or(0) };
    steps.push(Step { label: "🗂️ Files changed on the phone".into(), done: k, total: t });
  }
  let summary = log.lines().filter(|l| l.contains("SAFE TO UNPLUG")).last().map(|l| l.split_once("SAFE TO UNPLUG: ").map(|(_, r)| r).unwrap_or(l).to_string()).unwrap_or_default();
  Ok(Progress { folder: folder.to_string(), steps, finished, summary })
}

#[cfg(test)]
mod tests {
  use super::*;
  #[test]
  fn reads_since_from_custody() {
    let d = std::env::temp_dir().join("pnick_pull_test");
    let _ = fs::create_dir_all(&d);
    fs::write(d.join("custody_log.txt"), "2026-10-29 13:56:20 CDT Play pull\n").unwrap();
    assert_eq!(since_of(&d).as_deref(), Some("2026-10-29 13:56"));
  }
  #[test]
  fn parses_progress_lines() {
    let d = std::env::temp_dir().join("pnick_pull_test2");
    let _ = fs::create_dir_all(&d);
    fs::write(d.join("PULL_LOG.txt"), "x content://sms rows=12\nx new files 3/9\n").unwrap();
    let p = progress(d.to_str().unwrap()).unwrap();
    assert_eq!(p.steps.len(), 2);
    assert_eq!((p.steps[1].done, p.steps[1].total), (3, 9));
    assert!(!p.finished);
  }
}
