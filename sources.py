"""新聞來源設定：官方資料優先（priority=1），媒體新聞作為補充（priority=2）。

每個來源可用兩種方式抓取：
  - "rss"：該網站官方提供的 RSS 網址（可填多個）。連結直接是原文網址、通常附內文，最穩定。
  - 未填 rss：用 Google News RSS 以 site:網域 搜尋（連結是 Google 轉址，內文較難取得）。

"filter": True 表示只保留標題或內文含 MEDIA_KEYWORDS 關鍵字的新聞（用於綜合財經媒體）。
"""

# 媒體新聞只保留與保險／理財相關的主題，避免雜訊
MEDIA_KEYWORDS = [
    "保險", "壽險", "保單", "退休", "長照", "健保", "高齡", "失智", "醫療",
    "利率", "降息", "升息", "Fed", "聯準會", "央行", "匯率", "新台幣",
    "遺產稅", "贈與稅", "所得稅", "稅", "年金", "勞保", "勞退", "信託", "金管會",
]

SOURCES = [
    {"name": "金管會", "use": "保險政策、金融監理", "priority": 1,
     "rss": ["https://www.fsc.gov.tw/RSS/Messages?serno=201202290009&language=chinese"]},
    {"name": "金管會保險局", "use": "保險監理、保戶權益", "priority": 1,
     "rss": ["https://www.ib.gov.tw/RSS/ib/Messages?serno=201306280005&language=chinese"]},
    {"name": "壽險公會", "use": "壽險統計、產業資訊", "priority": 1,
     "domain": "lia-roc.org.tw"},
    {"name": "財政部", "use": "遺產稅、贈與稅、稅務", "priority": 1,
     "rss": ["https://www.mof.gov.tw/Rss/384fb3077bb349ea973e7fc6f13b6974"]},
    {"name": "衛福部", "use": "健保、醫療、長照", "priority": 1,
     "rss": ["https://www.mohw.gov.tw/rss-16-1.html"]},
    {"name": "中央銀行", "use": "利率、匯率、金融政策", "priority": 1,
     "rss": ["https://www.cbc.gov.tw/tw/rss-302-1.xml"]},
    {"name": "中央社", "use": "財經、醫療、政策", "priority": 2, "filter": True,
     "rss": ["https://feeds.feedburner.com/rsscna/finance"]},
    {"name": "工商時報", "use": "財經、保險產業", "priority": 2, "filter": True,
     "domain": "ctee.com.tw"},
    {"name": "經濟日報", "use": "金融、保險產業、理財", "priority": 2, "filter": True,
     "rss": ["https://money.udn.com/rssfeed/news/1001/12017?ch=money"]},
]

# 抓取時間範圍（小時）。官方網站更新頻率較低，給較長的範圍
LOOKBACK_HOURS = {1: 120, 2: 48}

# 每天發布幾則（建議 5～6 則）
NEWS_PER_DAY = 6

# 每個來源最多保留幾則（取最新），避免單一來源塞滿候選清單
PER_SOURCE = 10

# 送給 AI 挑選的候選新聞上限（第一段只送標題，數量可以多一些）
MAX_CANDIDATES = 80

# 內文至少要有幾個字，才算「讀得到原文」
MIN_CONTENT = 200
