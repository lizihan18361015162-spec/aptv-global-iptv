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

