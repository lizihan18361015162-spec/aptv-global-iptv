#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

SOURCES = [
    ("best-status", 0, "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all_status.m3u8"),
    ("guovin", 20, "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"),
    ("official", 30, "https://raw.githubusercontent.com/mytv-android/China-TV-Live-M3U8/main/iptv.m3u"),
    ("best-main", 40, "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all.m3u8"),
]

TARGET_FILES = ["china_stable.m3u", "china500.m3u"]

FETCH_TIMEOUT = 6
FFPROBE_TIMEOUT = 10
FFMPEG_TIMEOUT = 12
MAX_CANDIDATES_PER_CHANNEL = 10

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

def attrs(line):
    return dict(ATTR_RE.findall(line))

def http_fetch(url, limit=256 * 1024):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (AppleTV; U; CPU OS 18_0 like Mac OS X)",
            "Accept": "*/*",
            "Connection": "close",
        },
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        data = r.read(limit)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return data, r.geturl(), elapsed_ms

def fetch_text(url):
    data, _, _ = http_fetch(url, 2 * 1024 * 1024)
    return data.decode("utf-8", "ignore")

def cctv_key(name):
    s = (name or "").strip()

    if re.search(r'(?i)cctv[\s_-]*(?:4k|uhd)', s):
        return "CCTV-4K"
    if re.search(r'(?i)cctv[\s_-]*8k', s):
        return "CCTV-8K"

    m = re.search(r'(?i)cctv[\s_-]*0?(\d+)\s*\+', s)
    if m:
        return f"CCTV-{int(m.group(1))}+"

    m = re.search(r'(?i)cctv[\s_-]*0?(\d+)', s)
    if m:
        return f"CCTV-{int(m.group(1))}"

    return None

def quality(meta, name):
    s = (meta + " " + name).lower()
    for q, p in [
        (2160, r'4k|uhd|2160'),
        (1080, r'1080|fhd'),
        (720, r'720'),
        (576, r'576'),
        (480, r'480'),
    ]:
        if re.search(p, s):
            return q
    return 0

def score(meta, url, source_weight, name):
    m = re.search(r'response-time="(\d+)ms"', meta, re.I)
    rt = int(m.group(1)) if m else 180
    q = quality(meta, name)

    s = source_weight + rt

    if q == 1080:
        s -= 100
    elif q == 720:
        s -= 60
    elif q == 576:
        s -= 5
    elif q == 480:
        s += 10
    elif q >= 2160:
        s -= 20

    if url.startswith("https://"):
        s -= 15

    if ".m3u8" in url.lower():
        s -= 10

    # 运营商本地 tsfile/playlive 源经常“能连上但外网黑屏”，显著降权。
    if "/tsfile/live/" in url.lower() or "playlive=1" in url.lower():
        s += 160

    return s

def parse_source(text, source_name, source_weight):
    lines = text.splitlines()
    rows = []

    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue

        meta = line.strip()
        raw_name = meta.rsplit(",", 1)[-1].strip()
        a = attrs(meta)
        tvg_name = a.get("tvg-name", "")

        key = cctv_key(raw_name) or cctv_key(tvg_name)
        if not key:
            continue

        j = i + 1
        while j < len(lines) and (not lines[j].strip() or lines[j].startswith("#")):
            j += 1

        url = lines[j].strip() if j < len(lines) else ""
        if not re.match(r'^https?://', url, re.I):
            continue

        rows.append({
            "key": key,
            "name": key,
            "meta": meta,
            "attrs": a,
            "url": url,
            "source": source_name,
            "score": score(meta, url, source_weight, raw_name),
        })

    return rows

def verify_hls_manifest(url):
    """
    先做轻量网络/HLS检测，排除明显失效或返回HTML的地址。
    """
    try:
        data, final_url, manifest_ms = http_fetch(url)
        head = data[:2048].lower()

        if b"<html" in head or b"<!doctype html" in head:
            return None

        text = data.decode("utf-8", "ignore")
        if "#EXTM3U" not in text.upper():
            return None

        uris = [
            x.strip()
            for x in text.splitlines()
            if x.strip() and not x.lstrip().startswith("#")
        ]
        if not uris:
            return None

        # 至少确认第一个子清单/分片能访问。
        first_child = urllib.parse.urljoin(final_url, uris[0])
        child, _, child_ms = http_fetch(first_child, 64 * 1024)

        if len(child) < 256:
            return None

        if b"<html" in child[:1024].lower():
            return None

        return manifest_ms + child_ms
    except Exception:
        return None

def ffprobe_video(url):
    """
    必须检测到视频流。仅有音频、空清单、黑洞流都不通过。
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-user_agent", "Mozilla/5.0 (AppleTV; U; CPU OS 18_0 like Mac OS X)",
        "-rw_timeout", "8000000",
        "-show_entries", "stream=index,codec_type,codec_name,width,height,avg_frame_rate",
        "-of", "json",
        url,
    ]

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None

    if p.returncode != 0:
        return None

    try:
        data = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        return None

    videos = [
        s for s in data.get("streams", [])
        if s.get("codec_type") == "video"
        and int(s.get("width") or 0) > 0
        and int(s.get("height") or 0) > 0
    ]

    if not videos:
        return None

    best = max(videos, key=lambda s: int(s.get("height") or 0))
    return {
        "codec": best.get("codec_name") or "",
        "width": int(best.get("width") or 0),
        "height": int(best.get("height") or 0),
    }

def ffmpeg_decode(url):
    """
    实际解码几帧视频，专门排除“URL不超时但黑屏/不可解码”的情况。
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-user_agent", "Mozilla/5.0 (AppleTV; U; CPU OS 18_0 like Mac OS X)",
        "-rw_timeout", "8000000",
        "-i", url,
        "-map", "0:v:0",
        "-frames:v", "3",
        "-f", "null",
        "-",
    ]

    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=FFMPEG_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False

    return p.returncode == 0

def validate_candidate(row):
    url = row["url"]

    manifest_latency = verify_hls_manifest(url)
    if manifest_latency is None:
        return None

    info = ffprobe_video(url)
    if not info:
        return None

    if not ffmpeg_decode(url):
        return None

    return {
        "latency": manifest_latency,
        "codec": info["codec"],
        "width": info["width"],
        "height": info["height"],
    }

def pick_verified_cctv():
    by_key = {}

    for source_name, source_weight, source_url in SOURCES:
        try:
            rows = parse_source(fetch_text(source_url), source_name, source_weight)
            print(f"[OK] {source_name}: {len(rows)} CCTV candidates")
        except Exception as e:
            print(f"[WARN] {source_name}: {e}")
            continue

        for row in rows:
            by_key.setdefault(row["key"], []).append(row)

    selected = {}

    for key, rows in by_key.items():
        rows.sort(key=lambda x: x["score"])

        for row in rows[:MAX_CANDIDATES_PER_CHANNEL]:
            result = validate_candidate(row)

            if result is None:
                print(f"[FAIL] {key}: {row['url']}")
                continue

            # 最终再把实测分辨率、延迟并入优选。
            row["verify"] = result
            selected[key] = row

            print(
                f"[PASS] {key}: {row['source']} | "
                f"{result['width']}x{result['height']} | "
                f"{result['codec']} | "
                f"{result['latency']} ms | {row['url']}"
            )
            break

    return selected

def parse_m3u_records(text):
    lines = text.splitlines()
    header = []
    records = []
    i = 0
    seen_record = False

    while i < len(lines):
        line = lines[i]

        if not line.startswith("#EXTINF"):
            if not seen_record:
                header.append(line)
            i += 1
            continue

        seen_record = True
        meta = line
        extras = []
        j = i + 1

        while j < len(lines) and (not lines[j].strip() or lines[j].startswith("#")):
            extras.append(lines[j])
            j += 1

        url = lines[j].strip() if j < len(lines) else ""

        records.append({
            "meta": meta,
            "extras": extras,
            "url": url,
        })

        i = j + 1

    return header, records

def build_meta(row):
    a = row["attrs"]
    key = row["key"]

    group = "11·4K超高清" if key in {"CCTV-4K", "CCTV-8K"} else "01·央视频道"

    bits = ["#EXTINF:-1"]

    if a.get("tvg-id"):
        bits.append(f'tvg-id="{a["tvg-id"]}"')

    bits.append(f'tvg-name="{key}"')

    if a.get("tvg-logo"):
        bits.append(f'tvg-logo="{a["tvg-logo"]}"')

    bits.append(f'group-title="{group}"')
    bits.append("," + key)

    return " ".join(bits)

def patch_file(path, selected):
    p = Path(path)
    if not p.exists():
        print(f"[SKIP] {path} not found")
        return

    header, records = parse_m3u_records(
        p.read_text(encoding="utf-8", errors="ignore")
    )

    out = []
    seen_cctv = set()

    for x in header:
        if x.startswith("#UPDATED:"):
            continue
        out.append(x)

    for rec in records:
        a = attrs(rec["meta"])
        raw = rec["meta"].rsplit(",", 1)[-1].strip()
        key = cctv_key(raw) or cctv_key(a.get("tvg-name", ""))

        if not key:
            out.append(rec["meta"])
            out.extend(rec["extras"])
            out.append(rec["url"])
            continue

        if key in seen_cctv:
            continue

        seen_cctv.add(key)

        if key in selected:
            row = selected[key]
            out.append(build_meta(row))
            out.append(row["url"])
        else:
            # 若没有找到新的可解码线路，则保留原频道，避免直接删掉。
            out.append(rec["meta"])
            out.extend(rec["extras"])
            out.append(rec["url"])

    p.write_text(
        "\n".join(out).rstrip() + "\n",
        encoding="utf-8"
    )

    print(f"[DONE] patched {path}")

def main():
    selected = pick_verified_cctv()

    if not selected:
        print("[WARN] No verified CCTV replacement found.")
        return

    for path in TARGET_FILES:
        patch_file(path, selected)

if __name__ == "__main__":
    main()
