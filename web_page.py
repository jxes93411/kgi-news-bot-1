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


def _article(i: int, n: dict) -> str:
    link = (f' ｜<a href="{E(n["link"])}" target="_blank" rel="noopener">閱讀原文 ↗</a>'
            if n["link"].startswith("http") else "")
    chips = "".join(f"<span>{E(x)}</span>" for x in n["extended_needs"])
    note = ('<p class="note">※ 系統未能讀取原文內容，摘要僅依標題整理，詳細內容請點「閱讀原文」。</p>'
            if n.get("no_content") else "")
    return f"""
<article id="n{i}">
  <span class="tag">NEWS {i}｜{E(n['category'])}</span>
  <h2>{E(n['title'])}</h2>
  <div class="src">📌 {E(n['source'])}｜{E(n['date'])}{link}</div>
  <div class="f"><h3>📰 新聞摘要</h3><p>{E(n['summary'])}</p>{note}</div>
  <div class="f"><h3>💡 AI 保險觀點</h3><p>{E(n['ai_view'])}</p></div>
  <div class="f"><h3>🎯 延伸需求</h3><div class="chips">{chips}</div></div>
</article>"""


def _page(news: list[dict], d: datetime, url: str, archive: list[str]) -> str:
    toc = "".join(f'<a href="#n{i}"><b>{i}</b>{E(n["title"])}</a>' for i, n in enumerate(news, 1))
    arts = "".join(_article(i, n) for i, n in enumerate(news, 1))
    hist = "｜".join(f'<a href="{a}.html">{a[5:].replace("-", "/")}</a>' for a in archive[:14])
    desc = "、".join(n["title"] for n in news[:3])[:90]
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>今日保險財經新聞 {_date_label(d)}｜{BRAND}</title>
<meta property="og:title" content="今日保險財經新聞 {_date_label(d)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:type" content="article"><meta property="og:url" content="{E(url)}">
<meta name="robots" content="noindex">
<style>{CSS}</style></head><body>
<header><div class="brand">{BRAND}</div><h1>今日保險財經新聞</h1><div class="date">{_date_label(d)}</div></header>
<main>
  <nav class="toc">{toc}</nav>
  {arts}
</main>
<footer>※ 本內容由 AI 整理，僅供內部同仁參考。轉傳客戶前請再確認原文，並遵循公司法遵規範。
<br><br>歷史新聞：{hist}</footer>
<script>{JS}</script></body></html>"""


def build(news: list[dict]) -> tuple[str, str]:
    """產生網頁，回傳（當日網址, 分享文字）。"""
    d = datetime.now(TPE)
    day = d.strftime("%Y-%m-%d")
    base = os.getenv("SITE_URL", "").rstrip("/")
    url = f"{base}/{day}.html" if base else f"{day}.html"

    SITE.mkdir(exist_ok=True)
    (SITE / "data").mkdir(exist_ok=True)
    (SITE / "data" / f"{day}.json").write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = sorted({p.stem for p in (SITE / "data").glob("*.json")}, reverse=True)

    page = _page(news, d, url, archive)
    (SITE / f"{day}.html").write_text(page, encoding="utf-8")
    (SITE / "index.html").write_text(page, encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    st = share_text(news, url, d)
    (SITE / "share.txt").write_text(st, encoding="utf-8")
    return url, st
