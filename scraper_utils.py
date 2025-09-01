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
            # --- 日付パース（日本語 or 英語の月名に対応）---------------------------------
                        # --- 日付パース（日本語 or 英語の月名に対応）---------------------------------
            pub_date: Optional[datetime] = None

            # 連続スペースなどを正規化（"22  November  2023" → "22 November 2023"）
            date_text_norm = re.sub(r"\s+", " ", date_text or "").strip()

            def _num(s: str) -> int:
                return int(re.sub(r"\D", "", s or ""))

            try:
                # まずは呼び出し側から渡された正規表現で試す
                match = re.search(date_regex, date_text_norm) if date_regex else None

                if match:
                    groups = match.groups()
                    effective = [g for g in groups if g is not None]

                    if len(effective) == 3:
                        a, b, c = effective

                        # DMY（例: 22 November 2023 / 22 Nov 2023）
                        if re.match(r"^[A-Za-z]{3,}$", b):
                            # まずフル月名 %B、失敗したら短縮 %b
                            try:
                                pub_date = datetime.strptime(f"{a} {b} {c}", "%d %B %Y").replace(tzinfo=timezone.utc)
                            except ValueError:
                                pub_date = datetime.strptime(f"{a} {b} {c}", "%d %b %Y").replace(tzinfo=timezone.utc)

                        # MDY（例: Aug 6, 2025）※カンマ入りは別ルートで掴むことが多いが保険で対応
                        elif re.match(r"^[A-Za-z]{3,}$", a) and ("," in date_text_norm):
                            # "Aug 6, 2025" / "August 6, 2025"
                            try:
                                pub_date = datetime.strptime(f"{a} {int(_num(b))}, {int(_num(c))}", "%b %d, %Y").replace(tzinfo=timezone.utc)
                            except ValueError:
                                pub_date = datetime.strptime(f"{a} {int(_num(b))}, {int(_num(c))}", "%B %d, %Y").replace(tzinfo=timezone.utc)

                        else:
                            # 数値系（YMD 等）フォールバック
                            year, month, day = _num(a), _num(b), _num(c)
                            if year < 100:
                                year += 2000
                            pub_date = datetime(year, month, day, tzinfo=timezone.utc)

                    elif len(effective) == 2:
                        # 年月だけのケース（順不同対応）
                        x, y = effective
                        xn, yn = _num(x), _num(y)
                        if len(str(xn)) == 4:
                            year, mo = xn, yn
                        elif len(str(yn)) == 4:
                            year, mo = yn, xn
                        else:
                            raise ValueError("Year not found in two-group date")
                        if year < 100:
                            year += 2000
                        pub_date = datetime(year, mo, 1, tzinfo=timezone.utc)

                    else:
                        print("⚠ 想定外のグループ構成でした（date_regexを見直してください）")

                else:
                    # ---------- セカンダリの複合フォールバック ----------
                    # 1) DMY（フル/短縮月名）
                    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", date_text_norm)
                    if m:
                        d, mon, y = m.groups()
                        try:
                            pub_date = datetime.strptime(f"{d} {mon} {y}", "%d %B %Y").replace(tzinfo=timezone.utc)
                        except ValueError:
                            pub_date = datetime.strptime(f"{d} {mon} {y}", "%d %b %Y").replace(tzinfo=timezone.utc)
                    else:
                        # 2) MDY（英語月名 + 日, 年）
                        m2 = re.search(r"([A-Za-z]{3,})\s+(\d{1,2}),\s+(\d{4})", date_text_norm)
                        if m2:
                            mon, d, y = m2.groups()
                            try:
                                pub_date = datetime.strptime(f"{mon} {d}, {y}", "%b %d, %Y").replace(tzinfo=timezone.utc)
                            except ValueError:
                                pub_date = datetime.strptime(f"{mon} {d}, {y}", "%B %d, %Y").replace(tzinfo=timezone.utc)
                        else:
                            # 3) 日本語「M月 YYYY」→ day=1 補完
                            m3 = re.search(r"(\d{1,2})月\s+(\d{4})", date_text_norm)
                            if m3:
                                mo, y = map(_num, m3.groups())
                                if y < 100:
                                    y += 2000
                                pub_date = datetime(y, mo, 1, tzinfo=timezone.utc)
                            else:
                                # 4) 数値 Y-M-D
                                m4 = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", date_text_norm)
                                if m4:
                                    y, mo, d = map(_num, m4.groups())
                                    pub_date = datetime(y, mo, d, tzinfo=timezone.utc)
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
