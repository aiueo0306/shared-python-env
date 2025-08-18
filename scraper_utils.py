import re
from datetime import datetime, timezone
from urllib.parse import urljoin

# ------- 追加: 全角→半角、2桁西暦補正などのユーティリティ -------
_ZEN2HAN = str.maketrans("０１２３４５６７８９", "0123456789")

def _to_halfwidth_digits(s: str) -> str:
    return (s or "").translate(_ZEN2HAN)

def _safe_int(x: str) -> int:
    return int(_to_halfwidth_digits(x))

def _coerce_year(y: int) -> int:
    # 2桁西暦は 2000年代扱い（必要なら調整）
    return y + 2000 if y < 100 else y

def parse_pub_date(date_text: str, date_patterns: list):
    """
    複数パターンを順に試して UTC の datetime を返す。
    date_patterns: [{
        "regex": r"...",          # キャプチャは2 or 3個想定
        "order": "YMD|MDY|DMY|YM",# groupsの意味順
        "allow_missing_day": bool # Trueなら日欠損を day=1 で補完（YM 等）
    }, ...]
    """
    txt = _to_halfwidth_digits((date_text or "").strip())
    if not txt or not date_patterns:
        return None

    for pat in date_patterns:
        try:
            rgx = pat.get("regex")
            order = (pat.get("order") or "YMD").upper()
            allow_missing_day = bool(pat.get("allow_missing_day", False))
            if not rgx:
                continue

            m = re.search(rgx, txt, re.IGNORECASE)
            if not m:
                continue

            groups = list(m.groups())

            # 2グループ（例: YYYY.MM）の場合に日を補完
            if len(groups) == 2 and allow_missing_day:
                if order == "YM":
                    groups = [groups[0], groups[1], "1"]  # Y, M, (D=1)
                elif order == "MY":
                    groups = [groups[1], groups[0], "1"]  # (Yに入れ替え), M, D=1

            if len(groups) != 3:
                continue

            # Y/M/D の値を order に従って決定
            idx = {"Y": order.index("Y"), "M": order.index("M"), "D": order.index("D")}
            gY, gM, gD = groups[idx["Y"]], groups[idx["M"]], groups[idx["D"]]

            year = _coerce_year(_safe_int(gY))
            month = _safe_int(gM)
            day = _safe_int(gD)

            return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
        except Exception:
            continue

    return None

# ------- 既存ヘルパー -------
def _get_first_text_in_parent(parent_locator, selector, start_index=0):
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
        try:
            val = parent_locator.get_attribute(attr)
            return val
        except Exception:
            return None

# ------- ここを拡張（date_patterns 追加 & 後方互換維持） -------
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
    date_format,  # 互換のため残す（未使用でもOK）
    date_regex,
    max_items=10,
    date_patterns=None  # ← 追加（複数パターン用）
):
    # --- ページ安定化 & 可視を要求しない待機（DOMにアタッチされればOK）
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector(SELECTOR_TITLE, state="attached", timeout=30000)

    blocks1 = page.locator(SELECTOR_TITLE)
    count_titles = blocks1.count()
    print(f"📦 発見した記事数(タイトル側): {count_titles}")

    items = []

    # 日付セレクタは存在しない/別行数の可能性があるため独立して扱う
    blocks2 = page.locator(SELECTOR_DATE) if SELECTOR_DATE else None
    count_dates = blocks2.count() if blocks2 else 0
    print(f"🗓 取得可能な日付ブロック数: {count_dates}")

    row_count = min(count_titles, max_items)
    for i in range(row_count):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i) if blocks2 and i < count_dates else None

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
            full_link = urljoin(base_url, href) if href else base_url
            print(full_link)

            # --- 日付テキスト（title列とdate列の行ズレに耐える）
            date_text = ""
            target_for_date = block2 if block2 else block1  # 無ければ同じ行のタイトル側からも探す
            if date_selector:
                date_text = _get_first_text_in_parent(target_for_date, date_selector, date_index)
            else:
                try:
                    date_text = (target_for_date.text_content() or "").strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得に失敗: {e}")
                    date_text = ""

            print(date_text)

            # --- 日付パース（複数パターン or 従来ロジック）
            pub_date = None
            try:
                if date_patterns:
                    pub_date = parse_pub_date(date_text, date_patterns)
                else:
                    # 従来ロジック（後方互換）
                    match = re.search(date_regex, date_text)
                    if match:
                        groups = match.groups()
                        if len(groups) == 3:
                            # case1: YYYY-MM-DD 形式
                            if groups[0].isdigit():
                                year_str, month_str, day_str = groups
                                year = int(year_str)
                                if year < 100:
                                    year += 2000  # 2桁西暦は2000年以降と仮定
                                pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
                            # case2: Mon DD, YYYY 形式 (例: Aug 6, 2025)
                            else:
                                month_str, day_str, year_str = groups
                                pub_date = datetime.strptime(
                                    f"{month_str} {day_str}, {year_str}", "%b %d, %Y"
                                ).replace(tzinfo=timezone.utc)
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
                # "link": full_link,
                "link": base_url,
                "description": title,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items
