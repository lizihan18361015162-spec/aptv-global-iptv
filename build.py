#!/usr/bin/env python3
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone

MAX_CHANNELS = 500
EPG_URL = "https://live.fanmingming.cn/e.xml"

# Priority: recently auto-checked source first, then official-site aggregations,
# then broad China playlists for coverage.
SOURCES = [
    ("best-fan", 0, "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all.m3u8"),
    ("official", 1, "https://raw.githubusercontent.com/mytv-android/China-TV-Live-M3U8/main/iptv.m3u"),
    ("ew-cn", 2, "https://raw.githubusercontent.com/iptvjs/iptv/main/ew_cn.m3u"),
    ("hujingguang", 3, "https://raw.githubusercontent.com/iptvjs/iptv/main/hujingguang_cnTV_AutoUpdate.m3u"),
    ("hc-cntv", 4, "https://raw.githubusercontent.com/iptvjs/iptv/main/hc_cntv.m3u"),
    ("iptv-org-cn", 5, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"),
    ("iptvjs-cn", 6, "https://raw.githubusercontent.com/iptvjs/iptv/main/o_s_cn.m3u"),
]

ALIASES = {
    "anhuitv":"安徽卫视","anhuist":"安徽卫视","beijingtv":"北京卫视","brtv":"北京卫视",
    "dragontv":"东方卫视","shanghaisatellite":"东方卫视","jiangsutv":"江苏卫视",
    "zhejiangtv":"浙江卫视","hunantv":"湖南卫视","hubeitv":"湖北卫视","shandongtv":"山东卫视",
    "guangdongtv":"广东卫视","shenzhentv":"深圳卫视","henantv":"河南卫视","hebeitv":"河北卫视",
    "jiangxitv":"江西卫视","sichuantv":"四川卫视","chongqingtv":"重庆卫视","guangxitv":"广西卫视",
    "yunnantv":"云南卫视","guizhoutv":"贵州卫视","shaanxitv":"陕西卫视","shanxitv":"山西卫视",
    "liaoningtv":"辽宁卫视","jilintv":"吉林卫视","heilongjiangtv":"黑龙江卫视",
    "innermongoliatv":"内蒙古卫视","qinghaitv":"青海卫视","ningxiatv":"宁夏卫视",
    "xinjiangtv":"新疆卫视","tibettv":"西藏卫视","xizangtv":"西藏卫视","gansutv":"甘肃卫视",
    "hainantv":"海南卫视","fujiantv":"福建东南卫视","tianjintv":"天津卫视",
}

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent":"Mozilla/5.0 China-IPTV-500-Updater/1.0"}
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", "ignore")

def attrs(line):
    return dict(ATTR_RE.findall(line))

def clean_display(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r'\s*\([^)]*(?:2160p|1080p|720p|576p|480p|fhd|uhd|hd|sd)[^)]*\)\s*', ' ', s, flags=re.I)
    s = re.sub(r'\s*\[[^\]]*(?:2160p|1080p|720p|576p|480p|fhd|uhd|hd|sd)[^\]]*\]\s*', ' ', s, flags=re.I)
    return re.sub(r'\s{2,}', ' ', s).strip()

def key_for(meta, display):
    a = attrs(meta)
    n = unicodedata.normalize("NFKC", a.get("tvg-name") or display).lower()
    n = n.replace("中央电视台", "cctv").replace("央视", "cctv")
    n = re.sub(r'cctv[\s\-_]*0?(\d+)\s*\+', r'cctv\1plus', n, flags=re.I)
    n = re.sub(r'cctv[\s\-_]*0?(\d+)', r'cctv\1', n, flags=re.I)
    n = re.sub(r'(?:超清|高清|标清|蓝光|\bfhd\b|\buhd\b|\bhd\b|\bsd\b)', '', n, flags=re.I)
    n = re.sub(r'[\s_\-—·.（）()]+', '', n)
    n = re.sub(r'(频道|电视台)$', '', n)
    return ALIASES.get(n, n)

def pclass(display):
    if re.search(r'CCTV|央视|CGTN', display, re.I): return 0
    if re.search(r'卫视|Satellite', display, re.I): return 1
    if re.search(r'[\u3400-\u9fff]', display): return 2
    return 3

def score(meta, url, rank, display):
    s = rank * 1000.0
    m = re.search(r'response-time="(\d+)ms"', meta, re.I)
    if m:
        s += min(int(m.group(1)), 999) / 10.0

    blob = meta + " " + display
    if re.search(r'1080p', blob, re.I):
        s -= 30
    elif re.search(r'720p', blob, re.I):
        s -= 10

    # For quicker startup, don't automatically prefer 4K/8K over a good 1080p line.
    if re.search(r'4k|2160p|8k', blob, re.I):
        s += 25

    if not re.search(r'\.m3u8(?:\?|$)', url, re.I):
        s += 5
    return s

def parse_playlist(text, label, rank):
    lines = text.splitlines()
    items = []
    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue
        meta = line.strip()
        display0 = meta.rsplit(",", 1)[-1].strip()
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

        # Exclude local-only / multicast addresses which won't work in ordinary APTV Internet use.
        if re.match(r'^https?://(?:127\.0\.0\.1|localhost)', url, re.I):
            continue
        if re.match(r'^https?://239\.', url, re.I):
            continue

        display = clean_display(display0)
        if not display:
            continue

        a = attrs(meta)
        items.append({
            "key": key_for(meta, display),
            "display": display,
            "meta": meta,
            "url": url,
            "extras": extras,
            "attrs": a,
            "rank": rank,
            "source": label,
            "score": score(meta, url, rank, display),
        })
    return items

def esc(s):
    return str(s or "").replace('"', "'")

def main():
    chosen = {}

    for label, rank, url in SOURCES:
        try:
            text = fetch(url)
            print(f"[OK] {label}")
        except Exception as e:
            print(f"[WARN] {label}: {e}")
            continue

        for c in parse_playlist(text, label, rank):
            prev = chosen.get(c["key"])
            if prev is None or c["score"] < prev["score"]:
                chosen[c["key"]] = c

    items = list(chosen.values())
    items.sort(key=lambda c: (
        pclass(c["display"]),
        0 if re.search(r'[\u3400-\u9fff]', c["display"]) else 1,
        c["display"].casefold(),
    ))

    final = []
    seen_url = set()
    for c in items:
        if c["url"] in seen_url:
            continue
        seen_url.add(c["url"])
        final.append(c)
        if len(final) >= MAX_CHANNELS:
            break

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        f'#EXTM3U x-tvg-url="{EPG_URL}"',
        '#PLAYLIST: 中国电视500台｜自动更新｜去重｜低延迟优先',
        f'#UPDATED: {now}',
    ]

    for c in final:
        a = c["attrs"]
        bits = ["#EXTINF:-1"]
        if a.get("tvg-id"):
            bits.append(f'tvg-id="{esc(a["tvg-id"])}"')
        bits.append(f'tvg-name="{esc(a.get("tvg-name") or c["display"])}"')
        if a.get("tvg-logo"):
            bits.append(f'tvg-logo="{esc(a["tvg-logo"])}"')

        group = a.get("group-title")
        if not group:
            group = "央视频道" if pclass(c["display"]) == 0 else "卫视" if pclass(c["display"]) == 1 else "地方频道"
        bits.append(f'group-title="{esc(group)}"')
        bits.append("," + c["display"])
        out.append(" ".join(bits))

        for x in c["extras"]:
            if re.match(r'^#(?:EXTVLCOPT|KODIPROP)', x, re.I):
                out.append(x)

        out.append(c["url"])

    with open("china500.m3u", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print(f"Wrote {len(final)} unique channels from {len(chosen)} normalized candidates.")

if __name__ == "__main__":
    main()
