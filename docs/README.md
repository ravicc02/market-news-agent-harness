# 新消息快讯工作区

本工作区只采用新闻事件流程：轮询发现新链接，下载原文，Agent 整理单篇，插件发送“新消息快讯”。
所有文档路径从工作区根目录解析；目录和文件名使用英文，正文可以使用中文。

## 目录

```text
AGENTS.md                               机器入口
EXTRA_PROMPT.md                         AstrBot 路由提示词
docs/
  AGENTS.md                             Agent 职责与边界
  README.md                             本说明
  sources.md                            品种范围与有效 RSS 配置
  processing-rules.md                    单篇整理规则
  news-flash-template.md                 新消息快讯模板
  event-task.md                          单次事件执行指令
  monitoring.md                          轮询、去重与投递规则
  source-validation.md                   来源验证记录
tools/
  fetch-news.py                          插件使用的 RSS 与正文采集工具
data/
  raw/YYYY-MM-DD/<job-id>-a<attempt>/     原始网页、正文及元数据
  processed/YYYY-MM-DD/<job-id>.md        单篇整理稿
reports/YYYY-MM-DD/<job-id>.md            新消息快讯
runs/YYYY-MM-DD/events/<job-id>.json      事件输入与输出路径
runs/YYYY-MM-DD/<job-id>.md               Agent 执行记录
runs/monitor-status.json                 当前监测状态
runs/poll-log.jsonl                       逐源轮询记录
```

`<job-id>` 对应事件的 `job_id`，`<attempt>` 是采集尝试次数。运行目录由插件按需创建，Agent 使用事件内给定路径。
工具调用轨迹与模型返回值也保存在本次 `runs/YYYY-MM-DD/`，便于核对实际执行。

## 从发现到发送

1. RSS 插件每两分钟轮询 `docs/sources.md` 中的有效订阅。
2. 事件桥记录首次基线，按规范化链接去重，仅将符合相关性和时效规则的新条目入队。
3. 插件下载本篇原文，保存正文范围、链接、时间和文件校验信息，生成事件 JSON。
4. 当前 AstrBot Agent 读取 `docs/AGENTS.md`、`docs/event-task.md`、整理规则和指定原文，写入本篇整理稿。
5. Agent 按 `docs/news-flash-template.md` 保存本篇快讯和执行记录，原样返回快讯。
6. 插件校验已保存的文件，读取快讯并投递绑定微信，记录调用结果。

每个事件只对应本篇快讯，不等待固定时点，不拼接成多品种日报，不填无关类别。
轮询间隔与完整处理耗时分别计算，不能把“两分钟检查”描述成“两分钟内必达”。

## 文档与状态入口

Agent 的执行入口为 `docs/event-task.md`，职责与约束在 `docs/AGENTS.md`，模板在 `docs/news-flash-template.md`。
运行方式与异常状态见 `docs/monitoring.md`；来源与验证结果见 `docs/sources.md`、`docs/source-validation.md`。
微信命令 `/market status` 查看状态，`/market check` 检查来源；检查操作仍遵循去重与时效规则。

## 数据管理

本仓库只发布规则、模板、来源配置、工具和插件源码。
原文、整理稿、快讯、运行记录、收件箱状态和平台凭据均留在实例，源码更新不清空历史基线或投递记录。
