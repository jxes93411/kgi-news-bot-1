"""抓取股市指數與匯率（資料來源：Yahoo Finance，透過 yfinance 套件）。

資料與 tw.stock.yahoo.com 網頁顯示的是同一份 Yahoo 資料，
但用 yfinance 讀取比直接解析網頁穩定（網頁改版不會壞）。
任何一項抓不到都不影響新聞網頁產生，該項會顯示「暫無資料」。
"""
import logging
import time

log = logging.getLogger(__name__)

INDICES = [
    ("台股加權指數", "^TWII"),
    ("道瓊工業指數", "^DJI"),
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
    ("費城半導體", "^SOX"),
]

# (顯示名稱, Yahoo 代號, 備用代號（取倒數）, 小數位數)
FX = [
    ("美元 / 新台幣", "TWD=X", "TWDUSD=X", 3),
    ("日圓 / 新台幣", "JPYTWD=X", "TWDJPY=X", 4),
    ("歐元 / 新台幣", "EURTWD=X", "TWDEUR=X", 3),
]


def _history(symbol: str, period: str = "3mo") -> list[tuple[str, float]]:
    """回傳 [(日期, 收盤價), ...]，由舊到新。"""
    import yfinance as yf
    for attempt in range(3):
        try:
            df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
            df = df.dropna(subset=["Close"])
            if len(df):
                return [(idx.strftime("%Y-%m-%d"), float(v)) for idx, v in df["Close"].items()]
        except Exception as e:  # noqa: BLE001
            log.info("%s 第 %d 次讀取失敗：%s", symbol, attempt + 1, str(e)[:120])
        time.sleep(3 * (attempt + 1))
    return []


def _summary(name: str, series: list[tuple[str, float]], digits: int) -> dict:
    if len(series) < 2:
        return {"name": name, "ok": False}
    (_, prev), (date, last) = series[-2], series[-1]
    chg = last - prev
    return {
        "name": name, "ok": True, "date": date, "digits": digits,
        "last": last, "chg": chg, "pct": chg / prev * 100 if prev else 0.0,
        "series": series[-30:],  # 走勢圖用最近 30 個交易日
    }


def fetch_market() -> dict:
    indices = []
    for name, sym in INDICES:
        s = _history(sym, "1mo")
        indices.append(_summary(name, s, 2))
        log.info("[%s] %s", name, f"{s[-1][1]:,.2f}（{s[-1][0]}）" if s else "暫無資料")

    fx = []
    for name, sym, alt, digits in FX:
        s = _history(sym)
        if not s:  # 主要代號抓不到 → 用反向匯率取倒數
            s = [(d, 1 / v) for d, v in _history(alt) if v]
        fx.append(_summary(name, s, digits))
        log.info("[%s] %s", name, f"{s[-1][1]:.4f}（{s[-1][0]}）" if s else "暫無資料")

    return {"indices": indices, "fx": fx}
