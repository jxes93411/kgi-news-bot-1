# 凱基人壽 北一區域中心｜今日保險財經新聞

每天早上 7 點前，自動抓取官方與媒體新聞 → AI 整理成五個固定欄位 → 產生手機版新聞網頁，主管一鍵複製連結轉貼到 LINE 群組。

## 運作流程（目前模式：每日新聞網頁 + 主管轉貼連結）

```
06:30 GitHub Actions 啟動
  ├─ fetch_news.py   抓取 8 個來源近期新聞（官方優先）、還原原文連結、抓內文
  ├─ ai_curate.py    Gemini 挑出 6 則，產生摘要／保險觀點／延伸需求
  └─ web_page.py     產生手機版新聞網頁，發布到 GitHub Pages
約 06:45～07:00 網頁就緒 → 主管複製分享文字與連結 → 貼到 LINE 群組
```

每天的網址：`https://你的帳號.github.io/repo名稱/2026-11-17.html`
`index.html` 永遠是最新一天，頁尾有近兩週的歷史新聞連結。

## 五個欄位怎麼確保正確

| 欄位 | 產生方式 |
|---|---|
| 新聞標題 | **直接取自來源 RSS**，AI 不能改寫，確保是真實標題 |
| 新聞摘要 | AI 根據原文內文撰寫 100～150 字，規定不得補充原文沒有的數字 |
| 新聞來源 | **直接取自來源資料**（媒體名稱、日期、原文連結），附「閱讀原文」連結 |
| AI 保險觀點 | AI 撰寫 |
| 延伸需求 | AI 列出 3～5 個議題 |

AI 只能用 id 挑選候選新聞，回傳不存在的 id 會被丟棄，因此不會出現捏造的新聞。
提示詞內建法遵限制：不提商品名、不保證報酬、不比較同業、不製造恐慌。

## 建置步驟

### 1. 申請 Gemini API 金鑰（免費）
1. 用 Google 帳號登入 [Google AI Studio](https://aistudio.google.com/apikey)。
2. 按 **Create API key**（建立 API 金鑰），複製產生的金鑰。
3. 不需要綁信用卡，維持免費方案即可。

> 免費方案的使用限制：有每分鐘、每天的呼叫次數上限（本系統每天只呼叫 1 次，綽綽有餘）；
> 依 Google 規定，免費方案送出的內容可能被用來改進 Google 產品。本系統只送公開新聞，不含任何客戶資料。

### 2. 建立 GitHub repository 並上傳本專案
- **免費帳號**：GitHub Pages 只支援 **公開（Public）** repository。程式碼和每日新聞網頁會公開，但 API 金鑰存在 Secrets 裡，不會外流。網頁已設定 `noindex`，不會被 Google 搜尋到。
- **GitHub Pro／Team 付費帳號**：可以用私有（Private）repository。

### 3. 設定金鑰與網址
Settings → Secrets and variables → Actions：
- **Secrets** 分頁 → 新增 `GEMINI_API_KEY`
- **Variables** 分頁 → 新增 `SITE_URL`，值為 `https://你的帳號.github.io/repo名稱`

### 4. 開啟 GitHub Pages
Settings → Pages → Build and deployment → Source 選 **GitHub Actions**。

### 5. 手動測試一次
Actions 分頁 → 選「每日保險財經新聞網頁」→ **Run workflow**。
跑完後點進該次執行，摘要頁會顯示當日網址和分享文字。

## 每天主管要做的事（約 30 秒）
分享文字（每則標題 + 當日連結）可以從兩個地方取得：
- GitHub → Actions → 當天那次執行的摘要頁面，直接複製。
- 網址 `SITE_URL/share.txt`（建議加入手機書籤），打開後長按全選複製。

複製後貼到業務 LINE 群組即可。


## 之後想升級成 LINE OA 自動推播
`line_push.py` 已經寫好。申請 LINE OA 後，在 Secrets 新增 `LINE_CHANNEL_ACCESS_TOKEN`（選填 `LINE_TO`），並在 workflow 的 env 加上這兩個變數，系統就會在產生網頁的同時自動推播。

## 本機測試

```bash
pip install -r requirements.txt
python main.py --sample      # 用範例資料產生網頁（不呼叫 AI），打開 site/index.html 看版面
export GEMINI_API_KEY=你的金鑰
python main.py               # 完整跑一次
```

## 調整設定（sources.py）

- **新增／移除來源**：編輯 `SOURCES`。若網站有 RSS，填入 `"rss": "網址"` 最穩定；沒填則自動用 Google News 以 `site:網域` 搜尋。
- **媒體關鍵字**：`MEDIA_KEYWORDS`，控制中央社、工商時報抓哪些主題。
- **每日則數**：`NEWS_PER_DAY`（建議 5～6，上限 12）。
- **語氣與法遵規則**：`ai_curate.py` 的 `SYSTEM` 提示詞。
- **網頁顏色**：`web_page.py` CSS 裡的 `--main`（主色深藍）、`--light`（淺藍底），可換成公司 CI 的正式色碼。

## 注意事項

- 壽險公會、央行等官方網站的新聞稿未必都被 Google News 收錄，若某來源常常 0 則，建議改填該網站的官方 RSS 網址。
- GitHub 排程在尖峰時段可能延遲 5～15 分鐘，已提前到 06:30 執行。若需要更準時，可改用 Cloud Run / 公司內部主機的 cron。
- 內容由 AI 產生，建議初期請主管或法遵同仁抽查一段時間，再視需要調整提示詞。

## 費用

全部使用免費方案：GitHub Actions、GitHub Pages（公開 repository）、Gemini API 免費額度，**每月 0 元**。

若某天出現「Gemini 呼叫失敗」或 429 錯誤，代表免費額度暫時用完或 Google 調整了限制，系統會自動重試並改用備用模型；仍失敗時，到 Actions 手動按一次 Run workflow 即可。

## 股市指數與匯率

網頁最上方顯示前一交易日收盤的股市指數（台股加權、道瓊、S&P 500、NASDAQ、費城半導體），以及美元、日圓、歐元兌新台幣的近 30 個交易日走勢（`market.py`）。
資料來源為 Yahoo Finance（透過 yfinance 套件讀取，與 tw.stock.yahoo.com 同一份資料）。任何一項抓不到時只會顯示「暫無資料」，不影響新聞產生。
顏色依台灣習慣：紅色 ▲ 代表上漲、綠色 ▼ 代表下跌。
