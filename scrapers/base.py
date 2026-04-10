import time
import functools
from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    fetched_at: str           # 取得日時
    platform: str             # mercari / rakuma / yahoo
    keyword: str              # 検索キーワード
    item_id: str              # 重複管理用 (platform:raw_id)
    title: str                # 商品名
    price: int                # 価格（円）
    sold_at: Optional[str]    # 売れた日時（取得不能な場合はNone）
    condition: str            # 商品状態
    category: str             # カテゴリ
    thumbnail_url: str        # サムネイルURL
    item_url: str             # 商品詳細URL

    def to_row(self) -> list:
        """スプレッドシートへの書き込み用リスト"""
        return [
            self.fetched_at,
            self.platform,
            self.keyword,
            self.item_id,
            self.title,
            self.price,
            self.sold_at or "",
            self.condition,
            self.category,
            self.thumbnail_url,
            self.item_url,
        ]


def retry(times: int = 3, wait: int = 60, on_status: Optional[list] = None):
    """
    リトライデコレータ。
    - on_status: HTTPステータスコードのリスト（指定時はそのステータスのみリトライ）
    - それ以外の例外は常にリトライ
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    # HTTPエラーのステータスチェック
                    status = getattr(getattr(e, "response", None), "status_code", None)
                    if on_status and status not in on_status:
                        raise
                    print(f"[RETRY] {func.__name__} attempt {attempt}/{times}: {e}")
                    if attempt < times:
                        time.sleep(wait)
            raise last_exc
        return wrapper
    return decorator
