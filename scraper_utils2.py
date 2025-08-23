# -*- coding: utf-8 -*-
"""
Playwright ロケータからニュース記事を抽出するユーティリティ

- hidden 要素対策として text_content() を使用
- タイトル列と日付列の行ズレにある程度耐性あり
- 日本語(YYYY-MM-DD 等)／英語月名(Mon DD, YYYY)を正規表現でパース
- href は base_url と結合して絶対URL化

Note:
- `date_format` は後方互換のための未使用引数として残しています。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from typing import Any, Dict, List, Optional


def _get_first_text_in_parent(parent_locator, selector: Optional[str], start_index: int = 0) -> str:
    """
    親ロケータ内の selector に一致する要素を start_index から順に調べ、
    最初にテキストを取得できた要素のテキストを返す（親範囲外には出ない）
    ※ hidden 対応のため inner_text() ではなく text_content() を使用
    """
    try:
        elements = parent_locator.locator(selector)
        count = elements.count()
    except Exception:
        return ""

    for idx in range(start_index, count):
        try:
            txt = (elements.nth(idx).text_content() or "").strip()
            if txt:
                return txt
        except Exception:
            continue
    return ""


def _get_first_attr_in_parent(
    parent_locator,
    selector: Optional[str],
    attr: str,
    start_index: int = 0,
) -> Optional[str]:
    """
    親ロケータ内の selector に一致する要素を start_index から順に調べ、
    最初に attr を取得できた要素の値を返す（親範囲外には出ない）
    selector が空/None の場合は親自身から attr を取得する
    """
    if selector:
        try:
            elements = parent_locator.locator(selector)
            count = elements.count()
        except Exception:
            return None

        for idx in range(start_index, count):
            try:
                val = elements.nth(idx).get_attribute(attr)
                if val:
                    return val
            except Exception:
                continue
        return None
    else:
        # 親自身が <a> 等で href を持つケース
        try:
            val = parent_locator.get_attribute(attr)
            return val
        except Exception:
            return None


# 変更: extract_items の引数末尾に iframe 関係をオプション追加（既存呼び出しはそのまま動作）
def extract_items_iframe(
    page,
    iframe_selector: str,
    SELECTOR_DATE: Optional[str],
    SELECTOR_TITLE: str,
    title_selector: Optional[str],
    title_index: int,
    href_selector: Optional[str],
    href_index: int,
    base_url: str,
    date_selector: Optional[str],
    date_index: int,
    date_format: Optional[str],
    date_regex: str,
    max_items: int = 10,
    # ▼ 追加オプション（デフォルトは従来挙動）
    iframe_index: int = 0,
    timeout_ms: int = 30000,
) -> List[Dict[str, Any]]:

    try:
        page.wait_for_selector(iframe_selector, timeout=timeout_ms)
        handle = page.locator(iframe_selector).nth(iframe_index).element_handle()
        if not handle:
            print("⚠ iframeが見つかりませんでした")
            return []
        frame = handle.content_frame()
        if not frame:
            print("⚠ iframe の content_frame が None でした")
            return []
    except Exception as e:
        print(f"⚠ iframe 解決に失敗: {e}")
        return []

    # ここを追加：ロード状態の安定化
    try:
        frame.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except Exception:
        pass

    frame.wait_for_selector(SELECTOR_TITLE, state="attached", timeout=timeout_ms)

    blocks1 = frame.locator(SELECTOR_TITLE)
    count_titles = blocks1.count()
    print(f"📦 発見した記事数(タイトル側): {count_titles}")

    items: List[Dict[str, Any]] = []
    blocks2 = frame.locator(SELECTOR_DATE) if SELECTOR_DATE else None
    count_dates = blocks2.count() if blocks2 else 0
    print(f"🗓 取得可能な日付ブロック数: {count_dates}")

    row_count = min(count_titles, max_items)

    for i in range(row_count):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i) if (blocks2 and i < count_dates) else None

            # タイトル
            if title_selector:
                title = _get_first_text_in_parent(block1, title_selector, title_index)
            else:
                try:
                    title = (block1.text_content() or "").strip()
                except Exception:
                    title = ""

            if not title and title_selector:
                try:
                    maybe_title = block1.locator(title_selector).nth(title_index).get_attribute("title")
                    if maybe_title:
                        title = maybe_title.strip()
                except Exception:
                    pass
            print(title)

            # URL
            href = _get_first_attr_in_parent(block1, href_selector, "href", href_index)
            full_link = urljoin(base_url, href) if href else base_url
            print(full_link)

            # 日付
            target_for_date = block2 if block2 else block1
            if date_selector:
                date_text = _get_first_text_in_parent(target_for_date, date_selector, date_index)
            else:
                try:
                    date_text = (target_for_date.text_content() or "").strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得に失敗: {e}")
                    date_text = ""
            print(date_text)

            # パース（既存ロジック）
            pub_date: Optional[datetime] = None
            def _num(s: str) -> int:
                return int(re.sub(r"\D", "", s or "0"))

            try:
                match = re.search(date_regex, date_text)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        y, m, d = groups
                        year = _num(y)
                        if year < 100:
                            year += 2000
                        pub_date = datetime(year, _num(m), _num(d), tzinfo=timezone.utc)
                    elif len(groups) == 2 and all(g is not None for g in groups):
                        y, mo = groups
                        year = _num(y)
                        if year < 100:
                            year += 2000
                        pub_date = datetime(year, _num(mo), 1, tzinfo=timezone.utc)
                    else:
                        print("⚠ 想定外のグループ構成（date_regexの見直し推奨）")
                else:
                    print("⚠ 日付の抽出に失敗しました")
            except Exception as e:
                print(f"⚠ 日付パースに失敗: {e}")
                pub_date = None
            print(pub_date)

            if not title or not href:
                print(f"⚠ 必須フィールドが欠落したためスキップ（{i+1}行目）: title='{title}', href='{href}'")
                continue

            items.append({
                "title": title,
                "link": full_link,
                "description": title,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items
