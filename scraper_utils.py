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


def extract_items(
    page,
    SELECTOR_DATE: Optional[str],
    SELECTOR_TITLE: str,
    title_selector: Optional[str],
    title_index: int,
    href_selector: Optional[str],
    href_index: int,
    base_url: str,
    date_selector: Optional[str],
    date_index: int,
    date_format: Optional[str],  # 互換のため残す（未使用）
    date_regex: str,
    max_items: int = 10,
) -> List[Dict[str, Any]]:
    """
    Playwright の `page` から記事リストを抽出する。

    Returns:
        List[Dict]: [{"title": str, "link": str, "description": str, "pub_date": datetime|None}, ...]
    """
    # --- ページ安定化 & 可視を要求しない待機（DOMにアタッチされればOK）
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector(SELECTOR_TITLE, state="attached", timeout=30000)

    blocks1 = page.locator(SELECTOR_TITLE)
    count_titles = blocks1.count()
    print(f"📦 発見した記事数(タイトル側): {count_titles}")

    items: List[Dict[str, Any]] = []

    # 日付セレクタは存在しない/別行数の可能性があるため独立して扱う
    blocks2 = page.locator(SELECTOR_DATE) if SELECTOR_DATE else None
    count_dates = blocks2.count() if blocks2 else 0
    print(f"🗓 取得可能な日付ブロック数: {count_dates}")

    row_count = min(count_titles, max_items)

    for i in range(row_count):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i) if (blocks2 and i < count_dates) else None

            # --- タイトル（hidden対策: text_content()）
            if title_selector:
                title = _get_first_text_in_parent(block1, title_selector, title_index)
            else:
                try:
                    title = (block1.text_content() or "").strip()
                except Exception:
                    title = ""

            if not title and title_selector:
                # a要素のtitle属性フォールバック
                try:
                    maybe_title = block1.locator(title_selector).nth(title_index).get_attribute("title")
                    if maybe_title:
                        title = maybe_title.strip()
                except Exception:
                    pass
            print(title)

            # --- URL
            href = _get_first_attr_in_parent(block1, href_selector, "href", href_index)
            full_link = urljoin(base_url, href) if href else base_url
            print(full_link)

            # --- 日付テキスト（title列とdate列の行ズレに耐える）
            date_text = ""
            target_for_date = block2 if block2 else block1  # 無ければ同じ行のタイトル側からも探す

            if date_selector:
                date_text = _get_first_text_in_parent(target_for_date, date_selector, date_index)
            else:
                try:
                    date_text = (target_for_date.text_content() or "").strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得に失敗: {e}")
                    date_text = ""
            print(date_text)

            # --- 日付パース（日本語 or 英語の月名に対応）
                        # --- 日付パース（日本語 or 英語の月名に対応）
                        # --- 日付パース（日本語 or 英語の月名に対応）
                      # --- 日付パース（日本語 or 英語の月名に対応）
            
                        # --- 日付パース（日本語 or 英語の月名に対応）
                        # --- 日付パース ---
            pub_date: Optional[datetime] = None

            # 1) まずはあなたの基本ロジックをそのまま実行（数値YMD想定）
            try:
                match = re.search(date_regex, date_text)
                if match:
                    year_str, month_str, day_str = match.groups()
                    year = int(year_str)
                    if year < 100:
                        year += 2000  # 2桁西暦は2000年以降と仮定
                    pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
                else:
                    print("⚠ 日付の抽出に失敗しました")
            except Exception as e:
                print(f"⚠ 日付パースに失敗: {e}")
                pub_date = None

            # 2) フォールバック（基本ロジックで取れなかった場合のみ）
            if pub_date is None:
                import unicodedata
                def _norm(s: str) -> str:
                    # 全角→半角、前後空白除去
                    return unicodedata.normalize("NFKC", s or "").strip()
                def _num(s: str) -> int:
                    # 日本語「8月」「05日」等でも数字だけ抽出
                    return int(re.sub(r"\D", "", _norm(s)))
                def _year(s: str) -> int:
                    y = _num(s)
                    return y + 2000 if y < 100 else y

                txt = _norm(date_text)

                fallbacks = [
                    ("YMD_kanji", re.compile(r"(\d{2,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?")),
                    ("MDY_ja_month", re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*,\s*(\d{2,4})")),
                    ("DMY_ja_month", re.compile(r"(\d{1,2})\s*(\d{1,2})\s*月\s*(\d{2,4})")),
                    ("YMD_anysep", re.compile(r"(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})")),
                    ("MDY_en_short", re.compile(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*,\s*(\d{4})", re.I)),
                    ("DMY_en_long", re.compile(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", re.I)),
                    ("YM_dot", re.compile(r"(\d{2,4})\.(\d{1,2})")),  # day=1 補完
                ]

                for tag, rx in fallbacks:
                    m2 = rx.search(txt)
                    if not m2:
                        continue
                    g = m2.groups()
                    try:
                        if tag == "YMD_kanji":
                            y, mo, d = g
                            pub_date = datetime(_year(y), _num(mo), _num(d), tzinfo=timezone.utc)
                        elif tag == "MDY_ja_month":      # 6月 12, 2025
                            mo, d, y = g
                            pub_date = datetime(_year(y), _num(mo), _num(d), tzinfo=timezone.utc)
                        elif tag == "DMY_ja_month":      # 08 8月 2025
                            d, mo, y = g
                            pub_date = datetime(_year(y), _num(mo), _num(d), tzinfo=timezone.utc)
                        elif tag == "YMD_anysep":        # 2025-08-06 / 2025.8.6 / 2025/08/06
                            y, mo, d = g
                            pub_date = datetime(_year(y), _num(mo), _num(d), tzinfo=timezone.utc)
                        elif tag == "MDY_en_short":      # Aug 6, 2025
                            mon, d, y = g
                            pub_date = datetime.strptime(f"{mon} {int(d)}, {int(y)}", "%b %d, %Y").replace(tzinfo=timezone.utc)
                        elif tag == "DMY_en_long":       # 6 August 2025
                            d, mon, y = g
                            pub_date = datetime.strptime(f"{int(d)} {mon} {int(y)}", "%d %B %Y").replace(tzinfo=timezone.utc)
                        elif tag == "YM_dot":            # 2024.10 → day=1
                            y, mo = g
                            pub_date = datetime(_year(y), _num(mo), 1, tzinfo=timezone.utc)

                        if pub_date is not None:
                            break
                    except Exception as e2:
                        print(f"ℹ フォールバック '{tag}' 失敗: {e2}")
                        continue



            print(pub_date)

            # --- 必須フィールドチェック
            if not title or not href:
                print(f"⚠ 必須フィールドが欠落したためスキップ（{i+1}行目）: title='{title}', href='{href}'")
                continue

            items.append(
                {
                    "title": title,
                    "link": full_link,         # ← 絶対URLを格納
                    "description": title,
                    "pub_date": pub_date,
                }
            )

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items
