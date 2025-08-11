コンテンツへとスキップする
チャット履歴

あなた:
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
                    full_link = urljoin(base_url, href)
                except:
                    href = ""
                    full_link = base_url
            else:
                try:
                    href = block1.get_attribute("href")
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

このコードで日付取得ができなかった場合は今日のpuddateはNoneにして、次の処理に回したい
ChatGPT:
この場合、日付が取得できなかったときに pub_date を None にして、そのまま次の処理に回すようにするなら、if match: の else: 内で pub_date = None を明示すればOKです。
例えばこう書き換えれば意図通り動きます。

# 日付解析
match = re.search(date_regex, date_text)

if match:
    year_str, month_str, day_str = match.groups()
    year = int(year_str)
    if year < 100:
        year += 2000  # 2桁西暦は2000年以降と仮定
    pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
else:
    print("⚠ 日付の抽出に失敗しました")
    pub_date = None  # 取得できなかったら None にする

print(pub_date)
このようにすると、日付の抽出に失敗しても pub_date は None で保持され、
その後の

items.append({
    "title": title,
    "link": full_link,
    "description": title,
    "pub_date": pub_date
})
に渡すことができます。
continue せず None のまま次へ進むので、後続処理側で None を見て「日付なし」と判断すればOKです。

もし希望があれば、この extract_items() 関数を例外処理も含めてよりシンプルで安全に書き直したバージョンも作れます。

あなた:
Noneにすると、以下の関数でエラーになるよね？

from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os

def generate_rss(items, output_path, base_url, gakkai_name):
    fg = FeedGenerator()
    fg.title(f"{gakkai_name}トピックス")
    fg.link(href=base_url)
    fg.description(f"{gakkai_name}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)
        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
ChatGPT:
はい、そのまま None を入れると、

item['pub_date'].strftime('%Y%m%d')
の部分で AttributeError: 'NoneType' object has no attribute 'strftime' になります。

なので、generate_rss() 側で pub_date が None の場合の処理を分ける必要があります。

例えば、pub_date が None の場合は以下のように「日付なし」用の代替値を設定できます。

def generate_rss(items, output_path, base_url, gakkai_name):
    fg = FeedGenerator()
    fg.title(f"{gakkai_name}トピックス")
    fg.link(href=base_url)
    fg.description(f"{gakkai_name}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        if item['pub_date'] is not None:
            guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
            entry.pubDate(item['pub_date'])
        else:
            # 日付が無い場合は今日の日付を使う（または固定値でもOK）
            today = datetime.now(timezone.utc)
            guid_value = f"{item['link']}#{today.strftime('%Y%m%d')}"
            entry.pubDate(today)

        entry.guid(guid_value, permalink=False)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
こうすれば extract_items() で pub_date=None にしても安全に処理できますし、RSS側では日付がない記事にもエラーを出さずに対応できます。

もし「日付がない場合は RSS に含めない」という仕様にしたいなら、
generate_rss() のループ内で if item['pub_date'] is None: continue としてスキップも可能です。

どちらの仕様にしますか？

① 日付がない場合は今日の日付で代替

② 日付がない記事はRSSから除外

あなた:
今日の日付ではなくてただlinkだけにしてpermalinkもtrueにして
ChatGPT:
なるほど、
pub_date が None の場合は GUIDをリンクそのものにして permalink=True、
pubDate は付けずにRSSに含めるようにすればいいですね。

修正版はこうなります。

def generate_rss(items, output_path, base_url, gakkai_name):
    fg = FeedGenerator()
    fg.title(f"{gakkai_name}トピックス")
    fg.link(href=base_url)
    fg.description(f"{gakkai_name}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        if item['pub_date'] is not None:
            guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
            entry.guid(guid_value, permalink=False)
            entry.pubDate(item['pub_date'])
        else:
            # 日付がない場合はリンクそのものをGUIDにしてpermalink=True
            entry.guid(item['link'], permalink=True)
            # pubDateは設定しない

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
これなら、日付がない記事でも安全にRSS生成できますし、
GUIDがリンクのみ（permalink=True）になるのでRSSリーダー側でも一意に判別できます。

この仕様だと、extract_items() はそのまま pub_date=None を返してOKです。
希望があれば、extract_items() 側と合わせた完成版のコードにまとめますがそうしますか？

あなた:
s selector "". Did you mean to CSS.escape it?
Call log:
  - waiting for  >> nth=9


⚠ 日付の抽出に失敗しました
None
Traceback (most recent call last):
  File "C:\Users\sato.sota\Desktop\Gakkai_2\RSS18.py", line 79, in <module>
    generate_rss(items, rss_path, BASE_URL, GAKKAI)
  File "C:\Users\SATO~1.SOT\AppData\Local\Temp\shared-python-env\rss_utils.py", line 2, in generate_rss
    fg = FeedGenerator()
         ^^^^^^^^^^^^^
NameError: name 'FeedGenerator' is not defined
ChatGPT:

思考時間: 25s
エラーは2つあります。順番に直しましょ。

1) NameError: name 'FeedGenerator' is not defined
generate_rss を外部モジュール（rss_utils.py）に出したのに、そこで FeedGenerator を import していないのが原因です。rss_utils.py の先頭にこれを足してください。

# rss_utils.py
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os

def generate_rss(items, output_path, base_url, gakkai_name):
    fg = FeedGenerator()
    ...
ついでに、pip install feedgen 済みかも確認を。

2) Playwright の「selector "" Did you mean to CSS.escape it?」
これは 空文字のセレクタ を渡してしまったときに出やすいメッセージです。
今回のコードだと、最上部の

page.wait_for_selector(SELECTOR_TITLE, timeout=10000)
blocks1 = page.locator(SELECTOR_TITLE)
で SELECTOR_TITLE が ""（空）だと即アウトです。
また、blocks2 = page.locator(SELECTOR_DATE) も同様。

さらに、waiting for >> nth=9 は タイトルと日付の件数がズレている ときに、blocks2.nth(i) が存在しない要素を待ち続ける時にも出がちです。

対策（堅牢化パッチ）
セレクタ引数が None や空文字なら例外にする（最低限 TITLE は必須）。

タイトルの件数 と 日付の件数 の最小値でループする。

date_selector が空のときは block2.inner_text() を使う（既にそうしているが、件数ズレ対策が必要）。

差分イメージはこんな感じです。

def extract_items(page, SELECTOR_DATE, SELECTOR_TITLE, 
                  title_selector, title_index, 
                  href_selector, href_index, 
                  base_url, date_selector, date_index, 
                  date_format, date_regex, max_items=10):

    # 0) セレクタの事前バリデーション
    if not SELECTOR_TITLE or not str(SELECTOR_TITLE).strip():
        raise ValueError("SELECTOR_TITLE が空です。必須セレクタなので正しいCSS/XPathを指定してください。")
    if SELECTOR_DATE is None:
        raise ValueError("SELECTOR_DATE が None です。日付ブロックのラッパーは空文字でなく、正しいセレクタを渡してください。")

    page.wait_for_selector(SELECTOR_TITLE, timeout=10000)

    blocks1 = page.locator(SELECTOR_TITLE)
    blocks2 = page.locator(SELECTOR_DATE)

    count1 = blocks1.count()
    count2 = blocks2.count()
    count = min(count1, count2, max_items)

    print(f"📦 発見した記事数(タイトル): {count1}")
    print(f"📅 発見した日付ブロック数: {count2}")
    print(f"🔁 解析対象件数: {count}")

    items = []

    for i in range(count):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i)

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
                    href = block1.get_attribute("href")  # 念のためのフォールバック
            else:
                href = block1.get_attribute("href")

            full_link = urljoin(base_url, href) if href else base_url
            print(full_link)

            # 日付
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
3) pub_date=None のRSS対応（ご指定の仕様）
先ほどの合意どおり、日付なしは GUID=link（permalink=True）、pubDateは付けない にしておきましょう。rss_utils.py の generate_rss はこの形で。

from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os

def generate_rss(items, output_path, base_url, gakkai_name):
    fg = FeedGenerator()
    fg.title(f"{gakkai_name}トピックス")
    fg.link(href=base_url)
    fg.description(f"{gakkai_name}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        if item['pub_date'] is not None:
            guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
            entry.guid(guid_value, permalink=False)
            entry.pubDate(item['pub_date'])
        else:
            entry.guid(item['link'], permalink=True)
            # pubDateは設定しない

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
これで

FeedGenerator の NameError は解消

空セレクタ/件数ズレによる Playwright エラーを回避

pub_date=None でもRSS生成OK

の3点がまとまって直せます。必要なら、実際のセレクタ値（SELECTOR_TITLE / SELECTOR_DATE / title_selector / date_selector）を教えてくれれば、もう一歩突っ込んだセレクタ調整もやります。

あなた:
<a href="topic/20250807.pdf" target="_blank">京都大学　教員公募のお知らせ（2025/8/7）</a>

SELECTOR_DATE = "div#main_left li"
date_selector = "a"
date_index = 0
year_unit = "/"
month_unit = "/"
day_unit = ""
date_format = f"%Y{year_unit}%m{month_unit}%d{day_unit}"
date_regex = rf"(\d{{2,4}}){year_unit}(\d{{1,2}}){month_unit}(\d{{1,2}}){day_unit}"

これで日付部分正規表現で取り出せるはずだよね？
ChatGPT:
はい、そのHTMLとパラメータなら、その date_regex で日付部分はちゃんと取れるはずです。

理由
あなたのHTML:

<a href="topic/20250807.pdf" target="_blank">
  京都大学　教員公募のお知らせ（2025/8/7）
</a>
この中の日付部分は 2025/8/7 です。

あなたの date_regex:

rf"(\d{{2,4}}){year_unit}(\d{{1,2}}){month_unit}(\d{{1,2}}){day_unit}"
year_unit = "/"
month_unit = "/"
day_unit = ""

なので展開後は:

r"(\d{2,4})/(\d{1,2})/(\d{1,2})"
確認
import re
html_text = '京都大学　教員公募のお知らせ（2025/8/7）'
date_regex = r"(\d{2,4})/(\d{1,2})/(\d{1,2})"

match = re.search(date_regex, html_text)
if match:
    print(match.groups())
出力:

('2025', '8', '7')
補足
もし re.search でマッチしない場合は、
HTML内の全角スラッシュや全角数字、あるいは全角括弧が混ざっている可能性があります。
特に全角スラッシュ "／" だと "/" の正規表現には一致しません。

その場合は、事前に全角→半角変換すると安定します。

import unicodedata
text = unicodedata.normalize("NFKC", html_text)
必要なら、私のほうでこの正規表現を全角数字や全角スラッシュにも対応する形に直すこともできます。
そうしますか？

あなた:
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
                    full_link = urljoin(base_url, href)
                except:
                    href = ""
                    full_link = base_url
            else:
                try:
                    href = block1.get_attribute("href")
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

このコードを基軸として


from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://jasweb.or.jp/"
GAKKAI = "日本喘息学会"

selector = "dd"
TITLE_SELECTOR = "a"
TITLE_index= 0
href_SELECTOR = "a"
href_index = 0

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title(f"{GAKKAI}トピックス")
    fg.link(href=BASE_URL)
    fg.description(f"{GAKKAI}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        entry.guid(item['link'], permalink=True)
        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

def extract_items(page):
    # iframeを待機して取得
    page.wait_for_selector("iframe", timeout=10000)
    iframe_element = page.locator("iframe").first.element_handle()

    if iframe_element is None:
        print("⚠ iframeが見つかりませんでした")
        return []

    frame = iframe_element.content_frame()
    if frame is None:
        print("⚠ iframeの中身（frame）がまだ読み込まれていません")
        return []

    frame.wait_for_selector(selector, timeout=10000)

    blocks = frame.locator(selector)
    count = blocks.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    max_items = 10
    for i in range(min(count, max_items)):
        try:
            block = blocks.nth(i)
            pub_date = datetime.now(timezone.utc)
            title = block.locator(TITLE_SELECTOR).nth(TITLE_index).inner_text().strip()

            try:
                href = block.locator(href_SELECTOR).nth(href_index).get_attribute("href")
                full_link = urljoin(BASE_URL, href)
            except:
                href = ""
                full_link = BASE_URL

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

with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 記事を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠ 抽出できた記事がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/Feed3.xml"
    generate_rss(items, rss_path)
    browser.close()

このコードの該当部分のIframeに関して対応できるように変更したい


ChatGPT:

思考時間: 21s
いいね、iframe内でも動く汎用版にしておきます。
extract_items に iframe_selector（省略可）を追加して、指定があればその iframe の Frame 上でセレクタ探索を行うようにしました。未指定なら従来どおりページ直下を探索します。ついでに pub_date=None のときは guid=link(permalink=True) にして pubDate は付けないように generate_rss も調整しています。

import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def _get_root_context(page, iframe_selector=None, iframe_index=0, timeout=10000):
    """
    iframe_selector が指定されていれば、その iframe の content_frame を返す。
    指定が無ければ page をそのまま返す。
    """
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
    """
    汎用抽出。iframe_selector を渡すと、その iframe 内で SELECTOR_* を探索する。
    """
    root = _get_root_context(page, iframe_selector=iframe_selector, iframe_index=iframe_index, timeout=iframe_timeout)

    # まずタイトル側の存在を待機
    root.wait_for_selector(SELECTOR_TITLE, timeout=10000)

    blocks1 = root.locator(SELECTOR_TITLE)
    blocks2 = root.locator(SELECTOR_DATE)

    count1 = blocks1.count()
    count2 = blocks2.count()
    total = min(count1, count2, max_items)

    print(f"📦 発見した記事数(タイトル): {count1}")
    print(f"📅 発見した日付ブロック数: {count2}")
    print(f"🔁 解析対象件数: {total}")

    items = []

    for i in range(total):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i)

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
# ── こちらは RSS 生成側（pub_date=None の時は guid=link, permalink=True / pubDateなし）
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os

BASE_URL = "https://jasweb.or.jp/"
GAKKAI = "日本喘息学会"

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title(f"{GAKKAI}トピックス")
    fg.link(href=BASE_URL)
    fg.description(f"{GAKKAI}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        if item['pub_date'] is not None:
            guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
            entry.guid(guid_value, permalink=False)
            entry.pubDate(item['pub_date'])
        else:
            entry.guid(item['link'], permalink=True)
            # pubDate は付けない

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
使い方（今回のサイト例：iframe 内の dd → a）
# 例：京都大学のように iframe 内の <dd><a>…</a> を読むケース
items = extract_items(
    page,
    SELECTOR_DATE="dd",
    SELECTOR_TITLE="dd",
    title_selector="a",
    title_index=0,
    href_selector="a",
    href_index=0,
    base_url=BASE_URL,
    date_selector="a",
    date_index=0,
    date_format="%Y/%m/%d",
    date_regex=r"(\d{2,4})/(\d{1,2})/(\d{1,2})",
    max_items=10,
    iframe_selector="iframe",   # ← ここを指定すると iframe 内で探索
    iframe_index=0,
    iframe_timeout=10000
)
これで、同じ関数のまま 直下／iframe のどちらにも対応できます。必要なら、全角混じりの日付（全角スラッシュや全角数字）にも耐える前処理（NFKC正規化）を足すパッチも出しますよ。




選択されていません選択されていません
ChatGPT の回答は必ずしも正しいとは限りません。OpenAI はモデルの学習に CSD ワークスペース データを使用しません。
