# China & Global IPTV for APTV

中国及全球 IPTV 稳定直播源｜APTV / Apple TV

面向 **APTV / Apple TV** 整理的中国及海外 IPTV 播放列表。

项目重点不是单纯追求频道数量，而是尽量提高：

- 可播放率、稳定性和启动速度
- 1080p / 720p 清晰度线路优先级
- 频道分类与去重效果
- 自动更新能力
- APTV / Apple TV 日常使用体验

---

## 📺 当前版本

### 🇨🇳 中国稳定版

用于日常观看，优先选择近期自动检测或相对稳定的中国电视直播源。

主要特点：

- 最多约 **350 个频道**
- 优先 CCTV
- 优先全国卫视
- 优先 1080p / 720p
- 优先低响应线路
- 自动统一频道名称
- 自动去除重复频道
- 自动去除重复 URL
- 适合长期作为主订阅使用

订阅地址：

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/china_stable.m3u
```

---

### 🇨🇳 中国500台扩展版

在中国稳定版基础上加入更多地方频道和冷门频道。

主要特点：

- 最多约 **500 个中国频道**
- 地方频道数量更多
- 冷门频道数量更多
- 数量优先于稳定性
- 个别公网源可能因地区、运营商或上游服务器变化暂时不可播放

订阅地址：

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/china500.m3u
```

日常观看建议优先使用 `china_stable.m3u`。

---

## 🏙️ 中国重点地方频道

中国频道会尽量保留南京、苏州和上海等地区的本地频道。

### 南京

尽量收录南京新闻综合、南京教科、南京生活、南京信息、南京娱乐、南京少儿、南京十八以及其他当前可用南京频道。

### 苏州

尽量收录苏州新闻综合、苏州社会经济、苏州文化生活、苏州生活资讯、苏州4K，以及昆山、常熟、张家港、太仓、吴江等苏州地区频道。

### 上海

尽量收录东方卫视、上海新闻综合、第一财经、五星体育、纪实人文、上海都市、都市剧场、哈哈炫动、七彩戏剧、上海外语 / ICS、上海教育以及其他当前可用上海频道。

---

# 🌏 海外稳定版

海外稳定版目前重点覆盖：

**🇯🇵 日本｜🇹🇼 台湾｜🇭🇰 香港｜🇲🇴 澳门｜🇰🇷 韩国｜🇺🇸 美国｜🇬🇧 英国**

海外频道不是简单把所有公开地址全部加入播放列表。

GitHub Actions 会定期检测候选直播线路，尽量只保留当次能够访问并返回有效 HLS / 视频内容的线路。

---

## 🇯🇵 日本频道

尽量保留当前可播放的日本频道，例如：

NHK総合、NHK Eテレ、NHK BS、NHK WORLD JAPAN、日本テレビ、テレビ朝日、TBSテレビ、テレビ東京、フジテレビ、TOKYO MX、BS日テレ、BS朝日、BS-TBS、BSテレ東、BSフジ、WOWOW、J SPORTS、日テレNEWS、FNN 等。

实际频道数量会根据每次检测结果变化。

---

## 🇹🇼 台湾频道

尽量保留当前可访问的台湾新闻、综合、财经、影视、综艺及地方频道。

频道会根据上游公开源和自动检测结果动态调整。

---

## 🇭🇰 香港频道

尽量保留当前可访问的香港本地、新闻、综合及国际频道。

---

## 🇲🇴 澳门频道

尽量保留当前可访问的澳门本地、新闻及综合频道。

---

## 🇰🇷 韩国频道

尽量保留当前可访问的韩国综合、新闻、娱乐及地方频道。

---

## 🇺🇸 美国频道

美国公开 IPTV 数量较多。

稳定版会优先保留当前检测能够正常访问的：

新闻、地方电视台、公共电视、财经、娱乐、纪录、体育相关频道以及 FAST 免费流媒体频道。

不会为了单纯增加数量而强制保留大量检测失败的线路。

---

## 🇬🇧 英国频道

尽量保留当前可访问的英国新闻、综合、地方、娱乐、音乐及 FAST 免费频道。

---

# ✅ 海外稳定性检测

海外稳定版会自动检查候选播放地址。

优先选择：

```text
HTTPS
HLS / M3U8
1080p
720p
CDN 线路
官方或较稳定服务器
响应较快的线路
```

尽量排除：

```text
Geo-blocked
Offline
Broken
Dead
Not 24/7
连接超时
HTTP 错误
无有效视频内容
明显失效的线路
```

需要注意：

GitHub Actions 检测通过表示该线路在检测服务器当时能够访问。

这并不能保证该频道在所有地区、所有运营商和所有网络环境中都一定能够播放。

---

# ⭐ 推荐：全部稳定版

如果只想在 APTV 中添加一个订阅，推荐使用：

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/all_stable.m3u
```

包含：

```text
中国稳定频道
+
日本
台湾
香港
澳门
韩国
美国
英国
```

这是目前最适合作为日常主订阅的版本。

> `all_stable.m3u` 需要海外稳定版 GitHub Actions 至少成功运行一次后才会生成。

---

# 🌏 海外稳定版

如果只想观看海外频道：

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/world_stable.m3u
```

包含：

```text
日本
台湾
香港
澳门
韩国
美国
英国
```

并经过自动可用性检测。

> `world_stable.m3u` 需要 `.github/workflows/update_stable.yml` 成功运行后生成。

---

# 📂 频道分类

## 中国频道

```text
01·央视频道
02·卫视频道
03·地方频道
04·体育频道
05·新闻财经
06·影视剧场
07·少儿动漫
08·纪录科教
09·港澳台
10·国际频道
11·4K超高清
12·其他频道
14·南京频道
15·苏州频道
16·上海频道
```

## 海外频道

```text
13·日本频道
17·台湾频道
18·香港频道
19·澳门频道
20·韩国频道
21·美国频道
22·英国频道
```

---

# 📡 APTV 订阅地址

## ⭐ 全部稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/all_stable.m3u
```

**推荐日常使用。**

---

## 🌏 海外稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/world_stable.m3u
```

---

## 🇨🇳 中国稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/china_stable.m3u
```

---

## 🇨🇳 中国500台扩展版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/china500.m3u
```

扩展版频道更多，但整体稳定性低于稳定版。

---

# 📱 APTV 导入方法

在 APTV 中进入：

```text
配置
↓
订阅配置
↓
添加订阅
↓
粘贴订阅 URL
↓
保存
↓
应用
↓
刷新
```

日常使用推荐配置名称：

```text
中国及全球电视稳定版
```

订阅地址：

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/all_stable.m3u
```

如果 APTV 仍显示旧频道或旧分类，可以尝试手动刷新订阅、重新应用配置，或者删除旧订阅后使用新的配置名称重新添加。

---

# 📅 EPG 节目单

中国频道主要使用：

```text
https://live.fanmingming.cn/e.xml
```

海外稳定版还会加入部分日本、香港、韩国、美国和英国等地区的 EPG 数据源。

EPG 是否能正确显示取决于频道的 `tvg-id` 与节目单数据源是否匹配。

部分直播频道可能只有视频画面而没有节目单。

---

# 🔄 自动更新

项目使用 GitHub Actions 自动维护播放列表。

计划任务：

```text
每 6 小时自动更新
```

中国频道自动执行：

```text
获取最新公开 IPTV 列表
合并多个上游源
统一频道名称
自动去重
优先选择高质量线路
重新生成 M3U
自动提交更新
```

海外稳定版自动执行：

```text
获取候选海外频道
自动去重
检测频道 URL
检测 HLS / M3U8
过滤明显失效线路
重新生成 world_stable.m3u
合并生成 all_stable.m3u
自动提交更新
```

---

# 🧹 自动去重

频道会综合使用：

```text
tvg-id
标准化频道名称
频道 URL
```

进行去重。

例如：

```text
CCTV1
CCTV-1
CCTV 1
央视一套
CCTV-1 HD
CCTV-1 1080P
```

会尽量统一为：

```text
CCTV-1
```

并优先选择质量较好的线路。

---

# 🎞️ 清晰度选择

相同频道存在多条可用线路时，大致优先：

```text
1080p
↓
720p
↓
576p
↓
480p
```

4K / 8K 不一定作为稳定版第一优先级。

因为超高清直播通常需要更高带宽，也更容易受到网络质量影响。

因此稳定版更重视：

```text
稳定性
+
清晰度
+
启动速度
```

而不是单纯追求最高分辨率。

---

# ⚡ 低延迟优先

如果上游列表提供响应时间信息，会优先采用响应较快的线路。

同时优先考虑：

```text
HTTPS
HLS / M3U8
CDN
近期检测成功源
稳定服务器
```

---

# 🍎 Apple TV / APTV 使用建议

### 日常主订阅

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/all_stable.m3u
```

### 只看中国

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/china_stable.m3u
```

### 只看海外

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/world_stable.m3u
```

如果全部稳定版频道数量较多、APTV 加载速度变慢，可以把中国和海外拆成两个配置使用。

---

# 🛠️ 项目文件

项目主要文件：

```text
README.md

build.py
build_world_stable.py

china_stable.m3u
china500.m3u
world_stable.m3u
all_stable.m3u

.github/
└── workflows/
    ├── update.yml
    └── update_stable.yml
```

用途：

```text
build.py
→ 中国频道生成脚本

build_world_stable.py
→ 海外频道检测和生成脚本

china_stable.m3u
→ 中国稳定版

china500.m3u
→ 中国500台扩展版

world_stable.m3u
→ 海外稳定版

all_stable.m3u
→ 中国稳定版 + 海外稳定版

.github/workflows/update.yml
→ 中国频道自动更新

.github/workflows/update_stable.yml
→ 海外稳定频道自动检测和更新
```

---

# ⚠️ 重要说明

本项目：

```text
不托管视频文件
不提供电视节目内容
不破解付费电视服务
仅整理公开可访问的 IPTV 播放列表地址
```

所有直播地址均来自公开网络。

公网 IPTV 地址具有较强时效性，可能受到以下因素影响：

```text
上游服务器变化
CDN 调整
地理位置
网络运营商
IP 地址
DNS
地区限制
版权策略
频道停播
临时维护
```

因此：

**GitHub Actions 检测可播放 ≠ 所有地区和所有网络环境下一定可以播放。**

自动检测和自动更新的目标是尽量提高整体可播放率，而不是保证所有频道永久 100% 有效。

---

# ❤️ 推荐使用

### 首选：全部稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/all_stable.m3u
```

### 中国稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/china_stable.m3u
```

### 海外稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/aptv-global-iptv/main/world_stable.m3u
```

---

**播放列表由 GitHub Actions 自动维护和更新。**
