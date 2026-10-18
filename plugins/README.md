# Plugin sources

- `plugins/market-news-bridge/`: local AstrBot plugin implementing new-link deduplication, article capture, native Agent execution, report validation, and proactive delivery.
- `plugins/astrbot-plugin-rss-local.patch`: local integration patch for `Soulter/astrbot_plugin_rss`.

## Upstream baseline

```text
Repository: https://github.com/Soulter/astrbot_plugin_rss
Commit: 57244346672bd1b35098bd8e4adc8913aa412094
Metadata version: v1.1.2
AstrBot integration baseline: v4.29.1
```

The patch delegates monitored sessions to the bridge, keeps TLS validation enabled, and handles optional descriptions and timezone-aware RSS dates. The bridge supplies already fetched RSS bytes to the native parser, avoiding a second request; its shared policy covers RSS and article HTTP traffic. Unmonitored sessions retain the upstream direct-push behavior.

## Installation

Install the pinned upstream RSS checkout as `astrbot_plugin_rss` in AstrBot's plugin directory, then apply the patch from this repository with `git apply`. Copy `plugins/market-news-bridge/` to the sibling plugin directory named `astrbot_plugin_market_news`.

Configure both plugins in AstrBot. Use `plugins/market-news-config.example.json` as the bridge example. Set the RSS plugin's `delegate_sessions` list to the same target session; keep raw RSS forwarding disabled for that target. The bridge registers per-source cron minutes, seconds, and jitter from `docs/sources.md` at startup. The former global `poll_cron` setting is retired.

Restart or reload the plugins. Confirm `/market status` reports initialized sources. The first source pass records a historical baseline and does not send existing articles. A subsequent unseen and eligible URL enters the Agent queue. Each event follows `docs/event-task.md` and `docs/news-flash-template.md` to produce one “新消息快讯”; the bridge delivers the saved output. No daily digest task is required.

The bridge uses native AstrBot integration points verified against the version above. Revalidate the bridge and local patch before upgrading AstrBot or the RSS plugin.

## Polling and HTTP cooldowns

`plugins/market-news-bridge/polling.py` implements the per-source schedule and a persistent per-site request policy. Source types use 5–60 minute intervals, with minute/second offsets and up to 30 seconds of jitter. Same-site request starts are separated by at least 10 seconds.

HTTP 429 uses exponential backoff from 30 minutes to a default maximum of 6 hours. A longer `Retry-After`, in seconds or HTTP-date form, is honored. HTTP 403 pauses the site for at least 6 hours. Network and server failures back off from 5 to 60 minutes. Cooldowns affect sibling feeds and article downloads and survive restart in the plugin data directory's `http-state.json`.

Manual checks honor source due times and site cooldowns. On first migration, existing last-check timestamps seed source due times to avoid an immediate full-source burst. Cooldown deferrals do not consume Agent processing attempts. See `docs/monitoring.md` for policy and log fields.

## State and credentials

The bridge reuses the configured AstrBot model and platform instance. It does not require copied API keys or WeChat login tokens in this repository. Configure the workspace root and target session locally through AstrBot.

Runtime articles, model tool traces, reports, poll logs and SQLite state are intentionally excluded from Git. `ADAPTER_ACCEPTED` means the platform adapter accepted the send call; it is not a read receipt. An interrupted send becomes `UNKNOWN` and is not automatically resent.
