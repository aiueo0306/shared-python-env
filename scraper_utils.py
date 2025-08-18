# -*- coding: utf-8 -*-
"""
Playwright ロケータからニュース記事を抽出するユーティリティ

- hidden 要素対策として text_content() を使用
- タイトル列と日付列の行ズレにある程度耐性あり
- 渡された date_regex（呼び出し側指定）を最優先で試し、ヒットしなければ
  本モジュール内の「既出パターン」を順に試して柔軟にパース
- href は base_url と結合して絶対URL化

Note:
- `date_format` は後方互換のための未使用引数として残しています。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from typing import Any, Dict, List, Optional

# ---- 全角→半角の数字変換（例：２０２５→2025） ----
_ZEN2HAN = str.maketrans("０１２３４５６７８９", "0123456789")

def _to_halfwidth_digits(s: str) -> str:
    return (s or "").translate(_ZEN2HAN)

# 既出の英語月名（短縮/フル）
_EN_SHORT = ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")
_EN_LONG  = ("January","February","March","April","May","June","July","August","September","October","November","December")

# ---- 既出パターン（正規表現）----
# ※ここに “新規に判明した表記” を追記していく（呼び出し側の引数は増やさない）
_KNOWN_DATE_REGEXES: List[str] = [
    r"(\d{2,4})\.(\d{1,2})\.(\d{1,2})",                       # 2025.08.06 / 2025.8.6
    r"(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})",                   # 2025/08/06 or 2025-8-6
    r"(\d{2,4})\.(\d{1,2})",                                  # 2024.10（年.月 → day=1 補完）
    r"(\d{2,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?",     # 2025年8月6日（末尾 日 任意）
    r"(\d{1,2})\s*月\s*(\d{1,2}),\s*(\d{4})",                 # 6月 12, 2025（日本語月 + 英語カンマ）
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s*(\d{4})",  # Aug 6, 2025
    r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",  # 6 August 2025
]

def _try_parse_with_regex(txt: str, rgx: str) -> Optional[datetime]:
    """
    1つの既出パターン正規表現 rgx を使って txt を datetime(UTC) に変換して返す。
    ヒットしなければ None。
    """
    m = re.search(rgx, txt, re.IGNORECASE)
    if not m:
        return None
    groups = m.groups()

    # --- 3 数字（Y,M,D）: 例 2025.08.06 / 2025-8-6 / 2025/08/06 ---
    if len(groups) == 3 and all(g is not None and re.fullmatch(r"\d{1,4}", g) for g in groups):
        y, mo, d = groups
        y_i = int(y)
        if y_i < 100:  # 2桁西暦は 2000年代とみなす
            y_i += 2000
        return datetime(y_i, int(mo), int(d), tzinfo=timezone.utc)

    # --- 2 数字（Y,M）: 例 2024.10 → day=1 補完 ---
    if len(groups) == 2 and all(g is not None and re.fullmatch(r"\d{1,4}", g) for g in groups):
        y, mo = groups
        y_i = int(y)
        if y_i < 100:
            y_i += 2000
        return datetime(y_i, int(mo), 1, tzinfo=timezone.utc)

    # --- 和文: Y年M月D日（末尾「日」省略も regex 側で許容）---
    if len(groups) == 3 and ("年" in rgx and "月" in rgx):
        y, mo, d = groups
        y_i = int(y)
        if y_i < 100:
            y_i += 2000
        return datetime(y_i, int(mo), int(d), tzinfo=timezone.utc)

    # --- 和英ミックス: M月 D, YYYY ---
    if len(groups) == 3 and ("月" in rgx and "," in rgx):
        mo, d, y = groups
        y_i = int(y)
        if y_i < 100:
            y_i += 2000
        return datetime(y_i, int(mo), int(d), tzinfo=timezone.utc)

    # --- 英語短縮月名: Mon DD, YYYY ---
    if len(groups) == 3 and any(mon in rgx for mon in _EN_SHORT):
        mon, d, y = groups
        dt = datetime.strptime(f"{mon} {d}, {y}", "%b %d, %Y")
        return dt.replace(tzinfo=timezone.utc)

    # --- 英語フル月名: DD Month YYYY ---
    if len(groups) == 3 and any(name in rgx for name in _EN_LONG):
        d, mon, y = groups
        dt = datetime.strptime(f"{d} {mon} {y}", "%d %B %Y")
        return dt.replace(tzinfo=timezone.utc)

    # 既出パターンの範囲外 → None
    return None


def _parse_pub_date(date_text: str, primary_regex: str) -> Optional[datetime]:
    """
    呼び出し側が渡した primary_regex を最初に試し、
    ヒットしなければ本モジュール内の既出パターンを順に試す。
    """
    txt = _to_halfwidth_digits((date_text or "").strip())
    if not txt:
        return None

    # 1) 呼び出し側の正規表現を最初に試す
    tried = set()
    for rgx in [primary_regex] + [r for r in _KNOWN_DATE_REGEXES if r != primary_regex]:
        if rgx in tried:
            continue
        tried.add(rgx)
        try:
            dt = _try_parse_with_regex(txt, rgx)
            if dt is not None:
                return dt
        except Exception as e:
            print(f"⚠ パターン処理失敗: {e}")
            continue
    return None


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
    date_regex: str,             # 呼び出し側が渡す単体パターン（最優先）
    max_items: int = 10,
) -> List[Dict[str, Any]]:
    """
    Playwright の `page` から記事リストを抽出する。

    Returns:
        List[Dict]: [{"title": str, "link": str, "description": str, "pub_date": datetime|None}, ...]
    """
    # --- ページ安定化 & 可視を要求しない待機（DOMにアタッチされればOK）---
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

            # --- タイトル（hidden対策: text_content()）---
            if title_selector:
                title = _get_first_text_in_parent(block1, title_selector, title_index)
            else:
                try:
                    title = (block1.text_content() or "").strip()
                except Exception:
                    title = ""

            if not title and title_selector:
