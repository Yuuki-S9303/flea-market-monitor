"""
ヤフオクスクレイパー
- エンドポイント: GET https://auctions.yahoo.co.jp/closedsearch/closedsearch
- 売り切れ: istatus=2
- データ取得: HTMLの __NEXT_DATA__ タグからJSONパース
- 売れた日時: endTime フィールド（ISO形式）
- ページネーション: ?b=1&n=50 (b は開始位置、1始まり)
- 注意: __NEXT_DATA__のJSONパスは変更されやすい
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

import config
from scrapers.base import Item, retry

ENDPOINT = "https://auctions.yahoo.co.jp/closedsearch/closedsearch"
JST = timezone(timedelta(hours=9))
PAGE_SIZE = 50
MAX_PAGES = 10        # ヤフオクは最大500件（b=501以降は500エラー）
YAHOO_MAX_RESULTS = 500  # ヤフオクの検索結果上限


def _is_within_days(sold_at_str: Optional[str], days: int) -> bool:
    if sold_at_str is None:
        return True
    try:
        # ISO形式 or Unix timestamp
        if sold_at_str.isdigit():
            sold_at = datetime.fromtimestamp(int(sold_at_str), tz=timezone.utc)
        else:
            sold_at = datetime.fromisoformat(sold_at_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return sold_at >= cutoff
    except Exception:
        return True


@retry(times=3, wait=60, on_status=[429])
def _fetch_page(keyword: str, start: int) -> str:
    params = {
        "p": keyword,
        "istatus": "2",    # 落札済み
        "b": start,
        "n": PAGE_SIZE,
        "s1": "end",
        "o1": "d",         # 終了日時降順
    }
    resp = requests.get(
        ENDPOINT,
        params=params,
        headers=config.HEADERS,
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.text


def _extract_next_data(html: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if not tag:
        return None
    try:
        return json.loads(tag.string)
    except Exception:
        return None


def _get_items_from_next_data(data: dict) -> list[dict]:
    """
    __NEXT_DATA__ からアイテムリストを取得。
    確認済みパス: props.pageProps.initialState.search.items.listing.items
    パスは変更されやすいため複数候補を試みる。
    """
    # 確認済みパス（優先）
    try:
        listing = (
            data["props"]["pageProps"]["initialState"]["search"]["items"]["listing"]
        )
        items = listing.get("items", [])
        if isinstance(items, list):
            return items
    except (KeyError, TypeError):
        pass

    # フォールバック候補
    candidates = [
        ["props", "pageProps", "initialState", "search", "items"],
        ["props", "pageProps", "items"],
        ["props", "pageProps", "data", "items"],
    ]
    for path in candidates:
        node = data
        try:
            for key in path:
                node = node[key]
            if isinstance(node, list):
                return node
        except (KeyError, TypeError):
            continue
    return []


def _parse_items(html: str, keyword: str, fetched_at: str) -> list[Item]:
    data = _extract_next_data(html)
    if data is None:
        print(f"[WARN][yahoo] __NEXT_DATA__ が見つかりませんでした")
        return []

    raw_items = _get_items_from_next_data(data)
    if not raw_items:
        print(f"[WARN][yahoo] アイテムリストが空です（JSONパスが変わった可能性あり）")
        return []

    items: list[Item] = []
    for product in raw_items:
        # 確認済みフィールドマッピング
        raw_id = str(product.get("auctionId") or "")
        if not raw_id:
            continue

        title = product.get("title") or ""
        price = 0
        try:
            price = int(product.get("price") or product.get("buyNowPrice") or 0)
        except (ValueError, TypeError):
            pass

        # endTime は ISO 8601 形式（例: 2026-04-10T10:48:24+09:00）
        sold_at_raw = product.get("endTime")
        sold_at = str(sold_at_raw) if sold_at_raw else None

        # 30日フィルタ
        if not _is_within_days(sold_at, config.SOLD_WITHIN_DAYS):
            continue

        # カテゴリ: category.name または categoryPath の最後の要素
        category = ""
        cat = product.get("category")
        if isinstance(cat, dict):
            category = cat.get("name") or ""
        if not category:
            cat_path = product.get("categoryPath", [])
            if cat_path and isinstance(cat_path, list):
                category = cat_path[-1].get("name", "") if isinstance(cat_path[-1], dict) else ""

        thumbnail = product.get("imageUrl") or ""
        item_url = f"https://page.auctions.yahoo.co.jp/jp/auction/{raw_id}"

        # 商品状態: itemCondition フィールド（USED10=未使用に近い等、フィルタはしない）
        condition = str(product.get("itemCondition") or "")

        items.append(Item(
            fetched_at=fetched_at,
            platform="yahoo",
            keyword=keyword,
            item_id=f"yahoo:{raw_id}",
            title=title,
            price=price,
            sold_at=sold_at,
            condition=condition,
            category=category,
            thumbnail_url=thumbnail,
            item_url=item_url,
        ))

    return items


def scrape(keyword: str) -> list[Item]:
    fetched_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    items: list[Item] = []

    for page in range(MAX_PAGES):
        start = page * PAGE_SIZE + 1
        if start > YAHOO_MAX_RESULTS:
            break  # ヤフオク検索上限（500件）を超えないようにする

        try:
            html = _fetch_page(keyword, start)
        except Exception as e:
            print(f"[ERROR][yahoo] keyword='{keyword}' start={start}: {e}")
            break

        page_items = _parse_items(html, keyword, fetched_at)
        items.extend(page_items)

        if len(page_items) < PAGE_SIZE:
            break  # 最終ページ

    print(f"[yahoo] keyword='{keyword}': {len(items)}件取得")
    return items
