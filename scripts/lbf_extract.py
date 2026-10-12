#!/usr/bin/env python3
"""Stream-extract an LG Bridge .lbf backup (added in v0.6.0).

The .lbf starts with an encrypted index (~0.6 MB), then a stream of plain ZIP local entries
(flag 0x808, deflate, sizes in a data descriptor). This walks the entries in order, writes a
manifest of every entry (offset, path, zip date, size, sha256), and extracts the entries that
match KEEP (databases, audio/video); --all extracts every entry. Read-only on the .lbf.
Usage: lbf_extract.py <file.lbf> <outdir> [--all]
"""
import csv, hashlib, os, re, struct, sys, zlib

KEEP = re.compile(r"\.(db|db-wal|db-shm|xml|m4a|3ga|amr|awb|aac|wav|mp3|ogg|opus|3gp|mp4|mov|vcf)$|/(sounds|recordings?|voicerecorder|quickvoicerecorder|audiorecorder|call_?rec)", re.I)
SIG = b"PK\x03\x04"
CH = 1 << 22

def main(src, out, keep_all=False):
    os.makedirs(out, exist_ok=True)
    f = open(src, "rb")
    man = csv.writer(open(os.path.join(out, "LBF_MANIFEST.csv"), "w", newline=""))
    man.writerow(["offset", "path", "zip_date", "zip_time", "size", "sha256", "extracted"])
    buf, base = f.read(CH), 0
    pos = buf.find(SIG)
    n = kept = 0
    while pos != -1:
        f.seek(base + pos)
        hdr = f.read(30)
        if len(hdr) < 30 or hdr[:4] != SIG:
            break
        _, flag, meth, t, d, crc, cs, us, nl, el = struct.unpack("<HHHHHIIIHH", hdr[4:30])
        name = f.read(nl).decode("utf-8", "replace"); f.read(el)
        date = f"{((d >> 9) & 0x7f) + 1980}-{(d >> 5) & 0xf:02}-{d & 0x1f:02}"
        tm = f"{(t >> 11):02}:{(t >> 5) & 0x3f:02}:{(t & 0x1f) * 2:02}"
        keep = keep_all or bool(KEEP.search(name))
        h, size = hashlib.sha256(), 0
        dst = None
        if keep:
            p = os.path.join(out, "files", name.lstrip("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if os.path.exists(p):  # same path stored twice in the .lbf: keep both
                p = f"{p}__off{base + pos}"
            dst = open(p, "wb")
        dec = zlib.decompressobj(-15) if meth == 8 else None
        rest = b""
        remaining = cs if not (flag & 8) else None
        while True:
            chunk = f.read(CH if remaining is None else min(CH, remaining))
            if not chunk:
                break
            if dec:
                data = dec.decompress(chunk)
            else:
                data = chunk
            h.update(data); size += len(data)
            if dst: dst.write(data)
            if remaining is not None:
                remaining -= len(chunk)
                if remaining <= 0: break
            if dec and dec.eof:
                rest = dec.unused_data
                break
        if dst: dst.close()
        man.writerow([base + pos, name, date, tm, size, h.hexdigest(), int(keep)])
        n += 1; kept += keep
        # continue from where the compressed data ended (skip descriptor), then find the next header
        here = f.tell() - len(rest)
        f.seek(here)
        look = f.read(CH)
        nxt = look.find(SIG)
        if nxt == -1:
            # descriptor and padding can't exceed a chunk; stop at EOF
            break
        base, pos = here, nxt
        if n % 500 == 0:
            print(n, "entries", kept, "kept", round(here / 1e9, 2), "GB", flush=True)
    print("done", n, "entries", kept, "kept")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--all" in sys.argv)
