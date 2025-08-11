import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def _get_root_context(page, iframe_selector=None, iframe_index=0, timeout=10000):
    if not iframe_selector:
        return page  # ページ直下で探索

    # iframe を待って取得
    page.wait_for_selector(iframe_selector, timeout=timeout)
    iframe_loc = page.locator(iframe_selector).nth(iframe_index)
    handle = iframe_loc.element_handle()
    if handle is None:
        raise RuntimeError("iframe要素のハンドル取得に失敗しました。selector / index を確認してください。")
    frame = handle.content_frame()
    if frame is None:
        raise RuntimeError("iframeのcontent_frameがまだ読み込まれていません。少し待つかselectorを見直してください。")
    return frame

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
    date_format,
    date_regex,
    max_items=10,
    *,
    iframe_selector=None,
    iframe_index=0,
    iframe_timeout=10000
):
    root = _get_root_context(page, iframe_selector=iframe_selector,
                             iframe_index=iframe_index, timeout=iframe_timeout)

    # 必須: タイトル側は待つ
    if not SELECTOR_TITLE or not str(SELECTOR_TITLE).strip():
        raise ValueError("SELECTOR_TITLE が空です。正しいセレクタを指定してください。")
    root.wait_for_selector(SELECTOR_TITLE, timeout=10000)

    blocks1 = root.locator(SELECTOR_TITLE)

    # ★ ここがポイント: SELECTOR_DATE が空/Noneなら blocks2 は使わず、後で block1 を使う
    use_block1_for_date = (not SELECTOR_DATE) or (not str(SELECTOR_DATE).strip())
    if not use_block1_for_date:
        blocks2 = root.locator(SELECTOR_DATE)
        count2 = blocks2.count()
    else:
        blocks2 = None
        count2 = blocks1.count()

    count1 = blocks1.count()
    total = min(count1, count2, max_items)

    print(f"📦 発見した記事数(タイトル): {count1}")
    print(f"📅 発見した日付ブロック数: {count2} ({'TITLEを使うフォールバック' if use_block1_for_date else 'DATEセレクタ使用'})")
    print(f"🔁 解析対象件数: {total}")

    items = []

    for i in range(total):
        try:
            block1 = blocks1.nth(i)
            # ★ DATEセレクタが無ければ、日付抽出も block1 を母要素にする
            block2 = block1 if use_block1_for_date else blocks2.nth(i)

            # タイトル
            if title_selector:
                title_elem = block1.locator(title_selector).nth(title_index)
                title = title_elem.inner_text().strip()
            else:
                title = block1.inner_text().strip()
            print(title)

            # URL
            if title_selector:
                try:
                    href = block1.locator(href_selector).nth(href_index).get_attribute("href")
                except:
                    href = block1.get_attribute("href")
            else:
                href = block1.get_attribute("href")
            full_link = urljoin(base_url, href) if href else base_url
            print(full_link)

            # 日付テキスト
            if date_selector:
                try:
                    date_text = block2.locator(date_selector).nth(date_index).inner_text().strip()
                except Exception as e:
                    print(f"⚠ 日付セレクターによる取得に失敗: {e}")
                    date_text = ""
            else:
                try:
                    date_text = block2.inner_text().strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得に失敗: {e}")
                    date_text = ""
            print(date_text)

            # 正規表現で抽出
            match = re.search(date_regex, date_text)
            if match:
                year_str, month_str, day_str = match.groups()
                year = int(year_str)
                if year < 100:
                    year += 2000
                pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
            else:
                print("⚠ 日付の抽出に失敗しました")
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
