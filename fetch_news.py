"""抓取新聞候選清單，並為入選新聞補上原文內文。"""
import calendar
import html
import logging
import re
import time
from urllib.parse import quote

import feedparser
import requests

from sources import (LOOKBACK_HOURS, MAX_CANDIDATES, MEDIA_KEYWORDS, MIN_CONTENT,
                     PER_SOURCE, SOURCES)

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (KGI-North1-NewsBot)"}


def _google_news_rss(domain: str, hours: int, keywords: list[str] | None) -> str:
    days = max(1, round(hours / 24))
    kw = f"({' OR '.join(keywords)})" if keywords else ""
    q = f"site:{domain} {kw} when:{days}d".replace("  ", " ")
    return f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"


def _plain(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _entry_text(e) -> str:
    """RSS 項目附帶的內文（官方 RSS 通常是全文）。"""
    parts = [c.get("value", "") for c in e.get("content", [])] or [e.get("summary", "")]
    return _plain(" ".join(parts))


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
            log.info("Google 連結還原失敗：%s", str(r.get("message"))[:120])
        except Exception as e:  # noqa: BLE001
            log.info("Google 連結還原錯誤：%s", str(e)[:120])
        time.sleep(5 * (attempt + 1))
    return link


def _fetch_text(url: str, limit: int = 3000) -> str:
    """抓原文網頁內文；抓不到就回傳空字串。"""
    if "news.google.com" in url:
        return ""
    try:
        import trafilatura
        page = requests.get(url, headers=UA, timeout=20)
        page.encoding = page.apparent_encoding or page.encoding
        text = trafilatura.extract(page.text, include_comments=False) or ""
        return text[:limit]
    except Exception as e:  # noqa: BLE001
        log.info("內文抓取失敗 %s：%s", url[:80], str(e)[:120])
        return ""


def _match_keywords(text: str) -> bool:
    return any(k.lower() in text.lower() for k in MEDIA_KEYWORDS)


def fetch_candidates() -> list[dict]:
    now = time.time()
    items, seen = [], set()

    for src in SOURCES:
        hours = LOOKBACK_HOURS[src["priority"]]
        kw = MEDIA_KEYWORDS[:12] if src.get("filter") else None
        urls = src.get("rss") or [_google_news_rss(src["domain"], hours, kw)]
        mine = []
        for url in urls:
            try:
                resp = requests.get(url, headers=UA, timeout=30)
                feed = feedparser.parse(resp.content)
            except Exception as e:  # noqa: BLE001
                log.warning("[%s] RSS 抓取失敗：%s", src["name"], e)
                continue
            for e in feed.entries:
                ts = e.get("published_parsed") or e.get("updated_parsed")
                if not ts:
                    continue
                epoch = calendar.timegm(ts)
                if now - epoch > hours * 3600:
                    continue
                title = _plain(e.get("title", ""))
                if "news.google.com" in url:  # Google News 會在標題後加「 - 媒體名稱」
                    title = re.sub(r"\s+-\s+[^-]{1,30}$", "", title).strip()
                body = _entry_text(e)
                if src.get("filter") and not _match_keywords(title + body[:300]):
                    continue
                key = re.sub(r"\W", "", title)[:40]
                # 過濾雜訊：檔名（.pdf 等）、過短的標題
                if re.search(r"\.(pdf|docx?|xlsx?|odt)\b", title, re.I) or len(key) < 8:
                    continue
                if not title or key in seen:
                    continue
                seen.add(key)
                mine.append({
                    "source": src["name"],
                    "priority": src["priority"],
                    "title": title,
                    "date": time.strftime("%Y-%m-%d", time.gmtime(epoch + 8 * 3600)),  # 台灣時間
                    "epoch": epoch,
                    "link": e.get("link", ""),
                    "rss_summary": body[:300],
                    "content": body[:3000] if len(body) >= MIN_CONTENT else "",
                })
        mine.sort(key=lambda x: -x["epoch"])
        items.extend(mine[:PER_SOURCE])
        log.info("[%s] 符合條件 %d 則，保留 %d 則", src["name"], len(mine), min(len(mine), PER_SOURCE))

    # 官方優先、再依時間新舊排序
    items.sort(key=lambda x: (x["priority"], -x["epoch"]))
    items = items[:MAX_CANDIDATES]
    for i, it in enumerate(items):
        it["id"] = i
    return items


def enrich(ranked: list[dict], need: int) -> list[dict]:
    """依 AI 排序，逐則補上原文網址與內文，湊滿 need 則「讀得到原文」的新聞。
    讀不到原文的新聞只有在不夠時才補上，並標記 no_content。"""
    good, weak = [], []
    for it in ranked:
        if len(good) >= need:
            break
        if not it.get("content"):
            it["link"] = _resolve_link(it["link"])
            it["content"] = _fetch_text(it["link"])
            time.sleep(2)
        ok = len(it["content"]) >= MIN_CONTENT
        log.info("%s 內文 %d 字：%s", "✓" if ok else "✗", len(it["content"]), it["title"][:30])
        (good if ok else weak).append(it)
    for it in weak:
        it["no_content"] = True
    picked = (good + weak)[:need]
    picked.sort(key=lambda x: ranked.index(x))
    return picked
