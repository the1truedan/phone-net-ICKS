//! "Ask my records": local search over a folder + a local Ollama model.
//! Talks only to Ollama on 127.0.0.1. Reads text files under the chosen folder; writes nothing.

use serde::Serialize;
use serde_json::{json, Value};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

const OLLAMA: &str = "http://127.0.0.1:11434";
const TEXT_EXT: &[&str] = &["txt", "md", "csv", "tsv", "json", "jsonl", "srt", "vtt", "xml", "html"];
const MAX_FILES: usize = 50_000;
const MAX_FILE_BYTES: u64 = 8 * 1024 * 1024;
const MAX_DEPTH: usize = 10;

#[derive(Serialize, Clone)]
pub struct Hit {
    file: String,
    line: usize,
    text: String,
    #[serde(skip)]
    score: usize,
}

#[derive(Serialize)]
pub struct Answer {
    answer: String,
    hits: Vec<Hit>,
    files_searched: usize,
}

fn agent(secs: u64) -> ureq::Agent {
    ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(secs)))
        .build()
        .into()
}

pub fn models() -> Result<Vec<String>, String> {
    let mut resp = agent(5).get(&format!("{OLLAMA}/api/tags")).call().map_err(|e| e.to_string())?;
    let v: Value = resp.body_mut().read_json().map_err(|e| e.to_string())?;
    Ok(v["models"].as_array().into_iter().flatten()
        .filter_map(|m| m["name"].as_str().map(String::from))
        .filter(|n| !n.contains("embed"))
        .collect())
}

fn expand(p: &str) -> PathBuf {
    if let Some(rest) = p.strip_prefix("~/") {
        if let Some(h) = std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE")) {
            return PathBuf::from(h).join(rest);
        }
    }
    PathBuf::from(p)
}

const STOP: &[&str] = &["the", "and", "for", "was", "were", "did", "does", "what", "when", "which", "who", "how",
    "that", "this", "with", "from", "have", "has", "are", "any", "all", "last", "about", "there", "they", "their", "mention"];

fn terms(q: &str) -> Vec<String> {
    let mut seen = HashSet::new();
    q.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|w| w.len() >= 3 && !STOP.contains(w))
        .filter(|w| seen.insert(w.to_string()))
        .map(String::from)
        .collect()
}

fn walk(dir: &Path, depth: usize, out: &mut Vec<PathBuf>) {
    if depth > MAX_DEPTH || out.len() >= MAX_FILES {
        return;
    }
    let Ok(rd) = fs::read_dir(dir) else { return };
    for e in rd.flatten() {
        let p = e.path();
        let name = e.file_name().to_string_lossy().to_string();
        if name.starts_with('.') {
            continue;
        }
        let Ok(ft) = e.file_type() else { continue };
        if ft.is_dir() {
            walk(&p, depth + 1, out);
        } else if ft.is_file() {
            let ext = p.extension().map(|x| x.to_string_lossy().to_lowercase()).unwrap_or_default();
            if TEXT_EXT.contains(&ext.as_str()) && e.metadata().map(|m| m.len() <= MAX_FILE_BYTES).unwrap_or(false) {
                out.push(p);
            }
        }
        if out.len() >= MAX_FILES {
            return;
        }
    }
}

pub fn search(folder: &str, question: &str, limit: usize) -> Result<(Vec<Hit>, usize), String> {
    let root = expand(folder.trim());
    if folder.trim().is_empty() || !root.is_dir() {
        return Err("Choose a records folder first (a folder on this computer).".into());
    }
    let ts = terms(question);
    if ts.is_empty() {
        return Err("Ask with a few more specific words.".into());
    }
    let mut files = Vec::new();
    walk(&root, 0, &mut files);
    let mut hits: Vec<Hit> = Vec::new();
    for f in &files {
        let Ok(bytes) = fs::read(f) else { continue };
        let text = String::from_utf8_lossy(&bytes);
        let lines: Vec<&str> = text.lines().collect();
        for (i, l) in lines.iter().enumerate() {
            let low = l.to_lowercase();
            let score = ts.iter().filter(|t| low.contains(t.as_str())).count();
            if score == 0 {
                continue;
            }
            let ctx = [i.checked_sub(1).and_then(|j| lines.get(j)), Some(l), lines.get(i + 1)]
                .into_iter().flatten().map(|s| s.trim()).collect::<Vec<_>>().join(" ⏎ ");
            hits.push(Hit {
                file: f.strip_prefix(&root).unwrap_or(f).display().to_string(),
                line: i + 1,
                text: ctx.chars().take(500).collect(),
                score,
            });
        }
    }
    hits.sort_by(|a, b| b.score.cmp(&a.score).then_with(|| a.file.cmp(&b.file)));
    hits.truncate(limit);
    Ok((hits, files.len()))
}

pub fn ask(folder: &str, model: &str, question: &str) -> Result<Answer, String> {
    if model.trim().is_empty() {
        return Err("Pick a model (install Ollama and pull one first).".into());
    }
    let (hits, files_searched) = search(folder, question, 12)?;
    if hits.is_empty() {
        return Ok(Answer { answer: "I found nothing about that in the chosen folder.".into(), hits, files_searched });
    }
    let excerpts = hits.iter().enumerate()
        .map(|(i, h)| format!("[{}] {}:{}\n{}", i + 1, h.file, h.line, h.text))
        .collect::<Vec<_>>().join("\n\n");
    let system = "You help a family caregiver read their own records. Answer ONLY from the numbered excerpts. \
        Put the excerpt number in brackets after each fact, like [2]. If the excerpts do not answer the question, say so. \
        Do not guess dates, amounts or names. Keep it short and plain.";
    let body = json!({
        "model": model,
        "stream": false,
        // Thinking models (e.g. gemma, qwen3) can run for minutes without this; keep answers short.
        "think": false,
        "options": {"num_predict": 700},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": format!("Excerpts:\n{excerpts}\n\nQuestion: {question}")}
        ]
    });
    let mut resp = agent(600).post(&format!("{OLLAMA}/api/chat")).send_json(&body).map_err(|e| e.to_string())?;
    let v: Value = resp.body_mut().read_json().map_err(|e| e.to_string())?;
    let answer = v["message"]["content"].as_str().unwrap_or("(no answer)").trim().to_string();
    Ok(Answer { answer, hits, files_searched })
}
