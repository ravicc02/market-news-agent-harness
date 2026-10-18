"""Download fixed RSS and article text only. The Agent reads, summarizes and analyzes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def now():
    return datetime.now(UTC)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def settings():
    text = (ROOT / 'docs' / 'sources.md').read_text(encoding='utf-8-sig')
    match = re.search(r'```json\s*\n(.*?)\n```', text, re.S)
    if not match:
        raise ValueError('docs/sources.md has no JSON source settings')
    return json.loads(match.group(1))


def checked_url(url, domains):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in domains or p.username or p.password or p.port not in (None, 443):
        raise ValueError('URL must use a configured public HTTPS source domain')
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))


class SourceRedirect(HTTPRedirectHandler):
    def __init__(self, domains):
        self.domains = domains
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, self.domains)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, source, conf):
    url = checked_url(url, source['domains'])
    request = Request(url, headers={'User-Agent': 'MarketBriefing/1.0 (personal RSS reader)', 'Accept': '*/*'})
    with build_opener(SourceRedirect(source['domains'])).open(request, timeout=conf['timeout_seconds']) as response:
        checked_url(response.geturl(), source['domains'])
        raw = response.read(conf['max_response_bytes'] + 1)
        if len(raw) > conf['max_response_bytes']:
            raise ValueError('Response exceeds configured byte limit')
        return raw, response.geturl()


def parse_time(text):
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
    except (ValueError, TypeError):
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    # Never guess a timezone missing from the source.
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else None


def categories(text, conf):
    text = text.casefold()
    def matches(word):
        word = word.casefold()
        # Sites use EUR/USD, EURUSD and EUR-USD for the same pair.
        if re.fullmatch(r"[a-z]{3}/[a-z]{3}", word):
            base, quote = word.split("/")
            return bool(re.search(r"(?<![a-z])" + base + r"[\s/-]?" + quote + r"(?![a-z])", text))
        if word.isascii():
            return bool(re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text))
        return word in text
    return [name for name, words in conf['keywords'].items() if any(matches(word) for word in words)]


def discover(source, conf):
    raw, final = download(source['url'], source, conf)
    tree = ET.fromstring(raw)
    rows = []
    for item in tree.findall('.//item')[:conf['max_feed_items']]:
        title, url = (item.findtext('title') or '').strip(), (item.findtext('link') or '').strip()
        date = (item.findtext('pubDate') or '').strip()
        description = item.findtext('description') or ''
        if not title or not url:
            continue
        timestamp = parse_time(date)
        kinds = categories(title + ' ' + description, conf)
        if not kinds:
            kinds = list(source.get('default_categories', ['外汇货币对直盘'] if source['id'] in ('fed', 'ecb') else []))
        rows.append({'source_id': source['id'], 'source': source['name'], 'title': title, 'url': url,
                     'published_original': date, 'published_at': timestamp.isoformat() if timestamp else None,
                     'categories': kinds, 'feed_summary_html': description})
    return source, raw, final, rows


def select_rows(rows, conf, hours, limit):
    end = now() + timedelta(minutes=5)
    start = now() - timedelta(hours=hours)
    eligible = [row for row in rows if row['categories'] and row['published_at']
                and start <= datetime.fromisoformat(row['published_at']) <= end]
    eligible.sort(key=lambda row: row['published_at'], reverse=True)
    chosen, counts, used = [], {}, set()
    # Give each covered category a chance before filling remaining slots by recency.
    ordered = []
    for category in conf['keywords']:
        ordered.extend(row for row in eligible if category in row['categories'])
    ordered.extend(eligible)
    for row in ordered:
        if row['url'] in used or counts.get(row['source_id'], 0) >= conf['max_articles_per_source']:
            continue
        chosen.append(row)
        used.add(row['url'])
        counts[row['source_id']] = counts.get(row['source_id'], 0) + 1
        if len(chosen) >= limit:
            break
    return chosen


def clean_body(raw, source):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw, 'lxml')
    links = [a.get('href') for a in soup.select('a[href]')]
    restricted = bool(soup.select_one('[data-test="paywall"], .paywall, .paywall-overlay'))
    for node in soup.select('script, style, nav, header, footer, aside, .mega-menu, .mega-menu-overlay'):
        node.decompose()
    container = next((soup.select_one(selector) for selector in source['selectors'] if soup.select_one(selector)), None)
    paragraphs = []
    if container:
        tags = ['p', 'h2', 'h3', 'li'] + (['tr'] if source.get('include_tables') else [])
        for element in container.find_all(tags):
            if element.name == 'tr':
                cells = element.find_all(['th', 'td'], recursive=False)
                text = ' | '.join(' '.join(cell.get_text(' ', strip=True).split()) for cell in cells)
            else:
                text = ' '.join(element.get_text(' ', strip=True).split())
            if len(text) >= source.get('min_paragraph_characters', 40) and text not in paragraphs:
                paragraphs.append(text)
    good = (len(paragraphs) >= source.get('min_body_paragraphs', 3)
            and sum(map(len, paragraphs)) >= source.get('min_body_characters', 500))
    return paragraphs, links, ('partial_text' if restricted else 'full_text') if good else None


def retrieve(row, source, conf, batch):
    from bs4 import BeautifulSoup
    article_id = sha256(row['url'].encode()).hexdigest()[:12]
    html_dir = batch / 'html'
    bodies_dir = batch / 'articles'
    meta = {k: v for k, v in row.items() if k != 'feed_summary_html'}
    meta.update(article_id=article_id, retrieved_at=now().isoformat(), original_url=row['url'], captures=[])
    try:
        raw, final = download(row['url'], source, conf)
        captures = [(raw, final)]
        paragraphs, links, level = clean_body(raw, source)
        # Fed announcement pages often link to the actual HTML minutes.
        document = next((link for link in links if link and '/monetarypolicy/fomcminutes' in link and link.endswith('.htm')), None)
        if source['id'] == 'fed' and document:
            linked_url = urljoin(final, document)
            try:
                detail, detail_url = download(linked_url, source, conf)
                more, _, more_level = clean_body(detail, source)
                if more_level and sum(map(len, more)) > sum(map(len, paragraphs)):
                    captures.append((detail, detail_url))
                    paragraphs, level, final = more, more_level, detail_url
            except Exception as exc:
                meta['linked_document_error'] = type(exc).__name__ + ': ' + str(exc)[:180]
        for index, (content, url) in enumerate(captures, 1):
            html_file = html_dir / f'{article_id}-{index}.html'
            html_file.write_bytes(content)
            meta['captures'].append({'path':html_file.relative_to(ROOT).as_posix(), 'url':url, 'sha256':sha256(content).hexdigest()})
        if level is None:
            summary = ' '.join(BeautifulSoup(row['feed_summary_html'], 'lxml').get_text(' ', strip=True).split())
            paragraphs = [summary] if len(summary) >= 80 else []
            level = 'summary_only' if paragraphs else 'headline_only'
        meta.update(url=final, content_level=level, paragraphs=len(paragraphs), characters=sum(map(len, paragraphs)))
        meta['categories'] = list(dict.fromkeys(row['categories'] + categories(' '.join(paragraphs), conf)))
        # Keywords are discovery hints; the Agent decides relevance after reading.
        if paragraphs:
            path = bodies_dir / f'{article_id}.md'
            header = [f"# {row['title']}", '', f"来源：{row['source']}", f"原文链接：{final}",
                      f"发布时间：{row['published_original']}", f"采集时间：{meta['retrieved_at']}",
                      f"正文范围：{level}", f"候选类别：{'、'.join(meta['categories'])}", '', '## 原始提取正文', '']
            body = [f'[P{index:03d}] {text}' for index, text in enumerate(paragraphs, 1)]
            path.write_text('\n'.join(header + ['\n\n'.join(body)]) + '\n', encoding='utf-8')
            meta['text_path'] = path.relative_to(ROOT).as_posix()
            meta['text_sha256'] = sha256(path.read_bytes()).hexdigest()
    except Exception as exc:
        meta.update(content_level='blocked', error=type(exc).__name__ + ': ' + str(exc)[:200])
    write_json(bodies_dir / f'{article_id}.json', meta)
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours', type=int)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    conf = settings()
    hours = args.hours or conf['lookback_hours']
    limit = args.limit or conf['max_articles_total']
    if not 1 <= hours <= 168 or not 1 <= limit <= 30:
        raise ValueError('Use hours in 1..168 and limit in 1..30')
    local = datetime.now(ZoneInfo(conf['timezone']))
    batch = ROOT / 'data' / 'raw' / local.strftime('%Y-%m-%d') / local.strftime('%H%M%S-%f')
    for name in ('rss', 'html', 'articles'):
        (batch / name).mkdir(parents=True, exist_ok=True)
    feed_states, rows = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(discover, source, conf): source for source in conf['feeds']}
        for job in as_completed(jobs):
            source = jobs[job]
            try:
                _, raw, final, discovered = job.result()
                path = batch / 'rss' / (source['id'] + '.xml')
                path.write_bytes(raw)
                rows.extend(discovered)
                feed_states.append({'source':source['name'], 'status':'ok', 'items':len(discovered),
                                    'unknown_date_items':sum(not row['published_at'] for row in discovered),
                                    'url':final, 'path':path.relative_to(ROOT).as_posix(), 'sha256':sha256(raw).hexdigest()})
            except Exception as exc:
                feed_states.append({'source':source['name'], 'status':'failed', 'error':type(exc).__name__ + ': ' + str(exc)[:180]})
    chosen = select_rows(rows, conf, hours, limit)
    expanded = False
    if args.hours is None and len(chosen) < 4:
        hours = conf['fallback_hours']
        chosen = select_rows(rows, conf, hours, limit)
        expanded = True
    write_json(batch / 'discovery.json', rows)
    source_map = {source['id']:source for source in conf['feeds']}
    articles = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(retrieve, row, source_map[row['source_id']], conf, batch) for row in chosen]
        for job in as_completed(jobs):
            articles.append(job.result())
    articles.sort(key=lambda article: article.get('published_at') or '', reverse=True)
    usable = [article for article in articles if article.get('text_path')]
    record = {'created_at':now().isoformat(), 'timezone':conf['timezone'], 'window_hours':hours,
              'expanded_window':expanded, 'batch_path':batch.relative_to(ROOT).as_posix(),
              'feeds':feed_states, 'discovered':len(rows), 'selected':len(chosen),
              'usable':len(usable), 'articles':articles,
              'next_step':'Agent reads these originals and docs/processing-rules.md; this script writes no summaries or analysis.'}
    write_json(batch / 'collection.json', record)
    lines = ['# 本次原文索引', '', f'时间窗口：最近 {hours} 小时。', '关键词分类只是候选，Agent 需阅读正文确认。', '']
    for index, article in enumerate(articles, 1):
        lines.extend([f"## {index}. {article['title']}", f"- 来源：{article['source']}；时间：{article.get('published_original')}",
                      f"- 原文链接：{article.get('url', article['original_url'])}", f"- 候选类别：{'、'.join(article.get('categories', []))}",
                      f"- 范围：{article['content_level']}；正文文件：{article.get('text_path', '无可用正文')}", ''])
    if not articles:
        lines.append('本次没有取得符合窗口和候选规则的文章；查看采集记录，不能据此断言没有新闻。')
    (batch / 'index.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'batch_path':batch.relative_to(ROOT).as_posix(), 'window_hours':hours,
                      'feed_ok':sum(item['status']=='ok' for item in feed_states), 'feed_total':len(feed_states),
                      'articles':len(articles), 'usable':len(usable),
                      'full_text':sum(article['content_level']=='full_text' for article in articles),
                      'summary_only':sum(article['content_level']=='summary_only' for article in articles)}, ensure_ascii=False, indent=2))
    return 0 if usable else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status':'failed', 'error':type(exc).__name__ + ': ' + str(exc)[:220]}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
