# china-iptv-500

面向 APTV / Apple TV 的中国电视直播订阅。

## 当前版本

- **稳定版：最多 350 个频道**
  - 优先近期自动检测 / 自动筛选源
  - 优先 CCTV、卫视、1080p / 720p、低响应线路
  - 适合日常观看

- **扩展版：500 个频道**
  - 在稳定源基础上补充更多地方台和冷门频道
  - 频道更多，但个别公网源可能因地区、运营商或上游变化暂时不可播

- GitHub Actions **每 6 小时**自动更新
- 自动去重：统一 CCTV 命名、清晰度后缀和常见卫视名称，并去除重复 URL
- 自动分类：
  - 01·央视频道
  - 02·卫视频道
  - 03·地方频道
  - 04·体育频道
  - 05·新闻财经
  - 06·影视剧场
  - 07·少儿动漫
  - 08·纪录科教
  - 09·港澳台
  - 10·国际频道
  - 11·4K超高清
  - 12·其他频道
- EPG：`https://live.fanmingming.cn/e.xml`
- 仅聚合公开可访问的播放列表地址，不托管视频内容

## APTV 订阅地址

### 推荐：稳定版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/china-iptv-500/main/china_stable.m3u
### 不推荐：扩展版

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/china-iptv-500/main/china500.m3u
