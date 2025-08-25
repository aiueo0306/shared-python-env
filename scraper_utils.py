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
                        # --- 日付パース（日本語 or 英語の月名に対応）
            # --- 日付パース（まず Y年M月D日 を最優先 → その後 MDY/DMY/英語/月欠損の順でフォールバック）---
            # --- 日付パース（日本語 or 英語の月名に対応）---------------------------------
pub_date: Optional[datetime] = None

def _num(s: str) -> int:
    # 全角や「8月」「05日」などの非数字を除去してから数値化
    return int(re.sub(r"\D", "", s or ""))

try:
    match = re.search(date_regex, date_text)
    if match:
        groups = match.groups()

        # groups は以下いずれかの形になる:
        # 1) EN: (Mon, DD, YYYY, None, None)  → len=5、最初の3つが有効
        # 2) JP: (None, None, None, M, YYYY)  → len=5、後ろの2つが有効
        # 3) 旧来: len=3 or len=2 の単純パターン

        # 有効値だけを抽出（None を除外）
        effective = [g for g in groups if g is not None]

        if len(effective) == 3:
            # 英語短縮月名: Mon DD, YYYY → MDY
            if re.match(r"^[A-Za-z]{3}$", effective[0]):
                month_str, day_str, year_str = effective
                pub_date = datetime.strptime(
                    f"{month_str} {int(_num(day_str))}, {int(_num(year_str))}", "%b %d, %Y"
                ).replace(tzinfo=timezone.utc)
            else:
                # それ以外は数値YMDなど（従来の保険）
                year_str, month_str, day_str = effective
                year = _num(year_str)
                if year < 100:
                    year += 2000
                pub_date = datetime(year, _num(month_str), _num(day_str), tzinfo=timezone.utc)

        elif len(effective) == 2:
            # 年月だけのケース（順序が Y,M または M,Y のどちらでも対応）
            a, b = effective
            a_num, b_num = _num(a), _num(b)
            if len(str(a_num)) == 4:   # a が年
                year, mo = a_num, b_num
            elif len(str(b_num)) == 4: # b が年
                year, mo = b_num, a_num
            else:
                # 4桁年が見つからない場合は不正として扱う
                raise ValueError("Year not found in two-group date")
            if year < 100:
                year += 2000
            # day=1 補完
            pub_date = datetime(year, mo, 1, tzinfo=timezone.utc)

        else:
            print("⚠ 想定外のグループ構成でした（date_regexを見直してください）")
    else:
        # セカンダリ：念のため追加の素朴パターンでもトライ（保険）
        # 例) "8月 2025" / "Aug 6, 2025"
        m = re.search(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})", date_text)
        if m:
            month_str, day_str, year_str = m.groups()
            pub_date = datetime.strptime(
                f"{month_str} {int(_num(day_str))}, {int(_num(year_str))}", "%b %d, %Y"
            ).replace(tzinfo=timezone.utc)
        else:
            m2 = re.search(r"(\d{1,2})月\s+(\d{4})", date_text)
            if m2:
                mo, year = map(_num, m2.groups())
                if year < 100:
                    year += 2000
                pub_date = datetime(year, mo, 1, tzinfo=timezone.utc)
            else:
                print("⚠ 日付の抽出に失敗しました（正規表現にマッチしません）")
except Exception as e:
    print(f"⚠ 日付パースに失敗: {e}")
    pub_date = None
# --------------------------------------------------------------------------


            print(pub_date)

            # --- 必須フィールドチェック
            if not title:
                print(f"⚠ タイトルが空のためスキップ（{i+1}行目）")
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
