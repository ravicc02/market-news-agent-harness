所有路径相对于当前工作区根目录，使用北京时间。

按以下顺序完成本次国际金融简报：

1. 读取 docs/AGENTS.md，了解职责和执行要求。
2. 读取 docs/sources.md，按来源和搜索范围获取资料，可优先使用其中的采集脚本。
3. 确认本次资料已保存到 data/raw/YYYY-MM-DD/，记录实际正文范围和失败来源。
4. 读取 docs/processing-rules.md 和本次原文，整理到 data/processed/YYYY-MM-DD/。
5. 读取 docs/briefing-template.md，结合整理稿填写简报，保存到 reports/YYYY-MM-DD/，运行记录写入 runs/YYYY-MM-DD/。
6. 原样输出已保存的简报全文，由本定时任务自动投递微信，不另行发送。

用当前 Agent 完成整理，不调用 subagent。中断后按运行记录续做；无法完成时如实说明，不编造资料。
