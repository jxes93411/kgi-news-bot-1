"""用 Google Gemini（免費方案）挑選新聞並產生五欄位內容。

流程分兩段（減少對 Google News 的請求次數）：
  1. select()：AI 只看標題，從候選新聞挑出 N 則
  2. write()  ：抓回這 N 則的原文內文後，AI 撰寫摘要／觀點／延伸需求

標題、來源、日期、連結一律取自原始資料（以 id 對應），AI 不能改寫，確保新聞是真的。

環境變數：
  GEMINI_API_KEY   必填，到 https://aistudio.google.com/apikey 免費申請
  GEMINI_MODEL     選填，指定模型；不填會自動選用目前可用的最新 Flash 模型
"""
import json
import logging
import os
import re
import time

from google import genai
from google.genai import types

from sources import NEWS_PER_DAY

log = logging.getLogger(__name__)

PREFERRED = [os.getenv("GEMINI_MODEL"), "gemini-3.8-flash", "gemini-flash-latest"]
_SKIP = ("lite", "image", "tts", "audio", "live", "embedding", "thinking", "exp", "computer")

ROLE = """你是凱基人壽北一區域中心的資深保險財經編輯，服務對象是第一線業務同仁。一律使用台灣繁體中文。"""

SELECT_RULES = f"""從候選新聞中挑出 {NEWS_PER_DAY * 2} 則最值得業務員了解、可以拿來和客戶聊的新聞，依重要性由高到低排序（前 {NEWS_PER_DAY} 則是首選，其餘是備選）。
挑選原則：
1. 官方來源（金管會、保險局、壽險公會、財政部、衛福部、央行）優先，媒體新聞補充。
2. 與保險、退休、醫療、長照、稅務傳承、利率匯率相關性高者優先。
3. 主題盡量多元，不要多則講同一件事。
4. 不挑選單純報導個別保險公司得獎、業績排名、人事異動、每日例行公告、標案或徵才的新聞。
只輸出 JSON：{{"ids": [候選新聞的id數字, ...]}}"""

WRITE_RULES = """為每則新聞撰寫內容。
- summary：100～150 個中文字，只能根據提供的 content，不得補充 content 沒有的數字、事實或評論。
  若該則標示 no_content=true（讀不到原文），summary 只能改寫標題本身能確定的事實，寫 30～60 字即可，嚴禁推測或補充細節。
- ai_view：這則新聞與保險規劃的關聯，2～3 句。
- extended_needs：3～5 個可延伸討論的保障或財務規劃議題（短詞）。
- category：主題標籤，例如：退休規劃、醫療長照、稅務傳承、利率匯率、金融監理、產業趨勢。
法遵限制（務必遵守）：不得提及特定商品名稱、不得保證收益或報酬率、不得與其他公司比較、不得誇大或製造恐慌。
只輸出 JSON：{"news": [{"id": 數字, "category": "", "summary": "", "ai_view": "", "extended_needs": ["", ""]}]}"""

REQUIRED = ("id", "category", "summary", "ai_view", "extended_needs")
_client = None
_models = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        # 每次呼叫最多等 90 秒，避免 Google 沒回應時整個流程卡住
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                               http_options=types.HttpOptions(timeout=90_000))
    return _client


def _version(name: str) -> tuple:
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return (float(m.group(1)) if m else 0.0, "preview" not in name)


def _candidate_models() -> list[str]:
    """偏好清單 + 自動查詢帳號目前可用的 Flash 模型（新到舊）。"""
    global _models
    if _models is not None:
        return _models
    found = []
    try:
        for m in _get_client().models.list():
            name = m.name.split("/")[-1]
            actions = getattr(m, "supported_actions", None) or []
            if "flash" in name and not any(s in name for s in _SKIP) and \
               (not actions or "generateContent" in actions):
                found.append(name)
        found.sort(key=_version, reverse=True)
        log.info("可用的 Flash 模型：%s", found[:5])
    except Exception as e:  # noqa: BLE001
        log.warning("查詢模型清單失敗：%s", str(e)[:200])
    _models = list(dict.fromkeys([p for p in PREFERRED if p] + found))
    return _models


def _generate(model: str, system: str, prompt: str, limit: int = 120) -> str:
    """呼叫 Gemini；用背景執行緒再加一道 120 秒保險，確保絕不會無限等待。"""
    import threading
    box: dict = {}

    def run():
        try:
            resp = _get_client().models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )
            box["text"] = resp.text or ""
        except Exception as e:  # noqa: BLE001
            box["err"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=limit)
    if "err" in box:
        raise box["err"]
    if "text" not in box:
        raise TimeoutError(f"超過 {limit} 秒沒有回應")
    return box["text"]


def _call(system: str, prompt: str) -> dict:
    """依序嘗試可用模型。
    404（模型停用）→ 直接換下一個；503／逾時（使用量太大）→ 重試 1 次後換下一個；
    429（免費額度暫時用完）→ 等 30 秒重試。"""
    last_err = None
    started = time.time()
    for model in _candidate_models():
        for attempt in range(2):
            if time.time() - started > 8 * 60:
                raise RuntimeError(f"Gemini 嘗試超過 8 分鐘仍失敗：{last_err}")
            try:
                text = _generate(model, system, prompt)
                m = re.search(r"\{.*\}", text, re.S)
                data = json.loads(m.group(0) if m else text)
                log.info("使用模型：%s", model)
                return data
            except Exception as e:  # noqa: BLE001
                last_err = e
                msg = str(e)
                log.warning("Gemini %s 第 %d 次失敗：%s", model, attempt + 1, msg[:200])
                if "404" in msg or "NOT_FOUND" in msg or "not found" in msg.lower():
                    break
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    time.sleep(30)
                else:
                    time.sleep(5)
    raise RuntimeError(f"Gemini 呼叫失敗：{last_err}")


def select(candidates: list[dict]) -> list[dict]:
    """第一段：只看標題挑新聞。"""
    payload = [{"id": c["id"], "source": c["source"], "date": c["date"],
                "title": c["title"], "note": c["rss_summary"][:120]} for c in candidates]
    data = _call(ROLE + "\n" + SELECT_RULES,
                 "候選新聞（JSON）：\n" + json.dumps(payload, ensure_ascii=False))
    by_id = {c["id"]: c for c in candidates}
    picked = []
    for i in data.get("ids", []):
        try:
            c = by_id.get(int(i))
        except (TypeError, ValueError):
            continue
        if c and c not in picked:
            picked.append(c)
    return picked[:NEWS_PER_DAY * 2]


def write(items: list[dict]) -> list[dict]:
    """第二段：根據原文內文撰寫五欄位。"""
    payload = []
    for c in items:
        row = {"id": c["id"], "source": c["source"], "date": c["date"], "title": c["title"]}
        if c.get("no_content"):
            row["no_content"] = True
        else:
            row["content"] = c["content"][:2500]
        payload.append(row)
    data = _call(ROLE + "\n" + WRITE_RULES,
                 "今日精選新聞（JSON）：\n" + json.dumps(payload, ensure_ascii=False))

    by_id = {c["id"]: c for c in items}
    result, used = [], set()
    for p in data.get("news", []):
        try:
            pid = int(p.get("id"))
        except (TypeError, ValueError):
            continue
        src = by_id.get(pid)
        # 不存在的 id、重複、欄位不齊 → 丟掉，避免捏造或殘缺的新聞
        if not src or pid in used or not all(p.get(k) for k in REQUIRED):
            continue
        used.add(pid)
        needs = p["extended_needs"]
        result.append({
            "title": src["title"], "source": src["source"], "date": src["date"], "link": src["link"],
            "category": str(p["category"]), "summary": str(p["summary"]), "ai_view": str(p["ai_view"]),
            "extended_needs": needs if isinstance(needs, list) else [str(needs)],
            "no_content": bool(src.get("no_content")),
        })
    return result
