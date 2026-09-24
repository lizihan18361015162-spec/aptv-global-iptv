#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stable international IPTV builder for APTV / Apple TV.

Targets:
- Japan
- Taiwan
- Hong Kong
- Macau
- South Korea
- United States
- United Kingdom

Strategy:
1. Merge Free-TV + iptv-org country playlists.
2. Normalize and deduplicate channels.
3. Exclude entries explicitly marked Geo-blocked / Not 24/7 / offline.
4. Actively verify stream URLs from GitHub Actions using concurrent HTTP checks.
5. Prefer HTTPS, HLS, official/CDN-style hosts, and higher-resolution variants.
6. Preserve tvg-id, logo, referrer / user-agent playback options.
7. Generate:
   - world_stable.m3u
   - all_stable.m3u (China stable + world stable, if china_stable.m3u exists)
"""

import concurrent.futures
import re
import socket
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EPG_URLS = [
    "https://live.fanmingming.cn/e.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_JP1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_JP2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_HK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_KR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US_LOCALS2.xml.gz",
]
EPG = ",".join(EPG_URLS)

TIMEOUT = 6
MAX_WORKERS = 36
READ_BYTES = 16384

COUNTRIES = {
    "13·日本频道": [
        ("free-tv-jp", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_japan.m3u8"),
        ("iptv-org-jp", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/jp.m3u"),
    ],
    "17·台湾频道": [
        ("free-tv-tw", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_taiwan.m3u8"),
        ("iptv-org-tw", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tw.m3u"),
    ],
    "18·香港频道": [
        ("free-tv-hk", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_hong_kong.m3u8"),
        ("iptv-org-hk", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/hk.m3u"),
    ],
    "19·澳门频道": [
        ("free-tv-mo", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_macau.m3u8"),
        ("iptv-org-mo", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/mo.m3u"),
    ],
    "20·韩国频道": [
        ("free-tv-kr", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_korea.m3u8"),
        ("iptv-org-kr", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/kr.m3u"),
    ],
    "21·美国频道": [
        ("free-tv-us", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_usa.m3u8"),
        ("iptv-org-us", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u"),
    ],
    "22·英国频道": [
        ("free-tv-uk", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_uk.m3u8"),
        ("iptv-org-uk", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u"),
    ],
}

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

BAD_MARKERS = re.compile(
    r'geo[- ]?blocked|not\s*24/?7|offline|broken|dead|unavailable|'
    r'仅限|地区限制|不可用',
    re.I,
)

PREFERRED_HOST_HINTS = (
    "cloudfront.net", "akamaized.net", "akamaiedge.net", "fastly.net",
    "googlevideo.com", "youtube.com", "ytimg.com", "cdn", "live", "stream",
    "nhk", "kbs", "mbc", "sbs", "bbc", "sky", "pbs", "cbs", "nbc", "abc",
)

def fetch_text(url, timeout=25):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Stable-IPTV-Updater/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")

def attrs(line):
    return dict(ATTR_RE.findall(line))

def clean_name(s):
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = re.sub(
        r'\s*[\(\[][^)\]]*(?:2160p?|1080p?|720p?|576p?|540p?|480p?|'
        r'4k|8k|uhd|fhd|hd|sd|geo-blocked|not 24/7)[^)\]]*[\)\]]\s*$',
        "",
        s,
        flags=re.I,
    )
    return re.sub(r"\s{2,}", " ", s).strip()

def canonical_key(meta, name):
    a = attrs(meta)
    tvg_id = a.get("tvg-id", "").strip().lower()
    if tvg_id:
        tvg_id = re.sub(r'@(sd|hd|fhd|uhd|4k|8k)$', '', tvg_id)
        return "id:" + tvg_id

    n = clean_name(name).lower()
    n = re.sub(r'[\s_\-—·.（）()\[\]]+', '', n)
    return "n:" + n

def quality(meta, name):
    s = (meta + " " + name).lower()
    for q, p in [
        (4320, r'8k|4320'),
        (2160, r'4k|uhd|2160'),
        (1080, r'1080|fhd'),
        (720, r'720'),
        (576, r'576'),
        (540, r'540'),
        (480, r'480'),
    ]:
        if re.search(p, s):
            return q
    return 0

def stream_headers(extras):
    headers = {
        "User-Agent": "Mozilla/5.0 (AppleTV; U; CPU OS 18_0 like Mac OS X)",
        "Accept": "*/*",
    }

    for x in extras:
        m = re.match(r'#EXTVLCOPT:http-referrer=(.+)', x, re.I)
        if m:
            headers["Referer"] = m.group(1).strip()
        m = re.match(r'#EXTVLCOPT:http-user-agent=(.+)', x, re.I)
        if m:
            headers["User-Agent"] = m.group(1).strip()

    return headers

def parse_playlist(text, group_name, source_name, source_weight):
    lines = text.splitlines()
    out = []
    per_key_order = {}

    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue

        meta = line.strip()
        raw_name = meta.rsplit(",", 1)[-1].strip()
        if not raw_name:
            continue
        if BAD_MARKERS.search(meta + " " + raw_name):
            continue

        extras = []
        j = i + 1
        while j < len(lines) and (not lines[j].strip() or lines[j].startswith("#")):
            x = lines[j].strip()
            if x.startswith("#") and not x.startswith("#EXTINF") and not x.startswith("#EXTM3U"):
                extras.append(x)
            j += 1

        url = lines[j].strip() if j < len(lines) else ""
        if not re.match(r'^https?://', url, re.I):
            continue
        if re.match(r'^https?://(?:127\.0\.0\.1|localhost|239\.)', url, re.I):
            continue

        name = clean_name(raw_name or attrs(meta).get("tvg-name", ""))
        if not name:
            continue

        key = canonical_key(meta, name)
        per_key_order[key] = per_key_order.get(key, 0) + 1

        host = (urllib.parse.urlparse(url).hostname or "").lower()
        q = quality(meta, name)

        # Smaller score is better.
        s = source_weight + min(per_key_order[key] - 1, 15)
        if url.lower().startswith("https://"):
            s -= 20
        if ".m3u8" in url.lower() or "manifest" in url.lower():
            s -= 12
        if any(h in host for h in PREFERRED_HOST_HINTS):
            s -= 10
        if q == 1080:
            s -= 28
        elif q == 720:
            s -= 18
        elif q >= 2160:
            s -= 8
        elif q and q < 720:
            s += 5

        out.append({
            "key": key,
            "name": name,
            "meta": meta,
            "attrs": attrs(meta),
            "url": url,
            "extras": extras,
            "group": group_name,
            "source": source_name,
            "score": s,
            "quality": q,
        })

    return out

def candidate_pool():
    by_key = {}

    for group_name, sources in COUNTRIES.items():
        for source_name, weight, url in sources:
            try:
                rows = parse_playlist(fetch_text(url), group_name, source_name, weight)
                print(f"[OK] {source_name}: {len(rows)} candidates")
            except Exception as e:
                print(f"[WARN] {source_name}: {e}")
                continue

            for c in rows:
                by_key.setdefault((group_name, c["key"]), []).append(c)

    # Keep up to 4 fallback variants per channel for validation.
    pooled = []
    for _, rows in by_key.items():
        rows.sort(key=lambda c: c["score"])
        pooled.extend(rows[:4])

    return pooled

def verify_stream(c):
    url = c["url"]
    headers = stream_headers(c["extras"])

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            code = getattr(r, "status", 200)
            ctype = (r.headers.get("Content-Type") or "").lower()
            data = r.read(READ_BYTES)

            if code < 200 or code >= 400:
                return None

            lower = data[:4096].lower()

            # HLS / DASH / common media indicators.
            looks_media = (
                b"#extm3u" in lower
                or b"#ext-x-" in lower
                or b"<mpd" in lower
                or "mpegurl" in ctype
                or "video/" in ctype
                or "application/vnd.apple.mpegurl" in ctype
                or "application/x-mpegurl" in ctype
                or url.lower().endswith((".m3u8", ".mpd"))
            )

            if not looks_media:
                return None

            result = dict(c)
            result["verified"] = True
            result["final_url"] = r.geturl()
            return result

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, ValueError):
        return None
    except Exception:
        return None

def verified_channels():
    pool = candidate_pool()
    print(f"Verifying {len(pool)} stream candidates...")

    checked = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(verify_stream, c) for c in pool]
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r:
                checked.append(r)

    # One best verified stream per unique channel.
    chosen = {}
    for c in checked:
        k = (c["group"], c["key"])
        prev = chosen.get(k)
        if prev is None or c["score"] < prev["score"]:
            chosen[k] = c

    rows = list(chosen.values())
    rows.sort(key=lambda c: (list(COUNTRIES).index(c["group"]), c["name"].casefold()))

    print(f"Verified unique channels: {len(rows)}")
    return rows

def esc(s):
    return str(s or "").replace('"', "'")

def write_m3u(path, title, items):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        f'#EXTM3U x-tvg-url="{EPG}"',
        f'#PLAYLIST: {title}',
        f'#UPDATED: {now}',
    ]

    counts = {}

    for c in items:
        a = c["attrs"]
        counts[c["group"]] = counts.get(c["group"], 0) + 1

        bits = ["#EXTINF:-1"]

        if a.get("tvg-id"):
            bits.append(f'tvg-id="{esc(a["tvg-id"])}"')

        bits.append(f'tvg-name="{esc(c["name"])}"')

        if a.get("tvg-logo"):
            bits.append(f'tvg-logo="{esc(a["tvg-logo"])}"')

        bits.append(f'group-title="{c["group"]}"')
        bits.append("," + c["name"])

        out.append(" ".join(bits))

        for x in c["extras"]:
            if re.match(r'^#(?:EXTVLCOPT|KODIPROP)', x, re.I):
                out.append(x)

        out.append(c["url"])

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print(f"{path}: {len(items)} verified channels")
    for group_name in COUNTRIES:
        if counts.get(group_name):
            print(f"  {group_name}: {counts[group_name]}")

def append_to_china(world_items):
    china = Path("china_stable.m3u")
    if not china.exists():
        print("[INFO] china_stable.m3u not found; skip all_stable.m3u")
        return

    text = china.read_text(encoding="utf-8", errors="ignore").splitlines()
    header = []
    body = []

    for line in text:
        if line.startswith("#EXTM3U"):
            header = [f'#EXTM3U x-tvg-url="{EPG}"']
        elif line.startswith("#PLAYLIST:"):
            continue
        elif line.startswith("#UPDATED:"):
            continue
        else:
            body.append(line)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = header + [
        "#PLAYLIST: 中国稳定版 + 海外稳定版",
        f"#UPDATED: {now}",
    ] + body

    # Append verified world items.
    tmp = Path("_world_tmp.m3u")
    write_m3u(tmp, "tmp", world_items)
    world_lines = tmp.read_text(encoding="utf-8").splitlines()
    out += [x for x in world_lines if not x.startswith(("#EXTM3U", "#PLAYLIST:", "#UPDATED:"))]
    tmp.unlink(missing_ok=True)

    Path("all_stable.m3u").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("all_stable.m3u generated")

def main():
    rows = verified_channels()
    write_m3u(
        "world_stable.m3u",
        "海外稳定版｜日本·台湾·香港·澳门·韩国·美国·英国｜自动可用性验证",
        rows,
    )
    append_to_china(rows)

if __name__ == "__main__":
    main()
