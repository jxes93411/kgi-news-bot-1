"""抓取新聞候選清單。"""
import calendar
import logging
import re
import time
from urllib.parse import quote

import feedparser
import requests

from sources import LOOKBACK_HOURS, MAX_CANDIDATES, PER_SOURCE, SOURCES

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (KGI-North1-NewsBot)"}


def _google_news_rss(domain: str, keywords: str, hours: int) -> str:
    days = max(1, round(hours / 24))
    q = f"site:{domain} {('(' + keywords + ')') if keywords else ''} when:{days}d".strip()
    return f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"


def _clean_title(title: str, source_name: str) -> str:
    # Google News 會在標題後加「 - 媒體名稱」
    title = re.sub(r"\s+-\s+[^-]{1,30}$", "", title).strip()
    return title


def _resolve_link(link: str) -> str:
    """把 Google News 轉址連結還原成原文網址（失敗時保留原連結，點擊仍會轉到原文）。"""
    if "news.google.com" not in link:
        return link
    from googlenewsdecoder import gnewsdecoder
    for attempt in range(3):
        try:
            r = gnewsdecoder(link, interval=1)
            if r.get("status"):
                return r["decoded_url"]
            log.debug("decode status false: %s", r.get("message"))
        except Exception as e:  # noqa: BLE001
            log.debug("decode failed: %s", e)
        time.sleep(5 * (attempt + 1))  # 被 Google 限流（429）時多等一下
    return link


def _fetch_text(url: str, limit: int = 2500) -> str:
    """抓原文內文，給 AI 寫摘要用；抓不到就回傳空字串（AI 改用 RSS 摘要）。"""
    if "news.google.com" in url:
        return ""
    try:
        import trafilatura
        html = requests.get(url, headers=UA, timeout=15).text
        text = trafilatura.extract(html, include_comments=False) or ""
        return text[:limit]
    except Exception as e:  # noqa: BLE001
        log.debug("fetch text failed %s: %s", url, e)
        return ""


def fetch_candidates() -> list[dict]:
    now = time.time()
    items, seen = [], set()
    src_start = 0

    for src in SOURCES:
        hours = LOOKBACK_HOURS[src["priority"]]
        url = src.get("rss") or _google_news_rss(src["domain"], src["keywords"], hours)
        try:
            feed = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
        except Exception as e:  # noqa: BLE001
            log.warning("[%s] RSS 抓取失敗：%s", src["name"], e)
            continue

        count = 0
        for e in feed.entries:
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if not ts:
                continue
            epoch = calendar.timegm(ts)
            if now - epoch > hours * 3600:
                continue
            title = _clean_title(e.get("title", ""), src["name"])
            key = re.sub(r"\W", "", title)[:40]
            if not title or key in seen:
                continue
            seen.add(key)
            desc = re.sub("<[^>]+>", "", e.get("summary", ""))[:300]
            items.append({
                "source": src["name"],
                "source_use": src["use"],
                "priority": src["priority"],
                "title": title,
                "date": time.strftime("%Y-%m-%d", time.gmtime(epoch + 8 * 3600)),  # 台灣時間
                "epoch": epoch,
                "link": e.get("link", ""),
                "rss_summary": desc,
            })
            count += 1
        # 每個來源只留最新的 PER_SOURCE 則，避免單一來源塞滿候選清單
        mine = sorted(items[src_start:], key=lambda x: -x["epoch"])[:PER_SOURCE]
        items[src_start:] = mine
        src_start = len(items)
        log.info("[%s] 取得 %d 則，保留 %d 則", src["name"], count, len(mine))

    # 官方優先、再依時間新舊排序
    items.sort(key=lambda x: (x["priority"], -x["epoch"]))
    items = items[:MAX_CANDIDATES]
    for i, it in enumerate(items):
        it["id"] = i
    return items


def enrich(items: list[dict]) -> list[dict]:
    """只針對 AI 挑中的新聞：還原原文網址並抓內文（請求數少，不易被 Google 限流）。"""
    for it in items:
        it["link"] = _resolve_link(it["link"])
        it["content"] = _fetch_text(it["link"])
        log.info("內文 %d 字：%s", len(it["content"]), it["title"][:30])
        time.sleep(2)
    return items
