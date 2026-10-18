# 金融简报工作区

所有路径均相对于工作区根目录。文档中的引用不以 `docs/` 为相对基准。
Agent 负责阅读、筛选、整理和分析；脚本仅帮助采集原文。

## 目录

```text
AGENTS.md                       机器入口，仅指向 docs/AGENTS.md
EXTRA_PROMPT.md                 AstrBot 自动入口，仅做路由
docs/
  AGENTS.md                     职责与六步流程
  README.md                     本说明
  sources.md                    来源、搜索范围、脚本配置
  processing-rules.md            整理规则
  briefing-template.md           简报模板
  scheduled-task.md              定时任务提示词
tools/
  fetch-news.py                  可选的原文采集脚本
data/
  raw/YYYY-MM-DD/<batch-id>/     原始资料及采集索引
  processed/YYYY-MM-DD/          Agent 整理稿及 index.md
reports/YYYY-MM-DD/              最终简报
runs/YYYY-MM-DD/                 运行记录
```

## 六步流程

1. 读取 `docs/AGENTS.md`。
2. 读取 `docs/sources.md`，获取资料。
3. 确认原文已保存到 `data/raw/YYYY-MM-DD/`。
4. 读取 `docs/processing-rules.md` 与原文，整理到 `data/processed/YYYY-MM-DD/`。
5. 读取 `docs/briefing-template.md`，保存简报到 `reports/YYYY-MM-DD/`，记录写入 `runs/YYYY-MM-DD/`。
6. 手动任务输出保存的简报；事件模式由监测插件统一投递。

## 命名和采集

所有目录与文件名均为英文；文档、新闻标题和简报正文可以使用中文。
常规简报、运行记录用 `<run-id>.md`；逐篇整理稿用 `<batch-id>-<article-id>.md`。

在工作区根目录运行：

```sh
python tools/fetch-news.py
```

脚本从 `docs/sources.md` 读取来源设置，保存 RSS、网页和正文。
每个原文批次内使用 `rss/`、`html/`、`articles/`、`index.md`、`discovery.json` 和 `collection.json`。
脚本不生成摘要、不调用模型、不发送消息。
复制 `docs/scheduled-task.md` 的内容作为定时任务提示词。

## 数据管理

本仓库仅包含规则、模板、来源清单、工具和插件源码。
原文、整理稿、简报、运行记录和平台状态均由实例运行时创建，不随源码发布。
根目录保留机器识别的薄入口；完整规则集中在 `docs/`。

## 默认触发方式

当前使用新新闻事件监测，不按每天固定时间发送。
入口为 `docs/event-task.md`，配置与状态见 `docs/monitoring.md` 和 `runs/monitor-status.json`。
旧 `docs/scheduled-task.md` 仅保留作手动整份简报参考，不新增定时简报。
