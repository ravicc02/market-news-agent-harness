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

The patch delegates monitored sessions to the bridge, keeps TLS validation enabled, and handles optional descriptions and timezone-aware RSS dates. Unmonitored sessions retain the upstream direct-push behavior.

## Installation

Install the pinned upstream RSS checkout as `astrbot_plugin_rss` in AstrBot's plugin directory, then apply the patch from this repository with `git apply`. Copy `plugins/market-news-bridge/` to the sibling plugin directory named `astrbot_plugin_market_news`.

Configure both plugins in AstrBot. Use `plugins/market-news-config.example.json` as the bridge example. Set the RSS plugin's `delegate_sessions` list to the same target session; keep raw RSS forwarding disabled for that target. The bridge registers the four source subscriptions from `docs/sources.md` and restores the configured checking interval at startup.

Restart or reload the plugins. Confirm `/market status` reports initialized sources. The first source pass records a historical baseline and does not send existing articles. A subsequent unseen and eligible URL enters the Agent queue.

The bridge uses native AstrBot integration points verified against the version above. Revalidate the bridge and local patch before upgrading AstrBot or the RSS plugin.

## State and credentials

The bridge reuses the configured AstrBot model and platform instance. It does not require copied API keys or WeChat login tokens in this repository. Configure the workspace root and target session locally through AstrBot.

Runtime articles, model tool traces, reports, poll logs and SQLite state are intentionally excluded from Git. `ADAPTER_ACCEPTED` means the platform adapter accepted the send call; it is not a read receipt. An interrupted send becomes `UNKNOWN` and is not automatically resent.
