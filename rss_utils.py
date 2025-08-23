from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from hashlib import sha1
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
        title = item.get('title') or ''
        link = item.get('link') or None
        desc = item.get('description') or title
        pub_date = item.get('pub_date')

        # エントリの表示用リンク：あればそれ、なければ base_url
        entry.title(title)
        entry.link(href=link or base_url)
        entry.description(desc)

        if pub_date is not None:
            # pub_date あり → permalink=False で (リンク or base_url)#YYYYMMDD をGUIDに
            guid_value = f"{(link or base_url)}#{pub_date.strftime('%Y%m%d')}"
            entry.guid(guid_value, permalink=False)
            entry.pubDate(pub_date)
        else:
            if link:
                # pub_date なし & リンクあり → リンク自体をGUID（permalink=True）
                entry.guid(link, permalink=True)
            else:
                # pub_date なし & リンクなし → タイトルから安定GUID（permalink=False）
                # base_url とタイトルで安定ハッシュを作成（衝突回避用に prefix を付加）
                digest = sha1(f"{base_url}|{title}".encode('utf-8')).hexdigest()
                entry.guid(f"urn:newsitem:{digest}", permalink=False)
                # pubDate は設定しない

    dirpath = os.path.dirname(output_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
