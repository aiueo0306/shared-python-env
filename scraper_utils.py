import re
from datetime import datetime, timezone
from urllib.parse import urljoin

def extract_items(page, SELECTOR_DATE, SELECTOR_TITLE, title_selector, title_index, href_selector, href_index, base_url, date_selector, date_index, date_format, date_regex, max_items=10):
    
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

            # タイトル
            title_elem = block1.locator(title_selector).nth(title_index)
            title = title_elem.inner_text().strip()
            print(title)
            
            # URL
            try:
                href = block1.locator(href_selector).nth(href_index).get_attribute("href")
                full_link = urljoin(base_url, href)
            except:
                href = ""
                full_link = base_url
            print(full_link)
            
            # 日付
            # date_selector が空文字や None でない場合 → 子要素探索、それ以外はそのまま
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
            match = re.search(date_regex, date_text)
            print(match)
            if match:
                year_str, month_str, day_str = match.groups()
                year = int(year_str)
                if year < 100:
                    year += 2000  # 2桁西暦 → 2000年以降と仮定
                pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
            else:
                print("⚠ 日付の抽出に失敗しました")
                pub_date = None  # or continue
            
            # match = re.search(date_regex,date_text)
            # if match:
            #     date_str = match.group()
            #     pub_date = datetime.strptime(date_str, date_format).replace(tzinfo=timezone.utc)
            # else:
            #     print("⚠ 日付の抽出に失敗しました")

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
