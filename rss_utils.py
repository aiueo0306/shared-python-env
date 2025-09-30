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

        # 表示用リンクは常に base_url（元のコードに忠実）
        entry.title(title)
        entry.link(href=base_url)
        entry.description(desc)

        if pub_date is not None:
            ymd = pub_date.strftime('%Y%m%d')
        
            entry.link(href=f"{base_url}")
        
            if link:
                entry.guid(f"{title}#{ymd}", permalink=False)
                # entry.guid(f"{link}#{ymd}", permalink=False)
            else:
                entry.guid(f"{title}#{ymd}", permalink=False)
        
            entry.pubDate(pub_date)
        else:
            # pub_date がない場合
            entry.link(href=f"{base_url}")
            if link:
                entry.guid(link, permalink=False)
            else:
                digest = sha1(f"{base_url}|{title}".encode('utf-8')).hexdigest()
                entry.guid(f"urn:newsitem:{digest}", permalink=False)

    dirpath = os.path.dirname(output_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")
