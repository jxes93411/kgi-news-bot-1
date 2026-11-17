"""產生每日新聞網頁（手機優先），輸出到 site/ 資料夾。

  site/2026-11-17.html   當日新聞頁（分享這個連結）
  site/index.html        永遠顯示最新一天 + 歷史清單

環境變數：
  SITE_URL   網站根網址，例如 https://你的帳號.github.io/kgi-news-bot/
"""
import html
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
BRAND = "凱基人壽｜北一區域中心"
SITE = Path("site")
E = html.escape


def _date_label(d: datetime) -> str:
    return f"{d:%Y/%m/%d}（{'一二三四五六日'[d.weekday()]}）"


def share_text(news: list[dict], url: str, d: datetime) -> str:
    lines = "\n".join(f"{i}. {n['title']}" for i, n in enumerate(news, 1))
    return (f"☀️ 早安！{BRAND}\n今日保險財經新聞 {_date_label(d)}\n\n{lines}\n\n"
            f"👉 完整摘要與保險觀點：\n{url}")


CSS = """
:root{--main:#003B7A;--light:#E8F0FA;--bg:#F2F6FB;--card:#fff;--ink:#1E2A3A;--sub:#5F6F82;--line:#E3EAF3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:-apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;line-height:1.7}
header{background:linear-gradient(135deg,#002A5C,#00478F);color:#fff;padding:22px 18px 18px}
header .brand{font-size:13px;opacity:.85;letter-spacing:.05em}
header h1{margin:4px 0 2px;font-size:22px}header .date{font-size:14px;opacity:.9}
main{max-width:680px;margin:0 auto;padding:14px}
.toc{background:var(--card);border-radius:12px;padding:12px 16px;margin-bottom:14px}
.toc a{display:block;color:var(--ink);text-decoration:none;padding:6px 0;border-bottom:1px solid var(--line);font-size:15px}
.toc a:last-child{border:0}.toc b{color:var(--main);margin-right:6px}
article{background:var(--card);border-radius:14px;padding:18px 16px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,59,122,.08)}
.tag{display:inline-block;background:var(--light);color:var(--main);font-size:12px;font-weight:700;padding:2px 10px;border-radius:99px}
article h2{font-size:18px;margin:8px 0 6px;line-height:1.5}
.src{font-size:13px;color:var(--sub)}.src a{color:var(--main)}
.f{margin-top:14px}.f h3{font-size:13px;color:var(--main);margin:0 0 4px}
.f p{margin:0;font-size:15px}
.f p.note{margin-top:6px;font-size:12px;color:var(--sub)}
.script{background:var(--light);border-left:4px solid var(--main);padding:10px 12px;border-radius:6px;font-size:15px}
.chips span{display:inline-block;background:#fff;border:1px solid #C9D8EC;color:var(--main);font-size:13px;padding:3px 10px;border-radius:99px;margin:3px 4px 0 0}
button{border:0;background:var(--main);color:#fff;font-size:14px;font-weight:700;padding:9px 14px;border-radius:8px;margin-top:8px;cursor:pointer}
button.ghost{background:#fff;color:var(--main);border:1px solid var(--main)}
.mk{background:var(--card);border-radius:14px;padding:14px 14px 10px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,59,122,.08)}
.mk h2{font-size:15px;margin:0 0 2px;color:var(--main)}.mk .sub{font-size:12px;color:var(--sub);margin-bottom:10px}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
@media(min-width:620px){.tiles{grid-template-columns:repeat(5,1fr)}}
.tile{background:var(--bg);border-radius:10px;padding:9px 10px}
.tile .n{font-size:12px;color:var(--sub)}.tile .v{font-size:17px;font-weight:700;font-variant-numeric:tabular-nums}
.up{color:#C62828}.down{color:#2E7D32}.flat{color:var(--sub)}
.chg{font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}
.tile .chg{display:block;line-height:1.5}
.fx{display:grid;grid-template-columns:1fr auto;align-items:center;gap:4px 10px;padding:9px 0;border-top:1px solid var(--line)}
.fx:first-of-type{border-top:0}
.fx .n{font-size:13px;color:var(--sub)}.fx .v{font-size:17px;font-weight:700;font-variant-numeric:tabular-nums}
.fx svg{display:block;overflow:visible}.fx .cap{font-size:11px;color:var(--sub);text-align:right}
.na{color:var(--sub);font-size:13px}
footer{font-size:12px;color:var(--sub);text-align:center;padding:10px 18px 30px}
footer a{color:var(--sub)}
"""

JS = """
function copyText(t,btn){const done=()=>{const o=btn.textContent;btn.textContent='✓ 已複製';setTimeout(()=>btn.textContent=o,1500)};
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done,()=>fb(t,done))}else fb(t,done)}
function fb(t,done){const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';
document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){alert('請長按文字手動複製')}a.remove()}
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>copyText(b.dataset.copy,b));
"""


def _chg(m: dict, two_lines: bool = False) -> str:
    cls, arrow = ("up", "▲") if m["chg"] > 0 else ("down", "▼") if m["chg"] < 0 else ("flat", "－")
    d = m["digits"]
    sep = "<br>" if two_lines else ""
    return f'<span class="chg {cls}">{arrow} {abs(m["chg"]):,.{d}f}{sep}（{abs(m["pct"]):.2f}%）</span>'


def _spark(m: dict, w: int = 132, h: int = 38) -> str:
    """單一序列走勢小圖：2px 線、終點圓點、每個點可滑鼠／手指查看日期與數值。"""
    pts = m["series"]
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    xy = [(i * (w - 8) / max(1, len(pts) - 1) + 4, h - 4 - (v - lo) / span * (h - 8)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    d = m["digits"]
    hits = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="transparent"><title>{dt}　{v:,.{d}f}</title></circle>'
                   for (x, y), (dt, v) in zip(xy, pts))
    ex, ey = xy[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{E(m["name"])} 近 {len(pts)} 個交易日走勢，'
            f'最低 {lo:.{d}f}、最高 {hi:.{d}f}">'
            f'<polyline points="{line}" fill="none" stroke="#003B7A" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="#003B7A" stroke="#fff" stroke-width="2"/>{hits}</svg>')


def _market(mk: dict | None) -> str:
    if not mk:
        return ""
    tiles = ""
    for m in mk["indices"]:
        body = (f'<div class="v">{m["last"]:,.2f}</div>{_chg(m, True)}' if m["ok"] else '<div class="na">暫無資料</div>')
        tiles += f'<div class="tile"><div class="n">{E(m["name"])}</div>{body}</div>'
    fx = ""
    for m in mk["fx"]:
        if not m["ok"]:
            fx += f'<div class="fx"><div class="n">{E(m["name"])}</div><div class="na">暫無資料</div></div>'
            continue
        d = m["digits"]
        fx += (f'<div class="fx"><div><div class="n">{E(m["name"])}</div><div class="v">{m["last"]:.{d}f}</div>{_chg(m)}</div>'
               f'<div>{_spark(m)}<div class="cap">近 {len(m["series"])} 個交易日</div></div></div>')
    dates = sorted({m["date"] for m in mk["indices"] + mk["fx"] if m["ok"]})
    when = f"資料日期 {dates[0]}～{dates[-1]}" if len(dates) > 1 else (f"資料日期 {dates[0]}" if dates else "")
    return f"""
  <section class="mk"><h2>📈 股市指數</h2><div class="sub">前一交易日收盤｜{when}</div><div class="tiles">{tiles}</div></section>
  <section class="mk"><h2>💱 匯率走勢</h2><div class="sub">每 1 單位外幣可兌換新台幣｜資料來源：Yahoo Finance</div>{fx}</section>"""


def _article(i: int, n: dict) -> str:
    link = (f' ｜<a href="{E(n["link"])}" target="_blank" rel="noopener">閱讀原文 ↗</a>'
            if n["link"].startswith("http") else "")
    head = f"""
<article id="n{i}">
  <span class="tag">NEWS {i}｜{E(n['category'])}</span>
  <h2>{E(n['title'])}</h2>
  <div class="src">📌 {E(n['source'])}｜{E(n['date'])}{link}</div>"""
    if n.get("headline_only"):
        return head + "\n</article>"
    chips = "".join(f"<span>{E(x)}</span>" for x in n["extended_needs"])
    note = ('<p class="note">※ 系統未能讀取原文內容，摘要僅依標題整理，詳細內容請點「閱讀原文」。</p>'
            if n.get("no_content") else "")
    return head + f"""
  <div class="f"><h3>📰 新聞摘要</h3><p>{E(n['summary'])}</p>{note}</div>
  <div class="f"><h3>💡 AI 保險觀點</h3><p>{E(n['ai_view'])}</p></div>
  <div class="f"><h3>🎯 延伸需求</h3><div class="chips">{chips}</div></div>
</article>"""


def _page(news: list[dict], d: datetime, url: str, archive: list[str], mk: dict | None = None) -> str:
    toc = "".join(f'<a href="#n{i}"><b>{i}</b>{E(n["title"])}</a>' for i, n in enumerate(news, 1))
    arts = "".join(_article(i, n) for i, n in enumerate(news, 1))
    hist = "｜".join(f'<a href="{a}.html">{a[5:].replace("-", "/")}</a>' for a in archive[:14])
    desc = "、".join(n["title"] for n in news[:3])[:90]
    notice = ('<div class="mk na">⚠️ AI 整理服務今天暫時無法使用，以下先列出最新新聞標題與原文連結。</div>'
              if news and news[0].get("headline_only") else "")
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>北一保險財經新聞 {_date_label(d)}｜{BRAND}</title>
<meta property="og:title" content="北一保險財經新聞 {_date_label(d)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:type" content="article"><meta property="og:url" content="{E(url)}">
<meta name="robots" content="noindex">
<style>{CSS}</style></head><body>
<header><div class="brand">{BRAND}</div><h1>今日保險財經新聞</h1><div class="date">{_date_label(d)}</div></header>
<main>
  {_market(mk)}
  {notice}
  <nav class="toc">{toc}</nav>
  {arts}
</main>
<footer>※ 本內容由 AI 整理，僅供內部同仁參考。轉傳客戶前請再確認原文，並遵循公司法遵規範。
<br><br>歷史新聞：{hist}</footer>
<script>{JS}</script></body></html>"""


def build(news: list[dict], market: dict | None = None) -> tuple[str, str]:
    """產生網頁，回傳（當日網址, 分享文字）。"""
    d = datetime.now(TPE)
    day = d.strftime("%Y-%m-%d")
    base = os.getenv("SITE_URL", "").rstrip("/")
    url = f"{base}/{day}.html" if base else f"{day}.html"

    SITE.mkdir(exist_ok=True)
    (SITE / "data").mkdir(exist_ok=True)
    (SITE / "data" / f"{day}.json").write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = sorted({p.stem for p in (SITE / "data").glob("*.json")}, reverse=True)

    page = _page(news, d, url, archive, market)
    (SITE / f"{day}.html").write_text(page, encoding="utf-8")
    (SITE / "index.html").write_text(page, encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    st = share_text(news, url, d)
    (SITE / "share.txt").write_text(st, encoding="utf-8")
    return url, st
