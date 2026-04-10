"""
Google Sheetsへの書き込みモジュール
- gspreadを使用
- 重複チェック: 商品ID列（D列）を全件メモリ読み込みで判定
- スプシAPIエラー: @retry(times=3, wait=30)、全件失敗時はsys.exit(1)
"""

import json
import sys
import traceback

import gspread
from google.oauth2.service_account import Credentials

import config
from scrapers.base import Item, retry

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADER = [
    "取得日時", "プラットフォーム", "検索キーワード", "商品ID",
    "商品名", "価格", "売れた日時", "商品状態", "カテゴリ",
    "サムネイルURL", "商品URL",
]


def _build_client() -> gspread.Client:
    creds_info = json.loads(config.SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(SHEET_HEADER))
        ws.append_row(SHEET_HEADER)
        return ws


@retry(times=3, wait=30)
def _fetch_existing_ids(ws: gspread.Worksheet) -> set[str]:
    """D列（商品ID）を全件取得してセットで返す"""
    values = ws.col_values(4)  # D列 = index 4
    return set(values[1:])  # 1行目はヘッダー


@retry(times=3, wait=30)
def _append_rows(ws: gspread.Worksheet, rows: list[list]) -> None:
    ws.append_rows(rows, value_input_option="USER_ENTERED")


def write_items(items: list[Item], sheet_name: str) -> None:
    """
    重複を除いたアイテムをスプレッドシートに追記する。
    スプシAPIエラーが全リトライ失敗した場合はsys.exit(1)。
    """
    if not items:
        print(f"[sheets] 書き込み対象なし")
        return

    try:
        client = _build_client()
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        ws = _get_or_create_sheet(spreadsheet, sheet_name)
        existing_ids = _fetch_existing_ids(ws)
    except Exception as e:
        print(f"[ERROR][sheets] スプシ接続失敗: {e}")
        sys.exit(1)

    new_rows = []
    for item in items:
        if item.item_id in existing_ids:
            continue
        new_rows.append(item.to_row())
        existing_ids.add(item.item_id)  # 同一実行内での重複も防ぐ

    if not new_rows:
        print(f"[sheets] 新規アイテムなし（全件重複）")
        return

    try:
        _append_rows(ws, new_rows)
        print(f"[sheets] {len(new_rows)}件を '{sheet_name}' に書き込みました")
    except Exception as e:
        print(f"[ERROR][sheets] 書き込み失敗: {e}")
        sys.exit(1)


def load_keywords() -> dict[str, list[str]]:
    """
    キーワードリストシートのA列（キーワード）・B列（種類）を読み込み、
    種類ごとに分類して返す。

    Returns:
        {
            "指定": [キーワード指定型のキーワード, ...],   # B列が空 or "指定"
            "探索": [探索型のキーワード, ...],              # B列が "探索"
        }
    """
    try:
        client = _build_client()
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        ws = _get_or_create_sheet(spreadsheet, config.SHEET_KEYWORDS)

        # A列・B列を取得（行数を合わせるため get_all_values を使用）
        all_values = ws.get_all_values()
        if not all_values:
            return {"指定": [], "探索": []}

        result: dict[str, list[str]] = {"指定": [], "探索": []}
        for row in all_values[1:]:  # 1行目はヘッダー
            kw = row[0].strip() if len(row) > 0 else ""
            kind = row[1].strip() if len(row) > 1 else ""
            if not kw:
                continue
            if kind == "探索":
                result["探索"].append(kw)
            else:
                result["指定"].append(kw)

        print(f"[sheets] キーワード読み込み: 指定={len(result['指定'])}件, 探索={len(result['探索'])}件")
        return result
    except Exception as e:
        print(f"[ERROR][sheets] キーワード読み込み失敗: {e}")
        traceback.print_exc()
        sys.exit(1)
