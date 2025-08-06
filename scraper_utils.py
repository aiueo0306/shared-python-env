from datetime import datetime, timezone
from urllib.parse import urljoin

def extract_items(page, selector,counter, title_selector, title_index, href_selector, href_index, base_url, date_selector, date_index, date_format,max_items=10):
    page.wait_for_selector(selector, timeout=10000)
    
    blocks = page.locator(selector)
    counts = page.locator(counter)
    count = counts.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    for i in range(min(count, max_items)):
        try:
            block = blocks.nth(i)

            date_text = block.locator(date_selector).nth(date_index).inner_text().strip()
            pub_date = datetime.strptime(date_text, date_format).replace(tzinfo=timezone.utc)

            title = block.locator(title_selector).nth(title_index).inner_text().strip()

            try:
                href = block.locator(href_selector).nth(href_index).get_attribute("href")
                full_link = urljoin(base_url, href)
            except:
                href = ""
                full_link = base_url

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
