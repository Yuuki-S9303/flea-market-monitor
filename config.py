import os

# ── スプレッドシート設定 ──────────────────────────────
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

# ── シート名 ─────────────────────────────────────────
SHEET_KEYWORDS = "キーワードリスト"
SHEET_DATA_KEYWORD = "生データ（キーワード指定）"
SHEET_DATA_EXPLORE = "生データ（探索）"

# ── フィルタ条件 ──────────────────────────────────────
# メルカリ: 1=新品・未使用, 2=未使用に近い
TARGET_CONDITIONS_MERCARI = [1, 2]
TARGET_CONDITIONS_RAKUMA = [1]   # ラクマは1のみ（要確認）
SOLD_WITHIN_DAYS = 30

# ── HTTPリクエスト設定 ────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 15
