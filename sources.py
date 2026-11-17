"""新聞來源設定：官方資料優先（priority=1），媒體新聞作為補充（priority=2）。

每個來源可用兩種方式抓取：
  - "rss"：直接填入該網站提供的 RSS 網址（最穩定，有就優先用）
  - 未填 rss：自動用 Google News RSS 以 site:網域 搜尋該網站近期內容
"""

# 媒體新聞只抓與保險／理財相關的主題，避免雜訊
MEDIA_KEYWORDS = (
    "保險 OR 壽險 OR 退休 OR 長照 OR 健保 OR 高齡 OR 利率 OR 降息 OR 升息 "
    "OR 遺產稅 OR 贈與稅 OR 所得稅 OR 匯率 OR 年金 OR 醫療 OR 失智"
)

SOURCES = [
    {"name": "金管會",   "domain": "fsc.gov.tw",     "use": "保險政策、金融監理", "priority": 1, "keywords": ""},
    {"name": "壽險公會", "domain": "lia-roc.org.tw", "use": "壽險統計、產業資訊", "priority": 1, "keywords": ""},
    {"name": "財政部",   "domain": "mof.gov.tw",     "use": "遺產稅、贈與稅、稅務", "priority": 1, "keywords": ""},
    {"name": "衛福部",   "domain": "mohw.gov.tw",    "use": "健保、醫療、長照",   "priority": 1, "keywords": ""},
    {"name": "中央銀行", "domain": "cbc.gov.tw",     "use": "利率、匯率、金融政策", "priority": 1, "keywords": ""},
    {"name": "中央社",   "domain": "cna.com.tw",     "use": "財經、醫療、政策",   "priority": 2, "keywords": MEDIA_KEYWORDS},
    {"name": "工商時報", "domain": "ctee.com.tw",    "use": "財經、保險產業",     "priority": 2, "keywords": MEDIA_KEYWORDS},
    {"name": "經濟日報", "domain": "money.udn.com",  "use": "財經、保險產業、理財", "priority": 2, "keywords": MEDIA_KEYWORDS},
]

# 抓取時間範圍（小時）。官方網站更新頻率較低，給較長的範圍
LOOKBACK_HOURS = {1: 72, 2: 30}

# 每天推播幾則（LINE 輪播最多 12 則，建議 5～6 則）
NEWS_PER_DAY = 6

# 送給 AI 挑選的候選新聞上限
MAX_CANDIDATES = 30
