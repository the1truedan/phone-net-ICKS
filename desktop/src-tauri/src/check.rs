//! "Check my computer": finds the tools the pipeline needs and whether a phone is plugged in.
//! Read-only. It runs `--version`-style commands and `adb devices`; it reads no user files.

use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize)]
pub struct CheckRow {
    name: String,
    purpose: String,
    status: String, // "ok" | "missing" | "warn"
    detail: String,
    help_url: String,
}

struct Tool {
    name: &'static str,
    bins: &'static [&'static str],
    version_arg: &'static str,
    purpose: &'static str,
    help_url: &'static str,
}

const TOOLS: &[Tool] = &[
    Tool { name: "adb", bins: &["adb"], version_arg: "version",
           purpose: "Copies files from your Android phone over USB.",
           help_url: "https://developer.android.com/tools/releases/platform-tools" },
    Tool { name: "FFmpeg", bins: &["ffmpeg"], version_arg: "-version",
           purpose: "Reads true recording dates and cleans up audio.",
           help_url: "https://ffmpeg.org/download.html" },
    Tool { name: "ffprobe", bins: &["ffprobe"], version_arg: "-version",
           purpose: "Comes with FFmpeg. Reads when each file was made.",
           help_url: "https://ffmpeg.org/download.html" },
    Tool { name: "whisper.cpp", bins: &["whisper-cli", "whisper-cpp"], version_arg: "--help",
           purpose: "Turns speech into text on your own computer.",
           help_url: "https://github.com/ggml-org/whisper.cpp#quick-start" },
    Tool { name: "Ollama", bins: &["ollama"], version_arg: "--version",
           purpose: "Runs local models for summaries and search. Optional.",
           help_url: "https://ollama.com/download" },
];

/// Apps opened from the Dock or Start menu do not get the shell PATH,
/// so also look where Homebrew, apt and the installers usually put things.
fn search_dirs() -> Vec<PathBuf> {
    let mut dirs: Vec<PathBuf> = std::env::var_os("PATH")
        .map(|p| std::env::split_paths(&p).collect())
        .unwrap_or_default();
    for d in ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/snap/bin"] {
        dirs.push(PathBuf::from(d));
    }
    if let Some(home) = home_dir() {
        dirs.push(home.join("Library/Android/sdk/platform-tools"));
        dirs.push(home.join("Android/Sdk/platform-tools"));
        dirs.push(home.join(".local/bin"));
        dirs.push(home.join("AppData/Local/Android/Sdk/platform-tools"));
        dirs.push(home.join("AppData/Local/Programs/Ollama"));
    }
    dirs
}

fn home_dir() -> Option<PathBuf> {
    std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE")).map(PathBuf::from)
}

fn find_bin(names: &[&str]) -> Option<PathBuf> {
    let exts: &[&str] = if cfg!(windows) { &[".exe", ".cmd", ".bat", ""] } else { &[""] };
    for dir in search_dirs() {
        for n in names {
            for e in exts {
                let p = dir.join(format!("{n}{e}"));
                if p.is_file() {
                    return Some(p);
                }
            }
        }
    }
    None
}

fn first_line(bin: &Path, arg: &str) -> String {
    match Command::new(bin).arg(arg).output() {
        Ok(o) => {
            let text = if o.stdout.is_empty() { o.stderr } else { o.stdout };
            String::from_utf8_lossy(&text).lines().map(str::trim).find(|l| !l.is_empty()).unwrap_or("").chars().take(120).collect()
        }
        Err(e) => format!("found, but would not run: {e}"),
    }
}

fn phone_row(adb: Option<&PathBuf>) -> CheckRow {
    let mut row = CheckRow {
        name: "Phone connected".into(),
        purpose: "Plug in the phone, unlock it and tap Allow on the USB debugging prompt.".into(),
        status: "missing".into(),
        detail: String::new(),
        help_url: "https://developer.android.com/studio/debug/dev-options#Enable-debugging".into(),
    };
    let Some(adb) = adb else {
        row.detail = "needs adb first".into();
        return row;
    };
    match Command::new(adb).arg("devices").output() {
        Ok(o) => {
            let out = String::from_utf8_lossy(&o.stdout);
            let lines: Vec<&str> = out.lines().skip(1).filter(|l| !l.trim().is_empty()).collect();
            let ready = lines.iter().filter(|l| l.ends_with("\tdevice")).count();
            let unauth = lines.iter().filter(|l| l.contains("unauthorized")).count();
            if ready > 0 {
                row.status = "ok".into();
                row.detail = format!("{ready} phone(s) ready");
            } else if unauth > 0 {
                row.status = "warn".into();
                row.detail = "phone found: tap Allow on the phone screen".into();
            } else {
                row.detail = "no phone found".into();
            }
        }
        Err(e) => row.detail = format!("adb would not run: {e}"),
    }
    row
}

fn disk_row() -> CheckRow {
    let mut row = CheckRow {
        name: "Free disk space".into(),
        purpose: "Recordings take room. 50 GB free or more is comfortable.".into(),
        status: "warn".into(),
        detail: "could not read".into(),
        help_url: String::new(),
    };
    if let Some(gb) = free_gb() {
        row.detail = format!("{gb:.0} GB free in your home folder");
        row.status = if gb >= 50.0 { "ok" } else { "warn" }.into();
    }
    row
}

#[cfg(unix)]
fn free_gb() -> Option<f64> {
    let home = home_dir()?;
    let o = Command::new("df").arg("-Pk").arg(&home).output().ok()?;
    let out = String::from_utf8_lossy(&o.stdout);
    let kb: f64 = out.lines().nth(1)?.split_whitespace().nth(3)?.parse().ok()?;
    Some(kb / 1024.0 / 1024.0)
}

#[cfg(windows)]
fn free_gb() -> Option<f64> {
    let o = Command::new("powershell")
        .args(["-NoProfile", "-Command", "(Get-PSDrive -Name ($env:SystemDrive.TrimEnd(':'))).Free"])
        .output().ok()?;
    let bytes: f64 = String::from_utf8_lossy(&o.stdout).trim().parse().ok()?;
    Some(bytes / 1024.0 / 1024.0 / 1024.0)
}

pub fn run_checks() -> Vec<CheckRow> {
    let mut rows = Vec::new();
    let mut adb = None;
    for t in TOOLS {
        let found = find_bin(t.bins);
        let (status, detail) = match &found {
            Some(p) => ("ok", format!("{} · {}", p.display(), first_line(p, t.version_arg))),
            None => ("missing", "not found".to_string()),
        };
        if t.name == "adb" {
            adb = found.clone();
        }
        rows.push(CheckRow {
            name: t.name.into(),
            purpose: t.purpose.into(),
            status: status.into(),
            detail,
            help_url: t.help_url.into(),
        });
    }
    rows.push(phone_row(adb.as_ref()));
    rows.push(disk_row());
    rows
}

// ---------- Phone (read-only) ----------

const PHONE_APPS: &[(&str, &str, &str)] = &[
    ("epic.mychart.android", "MyChart (patient portal)", "Visit summaries and notes; save them with you in the loop."),
    ("com.gtindependence.Caregiver", "Caregiver time app (payroll agency)", "Shifts and approvals; screens saved as you go."),
    ("com.google.android.calendar", "Google Calendar", "Appointments; best copied with your account's own export."),
    ("com.google.android.gm", "Gmail", "Email; best copied with your account's own export."),
    ("com.google.android.apps.tasks", "Google Tasks", "Your notes and to-dos; account export."),
    ("com.google.android.apps.messaging", "Google Messages", "Texts. Long texts are stored as MMS."),
    ("com.truecaller", "Truecaller", "Caller ID and call history; can also export texts."),
    ("com.riteshsahu.SMSBackupRestore", "SMS Backup & Restore", "Helper app: backs up texts and calls to a file."),
];

fn adb_out(adb: &Path, args: &[&str]) -> Option<String> {
    let o = Command::new(adb).args(args).output().ok()?;
    o.status.success().then(|| String::from_utf8_lossy(&o.stdout).to_string())
}

fn count_rows(adb: &Path, uri: &str) -> Option<usize> {
    // IDs only: counts rows, never reads message text.
    let out = adb_out(adb, &["shell", "content", "query", "--uri", uri, "--projection", "_id"])?;
    Some(out.lines().filter(|l| l.starts_with("Row:")).count())
}

pub fn phone_checks() -> Vec<CheckRow> {
    let Some(adb) = find_bin(&["adb"]) else {
        return vec![CheckRow { name: "Phone".into(), purpose: "Needs adb first (see Check my computer).".into(),
            status: "missing".into(), detail: "adb not found".into(),
            help_url: "https://developer.android.com/tools/releases/platform-tools".into() }];
    };
    let devices = adb_out(&adb, &["devices"]).unwrap_or_default();
    if !devices.lines().skip(1).any(|l| l.ends_with("\tdevice")) {
        return vec![CheckRow { name: "Phone".into(), purpose: "Plug in, unlock, tap Allow on the USB debugging prompt.".into(),
            status: "missing".into(), detail: "no phone ready".into(),
            help_url: "https://developer.android.com/studio/debug/dev-options#Enable-debugging".into() }];
    }
    let model = adb_out(&adb, &["shell", "getprop", "ro.product.model"]).unwrap_or_default().trim().to_string();
    let pkgs = adb_out(&adb, &["shell", "pm", "list", "packages"]).unwrap_or_default();
    let have: std::collections::HashSet<&str> = pkgs.lines().filter_map(|l| l.strip_prefix("package:")).map(str::trim).collect();
    let mut rows = vec![CheckRow { name: format!("Phone connected: {model}"), purpose: "Read-only checks below. Nothing on the phone is changed.".into(),
        status: "ok".into(), detail: String::new(), help_url: String::new() }];
    for (pkg, name, purpose) in PHONE_APPS {
        let on = have.contains(pkg);
        rows.push(CheckRow { name: (*name).into(), purpose: (*purpose).into(),
            status: if on { "ok" } else { "warn" }.into(),
            detail: if on { format!("installed · {pkg}") } else { "not on this phone".into() },
            help_url: String::new() });
    }
    let sms = count_rows(&adb, "content://sms");
    let mms = count_rows(&adb, "content://mms");
    let (st, detail) = match (sms, mms) {
        (Some(s), Some(m)) if s + m > 0 => ("ok", format!("{s} texts + {m} MMS readable over the cable (counts only)")),
        (Some(_), Some(_)) => ("warn", "0 readable: this phone blocks it. Use a helper app (SMS Backup & Restore) instead.".into()),
        _ => ("warn", "could not read: use a helper app (SMS Backup & Restore) instead".into()),
    };
    rows.push(CheckRow { name: "Texts readable without a helper app".into(),
        purpose: "Long texts are stored as MMS, so both are counted.".into(), status: st.into(), detail,
        help_url: "https://www.synctech.com.au/sms-backup-restore/".into() });
    rows
}

// ---------- Speaker names (optional, local) ----------

pub fn speaker_checks(pointed: Option<String>) -> Vec<CheckRow> {
    let mut rows = Vec::new();
    // Prefer the Python the user pointed at, then a dedicated venv (~/.venvs/*), then the system Python.
    let mut cands: Vec<PathBuf> = Vec::new();
    if let Some(p) = pointed.as_deref().map(str::trim).filter(|p| !p.is_empty()) {
        let p = match p.strip_prefix("~/") { Some(r) => home_dir().map(|h| h.join(r)).unwrap_or_else(|| PathBuf::from(p)), None => PathBuf::from(p) };
        if p.is_file() { cands.push(p); }
    }
    if let Some(h) = home_dir() {
        let pref = h.join(".venvs/pyannote/bin/python");
        if pref.is_file() { cands.push(pref); }
        if let Ok(rd) = fs::read_dir(h.join(".venvs")) {
            for e in rd.flatten() {
                for n in ["bin/python", "Scripts/python.exe"] {
                    let p = e.path().join(n);
                    if p.is_file() && !cands.contains(&p) { cands.push(p); }
                }
            }
        }
    }
    if let Some(p) = find_bin(&["python3", "python"]) { cands.push(p); }
    let has_pyannote = |p: &Path| Command::new(p)
        .args(["-c", "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pyannote.audio') else 1)"])
        .status().map(|s| s.success()).unwrap_or(false);
    let with_pa = cands.iter().find(|p| has_pyannote(p)).cloned();
    let py = with_pa.clone().or_else(|| cands.last().cloned());
    rows.push(CheckRow { name: "Python 3".into(), purpose: "Runs the speaker-separation model (pyannote).".into(),
        status: if py.is_some() { "ok" } else { "missing" }.into(),
        detail: py.as_ref().map(|p| format!("{} · {}", p.display(), first_line(p, "--version"))).unwrap_or("not found".into()),
        help_url: "https://www.python.org/downloads/".into() });
    let ver = with_pa.as_ref().and_then(|p| Command::new(p)
        .args(["-c", "import importlib.metadata as m;print(m.version('pyannote.audio'))"]).output().ok())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default();
    rows.push(CheckRow { name: "pyannote.audio".into(),
        purpose: "Tells voices apart. Best in its own environment, e.g. ~/.venvs/pyannote (Python 3.12).".into(),
        status: if with_pa.is_some() { "ok" } else { "missing" }.into(),
        detail: match &with_pa { Some(p) => format!("{ver} · {}", p.display()), None => "not installed in any Python found".into() },
        help_url: "https://github.com/pyannote/pyannote-audio".into() });
    // Existence only. The token itself is never read or shown.
    let token = std::env::var_os("HF_TOKEN").is_some() || home_dir().map(|h| h.join(".cache/huggingface/token").is_file()).unwrap_or(false);
    rows.push(CheckRow { name: "Hugging Face token saved".into(),
        purpose: "1) Make a free account. 2) Open the model page and accept its terms. 3) Make a read token. 4) Run: hf auth login. The model then runs on this computer.".into(),
        status: if token { "ok" } else { "missing" }.into(), detail: if token { "found (not read)".into() } else { "not found".into() },
        help_url: "https://huggingface.co/pyannote/speaker-diarization-community-1".into() });
    rows
}

/// Open an https link in the user's normal browser (not inside the app window).
pub fn open_external(url: &str) -> Result<(), String> {
    if !url.starts_with("https://") {
        return Err("only https links".into());
    }
    #[cfg(target_os = "macos")]
    let r = Command::new("open").arg(url).status();
    #[cfg(target_os = "windows")]
    let r = Command::new("rundll32").args(["url.dll,FileProtocolHandler", url]).status();
    #[cfg(all(unix, not(target_os = "macos")))]
    let r = Command::new("xdg-open").arg(url).status();
    r.map(|_| ()).map_err(|e| e.to_string())
}

// ---------- Hugging Face access (on click only; contacts huggingface.co) ----------

const HF_MODEL: &str = "pyannote/speaker-diarization-community-1";

fn python_with_pyannote(pointed: Option<String>) -> Option<PathBuf> {
    let mut cands: Vec<PathBuf> = Vec::new();
    if let Some(p) = pointed.as_deref().map(str::trim).filter(|p| !p.is_empty()) {
        let p = match p.strip_prefix("~/") { Some(r) => home_dir().map(|h| h.join(r)).unwrap_or_else(|| PathBuf::from(p)), None => PathBuf::from(p) };
        if p.is_file() { cands.push(p); }
    }
    if let Some(h) = home_dir() {
        if let Ok(rd) = fs::read_dir(h.join(".venvs")) {
            for e in rd.flatten() {
                for n in ["bin/python", "Scripts/python.exe"] {
                    let p = e.path().join(n);
                    if p.is_file() { cands.push(p); }
                }
            }
        }
    }
    if let Some(p) = find_bin(&["python3", "python"]) { cands.push(p); }
    cands.into_iter().find(|p| Command::new(p)
        .args(["-c", "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('huggingface_hub') else 1)"])
        .status().map(|s| s.success()).unwrap_or(false))
}

/// Asks Hugging Face who the saved token belongs to and whether it can open the speaker model.
/// The token is never printed, returned or logged.
pub fn hf_access(pointed: Option<String>) -> Vec<CheckRow> {
    let row = |name: &str, purpose: &str, status: &str, detail: String, url: &str| CheckRow {
        name: name.into(), purpose: purpose.into(), status: status.into(), detail, help_url: url.into() };
    let Some(py) = python_with_pyannote(pointed) else {
        return vec![row("Hugging Face check", "Install pyannote first (it brings the Hugging Face library).", "missing",
            "no Python with huggingface_hub found".into(), "https://github.com/pyannote/pyannote-audio")];
    };
    let script = format!(r#"
from huggingface_hub import HfApi, get_token
from huggingface_hub.utils import GatedRepoError, HfHubHTTPError
t = get_token()
if not t:
    print("NOTOKEN"); raise SystemExit
api = HfApi(token=t)
try:
    print("ACCOUNT", api.whoami().get("name", "?"))
except HfHubHTTPError:
    print("BADTOKEN"); raise SystemExit
try:
    api.auth_check("{HF_MODEL}"); print("ACCESS ok")
except GatedRepoError:
    print("ACCESS terms")
except HfHubHTTPError:
    print("ACCESS error")
"#);
    let out = match Command::new(&py).args(["-I", "-c", &script]).output() {
        Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
        Err(e) => return vec![row("Hugging Face check", "Could not run the check.", "warn", e.to_string(), "")],
    };
    let mut rows = Vec::new();
    if out.contains("NOTOKEN") {
        rows.push(row("Hugging Face token", "Make a free account, then Settings > Access Tokens > New token (type: Read). Then in Terminal run: hf auth login, and paste it there (not here).",
            "missing", "no token saved on this computer".into(), "https://huggingface.co/settings/tokens"));
        return rows;
    }
    if out.contains("BADTOKEN") {
        rows.push(row("Hugging Face token", "The saved token was refused. Make a new Read token and run: hf auth login.",
            "missing", "token not accepted".into(), "https://huggingface.co/settings/tokens"));
        return rows;
    }
    let acct = out.lines().find_map(|l| l.strip_prefix("ACCOUNT ")).unwrap_or("?").trim().to_string();
    rows.push(row("Hugging Face token", "Saved and working. The token itself is never shown.", "ok", format!("account: {acct}"), ""));
    let (st, d, p) = if out.contains("ACCESS ok") {
        ("ok", "terms accepted · model can be downloaded".to_string(), "Ready. The model downloads once, then runs offline on this computer.")
    } else if out.contains("ACCESS terms") {
        ("missing", "terms not accepted yet".to_string(), "Open the model page while logged in, fill in the short form and click Agree. Then check again.")
    } else {
        ("warn", "could not reach Hugging Face".to_string(), "Check the internet connection and try again.")
    };
    rows.push(row("Speaker model terms", p, st, d, "https://huggingface.co/pyannote/speaker-diarization-community-1"));
    rows
}

/// adb location for other modules (same search as the checks).
pub fn adb_path() -> Option<PathBuf> {
    find_bin(&["adb"])
}
