"""
フリマ仕入れ商品分析 - メイン実行スクリプト
- Google Sheetsからキーワードを読み込み
- メルカリ・ラクマ・ヤフオクで売れた商品を収集
- 重複排除してスプレッドシートに追記
"""

import time

from dotenv import load_dotenv
load_dotenv()

import config
from scrapers import mercari, rakuma, yahoo
from scrapers.base import Item
from sheets.writer import load_keywords, write_items

SCRAPERS = [
    mercari.scrape,
    rakuma.scrape,
    yahoo.scrape,
]


def run(keywords: list[str], sheet_name: str) -> None:
    """指定されたキーワードリストでスクレイピングし、sheet_name に書き込む。"""
    all_items: list[Item] = []

    for keyword in keywords:
        print(f"\n=== キーワード: '{keyword}' ===")

        for scraper in SCRAPERS:
            try:
                items = scraper(keyword)
                all_items.extend(items)
            except Exception as e:
                # 1スクレイパーの失敗で全体は止めない
                print(f"[ERROR] {scraper.__module__} keyword='{keyword}': {e}")

            time.sleep(2)  # サーバー負荷軽減

    print(f"\n合計 {len(all_items)}件取得 → {sheet_name}")
    write_items(all_items, sheet_name)


def main() -> None:
    print("=== フリマ監視スタート ===")
    keyword_map = load_keywords()

    keywords_specified = keyword_map["指定"]
    keywords_explore = keyword_map["探索"]

    if not keywords_specified and not keywords_explore:
        print("[WARN] キーワードが登録されていません。スプシの「キーワードリスト」シートA列に追加してください。")
        return

    # 機能A: キーワード指定型
    if keywords_specified:
        print(f"\n【機能A: キーワード指定】{len(keywords_specified)}件")
        run(keywords_specified, config.SHEET_DATA_KEYWORD)

    # 機能B: 探索型
    if keywords_explore:
        print(f"\n【機能B: 探索】{len(keywords_explore)}件")
        run(keywords_explore, config.SHEET_DATA_EXPLORE)

    print("\n=== 処理完了 ===")


if __name__ == "__main__":
    main()
