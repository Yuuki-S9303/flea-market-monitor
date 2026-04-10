"""
ラクマスクレイパー（Playwright版）
- エンドポイント: https://fril.jp/s
- statuses[]=5 はサーバー側エラーのため使用不可
- 代替手段: フィルタなしで検索 → JavaScriptレンダリング後に
  「SOLD OUT」テキストを持つ item-box のみを抽出
- データ: data-rat-* 属性から取得
- sold_at: fril.jp の検索ページには日付が表示されないため None
- ページネーション: ?page=N（最大5ページ）
"""

from datetime import datetime, timezone, timedelta

from playwright.sync_api import sync_playwright, Page

import config
from scrapers.base import Item

JST = timezone(timedelta(hours=9))
SEARCH_URL = "https://fril.jp/s"
MAX_PAGES = 5
PAGE_LOAD_WAIT_MS = 3000


def _parse_items_from_page(page: Page, keyword: str, fetched_at: str) -> list[Item]:
    items: list[Item] = []

    cards = page.query_selector_all(".item-box")
    for card in cards:
        # SOLD OUT テキストを持つaタグがあれば売れた商品
        sold_link = card.query_selector('a:has-text("SOLD OUT")')
        if not sold_link:
            continue

        # data-rat-* 属性からデータ取得
        a = card.query_selector("a[data-rat-itemid]")
        if not a:
            continue

        rat_id = a.get_attribute("data-rat-itemid") or ""
        parts = rat_id.split("/")
        raw_id = parts[1] if len(parts) == 2 else rat_id

        title = (a.get_attribute("data-rat-item_name") or "").strip()
        price_raw = a.get_attribute("data-rat-price") or "0"
        category = a.get_attribute("data-rat-sgenre") or a.get_attribute("data-rat-igenre") or ""

        href = a.get_attribute("href") or ""
        item_url = href if href.startswith("http") else f"https://item.fril.jp/{href.lstrip('/')}"

        # サムネイル
        img = card.query_selector("img[data-original]")
        thumbnail = img.get_attribute("data-original") if img else ""
        if not thumbnail:
            img = card.query_selector("img[src]")
            thumbnail = img.get_attribute("src") if img else ""

        if not raw_id:
            continue

        try:
            price = int(str(price_raw).replace(",", ""))
        except (ValueError, TypeError):
            price = 0

        items.append(Item(
            fetched_at=fetched_at,
            platform="rakuma",
            keyword=keyword,
            item_id=f"rakuma:{raw_id}",
            title=title,
            price=price,
            sold_at=None,  # 検索ページに売れた日付の表示なし
            condition="",  # 検索ページに状態の表示なし
            category=str(category),
            thumbnail_url=thumbnail or "",
            item_url=item_url,
        ))

    return items


def scrape(keyword: str) -> list[Item]:
    fetched_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    all_items: list[Item] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=config.HEADERS["User-Agent"],
                locale="ja-JP",
            )
            page = context.new_page()

            for page_num in range(1, MAX_PAGES + 1):
                url = f"{SEARCH_URL}?query={keyword}&page={page_num}"
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

                page_items = _parse_items_from_page(page, keyword, fetched_at)
                all_items.extend(page_items)

                # 次ページの有無を確認
                has_next = page.query_selector("a[rel='next']")
                if not has_next or not page_items:
                    break

            browser.close()

    except Exception as e:
        print(f"[ERROR][rakuma] keyword='{keyword}': {e}")

    print(f"[rakuma] keyword='{keyword}': {len(all_items)}件取得（SOLD OUTのみ）")
    return all_items
