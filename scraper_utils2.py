# -*- coding: utf-8 -*-
"""
Playwright ロケータからニュース記事を抽出するユーティリティ（令和専用簡易版）

- hidden 要素対策として text_content() を使用
- タイトル列と日付列の行ズレにある程度耐性あり
- 日付は「令和N年M月D日」のみ対応（それ以外は pub_date=None）
- href は base_url と結合して絶対URL化

Note:
- `date_format` / `date_regex` は後方互換のための未使用引数として残しています。
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
    date_regex: str,             # 互換のため残す（未使用）
    max_items: int = 500,
) -> List[Dict[str, Any]]:
    """
    Playwright の `page` から記事リストを抽出する（令和表記専用簡易版）。

    Returns:
        List[Dict]: [{"title": str, "link": str, "description": str, "pub_date": datetime|None}, ...]
    """
    # --- ページ安定化 & 可視を要求しない待機（DOMにアタッチされればOK）
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector(SELECTOR_TITLE, state="attached", timeout=120000)

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
            full_link = urljoin(base_url, href) if href else None
            print(full_link)

            # --- 日付テキスト（title列とdate列の行ズレに耐える）
            date_text = ""
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

            # --- 日付パース（令和のみ対応）---------------------------------
            pub_date: Optional[datetime] = None

            # 連続スペースなどを正規化
            date_text_norm = re.sub(r"\s+", " ", date_text or "").strip()

            # 全角数字 → 半角数字
            def _to_ascii_digits(s: str) -> str:
                table = str.maketrans({chr(ord("０") + i): str(i) for i in range(10)})
                return (s or "").translate(table)

            def _num(s: str) -> int:
                s = _to_ascii_digits(s)
                return int(re.sub(r"\D", "", s))

            try:
                # 令和N年M月D日 / 令和Ｎ年Ｍ月Ｄ日 / 令和元年M月D日 だけを扱う
                m_reiwa = re.search(
                    r"令和\s*([0-9０-９]{1,2}|元)年\s*([0-9０-９]{1,2})月\s*([0-9０-９]{1,2})日",
                    date_text_norm,
                )

                if m_reiwa:
                    nen, mo, d = m_reiwa.groups()

                    # 「元年」対応（想定しないなら常に _num でもOK）
                    if nen == "元":
                        nen_i = 1
                    else:
                        nen_i = _num(nen)

                    mo_i = _num(mo)
                    d_i = _num(d)

                    # 令和1年 = 2019年 → 2018 + N
                    year = 2018 + nen_i
                    pub_date = datetime(year, mo_i, d_i, tzinfo=timezone.utc)
                else:
                    # 令和表記が無ければ pub_date は None のまま
                    print("⚠ 令和形式の日付が見つかりませんでした（pub_date=None）")

            except Exception as e:
                print(f"⚠ 日付パースに失敗: {e}")
                pub_date = None

            # ------------------------------------------------------------------
            if SELECTOR_DATE is None:
                pub_date = None

            print(pub_date)

            # pub_date がある場合のみ「3日以内」フィルタを適用
            if pub_date:
                now = datetime.now(timezone.utc)
                delta = now - pub_date
                if delta.days > 3:
                    print(f"⏳ {pub_date} は3日より古いためスキップ")
                    continue

            # --- 必須フィールドチェック
            if not title:
                print(f"⚠ タイトルが空のためスキップ（{i+1}行目）")
                continue

            items.append(
                {
                    "title": title,
                    "link": full_link,   # ← 絶対URLを格納
                    "description": title,
                    "pub_date": pub_date,
                }
            )

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items
