"""用 Google Gemini（免費方案）挑選新聞並產生五欄位內容。

設計重點：標題、來源、日期、連結一律取自原始資料（以 id 對應），
AI 只負責「挑選 + 摘要 + 觀點 + 延伸需求」，確保標題與連結是真的。

環境變數：
  GEMINI_API_KEY   必填，到 https://aistudio.google.com/apikey 免費申請
  GEMINI_MODEL     選填，預設 gemini-flash-latest（永遠指向最新的免費 Flash 模型）
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

MODELS = [m for m in [os.getenv("GEMINI_MODEL"), "gemini-flash-latest", "gemini-2.5-flash"] if m]

SYSTEM = f"""你是凱基人壽北一區域中心的資深保險財經編輯，服務對象是第一線業務同仁。
每天從候選新聞中挑出 {NEWS_PER_DAY} 則最值得業務員了解、可以拿來和客戶聊的新聞，並為每則撰寫內容。
一律使用台灣繁體中文。

挑選原則：
1. 官方來源（金管會、壽險公會、財政部、衛福部、央行）優先，媒體新聞補充。
2. 與保險、退休、醫療、長照、稅務傳承、利率匯率相關性高者優先。
3. 主題盡量多元，不要多則講同一件事。
4. 不挑選單純報導個別保險公司得獎、業績排名的新聞。

撰寫規則：
- summary：100～150 個中文字，只能根據提供的內文，不得補充原文沒有的數字或事實。
- ai_view：這則新聞與保險規劃的關聯，2～3 句。
- extended_needs：3～5 個可延伸討論的保障或財務規劃議題（短詞）。
- category：主題標籤，例如：退休規劃、醫療長照、稅務傳承、利率匯率、金融監理、產業趨勢。

法遵限制（務必遵守）：
- 不得提及特定商品名稱、不得保證收益或報酬率、不得與其他公司比較。
- 不得誇大或製造恐慌，不得引用未經證實的數據。

只輸出 JSON，格式如下，不要有其他文字：
{{"news": [{{"id": 候選新聞的id數字, "category": "", "summary": "", "ai_view": "", "extended_needs": ["", ""]}}]}}
"""

REQUIRED = ("id", "category", "summary", "ai_view", "extended_needs")


def _call(client: genai.Client, prompt: str) -> dict:
    last_err = None
    for model in MODELS:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM,
                        response_mime_type="application/json",
                        temperature=0.4,
                    ),
                )
                text = resp.text or ""
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0) if m else text)
            except Exception as e:  # noqa: BLE001
                last_err = e
                msg = str(e)
                log.warning("Gemini %s 第 %d 次失敗：%s", model, attempt + 1, msg[:200])
                if "404" in msg or "not found" in msg.lower():
                    break  # 模型名稱不存在 → 換下一個模型
                time.sleep(30 if "429" in msg else 5)  # 429 = 免費額度暫時用完，等一下再試
    raise RuntimeError(f"Gemini 呼叫失敗：{last_err}")


def curate(candidates: list[dict]) -> list[dict]:
    payload = [
        {
            "id": c["id"],
            "source": c["source"],
            "date": c["date"],
            "title": c["title"],
            "content": (c["content"] or c["rss_summary"])[:1500],
        }
        for c in candidates
    ]
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    data = _call(client, "以下是今日候選新聞（JSON）：\n" + json.dumps(payload, ensure_ascii=False))

    by_id = {c["id"]: c for c in candidates}
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
            "title": src["title"],
            "source": src["source"],
            "date": src["date"],
            "link": src["link"],
            "category": str(p["category"]),
            "summary": str(p["summary"]),
            "ai_view": str(p["ai_view"]),
            "extended_needs": needs if isinstance(needs, list) else [str(needs)],
        })
    return result[:NEWS_PER_DAY]
