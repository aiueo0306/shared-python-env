import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError as PlaywrightTimeout

def _get_first_text_in_parent(parent_locator, selector, start_index=0):
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

def _get_first_attr_in_parent(parent_locator, selector, attr, start_index=0):
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
        try:
            return parent_locator.get_attribute(attr)
        except Exception:
            return None

def extract_items(
    page,
    SELECTOR_DATE,   # 例: "ul.m-list-news"
    SELECTOR_TITLE,  # 例: "ul.m-list-news li"（※無視して最後のULから取ります）
    title_selector,
    title_index,
    href_selector,
    href_index,
    base_url,
    date_selector,
    date_index,
    date_format,  # 未使用（互換維持）
    date_regex,
    max_items=10
):
    # ページ安定化
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")

    # ---- ここが肝心：最後の ul.m-list-news をコンテナとして固定 ----
    news_lists = page.locator("ul.m-list-news")
    # まずDOMに付くのを待機（可視は要求しない）
    news_lists.first.wait_for(state="attached", timeout=30000)
    # 最後の UL を取得
    container = news_lists.last
    container.wait_for(state="attached", timeout=30000)

    # li 群（タイトル側）
    blocks1 = container.locator("li")
    count_titles = blocks1.count()
    print(f"📦 対象コンテナ内の記事数: {count_titles}")

    items = []

    # 日付は原則コンテナ内の time から拾う（SELECTOR_DATE は無視してOK）
    # ただし互換のため、呼び出し元が渡してきた SELECTOR_DATE がある場合は
    # それがコンテナを指す想定で container を優先
    blocks2 = container  # date 用の基点はコンテナ

    row_count = min(count_titles, max_items)

    for i in range(row_count):
        try:
            block1 = blocks1.nth(i)
            # --- タイトル
            if title_selector:
                title = _get_first_text_in_parent(block1, title_selector, title_index)
            else:
                try:
                    title = (block1.text_content() or "").strip()
                except Exception:
                    title = ""
            if not title and title_selector:
                # title属性フォールバック
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

            # --- 日付テキスト（コンテナ内で相対的に取得）
            date_text = ""
            if date_selector:
                date_text = _get_first_text_in_parent(block1, date_selector, date_index) \
                            or _get_first_text_in_parent(blocks2, date_selector, i)  # 同行→コンテナの順で探索
            else:
                try:
                    date_text = (block1.text_content() or "").strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得に失敗: {e}")
                    date_text = ""
            print(date_text)

            # --- 日付パース（yyyy, mm, dd の3グループを想定）
            pub_date = None
            try:
                match = re.search(date_regex, date_text)
                if match:
                    year_str, month_str, day_str = match.groups()
                    year = int(year_str)
                    if year < 100:
                        year += 2000
                    pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
                else:
                    print("⚠ 日付の抽出に失敗しました")
            except Exception as e:
                print(f"⚠ 日付パースに失敗: {e}")
                pub_date = None

            print(pub_date)

            # --- 必須チェック
            if not title or not href:
                print(f"⚠ 必須フィールド欠落のためスキップ（{i+1}件目）: title='{title}', href='{href}'")
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
