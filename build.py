#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
China IPTV 500 builder for APTV / Apple TV

功能：
1. 最多 500 个中国电视直播频道
2. 同一频道只保留 1 条线路
3. 央视 / 卫视优先完整保留
4. 优先近期自动检测、响应时间较低、1080p/720p 的线路
5. 自动分类：
   央视、卫视、地方、体育、新闻财经、影视、少儿、纪录科教、
   港澳台、国际、4K、其他
6. 自动写入 EPG、台标、group-title
7. GitHub Actions 每 6 小时自动更新
"""

import re
import unicodedata
import urllib.request
from datetime import datetime, timezone


MAX_CHANNELS = 500

EPG_URL = "https://live.fanmingming.cn/e.xml"


# ============================================================
# 上游直播源
# 数值越小，优先级越高
# ============================================================

SOURCES = [
    (
        "best-fan-status",
        0,
        "https://raw.githubusercontent.com/"
        "best-fan/iptv-sources/main/cn_all_status.m3u8",
    ),

    (
        "best-fan-main",
        12,
        "https://raw.githubusercontent.com/"
        "best-fan/iptv-sources/main/cn_all.m3u8",
    ),

    (
        "official-sites",
        22,
        "https://raw.githubusercontent.com/"
        "mytv-android/China-TV-Live-M3U8/main/iptv.m3u",
    ),

    (
        "iptvjs-ew-cn",
        35,
        "https://raw.githubusercontent.com/"
        "iptvjs/iptv/main/ew_cn.m3u",
    ),

    (
        "hujingguang",
        42,
        "https://raw.githubusercontent.com/"
        "iptvjs/iptv/main/hujingguang_cnTV_AutoUpdate.m3u",
    ),

    (
        "hc-cntv",
        48,
        "https://raw.githubusercontent.com/"
        "iptvjs/iptv/main/hc_cntv.m3u",
    ),

    (
        "iptv-org-cn",
        60,
        "https://raw.githubusercontent.com/"
        "iptv-org/iptv/master/streams/cn.m3u",
    ),

    (
        "iptvjs-cn",
        68,
        "https://raw.githubusercontent.com/"
        "iptvjs/iptv/main/o_s_cn.m3u",
    ),
]


# ============================================================
# 属性解析
# ============================================================

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


# ============================================================
# 常见卫视频道名称统一
# ============================================================

ALIASES = {

    "anhuitv": "安徽卫视",
    "anhuist": "安徽卫视",

    "beijingtv": "北京卫视",
    "brtv": "北京卫视",

    "dragontv": "东方卫视",
    "shanghaisatellite": "东方卫视",

    "jiangsutv": "江苏卫视",
    "zhejiangtv": "浙江卫视",
    "hunantv": "湖南卫视",

    "hubeitv": "湖北卫视",
    "shandongtv": "山东卫视",

    "guangdongtv": "广东卫视",
    "shenzhentv": "深圳卫视",

    "henantv": "河南卫视",
    "hebeitv": "河北卫视",

    "jiangxitv": "江西卫视",
    "sichuantv": "四川卫视",

    "chongqingtv": "重庆卫视",
    "guangxitv": "广西卫视",

    "yunnantv": "云南卫视",
    "guizhoutv": "贵州卫视",

    "shaanxitv": "陕西卫视",
    "shanxitv": "山西卫视",

    "liaoningtv": "辽宁卫视",
    "jilintv": "吉林卫视",

    "heilongjiangtv": "黑龙江卫视",

    "innermongoliatv": "内蒙古卫视",

    "qinghaitv": "青海卫视",
    "ningxiatv": "宁夏卫视",

    "xinjiangtv": "新疆卫视",

    "tibettv": "西藏卫视",
    "xizangtv": "西藏卫视",

    "gansutv": "甘肃卫视",
    "hainantv": "海南卫视",

    "fujiantv": "东南卫视",
    "fudiantv": "东南卫视",

    "tianjintv": "天津卫视",
}


# ============================================================
# APTV 分类排序
# ============================================================

GROUP_ORDER = {

    "01·央视频道": 1,

    "02·卫视频道": 2,

    "03·地方频道": 3,

    "04·体育频道": 4,

    "05·新闻财经": 5,

    "06·影视剧场": 6,

    "07·少儿动漫": 7,

    "08·纪录科教": 8,

    "09·港澳台": 9,

    "10·国际频道": 10,

    "11·4K超高清": 11,

    "12·其他频道": 12,
}


# ============================================================
# 下载文件
# ============================================================

def fetch(url):

    req = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "Mozilla/5.0 China-IPTV-500-Updater/2.0",

            "Accept": "*/*",
        },
    )

    with urllib.request.urlopen(
        req,
        timeout=30,
    ) as resp:

        return resp.read().decode(
            "utf-8",
            "ignore",
        )


# ============================================================
# 解析 EXTINF 属性
# ============================================================

def attrs(line):

    return dict(
        ATTR_RE.findall(line)
    )


# ============================================================
# 清理画质 / 编码标签
# ============================================================

def strip_tags(s):

    s = unicodedata.normalize(
        "NFKC",
        s or "",
    ).strip()

    # 去除开头：
    # [1080]
    # [720]
    # [S]
    # [VGA]
    # [HEVC]
    # [HD]
    # 等

    s = re.sub(
        r'^\s*'
        r'(?:'
        r'\['
        r'(?:2160p?|1080p?|720p?|576p?|480p?|'
        r'4k|8k|uhd|fhd|hd|sd|vga|hevc|avc|'
        r'h265|h264|s)'
        r'\]\s*'
        r')+',
        '',
        s,
        flags=re.I,
    )

    # 去除结尾：
    # CCTV1 (1080p)
    # 江苏卫视 [720p]

    s = re.sub(
        r'\s*'
        r'[\(\[]'
        r'[^)\]]*'
        r'(?:2160p?|1080p?|720p?|576p?|480p?|'
        r'4k|8k|uhd|fhd|hd|sd)'
        r'[^)\]]*'
        r'[\)\]]'
        r'\s*$',
        '',
        s,
        flags=re.I,
    )

    return re.sub(
        r'\s{2,}',
        ' ',
        s,
    ).strip()


# ============================================================
# 标准频道显示名称
# ============================================================

def canonical_display(
    meta,
    display,
):

    a = attrs(meta)

    n = strip_tags(
        display
        or a.get("tvg-name")
        or ""
    )

    # ----------------------------
    # CCTV-5+
    # ----------------------------

    m = re.match(
        r'(?i)^cctv[\s_\-]*0?(\d+)\s*\+$',
        n,
    )

    if m:

        return (
            f"CCTV-{int(m.group(1))}+"
        )

    # ----------------------------
    # CCTV 1-17
    # ----------------------------

    m = re.match(
        r'(?i)^cctv[\s_\-]*0?(\d+)'
        r'(?:\s+.*)?$',
        n,
    )

    if m:

        num = int(
            m.group(1)
        )

        # CCTV-4
        # 美洲 / 欧洲单独保留

        if (
            num == 4
            and re.search(
                r'(美洲|欧洲|america|europe)',
                n,
                re.I,
            )
        ):

            if re.search(
                r'(美洲|america)',
                n,
                re.I,
            ):

                suffix = "美洲"

            else:

                suffix = "欧洲"

            return (
                f"CCTV-4 {suffix}"
            )

        return (
            f"CCTV-{num}"
        )

    # ----------------------------
    # CCTV 4K
    # ----------------------------

    if re.match(
        r'(?i)^cctv[\s_\-]*(4k|uhd)$',
        n,
    ):

        return "CCTV-4K"

    # ----------------------------
    # CCTV 8K
    # ----------------------------

    if re.match(
        r'(?i)^cctv[\s_\-]*(8k)$',
        n,
    ):

        return "CCTV-8K"

    # ----------------------------
    # 英文卫视名称转中文
    # ----------------------------

    key = re.sub(
        r'[\s_\-—·.（）()]+',
        '',
        n.lower(),
    )

    if key in ALIASES:

        return ALIASES[key]

    return n


# ============================================================
# 去重 Key
# ============================================================

def canonical_key(
    meta,
    display,
):

    n = canonical_display(
        meta,
        display,
    )

    low = unicodedata.normalize(
        "NFKC",
        n,
    ).lower()

    # ----------------------------
    # CCTV5+
    # ----------------------------

    m = re.match(
        r'cctv-(\d+)\+$',
        low,
    )

    if m:

        return (
            f"cctv{int(m.group(1))}plus"
        )

    # ----------------------------
    # CCTV1-17
    # ----------------------------

    m = re.match(
        r'cctv-(\d+)$',
        low,
    )

    if m:

        return (
            f"cctv{int(m.group(1))}"
        )

    # ----------------------------
    # CCTV4K / 8K
    # ----------------------------

    if low == "cctv-4k":

        return "cctv4k"

    if low == "cctv-8k":

        return "cctv8k"

    # CCTV-4 美洲/欧洲
    # 不合并

    if low.startswith(
        "cctv-4 "
    ):

        return re.sub(
            r'[\s_\-—·.（）()]+',
            '',
            low,
        )

    # 去掉清晰度名称

    low = re.sub(
        r'(?:'
        r'超清|高清|标清|蓝光|'
        r'\bfhd\b|'
        r'\buhd\b|'
        r'\bhd\b|'
        r'\bsd\b'
        r')',
        '',
        low,
        flags=re.I,
    )

    low = re.sub(
        r'[\s_\-—·.（）()]+',
        '',
        low,
    )

    low = re.sub(
        r'(频道|电视台)$',
        '',
        low,
    )

    return ALIASES.get(
        low,
        low,
    )


# ============================================================
# 获取 response-time
# ============================================================

def parse_response_time(meta):

    m = re.search(
        r'response-time="(\d+)ms"',
        meta,
        re.I,
    )

    if not m:

        return None

    try:

        return int(
            m.group(1)
        )

    except ValueError:

        return None


# ============================================================
# 获取画质
# ============================================================

def quality(
    meta,
    display,
):

    blob = (
        f"{meta} {display}"
    ).lower()

    if re.search(
        r'(?:8k|4320)',
        blob,
    ):

        return 4320

    if re.search(
        r'(?:4k|uhd|2160)',
        blob,
    ):

        return 2160

    if re.search(
        r'(?:1080|fhd)',
        blob,
    ):

        return 1080

    if re.search(
        r'720',
        blob,
    ):

        return 720

    if re.search(
        r'576',
        blob,
    ):

        return 576

    if re.search(
        r'480',
        blob,
    ):

        return 480

    return 0


# ============================================================
# 自动分类
# ============================================================

def category(display):

    n = display

    low = n.lower()

    # ----------------------------
    # 4K / 8K
    # ----------------------------

    if re.search(
        r'(?:4k|8k|uhd|超高清)',
        n,
        re.I,
    ):

        return "11·4K超高清"

    # ----------------------------
    # CCTV
    # ----------------------------

    if re.search(
        r'\bCCTV[-\s]?\d',
        n,
        re.I,
    ):

        return "01·央视频道"

    # ----------------------------
    # 卫视
    # ----------------------------

    if (
        "卫视" in n
        or low in ALIASES
    ):

        return "02·卫视频道"

    # ----------------------------
    # 港澳台
    # ----------------------------

    if re.search(

        r'('
        r'凤凰|TVB|翡翠|明珠|香港|港台|'
        r'RTHK|ViuTV|澳门|澳视|莲花|'
        r'台视|中视|华视|公视|民视|'
        r'三立|东森|中天|纬来|年代|壹电视'
        r')',

        n,

        re.I,
    ):

        return "09·港澳台"

    # ----------------------------
    # 国际频道
    # ----------------------------

    if re.search(

        r'('
        r'CGTN|NHK|Arirang|KBS|'
        r'BBC|CNN|DW|France\s*24|'
        r'TV5MONDE|Al Jazeera|'
        r'CNA|Bloomberg|'
        r'Russia Today'
        r')',

        n,

        re.I,
    ):

        return "10·国际频道"

    # ----------------------------
    # 体育
    # ----------------------------

    if re.search(

        r'('
        r'体育|Sports?|足球|篮球|'
        r'网球|高尔夫|台球|搏击|'
        r'赛车|劲爆|五星体育|咪咕'
        r')',

        n,

        re.I,
    ):

        return "04·体育频道"

    # ----------------------------
    # 新闻 / 财经
    # ----------------------------

    if re.search(

        r'('
        r'新闻|财经|经济|证券|'
        r'第一财经|财富|金融|商业|资讯'
        r')',

        n,

        re.I,
    ):

        return "05·新闻财经"

    # ----------------------------
    # 影视
    # ----------------------------

    if re.search(

        r'('
        r'电影|影视|剧场|电视剧|'
        r'影院|动作|家庭影院|'
        r'都市剧场|欢笑剧场'
        r')',

        n,

        re.I,
    ):

        return "06·影视剧场"

    # ----------------------------
    # 少儿 / 动漫
    # ----------------------------

    if re.search(

        r'('
        r'少儿|动漫|动画|卡通|'
        r'金鹰卡通|嘉佳卡通|优漫|'
        r'哈哈炫动|亲子|宝贝'
        r')',

        n,

        re.I,
    ):

        return "07·少儿动漫"

    # ----------------------------
    # 纪录 / 科教 / 教育
    # ----------------------------

    if re.search(

        r'('
        r'纪录|纪实|科教|教育|'
        r'课堂|探索|地理|科学|'
        r'人文|求索|CETV'
        r')',

        n,

        re.I,
    ):

        return "08·纪录科教"

    # ----------------------------
    # 中文地方台
    # ----------------------------

    if re.search(
        r'[\u3400-\u9fff]',
        n,
    ):

        return "03·地方频道"

    # ----------------------------
    # 其他
    # ----------------------------

    return "12·其他频道"


# ============================================================
# 线路评分
# 越低越优
# ============================================================

def line_score(
    meta,
    url,
    source_weight,
    display,
):

    rt = parse_response_time(
        meta
    )

    if rt is None:

        # 没有公开延迟数据
        # 不删除，只降低优先级

        rt = 180

    q = quality(
        meta,
        display,
    )

    # ----------------------------
    # 画质权重
    # 1080p 综合最优
    # ----------------------------

    quality_bonus = {

        4320: -10,

        2160: -18,

        1080: -70,

        720: -42,

        576: -12,

        480: -5,

        0: 0,
    }

    s = (

        float(source_weight)

        + float(rt)

        + quality_bonus.get(
            q,
            0,
        )
    )

    # ----------------------------
    # best-fan [S]
    # 表示成功检测
    # ----------------------------

    if re.search(
        r'\[S\]',
        meta,
        re.I,
    ):

        s -= 12

    # ----------------------------
    # IPTV tsfile
    # 一般启动快
    # ----------------------------

    if (
        "/tsfile/live/"
        in url.lower()
        or
        "playlive=1"
        in url.lower()
    ):

        s -= 14

    # ----------------------------
    # HLS
    # ----------------------------

    if ".m3u8" in url.lower():

        s -= 4

    # ----------------------------
    # 特殊中转格式略降级
    # ----------------------------

    if re.search(
        r'\.(?:ctv)(?:\?|$)',
        url,
        re.I,
    ):

        s += 18

    # ----------------------------
    # 4K / 8K 不作为低延迟首选
    # ----------------------------

    if q >= 2160:

        s += 18

    return s


# ============================================================
# 解析 M3U
# ============================================================

def parse_playlist(
    text,
    source_name,
    source_weight,
):

    lines = text.splitlines()

    items = []

    for i, line in enumerate(
        lines
    ):

        if not line.startswith(
            "#EXTINF"
        ):

            continue

        meta = line.strip()

        display0 = meta.rsplit(
            ",",
            1,
        )[-1].strip()

        extras = []

        j = i + 1

        while (
            j < len(lines)
            and
            (
                not lines[j].strip()
                or
                lines[j].startswith("#")
            )
        ):

            x = lines[j].strip()

            if (
                x.startswith("#")
                and
                not x.startswith("#EXTINF")
                and
                not x.startswith("#EXTM3U")
            ):

                extras.append(x)

            j += 1

        url = (
            lines[j].strip()
            if j < len(lines)
            else ""
        )

        # ----------------------------
        # 只要 http / https
        # ----------------------------

        if not re.match(
            r'^https?://',
            url,
            re.I,
        ):

            continue

        # ----------------------------
        # 排除本地地址
        # ----------------------------

        if re.match(
            r'^https?://'
            r'(?:127\.0\.0\.1|localhost)',
            url,
            re.I,
        ):

            continue

        # ----------------------------
        # 排除 IPTV 局域网组播地址
        # ----------------------------

        if re.match(
            r'^https?://239\.',
            url,
            re.I,
        ):

            continue

        display = canonical_display(
            meta,
            display0,
        )

        if not display:

            continue

        a = attrs(meta)

        key = canonical_key(
            meta,
            display,
        )

        items.append({

            "key":
            key,

            "display":
            display,

            "meta":
            meta,

            "url":
            url,

            "extras":
            extras,

            "attrs":
            a,

            "source":
            source_name,

            "source_weight":
            source_weight,

            "score":
            line_score(
                meta,
                url,
                source_weight,
                display,
            ),

            "group":
            category(
                display
            ),

            "quality":
            quality(
                meta,
                display,
            ),

            "rt":
            parse_response_time(
                meta
            ),
        })

    return items


# ============================================================
# 最终排序
# ============================================================

def channel_sort_key(c):

    g = GROUP_ORDER.get(
        c["group"],
        99,
    )

    n = c["display"]

    # ----------------------------
    # CCTV 数字顺序
    # ----------------------------

    m = re.match(
        r'(?i)^CCTV-(\d+)(\+)?$',
        n,
    )

    if m:

        num = int(
            m.group(1)
        )

        plus = (
            1
            if m.group(2)
            else 0
        )

        return (
            g,
            0,
            num,
            plus,
            n,
        )

    # ----------------------------
    # CCTV 4K
    # ----------------------------

    if n == "CCTV-4K":

        return (
            g,
            0,
            40,
            0,
            n,
        )

    # ----------------------------
    # CCTV 8K
    # ----------------------------

    if n == "CCTV-8K":

        return (
            g,
            0,
            80,
            0,
            n,
        )

    chinese_first = (

        0
        if re.search(
            r'[\u3400-\u9fff]',
            n,
        )
        else
        1
    )

    return (
        g,
        1,
        chinese_first,
        n.casefold(),
    )


# ============================================================
# XML / M3U 属性转义
# ============================================================

def esc(s):

    return str(
        s or ""
    ).replace(
        '"',
        "'",
    )


# ============================================================
# 主程序
# ============================================================

def main():

    chosen = {}

    source_stats = {}

    # ========================================================
    # 下载并合并所有源
    # ========================================================

    for (
        source_name,
        source_weight,
        url,
    ) in SOURCES:

        try:

            text = fetch(
                url
            )

            candidates = parse_playlist(
                text,
                source_name,
                source_weight,
            )

            source_stats[
                source_name
            ] = len(
                candidates
            )

            print(
                f"[OK] "
                f"{source_name}: "
                f"{len(candidates)} usable entries"
            )

        except Exception as e:

            source_stats[
                source_name
            ] = 0

            print(
                f"[WARN] "
                f"{source_name}: "
                f"{e}"
            )

            continue

        # ====================================================
        # 同频道只保留评分最低线路
        # ====================================================

        for c in candidates:

            prev = chosen.get(
                c["key"]
            )

            if (
                prev is None
                or
                c["score"]
                <
                prev["score"]
            ):

                chosen[
                    c["key"]
                ] = c


    items = list(
        chosen.values()
    )


    # ========================================================
    # CCTV + 卫视 + 4K
    # 强制优先保留
    # ========================================================

    must_keep_groups = {

        "01·央视频道",

        "02·卫视频道",

        "11·4K超高清",
    }


    must_keep = [

        c

        for c in items

        if (
            c["group"]
            in must_keep_groups
        )
    ]


    others = [

        c

        for c in items

        if (
            c["group"]
            not in must_keep_groups
        )
    ]


    must_keep.sort(
        key=channel_sort_key
    )


    # ========================================================
    # 其他频道
    # 按线路质量排序
    # ========================================================

    others.sort(

        key=lambda c: (

            c["score"],

            (
                0
                if re.search(
                    r'[\u3400-\u9fff]',
                    c["display"],
                )
                else
                1
            ),

            GROUP_ORDER.get(
                c["group"],
                99,
            ),

            c["display"].casefold(),
        )
    )


    final = []

    seen_url = set()


    # ========================================================
    # 最多 500 台
    # ========================================================

    for c in (
        must_keep
        +
        others
    ):

        # 同一 URL 不重复

        if (
            c["url"]
            in seen_url
        ):

            continue

        seen_url.add(
            c["url"]
        )

        final.append(c)

        if (
            len(final)
            >= MAX_CHANNELS
        ):

            break


    # ========================================================
    # 输出时按分类排序
    # ========================================================

    final.sort(
        key=channel_sort_key
    )


    now = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )


    # ========================================================
    # M3U 文件头
    # ========================================================

    out = [

        (
            f'#EXTM3U '
            f'x-tvg-url="{EPG_URL}"'
        ),

        (
            '#PLAYLIST: '
            '中国电视500台｜'
            '去重｜'
            '分类｜'
            '低延迟优先｜'
            '自动更新'
        ),

        f'#UPDATED: {now}',
    ]


    group_counts = {}


    # ========================================================
    # 写入所有频道
    # ========================================================

    for c in final:

        a = c["attrs"]

        group = c["group"]

        group_counts[
            group
        ] = (

            group_counts.get(
                group,
                0,
            )

            + 1
        )


        bits = [
            "#EXTINF:-1"
        ]


        # ----------------------------
        # EPG ID
        # ----------------------------

        if a.get(
            "tvg-id"
        ):

            bits.append(

                f'tvg-id="'
                f'{esc(a["tvg-id"])}'
                f'"'
            )


        # ----------------------------
        # 频道名称
        # ----------------------------

        bits.append(

            f'tvg-name="'
            f'{esc(c["display"])}'
            f'"'
        )


        # ----------------------------
        # 台标
        # ----------------------------

        if a.get(
            "tvg-logo"
        ):

            bits.append(

                f'tvg-logo="'
                f'{esc(a["tvg-logo"])}'
                f'"'
            )


        # ----------------------------
        # 分类
        # ----------------------------

        bits.append(

            f'group-title="'
            f'{esc(group)}'
            f'"'
        )


        # ----------------------------
        # 显示名称
        # ----------------------------

        bits.append(
            ","
            +
            c["display"]
        )


        out.append(
            " ".join(
                bits
            )
        )


        # ----------------------------
        # 保留播放器附加参数
        # ----------------------------

        for x in c[
            "extras"
        ]:

            if re.match(
                r'^#(?:EXTVLCOPT|KODIPROP)',
                x,
                re.I,
            ):

                out.append(x)


        # ----------------------------
        # 直播 URL
        # ----------------------------

        out.append(
            c["url"]
        )


    # ========================================================
    # 保存 china500.m3u
    # ========================================================

    with open(

        "china500.m3u",

        "w",

        encoding="utf-8",

        newline="\n",

    ) as f:

        f.write(

            "\n".join(
                out
            )

            + "\n"
        )


    # ========================================================
    # 日志
    # ========================================================

    print()

    print(
        f"Wrote "
        f"{len(final)} "
        f"unique channels "
        f"from "
        f"{len(chosen)} "
        f"normalized candidates."
    )


    print()

    print(
        "Groups:"
    )


    for group in sorted(

        group_counts,

        key=lambda g:

        GROUP_ORDER.get(
            g,
            99,
        ),
    ):

        print(

            f"  "
            f"{group}: "
            f"{group_counts[group]}"
        )


    print()

    print(
        "Source candidates:"
    )


    for (
        name,
        _,
        _,
    ) in SOURCES:

        print(

            f"  "
            f"{name}: "
            f"{source_stats.get(name, 0)}"
        )


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":

    main()
