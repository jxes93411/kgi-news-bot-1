"""每日流程：抓新聞 → AI 整理六欄位 → 產生網頁（可選：LINE 推播）。

  python main.py              正式執行：產生網頁到 site/
  python main.py --sample     用範例資料產生網頁（不呼叫 AI，測版面用）

若有設定 LINE_CHANNEL_ACCESS_TOKEN，會同時用 LINE OA 推播（之後想升級時再設定即可）。
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from web_page import TPE, build

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("main")

SAMPLE = [
    {
        "title": "（範例）台灣邁入超高齡社會，退休準備成為家庭重要課題",
        "source": "中央社", "date": datetime.now(TPE).strftime("%Y-%m-%d"),
        "link": "https://www.cna.com.tw/", "category": "退休規劃",
        "summary": "這是一則測試用的範例摘要，用來確認網頁版面是否正常顯示。正式執行時，這裡會是 AI 根據原文整理的 100 到 150 字重點，內容只會根據原文，不會額外補充原文沒有的數據，讓業務同仁快速掌握新聞重點。",
        "ai_view": "退休後的收入來源、醫療支出與長照需求值得提前規劃。",
        "extended_needs": ["退休現金流", "年金規劃", "醫療保障", "長照準備"],
    },
    {
        "title": "（範例）央行理監事會決議利率維持不變",
        "source": "中央銀行", "date": datetime.now(TPE).strftime("%Y-%m-%d"),
        "link": "https://www.cbc.gov.tw/", "category": "利率匯率",
        "summary": "第二則範例摘要，示範官方來源新聞在網頁上的呈現方式。正式內容會由 AI 依據央行新聞稿整理利率決策重點與央行對經濟情勢的看法，字數控制在 100 到 150 字之間，方便業務同仁閱讀。",
        "ai_view": "利率環境影響儲蓄型保單與退休金累積的規劃方式，可藉機與客戶檢視資產配置。",
        "extended_needs": ["資產配置", "儲蓄規劃", "外幣資產", "子女教育金"],
    },
]


def today_done() -> bool:
    """今天的資料檔存在，且不是「只列標題」的備案版本。"""
    from pathlib import Path
    f = Path("site/data") / f"{datetime.now(TPE):%Y-%m-%d}.json"
    if not f.exists():
        return False
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return bool(data) and not data[0].get("headline_only")
    except Exception:  # noqa: BLE001
        return False


def headline_only(candidates: list[dict], n: int) -> list[dict]:
    """AI 無法使用時的備案：官方來源優先列出最新標題與原文連結（不含 AI 欄位）。"""
    return [{
        "title": c["title"], "source": c["source"], "date": c["date"], "link": c["link"],
        "category": "今日新聞", "summary": "", "ai_view": "", "extended_needs": [], "headline_only": True,
    } for c in candidates[:n]]


def sample_market() -> dict:
    """範例行情（測試版面用，非真實數據）。"""
    import math
    def s(base, amp, digits, name):
        series = [(f"2026-10-{i+1:02d}", base + amp * math.sin(i / 4) + i * amp / 20) for i in range(30)]
        (_, p), (dt, v) = series[-2], series[-1]
        return {"name": name, "ok": True, "date": dt, "digits": digits, "last": v, "chg": v - p,
                "pct": (v - p) / p * 100, "series": series}
    return {"indices": [s(23000, 300, 2, "台股加權指數"), s(44000, -400, 2, "道瓊工業指數"),
                        s(6000, 60, 2, "S&P 500"), s(19000, 250, 2, "NASDAQ"), {"name": "費城半導體", "ok": False}],
            "fx": [s(32.5, .3, 3, "美元 / 新台幣"), s(.2150, -.002, 4, "日圓 / 新台幣"), s(35.2, .4, 3, "歐元 / 新台幣")]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--skip-if-done", action="store_true",
                    help="今天已經有 AI 整理好的新聞就直接結束（給 7:00、7:30 的補跑使用）")
    args = ap.parse_args()

    if args.skip_if_done and today_done():
        log.info("今天的新聞已由 AI 整理完成，略過這次補跑")
        return 0

    if args.sample:
        news = SAMPLE
    else:
        from ai_curate import select, write
        from fetch_news import enrich, fetch_candidates
        from sources import NEWS_PER_DAY
        candidates = fetch_candidates()
        log.info("候選新聞共 %d 則", len(candidates))
        if not candidates:
            log.error("今天沒有抓到任何新聞，停止產生網頁")
            return 1
        try:
            ranked = select(candidates)
            log.info("AI 挑選並排序 %d 則，開始讀取原文", len(ranked))
            news = write(enrich(ranked, NEWS_PER_DAY))
            log.info("AI 完成 %d 則", len(news))
        except Exception as e:  # noqa: BLE001
            log.error("AI 暫時無法使用，改為只列出新聞標題：%s", str(e)[:300])
            news = []
        if not news:
            news = headline_only(candidates, NEWS_PER_DAY)

    market = None
    if args.sample:
        market = sample_market()
    else:
        try:
            from market import fetch_market
            market = fetch_market()
        except Exception as e:  # noqa: BLE001 — 行情抓不到不影響新聞
            log.warning("市場行情抓取失敗：%s", e)
    url, text = build(news, market)
    log.info("網頁已產生：%s", url)
    print("\n===== 今日分享文字 =====\n" + text + "\n")

    # GitHub Actions 執行摘要頁面也顯示分享文字，方便直接複製
    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## 今日新聞網頁\n{url}\n\n### 分享文字\n```\n{text}\n```\n")

    if os.getenv("LINE_CHANNEL_ACCESS_TOKEN") and not args.sample:
        from line_push import build_messages, send
        send(build_messages(news))
        log.info("LINE 推播完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
