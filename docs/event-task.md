# 新消息快讯事件指令

收到新闻事件文件后，在当前工作区执行：

1. 读取 `docs/AGENTS.md`、`docs/sources.md` 和本次事件 JSON，确认 `article.text_path` 与 `outputs.processed`、`outputs.report`、`outputs.note`。
2. 读取 `docs/processing-rules.md` 和指定原文，核对相关性与正文范围。本篇原文已经下载，不运行整批采集或搜索补闻。
3. 将本篇整理稿写入 `outputs.processed`，保留原文相对路径、真实链接、来源、时间和段落依据。
4. 读取 `docs/news-flash-template.md`，只填写本篇主要类别，将“新消息快讯”写入 `outputs.report`；执行记录写入 `outputs.note`。
5. 最终回复原样返回已保存快讯。插件统一投递，Agent 不调用消息工具。

若本篇不相关或有效依据不足，在 `outputs.note` 写明原因，最终仅返回 `SKIP: 原因`，不为跳过的事件生成快讯。
只使用提供的文件读写工具，可以批量读取规则和原文；不调用子代理、其他模型或联网工具。
当前没有独立行情核验，影响部分写新闻因素分析，区分作者观点与自己的推断。
规则、脚本和原文只读，仅写事件指定的三个输出文件；所有路径相对于工作区根目录。
