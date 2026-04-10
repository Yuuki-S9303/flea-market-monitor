"""
メルカリスクレイパー（Playwright版）
- ブラウザを起動して jp.mercari.com の検索ページを開く
- ブラウザが自動でDoPP認証を付与してAPIを叩く
- `api.mercari.jp/v2/entities:search` のレスポンスをインターセプト
- 初回ロードで最大120件取得（ページネーションは現在未対応）
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from playwright.sync_api import sync_playwright, Response

import config
from scrapers.base import Item

JST = timezone(timedelta(hours=9))
SEARCH_URL = "https://jp.mercari.com/search"
API_ENDPOINT = "https://api.mercari.jp/v2/entities:search"
PAGE_LOAD_WAIT_MS = 8000   # APIレスポンス待機時間（ms）


def _parse_condition(condition_id: int) -> str:
    mapping = {
        1: "新品・未使用",
        2: "未使用に近い",
        3: "目立った傷や汚れなし",
        4: "やや傷や汚れあり",
        5: "傷や汚れあり",
        6: "全体的に状態が悪い",
    }
    return mapping.get(condition_id, str(condition_id))


def _is_within_days(sold_at_ts: Optional[int], days: int) -> bool:
    if sold_at_ts is None:
        return True
    try:
        sold_at = datetime.fromtimestamp(int(sold_at_ts), tz=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return sold_at >= cutoff
    except Exception:
        return True


def _parse_raw_items(raw_items: list[dict], keyword: str, fetched_at: str) -> list[Item]:
    items: list[Item] = []
    for product in raw_items:
        raw_id = product.get("id", "")
        if not raw_id:
            continue

        title = product.get("name", "")
        price = 0
        try:
            price = int(product.get("price", 0))
        except (ValueError, TypeError):
            pass

        condition_id = int(product.get("itemConditionId", 0) or 0)
        condition = _parse_condition(condition_id)
        category = product.get("categoryDisplayName", "")

        thumbnails = product.get("thumbnails", [])
        thumbnail = thumbnails[0] if thumbnails else ""

        # 商品状態フィルタ
        if condition_id not in config.TARGET_CONDITIONS_MERCARI:
            continue

        # sold_at: updated フィールド（Unix timestamp）
        sold_at_ts = product.get("updated")
        sold_at = None
        if sold_at_ts:
            try:
                sold_at = datetime.fromtimestamp(int(sold_at_ts), tz=timezone.utc).isoformat()
            except Exception:
                pass

        # 30日フィルタ
        if not _is_within_days(sold_at_ts, config.SOLD_WITHIN_DAYS):
            continue

        items.append(Item(
            fetched_at=fetched_at,
            platform="mercari",
            keyword=keyword,
            item_id=f"mercari:{raw_id}",
            title=title,
            price=price,
            sold_at=sold_at,
            condition=condition,
            category=category,
            thumbnail_url=thumbnail,
            item_url=f"https://jp.mercari.com/item/{raw_id}",
        ))
    return items


def scrape(keyword: str) -> list[Item]:
    fetched_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    all_items: list[Item] = []
    api_responses: list[dict] = []

    condition_param = ",".join(str(c) for c in config.TARGET_CONDITIONS_MERCARI)
    url = f"{SEARCH_URL}?keyword={keyword}&status=sold_out&item_condition_id={condition_param}"

    def on_response(response: Response):
        if API_ENDPOINT in response.url:
            try:
                api_responses.append(response.json())
            except Exception:
                pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=config.HEADERS["User-Agent"],
                locale="ja-JP",
            )
            page = context.new_page()
            page.on("response", on_response)

            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

            browser.close()

    except Exception as e:
        print(f"[ERROR][mercari] keyword='{keyword}': {e}")
        return all_items

    if not api_responses:
        print(f"[WARN][mercari] keyword='{keyword}': APIレスポンスが取得できませんでした")
        return all_items

    for resp_data in api_responses:
        raw_items = resp_data.get("items", [])
        all_items.extend(_parse_raw_items(raw_items, keyword, fetched_at))

    print(f"[mercari] keyword='{keyword}': {len(all_items)}件取得")
    return all_items
