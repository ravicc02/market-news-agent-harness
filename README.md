# Market News Agent Harness

Agent-led financial news monitoring for AstrBot. The RSS monitor detects new items, stores source material, invokes the native AstrBot Agent for article-level processing, and delivers the saved brief through the configured platform adapter.

## Repository layout

- `docs/`: agent rules, source list, event task, formatting, and monitoring behavior.
- `tools/fetch-news.py`: optional fixed-source RSS and article collector. It does not call a model or send messages.
- `plugins/market-news-bridge/`: local AstrBot bridge source.
- `plugins/astrbot-plugin-rss-local.patch`: local changes applied to the upstream RSS plugin.

Runtime data, raw articles, generated reports, SQLite state, account configuration, and platform tokens stay outside this repository.

## Runtime flow

```text
RSS source -> new-link deduplication -> article download -> native AstrBot Agent
-> processed article + single-news brief -> configured adapter delivery
```

The first monitor bootstrap records existing feed items as a baseline and does not send them. Subsequent unseen links are processed individually.

## Setup

Read `docs/monitoring.md`, then configure the bridge workspace and target session in AstrBot. Apply the local RSS patch to the pinned upstream checkout before enabling the bridge. Keep all runtime configuration and credentials out of Git.
