//! "Scan my phone": a read-only, metadata-only look at a connected Android phone, as if it were new.
//! Lists file dates, sizes and types, and the dates of recent calls. Copies no file and reads no message,
//! number or name. Saves only that summary (dates, counts, sizes) to a scan file on this computer.

use serde::Serialize;
use std::collections::BTreeMap;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize)]
pub struct Device { serial_tail: String, serial: String, model: String }

#[derive(Serialize, Default, Clone)]
pub struct Category { name: String, files: u64, bytes: u64, newest: i64, oldest: i64 }

#[derive(Serialize)]
pub struct Call { when_ms: i64, seconds: i64, kind: String }

#[derive(Serialize)]
pub struct Recording { when: i64, bytes: u64, folder: String }

#[derive(Serialize)]
pub struct Scan {
    model: String, android: String, serial_tail: String, scanned_at: i64,
    volumes: Vec<String>, total_files: u64, total_bytes: u64,
    categories: Vec<Category>, top_folders: Vec<(String, u64)>,
    recent_calls: Vec<Call>, calls_readable: bool,
    recent_recordings: Vec<Recording>, saved_to: String,
}

fn adb(serial: &str, args: &[&str]) -> Result<String, String> {
    let bin = crate::check::adb_path().ok_or("adb not found")?;
    let o = Command::new(bin).arg("-s").arg(serial).args(args).output().map_err(|e| e.to_string())?;
    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub fn devices() -> Vec<Device> {
    let Some(bin) = crate::check::adb_path() else { return vec![] };
    let out = Command::new(bin).args(["devices", "-l"]).output().map(|o| String::from_utf8_lossy(&o.stdout).to_string()).unwrap_or_default();
    out.lines().skip(1).filter(|l| l.contains(" device ")).filter_map(|l| {
        let serial = l.split_whitespace().next()?.to_string();
        let model = l.split_whitespace().find_map(|w| w.strip_prefix("model:")).unwrap_or("phone").replace('_', " ");
        let tail = serial.chars().rev().take(4).collect::<String>().chars().rev().collect();
        Some(Device { serial_tail: tail, serial, model })
    }).collect()
}

fn kind_of(path: &str) -> &'static str {
    let ext = path.rsplit('.').next().unwrap_or("").to_lowercase();
    match ext.as_str() {
        "jpg" | "jpeg" | "png" | "heic" | "heif" | "webp" | "dng" | "gif" => "Photos and images",
        "mp4" | "mov" | "mkv" | "webm" | "avi" => "Videos",
        "m4a" | "amr" | "wav" | "aac" | "ogg" | "opus" | "mp3" | "flac" => "Audio (recordings, voice notes)",
        "3gp" => if path.to_lowercase().contains("record") || path.to_lowercase().contains("call") { "Audio (recordings, voice notes)" } else { "Videos" },
        "pdf" | "doc" | "docx" | "xls" | "xlsx" | "ppt" | "pptx" | "txt" | "csv" | "rtf" | "odt" => "Documents",
        "vcf" | "xml" | "json" | "db" | "zip" => "Exports and backups",
        _ => "Other",
    }
}

pub fn scan(serial: &str) -> Result<Scan, String> {
    let model = adb(serial, &["shell", "getprop", "ro.product.model"])?.trim().to_string();
    let android = adb(serial, &["shell", "getprop", "ro.build.version.release"])?.trim().to_string();
    let mut volumes = vec!["/storage/emulated/0/".to_string()];
    for v in adb(serial, &["shell", "ls", "/storage/"])?.split_whitespace() {
        if v != "emulated" && v != "self" && !v.is_empty() { volumes.push(format!("/storage/{v}/")); }
    }
    let mut cats: BTreeMap<&str, Category> = BTreeMap::new();
    let mut folders: BTreeMap<String, u64> = BTreeMap::new();
    let mut audio: Vec<Recording> = Vec::new();
    let (mut total_files, mut total_bytes) = (0u64, 0u64);
    for vol in &volumes {
        // Hidden folders and app caches are skipped; nothing is copied, only date|size|path is listed.
        let cmd = format!("find {vol} \\( -path '*/.*' -o -path '*/Android/obb' -o -path '*/Android/data' \\) -prune -o -type f -exec stat -c '%Y|%s|%n' {{}} +");
        let out = adb(serial, &["shell", &cmd])?;
        for line in out.lines() {
            let mut it = line.splitn(3, '|');
            let (Some(t), Some(sz), Some(p)) = (it.next(), it.next(), it.next()) else { continue };
            let (Ok(t), Ok(sz)) = (t.parse::<i64>(), sz.parse::<u64>()) else { continue };
            let k = kind_of(p);
            let c = cats.entry(k).or_insert_with(|| Category { name: k.into(), oldest: i64::MAX, ..Default::default() });
            c.files += 1; c.bytes += sz; c.newest = c.newest.max(t); c.oldest = c.oldest.min(t);
            total_files += 1; total_bytes += sz;
            let rel = p.strip_prefix(vol.as_str()).unwrap_or(p);
            let top = rel.split('/').next().unwrap_or("").to_string();
            let label = if vol.contains("emulated") { top } else { format!("SD card/{top}") };
            *folders.entry(label.clone()).or_default() += 1;
            if k.starts_with("Audio") {
                let folder = rel.rsplit_once('/').map(|(d, _)| d).unwrap_or("").to_string();
                let folder = if vol.contains("emulated") { folder } else { format!("SD card/{folder}") };
                audio.push(Recording { when: t, bytes: sz, folder });
            }
        }
    }
    audio.sort_by(|a, b| b.when.cmp(&a.when)); audio.truncate(10);
    let mut top: Vec<(String, u64)> = folders.into_iter().collect();
    top.sort_by(|a, b| b.1.cmp(&a.1)); top.truncate(8);
    // Calls: date, length and direction only. No number, no name.
    let raw = adb(serial, &["shell", "content", "query", "--uri", "content://call_log/calls", "--projection", "date:duration:type"])?;
    let mut calls: Vec<Call> = raw.lines().filter_map(|l| {
        let g = |k: &str| l.split(&format!("{k}=")).nth(1)?.split(',').next()?.trim().parse::<i64>().ok();
        let kind = match g("type")? { 1 => "incoming", 2 => "outgoing", 3 => "missed", 4 => "voicemail", 5 => "declined", 6 => "blocked", _ => "other" };
        Some(Call { when_ms: g("date")?, seconds: g("duration").unwrap_or(0), kind: kind.into() })
    }).collect();
    let calls_readable = !calls.is_empty();
    calls.sort_by(|a, b| b.when_ms.cmp(&a.when_ms)); calls.truncate(10);
    let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0);
    let tail: String = serial.chars().rev().take(4).collect::<String>().chars().rev().collect();
    let mut categories: Vec<Category> = cats.into_values().collect();
    categories.sort_by(|a, b| b.files.cmp(&a.files));
    let mut scan = Scan { model, android, serial_tail: tail, scanned_at: now, volumes, total_files, total_bytes,
        categories, top_folders: top, recent_calls: calls, calls_readable, recent_recordings: audio, saved_to: String::new() };
    // Save the summary (dates, counts, sizes only) next to earlier scans.
    if let Some(home) = std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE")) {
        let dir = std::path::PathBuf::from(home).join("phone-net-ICKS").join("scans");
        if std::fs::create_dir_all(&dir).is_ok() {
            let safe: String = scan.model.chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect();
            let f = dir.join(format!("scan_{now}_{safe}_{}.json", scan.serial_tail));
            if let Ok(j) = serde_json::to_string_pretty(&scan) {
                if std::fs::write(&f, j).is_ok() { scan.saved_to = f.display().to_string(); }
            }
        }
    }
    Ok(scan)
}
