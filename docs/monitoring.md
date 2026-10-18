# 新闻事件监测

## 流程

RSS 插件每两分钟检查 `docs/sources.md` 的 12 个有效 RSS 订阅（10 个网站）。
Market News 桥按链接去重；首次只记录基线，只有后续新条目进入队列。
下载正文到 `data/raw/YYYY-MM-DD/`，然后触发 AstrBot 当前主 Agent。
Agent 按 `docs/event-task.md` 写整理稿、快讯和运行记录。
插件读取快讯文件，主动发送到已绑定的个人微信会话。

## 状态

运行状态见 `runs/monitor-status.json`，也可在绑定微信中发送 `/market status`。
`/market check` 手动检查来源，不补发已处理内容。

- QUEUED：待处理。
- RUNNING：主 Agent 正在阅读整理。
- RENDERED：快讯已保存。
- BLOCKED_CONTEXT：登录或微信会话上下文不足；用户发消息刷新后再尝试投递。
- ADAPTER_ACCEPTED：微信适配器完成发送调用，不代表用户已读。
- UNKNOWN：发送超时或中断，无法确定结果，不自动重发。
- FAILED／SKIPPED／EXPIRED：失败、不相关或过期，不反复刷屏。

## 插件

实例安装 `astrbot_plugin_rss` 与 `astrbot_plugin_market_news`。
前者负责 RSS 调度和解析，后者负责本工作区衔接与发送去重。
RSS 本地补丁修复时区解析、可选摘要和 TLS 校验，并将本会话交给事件桥，防止标题摘要直接推送。
上游插件升级前检查本地补丁；部署版本和验证记录保存在 `runs/`。

检查间隔不等于完整送达延迟，还包括来源更新、正文下载和 Agent 整理时间。
电脑、Docker 和网络保持运行才会持续监测。

新增订阅和样例正文验证见 `docs/source-validation.md`。正文与带时区日期未通过验证的来源不启用。

暂停来源放在 `docs/sources.md` 的 `paused_feeds`，不会继续注册轮询任务。历史去重记录保留，恢复时不清空基线。
