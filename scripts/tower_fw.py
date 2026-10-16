"""Tower CPU lane (2026-10-15): faster-whisper large-v3 int8 on CPU, beam 10, VAD, word confidence. Args: in.wav out_prefix [prompt]."""
import sys, os, json, time, soundfile as sf
from faster_whisper import WhisperModel
T = int(os.environ.get("LOWPRIO_THREADS", "16"))
m = WhisperModel(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models/faster-whisper-large-v3"), device="cpu", compute_type="int8", cpu_threads=T)
audio, _ = sf.read(sys.argv[1], dtype="float32"); t0 = time.time()
segs, info = m.transcribe(audio, language="en", beam_size=10, vad_filter=True, vad_parameters={"threshold": 0.3, "min_silence_duration_ms": 400},
                          word_timestamps=True, initial_prompt=(sys.argv[3] if len(sys.argv) > 3 else None))
out = []
for s in segs:
    conf = sum(w.probability for w in s.words) / max(1, len(s.words))
    out.append({"start": s.start, "end": s.end, "text": s.text.strip(), "conf": round(conf, 3)})
md = [f"# {os.path.basename(sys.argv[1])} — faster-whisper large-v3 int8 CPU (Tower, {T} threads), beam 10", ""]
md += [f"[{int(x['start'])//60:02d}:{int(x['start'])%60:02d}] {x['text']}" + ("  ⟨low conf⟩" if x["conf"] < 0.6 else "") for x in out]
json.dump(out, open(sys.argv[2] + ".json", "w"), indent=1); open(sys.argv[2] + ".md", "w").write("\n".join(md) + "\n")
print(json.dumps({"segments": len(out), "low_conf": sum(1 for x in out if x["conf"] < 0.6), "audio_s": round(len(audio) / 16000), "wall_s": round(time.time() - t0), "threads": T}))
