# RSS 来源验证

验证日期：2026-10-19。执行环境：当前 AstrBot 容器。

## 第一轮扩展

| 订阅 | RSS 条目 | 带时区时间 | 正文样例 | 结果 |
|---|---:|---:|---:|---|
| investingLive News | 25 | 25 | 2 篇 | 启用 |
| investingLive Technical Analysis | 25 | 25 | 2 篇 | 启用 |
| investingLive Central Banks | 25 | 25 | 2 篇 | 启用 |
| OilPrice | 15 | 15 | 2 篇 | 启用 |
| MarketPulse | 3 | 3 | 1 篇 | 启用 |

第一轮新增 5 个订阅来自 3 个网站；当时共 9 个订阅、7 个网站。最终启用数量以第二轮扩展为准。
已使用采集脚本和实例实际 RSS 解析器分别请求验证，新增正文共检查 9 篇。
RSS 与正文可读只是本轮验证结果，不是长期可用性或更新速度承诺。

## 正文提取

- investingLive：使用 `.article-body-normal`，排除页脚及推荐区域；允许精确正文容器内的短快讯。
- OilPrice：使用 `#article-content`，排除作者侧栏。
- MarketPulse：使用 `.post-body`，避免只读取第一个 `.rich-text` 摘要块。
- 时间必须带明确时区；不根据本机时区猜测 RSS 的发布时间。
- EURUSD、USDJPY、GBP-JPY 等写法用于候选识别；英文关键词匹配增加词边界，减少 Goldman、soil 等误匹配。

## 未启用

| 候选 | 实测情况 | 处理 |
|---|---|---|
| Investing.com 外汇、商品 RSS | 各返回 10 条，但日期不带时区；4 个正文样例均返回 403 | 暂不启用 |
| 金十数据 | 官网没有发现 RSS 声明；测试候选地址返回 404 | 未确认公开 RSS，不启用 |
| 财联社 | 官网没有发现新闻 RSS 声明；测试候选地址返回 404 | 未确认公开 RSS，不启用 |
| Newsquawk | 官网没有发现 RSS 声明；测试候选地址返回 404 | 未确认公开 RSS，不启用 |
| Rigzone | 本次候选 RSS 地址返回空内容 | 不启用 |
| Kitco | 本次候选 RSS 地址返回 404 | 不启用 |

“未确认”只表示本轮未找到通过验证的公开订阅，不代表网站永远不提供其他接入方式。
本次未绕过验证码、付费内容或访问限制。

## 现有来源状态

FXStreet RSS 和样例正文持续返回 403，第二轮已移到 `paused_feeds`，停止本会话轮询；保留历史去重状态。
EIA RSS 本次可读，但存在缺少年份的日期；采集器将其标为未知时间，不混入严格时间窗口。实例上游解析器的兼容行为不能视为年份已被来源确认。
其他来源正常时继续监测，单站失败不会阻塞全部订阅。

## 第二轮扩展

上线前再次使用实际采集器与已安装 RSS 插件的 `poll_rss` 方法验证，未创建额外调度器。

| 订阅 | RSS 条目 | 带时区时间 | 正文样例 | 结果 |
|---|---:|---:|---:|---|
| FXEmpire Forecasts | 20 | 20 | 2 篇 | 启用 |
| ExchangeRates Currency News | 25 | 25 | 2 篇 | 启用 |
| GoldSeek | 10 | 10 | 2 篇 | 启用 |
| SilverSeek | 10 | 10 | 2 篇 | 启用 |

第二轮新增 4 个订阅，暂停原有 FXStreet，最终共 12 个有效订阅、10 个网站；另有 1 个暂停来源。
GoldSeek 和 SilverSeek 属于同系列出版网站，不能当成完全独立的观点来源。
这四个订阅并非都属于高频快讯；贵金属评论、COT 持仓和公司公告按各自节奏更新。

- FXEmpire 只启用 Forecasts。作者预测须与已发生事实区分。
- ExchangeRates 覆盖货币、直盘和交叉盘；正文中的机构汇率目标保留主体和日期。
- GoldSeek 使用 `.article-text .text-long`，避免将作者简介当成正文。
- SilverSeek 使用同类正文容器，并按行保留表头、单元格和列分隔符。样例 COT 报告保留 16 个表格行；表格是正文依据，不能因段落短就丢弃。
- 新增表格提取只对显式开启 `include_tables` 的来源生效，普通来源的正文质量门槛保持不变。
- 独立临时数据库验证了同订阅重复链接、跨订阅带跟踪参数的重复链接均只入队一次；未改动实例收件箱。

| 第二轮未启用候选 | 实测情况 | 处理 |
|---|---|---|
| MINING.COM Gold | 初测 RSS 和正文可读，上线前两次复测 RSS 均返回 403 | 不启用 |
| FXEmpire News | RSS 可读，但最新新闻仍停在 2026-08-04 | 不启用 |
| CNBC Energy／Economy | RSS 可读，样例文章只有公开计量付费预览 | 不启用全文采集 |
| ForexCrunch | RSS 与样例正文可读，近期主题主要为加密资产 | 暂不启用 |
| DailyForex 候选订阅 | 返回 404 | 不启用 |
| FXLeaders／FXCM 候选订阅 | 返回 403 | 不启用 |
| PoundSterlingLive 候选订阅 | 返回空订阅 | 不启用 |

## 上线与回溯

首次加入的订阅只记录已有条目基线，不触发旧闻推送。
同一接收会话下，相同规范化 URL 在不同订阅之间共享去重状态。
验证记录写入实例 `runs/rss-source-probe-2026-10-19.json`、`runs/rss-article-probe-2026-10-19.json` 和 `runs/rss-source-acceptance-2026-10-19.json`。
这些实例运行记录不提交到公开仓库。

第二轮网络探测、正文检查和验收分别保存到实例 `runs/rss-expansion-round2-probe-2026-10-19.json`、`runs/rss-expansion-round2-articles-2026-10-19.json`、`runs/rss-expansion-round2-acceptance-2026-10-19.json`。

上线后通过实例实际调度回调再次轮询：12 个有效订阅均有基线，来源错误为空；4 个新增订阅分别读取 20、25、10、10 条，新入队均为 0，未补发旧闻。实例部署验收见 `runs/rss-expansion-round2-deployment-2026-10-19.json`。
