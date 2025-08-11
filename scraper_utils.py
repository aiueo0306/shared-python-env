import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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
    iframe_selector=None,   # 例: "iframe" / "iframe#ifm1"
    iframe_index=0
):
    if not SELECTOR_TITLE or not str(SELECTOR_TITLE).strip():
        raise ValueError("SELECTOR_TITLE が空です。")

    # --- rootLoc: page か frame_locator のどちらかを用意 ---
    if iframe_selector:
        # iframe内の要素を直接狙う: frame_locator(...).locator(...)
        root_loc = page.frame_locator(iframe_selector).nth(iframe_index)
        title_loc = root_loc.locator(SELECTOR_TITLE)
        # visible ではなく attached でまず存在を待つ
        title_loc.first.wait_for(state="attached", timeout=10000)
    else:
        # ページ直下
        title_loc = page.locator(SELECTOR_TITLE)
        title_loc.first.wait_for(state="attached", timeout=10000)

    blocks1 = title_loc
    count1 = blocks1.count()

    # SELECTOR_DATE が無ければタイトル側を日付の母要素として使う
    use_block1_for_date = (not SELECTOR_DATE) or (not str(SELECTOR_DATE).strip())
    if use_block1_for_date:
        blocks2 = None
        count2 = count1
    else:
        if iframe_selector:
            date_loc = root_loc.locator(SELECTOR_DATE)
        else:
            date_loc = page.locator(SELECTOR_DATE)
        # こちらも存在だけ待つ
        date_loc.first.wait_for(state="attached", timeout=10000)
        blocks2 = date_loc
        count2 = blocks2.count()

    total = min(count1, count2, max_items)
    print(f"📦 発見した記事数(タイトル): {count1}")
    print(f"📅 発見した日付ブロック数: {count2} ({'TITLEフォールバック' if use_block1_for_date else 'DATEセレクタ使用'})")
    print(f"🔁 解析対象件数: {total}")

    items = []

    for i in range(total):
        try:
            block1 = blocks1.nth(i)
            block2 = block1 if use_block1_for_date else blocks2.nth(i)

            # タイトル
            if title_selector:
                title = block1.locator(title_selector).nth(title_index).inner_text().strip()
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
                    print(f"⚠ 日付セレクター取得失敗: {e}")
                    date_text = ""
            else:
                try:
                    date_text = block2.inner_text().strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得失敗: {e}")
                    date_text = ""

            print(date_text)

            # 正規表現で抽出（取れないときは None）
            m = re.search(date_regex, date_text) if date_regex else None
            if m:
                y, mo, d = m.groups()
                y = int(y)
                if y < 100:
                    y += 2000
                pub_date = datetime(y, int(mo), int(d), tzinfo=timezone.utc)
            else:
                pub_date = None
                print("⚠ 日付の抽出に失敗しました")

            print(pub_date)

            if not title or not href:
                print(f"⚠ スキップ（{i+1}行目）: title='{title}', href='{href}'")
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
