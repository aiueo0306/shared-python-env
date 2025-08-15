import re
from datetime import datetime, timezone
from urllib.parse import urljoin

def _get_first_text_in_parent(parent_locator, selector, start_index=0):
    """
    親ロケータ内の selector に一致する要素を start_index から順に調べ、
    最初にテキストを取得できた要素のテキストを返す（親範囲外には出ない）
    """
    try:
        elements = parent_locator.locator(selector)
        count = elements.count()
    except Exception:
        return ""
    for idx in range(start_index, count):
        try:
            txt = elements.nth(idx).inner_text().strip()
            if txt:
                return txt
        except Exception:
            continue
    return ""

def _get_first_attr_in_parent(parent_locator, selector, attr, start_index=0):
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
    SELECTOR_DATE,
    SELECTOR_TITLE,
    title_selector,
    title_index,
    href_selector,
    href_index,
    base_url,
    date_selector,
    date_index,
    date_format,  # 互換のため残す（未使用）
    date_regex,
    max_items=10
):
    page.wait_for_selector(SELECTOR_TITLE, timeout=10000)

    blocks1 = page.locator(SELECTOR_TITLE)
    count = blocks1.count()

    print(f"📦 発見した記事数: {count}")
    items = []

    blocks2 = page.locator(SELECTOR_DATE)

    for i in range(min(count, max_items)):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i)

            # --- タイトル（親<li>の範囲内で title_index から次候補を探索）
            if title_selector:
                title = _get_first_text_in_parent(block1, title_selector, title_index)
            else:
                # セレクタ未指定なら親自身のテキスト
                try:
                    title = block1.inner_text().strip()
                except Exception:
                    title = ""
            print(title)

            # --- URL（親<li>の範囲内で href_index から次候補を探索）
            href = _get_first_attr_in_parent(block1, href_selector, "href", href_index)
            if href:
                full_link = urljoin(base_url, href)
            else:
                full_link = base_url
            print(full_link)

            # --- 日付テキスト（親<li>/日付ブロックの範囲内で date_index から次候補を探索）
            if date_selector:
                date_text = _get_first_text_in_parent(block2, date_selector, date_index)
            else:
                try:
                    date_text = block2.inner_text().strip()
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
                        year += 2000  # 2桁西暦は2000年以降と仮定
                    pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
                else:
                    print("⚠ 日付の抽出に失敗しました")
            except Exception as e:
                print(f"⚠ 日付パースに失敗: {e}")
                pub_date = None

            print(pub_date)

            # --- 必須フィールドチェック
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
