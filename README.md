# china-iptv-500

面向 APTV / Apple TV 的中国电视直播订阅。

- 最多 500 个规范化后的唯一频道
- GitHub Actions 每 6 小时重新抓取一次上游公开播放列表
- 自动去重：统一 CCTV 命名、清晰度后缀和常见卫视别名，并去除重复 URL
- 低延迟优先：优先采用近期自动检测源的 response-time 标记；1080p/720p 优先，4K/8K 不作为低延迟首选
- EPG：`https://live.fanmingming.cn/e.xml`
- 仅聚合公开可访问的播放列表地址，不托管视频内容

## APTV 订阅地址

```text
https://raw.githubusercontent.com/lizihan18361015162-spec/china-iptv-500/main/china500.m3u
```

在 APTV 中选择：

**配置 → 订阅配置 → 粘贴上述 URL → 保存并应用**

> 公网直播源会随上游、地区、运营商和版权策略变化。自动更新能降低失效概率，但不能保证任意频道在任意网络环境下始终可播。
