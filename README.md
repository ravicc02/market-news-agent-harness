# Market News Agent Harness

Agent-led financial news monitoring for AstrBot. RSS polling detects new links, the bridge downloads the article, and the native AstrBot Agent prepares a single “新消息快讯” news flash for delivery to the configured WeChat session.

## Runtime flow

```text
RSS polling -> new-link deduplication -> article download -> native AstrBot Agent
-> processed article + single news flash + run note -> bridge delivery
```

The first source bootstrap records existing items as a baseline. Subsequent unseen, eligible links enter the queue individually. Sources are currently polled every two minutes; actual delivery also takes article download and Agent processing time. Each event produces one news flash. No scheduled digest is generated.

The Agent reads `docs/AGENTS.md`, `docs/event-task.md`, `docs/processing-rules.md`, and `docs/news-flash-template.md`. It reads only the event's downloaded article, saves the three specified outputs, and returns the saved flash. The bridge handles delivery.

## Repository layout

- `docs/`: Agent rules, source configuration, event instructions, news flash template, monitoring behavior, and source validation.
- `tools/fetch-news.py`: RSS and article collection helpers used by the bridge; no model calls or delivery.
- `plugins/market-news-bridge/`: local AstrBot bridge source.
- `plugins/astrbot-plugin-rss-local.patch`: integration changes for the upstream RSS plugin.

Runtime originals, processed articles, news flashes, logs, SQLite state, account configuration, and platform tokens stay outside this repository. Document paths are relative to the workspace root; folder and file names use English.

## Setup

Read `docs/README.md`, `docs/monitoring.md`, and `plugins/README.md`. Configure the bridge workspace and target session in AstrBot, apply the local RSS patch to the pinned upstream checkout, and enable the plugins. Source subscriptions come from `docs/sources.md`. Configure polling in the RSS bridge; a scheduled digest task is not required.
