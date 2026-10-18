# 来源与搜索范围

## 搜什么

目标是国际黄金、白银、WTI、Brent，以及主要外汇直盘和交叉盘的新闻与原始公告。
优先执行前 24 小时；周末或资料不足可扩展到 72 小时，保留实际发布时间。
来源没有更新或访问失败都应保留状态。时间未知的文章不混入严格时间窗口。

| 类别 | 搜索重点 | 首选来源 |
|---|---|---|
| 国际黄金 | 黄金、XAU、美元、利率和直接相关事件 | FXEmpire、GoldSeek、investingLive、MarketPulse；美联储、ECB 原始公告作补充依据 |
| 白银 | 白银、XAG、工业需求和直接相关事件 | SilverSeek、FXEmpire、GoldSeek；相关官方公告 |
| 原油 | WTI、Brent、供需、库存、OPEC | OilPrice、EIA、FXEmpire、investingLive；必要时搜索 OPEC 原始页面 |
| 外汇直盘 | 七大美元直盘及相关央行政策、统计 | ExchangeRates、FXEmpire、investingLive、MarketPulse；美联储、ECB |
| 交叉盘 | 具体交叉盘，以及组成货币的事件 | ExchangeRates、FXEmpire、investingLive 技术分析；对应央行和统计机构 |

关键词只是发现线索。Agent 阅读后决定真实相关性，不因词语出现就一定采用。
固定源未覆盖某类时，可以使用已有搜索或网页工具补充，保留原始来源和发布时间。
不要给每个货币对硬凑新闻。

## 已验证的 RSS 扩展

当前启用 12 个 RSS 订阅、10 个网站；另保留 1 个暂停来源（FXStreet）。investingLive 使用新闻、技术分析和央行动态三个独立订阅。
2026-10-19 两轮扩展均验证 RSS、带时区发布时间和样例正文；详情见 `docs/source-validation.md`。

- investingLive：使用 `.article-body-normal`，只提取正文区域；支持短快讯，不把导航或页脚当正文。
- OilPrice：使用 `#article-content` 提取正文，排除作者侧栏。
- MarketPulse：使用 `.post-body` 提取完整正文区域。
- 投资新闻中的 EURUSD、USDJPY 等紧连写法也用于候选分类，原油关键词按英文词边界匹配。
- RSS 返回成功只表示这次可读，不代表持续可用或一定有最近一天的更新。
- 首次加入只记历史基线，不发旧闻。跨订阅相同 URL 沿用现有去重规则。

Investing.com 本次 RSS 缺少时区且样例正文返回 403，因此未启用。
金十、财联社和 Newsquawk 未发现已验证可用的公开 RSS；Rigzone 和 Kitco 本次候选地址也未通过验证。
FXStreet 持续返回 403，已移到 `paused_feeds`，不参与有效轮询；未绕过访问限制。

## 第二轮新增与暂停来源

- FXEmpire Forecasts：外汇、贵金属与商品预测；这是作者分析，不当成已证实事实。
- ExchangeRates：直盘、交叉盘和机构汇率观点，保留预测主体和时点。
- GoldSeek／SilverSeek：贵金属评论与持仓资料；包含观点和公司公告，不保证分钟级更新。
- SilverSeek 表格按行保留列分隔符，避免白银持仓报告只剩作者简介或丢失表头。
- 同一订阅内部重复链接继续按现有唯一键去重。

MINING.COM Gold 初测可读，但上线前两次复测 RSS 均返回 403，因此本次不启用。
本次没有启用正文受限的 CNBC、返回 403 的 FXLeaders／FXCM、返回 404 的 DailyForex 候选订阅，也没有启用最近新闻停在 8 月的 FXEmpire News。
ForexCrunch 主订阅可读，但最近内容偏加密资产，本轮不启用。

## 怎么取

先将执行目录设为本工作区，再运行：

```sh
python tools/fetch-news.py
```

需要明确扩大到最近 72 小时时：

```sh
python tools/fetch-news.py --hours 72
```

等待命令结束；若工具返回运行中的会话，继续等同一会话，不重复启动。
脚本设置单次网络超时和总量上限，任务工具可给约 300 秒执行窗口。
资料落到 `data/raw/YYYY-MM-DD/<batch-id>/`，返回目录和采集状态。
先读批次的 `index.md` 和 `collection.json`，再读有用的原文。
采集器不调用模型、不生成摘要、不推断走势、不发消息。
当前脚本需要容器中已有的 BeautifulSoup 和 lxml；缺少时用网页工具采集，不在定时任务中临时安装。

访问 403、付费或验证码时保留失败记录，不当成读过正文。
EIA 是能源综合源，光伏和电力文章可能不符合原油范围；Agent 应据正文筛选。
央行公告有纪要链接时继续读实际纪要，脚本会尝试官方 HTML 文档。

## 行情补充

新闻是主体。走势分析需要核验报价时，Agent 可使用现有联网工具访问：

- ECB：`https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml`，日度参考汇率。
- EIA：`https://www.eia.gov/dnav/pet/PET_PRI_SPT_S1_D.htm`，WTI、Brent 日度现货。
- 贵金属：从公开报价页核对现货或期货标识；只有 COMEX 期货时必须注明。

补充的行情资料同样保存到本次原文目录，并记录链接、日期与口径。
没有可核实行情时只做新闻因素分析，不能凭模型记忆填写价格。

## 脚本读取的来源设置

下面 JSON 是脚本唯一来源配置。Agent 也可直接阅读，不另维护一份配置文件。

```json
{
  "timezone": "Asia/Shanghai",
  "lookback_hours": 24,
  "fallback_hours": 72,
  "max_feed_items": 30,
  "max_articles_per_source": 4,
  "max_articles_total": 12,
  "timeout_seconds": 15,
  "max_response_bytes": 4000000,
  "feeds": [
    {
      "id": "fed",
      "name": "美联储",
      "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
      "domains": [
        "www.federalreserve.gov"
      ],
      "selectors": [
        "#article"
      ]
    },
    {
      "id": "ecb",
      "name": "欧洲央行",
      "url": "https://www.ecb.europa.eu/rss/press.html",
      "domains": [
        "www.ecb.europa.eu"
      ],
      "selectors": [
        "main"
      ]
    },
    {
      "id": "eia",
      "name": "EIA",
      "url": "https://www.eia.gov/rss/todayinenergy.xml",
      "domains": [
        "www.eia.gov"
      ],
      "selectors": [
        ".tie-article"
      ]
    },
    {
      "id": "investinglive_news",
      "name": "investingLive News",
      "url": "https://investinglive.com/feed/news/",
      "domains": [
        "investinglive.com",
        "www.investinglive.com"
      ],
      "selectors": [
        ".article-body-normal"
      ],
      "min_paragraph_characters": 20,
      "min_body_paragraphs": 1,
      "min_body_characters": 120
    },
    {
      "id": "investinglive_technical",
      "name": "investingLive Technical Analysis",
      "url": "https://investinglive.com/feed/technicalanalysis/",
      "domains": [
        "investinglive.com",
        "www.investinglive.com"
      ],
      "selectors": [
        ".article-body-normal"
      ],
      "min_paragraph_characters": 20,
      "min_body_paragraphs": 1,
      "min_body_characters": 120
    },
    {
      "id": "investinglive_centralbank",
      "name": "investingLive Central Banks",
      "url": "https://investinglive.com/feed/centralbank/",
      "domains": [
        "investinglive.com",
        "www.investinglive.com"
      ],
      "selectors": [
        ".article-body-normal"
      ],
      "min_paragraph_characters": 20,
      "min_body_paragraphs": 1,
      "min_body_characters": 120,
      "default_categories": [
        "外汇货币对直盘"
      ]
    },
    {
      "id": "oilprice",
      "name": "OilPrice",
      "url": "https://oilprice.com/rss/main",
      "domains": [
        "oilprice.com",
        "www.oilprice.com"
      ],
      "selectors": [
        "#article-content"
      ]
    },
    {
      "id": "marketpulse",
      "name": "MarketPulse",
      "url": "https://www.marketpulse.com/feed/",
      "domains": [
        "www.marketpulse.com",
        "marketpulse.com"
      ],
      "selectors": [
        ".post-body"
      ]
    },
    {
      "id": "fxempire_forecasts",
      "name": "FXEmpire Forecasts",
      "url": "https://www.fxempire.com/api/v1/en/articles/rss/forecasts",
      "domains": [
        "www.fxempire.com",
        "fxempire.com"
      ],
      "selectors": [
        "article"
      ]
    },
    {
      "id": "exchangerates",
      "name": "ExchangeRates Currency News",
      "url": "https://www.exchangerates.org.uk/news/rss.xml",
      "domains": [
        "www.exchangerates.org.uk",
        "exchangerates.org.uk"
      ],
      "selectors": [
        ".erukNewsBody"
      ]
    },
    {
      "id": "goldseek",
      "name": "GoldSeek",
      "url": "https://www.goldseek.com/rss.xml",
      "domains": [
        "goldseek.com",
        "www.goldseek.com"
      ],
      "selectors": [
        ".article-text .text-long"
      ]
    },
    {
      "id": "silverseek",
      "name": "SilverSeek",
      "url": "https://www.silverseek.com/rss.xml",
      "domains": [
        "silverseek.com",
        "www.silverseek.com"
      ],
      "selectors": [
        ".article-text .text-long"
      ],
      "include_tables": true,
      "min_paragraph_characters": 1,
      "min_body_paragraphs": 3,
      "min_body_characters": 200
    }
  ],
  "keywords": {
    "国际黄金": [
      "gold",
      "gold bullion",
      "xau",
      "黄金"
    ],
    "白银": [
      "silver",
      "xag",
      "白银"
    ],
    "原油": [
      "crude",
      "brent",
      "wti",
      "opec",
      "oil price",
      "oil supply",
      "oil demand",
      "petroleum",
      "oil production",
      "oil inventories",
      "原油",
      "oil",
      "energy inventories",
      "refinery",
      "hormuz"
    ],
    "外汇货币对直盘": [
      "eur/usd",
      "gbp/usd",
      "aud/usd",
      "nzd/usd",
      "usd/jpy",
      "usd/chf",
      "usd/cad",
      "dollar",
      "forex",
      "greenback",
      "euro",
      "sterling",
      "yen",
      "kiwi",
      "aussie",
      "swiss franc",
      "canadian dollar",
      "federal open market",
      "fomc",
      "monetary policy",
      "discount rate",
      "美元",
      "外汇",
      "fed",
      "bank of japan",
      "bank of england",
      "rba",
      "rbnz",
      "ecb",
      "boj",
      "boe",
      "boc",
      "swiss",
      "franc",
      "pound",
      "japanese yen",
      "exchange rate",
      "interest rate"
    ],
    "交叉盘": [
      "eur/jpy",
      "gbp/jpy",
      "eur/gbp",
      "eur/chf",
      "eur/aud",
      "eur/cad",
      "eur/nzd",
      "gbp/chf",
      "gbp/aud",
      "gbp/cad",
      "gbp/nzd",
      "aud/jpy",
      "aud/chf",
      "aud/cad",
      "aud/nzd",
      "nzd/jpy",
      "nzd/chf",
      "nzd/cad",
      "cad/jpy",
      "cad/chf",
      "chf/jpy",
      "cross currency",
      "cross-currency",
      "交叉盘"
    ]
  },
  "paused_feeds": [
    {
      "id": "fxstreet",
      "name": "FXStreet",
      "url": "https://www.fxstreet.com/rss/news",
      "domains": [
        "www.fxstreet.com"
      ],
      "selectors": [
        "article"
      ],
      "reason": "RSS and article samples repeatedly returned HTTP 403 on 2026-10-19; excluded from active polling until verified recovery"
    }
  ]
}
```
