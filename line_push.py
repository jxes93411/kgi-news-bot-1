"""把整理好的新聞做成 LINE Flex 輪播並推播。

環境變數：
  LINE_CHANNEL_ACCESS_TOKEN  必填，LINE OA 的 Channel access token
  LINE_TO                    選填，逗號分隔的 userId / groupId；留空 = 推播給所有好友（broadcast）
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import requests

TPE = timezone(timedelta(hours=8))
BRAND = "凱基人壽｜北一區域中心"
API = "https://api.line.me/v2/bot/message"

C_MAIN = "#003B7A"   # 主色（可依公司 CI 調整）
C_GRAY = "#666666"


def _section(label: str, text: str, color: str = "#333333") -> list[dict]:
    return [
        {"type": "text", "text": label, "size": "xs", "weight": "bold", "color": C_MAIN, "margin": "lg"},
        {"type": "text", "text": text or "－", "size": "sm", "wrap": True, "color": color, "margin": "xs"},
    ]


def _bubble(n: int, item: dict) -> dict:
    footer = []
    if item["link"].startswith("http"):
        footer.append({"type": "button", "style": "secondary", "height": "sm",
                       "action": {"type": "uri", "label": "閱讀原文", "uri": item["link"]}})
    bubble = {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": C_MAIN, "paddingAll": "md",
            "contents": [{"type": "text", "text": f"NEWS {n}｜{item['category']}",
                          "color": "#FFFFFF", "size": "sm", "weight": "bold"}],
        },
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": item["title"], "weight": "bold", "size": "md", "wrap": True},
                *_section("📰 新聞摘要", item["summary"]),
                *_section("📌 新聞來源", f"{item['source']}｜{item['date']}", C_GRAY),
                *_section("💡 AI 保險觀點", item["ai_view"]),
                *_section("🎯 延伸需求", "、".join(item["extended_needs"])),
            ],
        },
    }
    if footer:
        bubble["footer"] = {"type": "box", "layout": "vertical", "spacing": "sm", "contents": footer}
    return bubble


def build_messages(news: list[dict]) -> list[dict]:
    today = datetime.now(TPE)
    date_str = f"{today:%m/%d}（{'一二三四五六日'[today.weekday()]}）"
    headline = "\n".join(f"{i}. {n['title']}" for i, n in enumerate(news, 1))
    return [
        {"type": "text",
         "text": f"☀️ 早安！{BRAND}\n今日保險財經新聞 {date_str}\n\n{headline}\n\n👉 左右滑動看完整內容"},
        {"type": "flex", "altText": f"今日保險財經新聞 {date_str}",
         "contents": {"type": "carousel", "contents": [_bubble(i, n) for i, n in enumerate(news, 1)]}},
        {"type": "text",
         "text": "※ 本內容由 AI 整理，僅供內部同仁參考。轉傳客戶前請再確認原文，並遵循公司法遵規範。"},
    ]


def send(messages: list[dict]) -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    targets = [t.strip() for t in os.getenv("LINE_TO", "").split(",") if t.strip()]

    jobs = [("broadcast", {"messages": messages})] if not targets else \
           [("push", {"to": t, "messages": messages}) for t in targets]
    for endpoint, body in jobs:
        # X-Line-Retry-Key：重試時不會重複發送
        r = requests.post(f"{API}/{endpoint}", json=body, timeout=30,
                          headers={**headers, "X-Line-Retry-Key": str(uuid.uuid4())})
        if r.status_code != 200:
            raise RuntimeError(f"LINE {endpoint} 失敗 {r.status_code}: {r.text}")
