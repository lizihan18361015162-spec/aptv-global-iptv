#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Strict stable international IPTV builder for APTV / Apple TV.

重点：
- 日本 / 台湾 / 香港 / 澳门 / 韩国 / 美国 / 英国
- 港澳台扩充更多公开候选源
- 不只检查 M3U8 地址本身，还实际检查媒体播放列表与视频分片
- 同一频道多线路时，优先选择验证通过、响应较快、1080p/720p、HTTPS/CDN 线路
"""

import concurrent.futures
import re
import socket
import time
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

TIMEOUT = 7
MAX_WORKERS = 42
MANIFEST_BYTES = 256 * 1024
SEGMENT_BYTES = 64 * 1024

# 港澳台增加 epg.pw + IPTV-CN 作为额外候选源。
COUNTRIES = {
    "13·日本频道": [
        ("free-tv-jp", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_japan.m3u8"),
        ("iptv-org-jp", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/jp.m3u"),
    ],
    "17·台湾频道": [
        ("free-tv-tw", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_taiwan.m3u8"),
        ("epg-pw-tw", 6, "https://epg.pw/test_channels_taiwan.m3u"),
        ("iptv-cn-tw", 12, "https://iptv-cn.github.io/IPTV/countries/tw.m3u"),
        ("iptv-org-tw", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tw.m3u"),
    ],
    "18·香港频道": [
        ("free-tv-hk", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_hong_kong.m3u8"),
        ("epg-pw-hk", 6, "https://epg.pw/test_channels_hong_kong.m3u"),
        ("iptv-cn-hk", 12, "https://iptv-cn.github.io/IPTV/countries/hk.m3u"),
        ("iptv-org-hk", 20, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/hk.m3u"),
    ],
    "19·澳门频道": [
        ("free-tv-mo", 0, "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_macau.m3u8"),
        ("epg-pw-mo", 6, "https://epg.pw/test_channels_macau.m3u"),
        ("iptv-cn-mo", 12, "https://iptv-cn.github.io/IPTV/countries/mo.m3u"),
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
    "cloudfront.net", "akamaized.net", "akamaihd.net", "akamaiedge.net",
    "fastly.net", "cdn", "live", "stream",
    "nhk", "tdm.com.mo", "rthk", "viutv",
    "kbs", "mbc", "sbs", "bbc", "sky",
    "pbs", "cbs", "nbc", "abc",
)

# 港澳台多保留候选线路供严格检测，其他地区减少重复检测量。
CANDIDATE_LIMIT = {
    "17·台湾频道": 8,
    "18·香港频道": 8,
    "19·澳门频道": 10,
}
DEFAULT_CANDIDATE_LIMIT = 4


def request_headers(extras=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (AppleTV; U; CPU OS 18_0 like Mac OS X)",
        "Accept": "*/*",
        "Connection": "close",
    }

    for x in extras or []:
        m = re.match(r'#EXTVLCOPT:http-referrer=(.+)', x, re.I)
        if m:
            headers["Referer"] = m.group(1).strip()

        m = re.match(r'#EXTVLCOPT:http-user-agent=(.+)', x, re.I)
        if m:
            headers["User-Agent"] = m.group(1).strip()

    return headers


def fetch_bytes(url, extras=None, limit=MANIFEST_BYTES, timeout=TIMEOUT):
    req = urllib.request.Request(
        url,
        headers=request_headers(extras),
        method="GET",
    )
    started = time.monotonic()

    with urllib.request.urlopen(req, timeout=timeout) as r:
        code = getattr(r, "status", 200)
        if code < 200 or code >= 400:
            raise urllib.error.HTTPError(
                url, code, "bad status", r.headers, None
            )

        data = r.read(limit)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        return {
            "data": data,
            "ctype": (r.headers.get("Content-Type") or "").lower(),
            "url": r.geturl(),
            "elapsed_ms": elapsed_ms,
        }


def fetch_text(url, timeout=25):
    r = fetch_bytes(url, limit=2 * 1024 * 1024, timeout=timeout)
    return r["data"].decode("utf-8", "ignore")


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

            if (
                x.startswith("#")
                and not x.startswith("#EXTINF")
                and not x.startswith("#EXTM3U")
            ):
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

        # Smaller score = preferred candidate before verification.
        s = source_weight + min(per_key_order[key] - 1, 15)

        if url.lower().startswith("https://"):
            s -= 18

        if ".m3u8" in url.lower() or "manifest" in url.lower():
            s -= 10

        if any(h in host for h in PREFERRED_HOST_HINTS):
            s -= 12

        if q == 1080:
            s -= 25
        elif q == 720:
            s -= 16
        elif q >= 2160:
            s -= 5
        elif q and q < 720:
            s += 4

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
                rows = parse_playlist(
                    fetch_text(url),
                    group_name,
                    source_name,
                    weight,
                )
                print(f"[OK] {source_name}: {len(rows)} candidates")
            except Exception as e:
                print(f"[WARN] {source_name}: {e}")
                continue

            for c in rows:
                by_key.setdefault((group_name, c["key"]), []).append(c)

    pooled = []

    for (group_name, _), rows in by_key.items():
        rows.sort(key=lambda c: c["score"])

        limit = CANDIDATE_LIMIT.get(
            group_name,
            DEFAULT_CANDIDATE_LIMIT,
        )

        pooled.extend(rows[:limit])

    return pooled


def non_comment_uris(text):
    return [
        x.strip()
        for x in text.splitlines()
        if x.strip() and not x.lstrip().startswith("#")
    ]


def choose_master_variant(text, base_url):
    lines = text.splitlines()
    candidates = []

    for i, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue

        bandwidth = 0
        m = re.search(r'BANDWIDTH=(\d+)', line, re.I)
        if m:
            bandwidth = int(m.group(1))

        resolution = 0
        m = re.search(r'RESOLUTION=\d+x(\d+)', line, re.I)
        if m:
            resolution = int(m.group(1))

        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1

        if j < len(lines) and not lines[j].lstrip().startswith("#"):
            uri = urllib.parse.urljoin(base_url, lines[j].strip())
            candidates.append((resolution, bandwidth, uri))

    if not candidates:
        return None

    # 稳定优先：1080/720 比 4K 更适合日常播放。
    def variant_rank(v):
        resolution, bandwidth, _ = v

        if 720 <= resolution <= 1080:
            quality_rank = 0
        elif 480 <= resolution < 720:
            quality_rank = 1
        elif resolution > 1080:
            quality_rank = 2
        else:
            quality_rank = 3

        return (quality_rank, -resolution, -bandwidth)

    candidates.sort(key=variant_rank)
    return candidates[0][2]


def fetch_segment(url, extras):
    r = fetch_bytes(
        url,
        extras=extras,
        limit=SEGMENT_BYTES,
        timeout=TIMEOUT,
    )

    if len(r["data"]) < 512:
        return None

    # HTML 登录页 / 错误页不算有效视频分片。
    head = r["data"][:1024].lower()
    if b"<html" in head or b"<!doctype html" in head:
        return None

    return r


def verify_hls(c):
    """
    严格三级检测：
    1. 主 URL 可访问
    2. 如果是 master playlist，继续进入 media playlist
    3. 实际下载前两个媒体分片；至少两个分片均成功才通过
       若实时列表当前只有一个分片，则一个分片成功也可通过
    """
    first = fetch_bytes(
        c["url"],
        extras=c["extras"],
        limit=MANIFEST_BYTES,
        timeout=TIMEOUT,
    )

    data = first["data"]
    ctype = first["ctype"]
    final_url = first["url"]

    text = data.decode("utf-8", "ignore")
    lower = data[:4096].lower()

    is_hls = (
        b"#extm3u" in lower
        or b"#ext-x-" in lower
        or "mpegurl" in ctype
        or ".m3u8" in final_url.lower()
    )

    if not is_hls:
        # 少数直接视频流也接受，但必须确实返回视频数据。
        if "video/" in ctype and len(data) >= 4096:
            return {
                **c,
                "latency_ms": first["elapsed_ms"],
                "verified_level": "direct-video",
            }
        return None

    # Master -> Media
    if "#EXT-X-STREAM-INF" in text:
        variant = choose_master_variant(text, final_url)
        if not variant:
            return None

        second = fetch_bytes(
            variant,
            extras=c["extras"],
            limit=MANIFEST_BYTES,
            timeout=TIMEOUT,
        )

        text = second["data"].decode("utf-8", "ignore")
        media_url = second["url"]
        manifest_ms = first["elapsed_ms"] + second["elapsed_ms"]
    else:
        media_url = final_url
        manifest_ms = first["elapsed_ms"]

    if "#EXTM3U" not in text.upper():
        return None

    uris = non_comment_uris(text)

    # Media playlist 至少应该出现一个媒体 URI。
    if not uris:
        return None

    # 取最前面的两个媒体对象进行真实访问检测。
    segment_urls = [
        urllib.parse.urljoin(media_url, x)
        for x in uris[:2]
    ]

    segment_times = []

    for segment_url in segment_urls:
        seg = fetch_segment(segment_url, c["extras"])
        if not seg:
            return None
        segment_times.append(seg["elapsed_ms"])

    total_latency = manifest_ms + sum(segment_times)

    return {
        **c,
        "latency_ms": total_latency,
        "verified_level": "2-segment" if len(segment_urls) >= 2 else "1-segment",
    }


def verify_stream(c):
    try:
        return verify_hls(c)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        socket.timeout,
        ValueError,
    ):
        return None
    except Exception:
        return None


def verified_channels():
    pool = candidate_pool()

    print(f"Strict-verifying {len(pool)} stream candidates...")

    checked = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as ex:
        futures = [
            ex.submit(verify_stream, c)
            for c in pool
        ]

        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r:
                checked.append(r)

    # 同频道选严格验证通过后综合质量最好的线路。
    chosen = {}

    for c in checked:
        k = (c["group"], c["key"])

        # 验证后把实测连接速度加入最终评分。
        final_score = c["score"] + min(c["latency_ms"] // 60, 80)
        c["final_score"] = final_score

        prev = chosen.get(k)

        if prev is None or c["final_score"] < prev["final_score"]:
            chosen[k] = c

    rows = list(chosen.values())

    country_order = list(COUNTRIES)

    rows.sort(
        key=lambda c: (
            country_order.index(c["group"]),
            c["name"].casefold(),
        )
    )

    print(f"Strict verified unique channels: {len(rows)}")

    counts = {}
    for c in rows:
        counts[c["group"]] = counts.get(c["group"], 0) + 1

    for group_name in country_order:
        print(f"[RESULT] {group_name}: {counts.get(group_name, 0)}")

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

        # 保留 referrer / user-agent 等播放器参数。
        for x in c["extras"]:
            if re.match(r'^#(?:EXTVLCOPT|KODIPROP)', x, re.I):
                out.append(x)

        out.append(c["url"])

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print(f"{path}: {len(items)} strict-verified channels")

    for group_name in COUNTRIES:
        if counts.get(group_name):
            print(f"  {group_name}: {counts[group_name]}")


def append_to_china(world_items):
    china = Path("china_stable.m3u")

    if not china.exists():
        print("[INFO] china_stable.m3u not found; skip all_stable.m3u")
        return

    china_lines = china.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    body = []

    for line in china_lines:
        if line.startswith(("#EXTM3U", "#PLAYLIST:", "#UPDATED:")):
            continue
        body.append(line)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    out = [
        f'#EXTM3U x-tvg-url="{EPG}"',
        "#PLAYLIST: 中国稳定版 + 海外严格稳定版",
        f"#UPDATED: {now}",
    ] + body

    tmp = Path("_world_tmp.m3u")

    write_m3u(
        tmp,
        "tmp",
        world_items,
    )

    world_lines = tmp.read_text(
        encoding="utf-8"
    ).splitlines()

    out += [
        x for x in world_lines
        if not x.startswith(("#EXTM3U", "#PLAYLIST:", "#UPDATED:"))
    ]

    tmp.unlink(missing_ok=True)

    Path("all_stable.m3u").write_text(
        "\n".join(out) + "\n",
        encoding="utf-8",
    )

    print("all_stable.m3u generated")


def main():
    rows = verified_channels()

    write_m3u(
        "world_stable.m3u",
        "海外严格稳定版｜港澳台加强｜实际视频分片验证",
        rows,
    )

    append_to_china(rows)


if __name__ == "__main__":
    main()
