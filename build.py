#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, unicodedata, urllib.request
from datetime import datetime, timezone

EPG = "https://live.fanmingming.cn/e.xml"
STABLE_MAX = 350
EXTENDED_MAX = 500

# 稳定版只用“已检测/自动筛选”源；扩展版再补充大列表。
STABLE_SOURCES = [
    ("best-status", 0, "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all_status.m3u8"),
    ("guovin", 15, "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"),
    ("official", 25, "https://raw.githubusercontent.com/mytv-android/China-TV-Live-M3U8/main/iptv.m3u"),
]
FALLBACK_SOURCES = [
    ("best-main", 45, "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all.m3u8"),
    ("iptv-org", 80, "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"),
    ("iptvjs", 90, "https://raw.githubusercontent.com/iptvjs/iptv/main/o_s_cn.m3u"),
    ("iptvjs-ew", 95, "https://raw.githubusercontent.com/iptvjs/iptv/main/ew_cn.m3u"),
]

ATTR = re.compile(r'([\w-]+)="([^"]*)"')
GROUPS = [
    "01·央视频道","02·卫视频道","03·地方频道","04·体育频道",
    "05·新闻财经","06·影视剧场","07·少儿动漫","08·纪录科教",
    "09·港澳台","10·国际频道","11·4K超高清","12·其他频道"
]

ALIASES = {
    "brtv":"北京卫视","beijingtv":"北京卫视","dragontv":"东方卫视",
    "shanghaisatellite":"东方卫视","jiangsutv":"江苏卫视",
    "zhejiangtv":"浙江卫视","hunantv":"湖南卫视","hubeitv":"湖北卫视",
    "shandongtv":"山东卫视","guangdongtv":"广东卫视","shenzhentv":"深圳卫视",
    "henantv":"河南卫视","hebeitv":"河北卫视","jiangxitv":"江西卫视",
    "sichuantv":"四川卫视","chongqingtv":"重庆卫视","guangxitv":"广西卫视",
    "yunnantv":"云南卫视","guizhoutv":"贵州卫视","shaanxitv":"陕西卫视",
    "shanxitv":"山西卫视","liaoningtv":"辽宁卫视","jilintv":"吉林卫视",
    "heilongjiangtv":"黑龙江卫视","innermongoliatv":"内蒙古卫视",
    "qinghaitv":"青海卫视","ningxiatv":"宁夏卫视","xinjiangtv":"新疆卫视",
    "tibettv":"西藏卫视","xizangtv":"西藏卫视","gansutv":"甘肃卫视",
    "hainantv":"海南卫视","fujiantv":"东南卫视","tianjintv":"天津卫视",
    "anhuitv":"安徽卫视"
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 IPTV-Updater/3.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8","ignore")

def at(line):
    return dict(ATTR.findall(line))

def clean(s):
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = re.sub(
        r'^\s*(?:\[(?:2160p?|1080p?|720p?|576p?|480p?|4k|8k|uhd|fhd|hd|sd|vga|hevc|avc|h265|h264|s)\]\s*)+',
        '', s, flags=re.I
    )
    s = re.sub(
        r'\s*[\(\[][^)\]]*(?:2160p?|1080p?|720p?|576p?|480p?|4k|8k|uhd|fhd|hd|sd)[^)\]]*[\)\]]\s*$',
        '', s, flags=re.I
    )
    return re.sub(r'\s{2,}',' ',s).strip()

def display_name(meta, name):
    n = clean(name or at(meta).get("tvg-name",""))

    m = re.match(r'(?i)^cctv[\s_-]*0?(\d+)\s*\+$', n)
    if m:
        return f"CCTV-{int(m.group(1))}+"

    if re.match(r'(?i)^cctv[\s_-]*(4k|uhd)$', n):
        return "CCTV-4K"

    if re.match(r'(?i)^cctv[\s_-]*8k$', n):
        return "CCTV-8K"

    m = re.match(r'(?i)^cctv[\s_-]*0?(\d+)(?:\s+.*)?$', n)
    if m:
        num = int(m.group(1))
        if num == 4 and re.search(r'(美洲|america)', n, re.I):
            return "CCTV-4 美洲"
        if num == 4 and re.search(r'(欧洲|europe)', n, re.I):
            return "CCTV-4 欧洲"
        return f"CCTV-{num}"

    k = re.sub(r'[\s_\-—·.（）()]+', '', n.lower())
    return ALIASES.get(k, n)

def key(meta, name):
    n = display_name(meta, name).lower()
    n = n.replace("中央电视台","cctv").replace("央视","cctv")
    n = re.sub(r'cctv[\s_-]*0?(\d+)\s*\+', r'cctv\1plus', n, flags=re.I)
    n = re.sub(r'cctv[\s_-]*0?(\d+)', r'cctv\1', n, flags=re.I)
    n = re.sub(r'(?:超清|高清|标清|蓝光|\bfhd\b|\buhd\b|\bhd\b|\bsd\b)', '', n, flags=re.I)
    n = re.sub(r'[\s_\-—·.（）()]+', '', n)
    n = re.sub(r'(频道|电视台)$', '', n)
    return ALIASES.get(n, n)

def group(n):
    if re.search(r'(4K|8K|UHD|超高清)', n, re.I):
        return "11·4K超高清"

    if re.match(r'(?i)^CCTV-', n):
        return "01·央视频道"

    if "卫视" in n:
        return "02·卫视频道"

    if re.search(r'(凤凰|TVB|翡翠|明珠|香港|港台|RTHK|ViuTV|澳门|澳视|莲花|台视|中视|华视|公视|民视|三立|东森|中天|纬来)', n, re.I):
        return "09·港澳台"

    if re.search(r'(CGTN|NHK|KBS|BBC|CNN|DW|France\s*24|Al Jazeera|CNA|Bloomberg)', n, re.I):
        return "10·国际频道"

    if re.search(r'(体育|Sports?|足球|篮球|网球|高尔夫|台球|搏击|赛车|五星体育)', n, re.I):
        return "04·体育频道"

    if re.search(r'(新闻|财经|经济|证券|第一财经|财富|金融|资讯)', n, re.I):
        return "05·新闻财经"

    if re.search(r'(电影|影视|剧场|电视剧|影院|欢笑剧场|都市剧场)', n, re.I):
        return "06·影视剧场"

    if re.search(r'(少儿|动漫|动画|卡通|优漫|哈哈炫动|亲子|宝贝)', n, re.I):
        return "07·少儿动漫"

    if re.search(r'(纪录|纪实|科教|教育|课堂|探索|地理|科学|人文|CETV)', n, re.I):
        return "08·纪录科教"

    if re.search(r'[\u3400-\u9fff]', n):
        return "03·地方频道"

    return "12·其他频道"

def quality(meta, name):
    s = (meta + " " + name).lower()
    for q, p in [
        (4320, r'8k|4320'),
        (2160, r'4k|uhd|2160'),
        (1080, r'1080|fhd'),
        (720, r'720'),
        (576, r'576'),
        (480, r'480')
    ]:
        if re.search(p, s):
            return q
    return 0

def score(meta, url, weight, name, ordinal):
    m = re.search(r'response-time="(\d+)ms"', meta, re.I)
    rt = int(m.group(1)) if m else 180

    q = quality(meta, name)

    qb = {
        4320:-5,
        2160:-10,
        1080:-65,
        720:-40,
        576:-10,
        480:-5,
        0:0
    }.get(q, 0)

    s = weight + rt + qb + min(ordinal, 20)

    if re.search(r'\[S\]', meta, re.I):
        s -= 15

    if "/tsfile/live/" in url.lower() or "playlive=1" in url.lower():
        s -= 10

    if ".m3u8" in url.lower():
        s -= 4

    if q >= 2160:
        s += 15

    return s

def parse(text, source, weight):
    lines = text.splitlines()
    out = []
    order = {}

    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue

        meta = line.strip()
        raw = meta.rsplit(",",1)[-1].strip()

        if re.match(r'^20\d\d-\d\d-\d\d', raw):
            continue

        j = i + 1
        while j < len(lines) and (not lines[j].strip() or lines[j].startswith("#")):
            j += 1

        url = lines[j].strip() if j < len(lines) else ""

        if not re.match(r'^https?://', url, re.I):
            continue

        if re.match(r'^https?://(?:127\.0\.0\.1|localhost|239\.)', url, re.I):
            continue

        name = display_name(meta, raw)
        if not name:
            continue

        k = key(meta, name)
        order[k] = order.get(k, 0) + 1
        a = at(meta)

        out.append({
            "key": k,
            "name": name,
            "url": url,
            "meta": meta,
            "attrs": a,
            "group": group(name),
            "score": score(meta, url, weight, name, order[k]-1),
            "source": source
        })

    return out

def merge(sources):
    chosen = {}

    for source, weight, url in sources:
        try:
            rows = parse(fetch(url), source, weight)
            print(f"[OK] {source}: {len(rows)} entries")
        except Exception as e:
            print(f"[WARN] {source}: {e}")
            continue

        for c in rows:
            if c["key"] not in chosen or c["score"] < chosen[c["key"]]["score"]:
                chosen[c["key"]] = c

    return chosen

def sortkey(c):
    gi = GROUPS.index(c["group"]) if c["group"] in GROUPS else 99

    m = re.match(r'^CCTV-(\d+)(\+)?$', c["name"], re.I)
    if m:
        return (
            gi,
            0,
            int(m.group(1)),
            1 if m.group(2) else 0,
            c["name"]
        )

    return (gi, 1, 0, c["name"])

def pick(chosen, limit):
    items = list(chosen.values())

    must = [
        c for c in items
        if c["group"] in {
            "01·央视频道",
            "02·卫视频道",
            "11·4K超高清"
        }
    ]

    rest = [
        c for c in items
        if c not in must
    ]

    must.sort(key=sortkey)

    rest.sort(
        key=lambda c: (
            c["score"],
            GROUPS.index(c["group"]) if c["group"] in GROUPS else 99,
            c["name"]
        )
    )

    final = []
    urls = set()

    for c in must + rest:
        if c["url"] in urls:
            continue

        urls.add(c["url"])
        final.append(c)

        if len(final) >= limit:
            break

    return sorted(final, key=sortkey)

def esc(s):
    return str(s or "").replace('"', "'")

def write_m3u(path, title, items):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    out = [
        f'#EXTM3U x-tvg-url="{EPG}"',
        f'#PLAYLIST: {title}',
        f'#UPDATED: {now}'
    ]

    counts = {}

    for c in items:
        a = c["attrs"]

        counts[c["group"]] = counts.get(c["group"], 0) + 1

        x = ['#EXTINF:-1']

        if a.get("tvg-id"):
            x.append(f'tvg-id="{esc(a["tvg-id"])}"')

        x.append(f'tvg-name="{esc(c["name"])}"')

        if a.get("tvg-logo"):
            x.append(f'tvg-logo="{esc(a["tvg-logo"])}"')

        x.append(f'group-title="{c["group"]}"')
        x.append("," + c["name"])

        out += [
            " ".join(x),
            c["url"]
        ]

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print(f"{path}: {len(items)} channels")

    for g in GROUPS:
        if counts.get(g):
            print(f"  {g}: {counts[g]}")

def main():
    stable_map = merge(STABLE_SOURCES)

    stable = pick(
        stable_map,
        STABLE_MAX
    )

    write_m3u(
        "china_stable.m3u",
        "中国电视稳定版｜去重｜分类｜低延迟优先",
        stable
    )

    extended_map = dict(stable_map)

    fallback = merge(FALLBACK_SOURCES)

    for k, c in fallback.items():
        if k not in extended_map or c["score"] < extended_map[k]["score"]:
            extended_map[k] = c

    extended = pick(
        extended_map,
        EXTENDED_MAX
    )

    write_m3u(
        "china500.m3u",
        "中国电视500台扩展版｜去重｜分类｜自动更新",
        extended
    )

if __name__ == "__main__":
    main()
