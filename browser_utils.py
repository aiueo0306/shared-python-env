def click_button_in_order(page, label: str, step_idx: int, timeout_ms: int = 12000, delay_before_click_ms: int = 0) -> bool:
    """
    指定ラベルの要素（ボタン/リンク/その他）を探索してクリック。成功で True。
    - ボタン(role=button) → リンク(role=link) → 汎用テキスト → CSS:has-text の順に探索
    - 可視要素を優先
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    appeared = None
    pattern = re.compile(re.escape(label), re.I)

    def _frames():
        yield page
        for fr in page.frames:
            yield fr

    while time.time() < deadline and appeared is None:
        for fr in _frames():
            try:
                btn = fr.get_by_role("button", name=pattern)
                if btn.count() > 0 and btn.first.is_visible():
                    appeared = btn.first
                    break
            except Exception:
                pass
            try:
                link = fr.get_by_role("link", name=pattern)
                if link.count() > 0 and link.first.is_visible():
                    appeared = link.first
                    break
            except Exception:
                pass
            try:
                loc = fr.get_by_text(pattern, exact=False)
                if loc.count() > 0 and loc.first.is_visible():
                    appeared = loc.first
                    break
            except Exception:
                pass
            try:
                loc2 = fr.locator(f':has-text("{label}")')
                if loc2.count() > 0 and loc2.first.is_visible():
                    appeared = loc2.first
                    break
            except Exception:
                pass
        if appeared:
            break
        page.wait_for_timeout(250)

    if not appeared:
        print(f"ℹ ポップアップ[{step_idx}] '{label}' は {timeout_ms}ms 以内に表示されませんでした")
        return False

    try:
        if delay_before_click_ms > 0:
            page.wait_for_timeout(delay_before_click_ms)

        appeared.click(timeout=4000)
        print(f"✅ ポップアップ[{step_idx}] クリック: {label}")
        return True
    except Exception:
        try:
            appeared.click(force=True, timeout=3000)
            print(f"✅ ポップアップ[{step_idx}] 強制クリック: {label}")
            return True
        except Exception as e:
            print(f"⚠ ポップアップ[{step_idx}] クリック失敗: {label} ({e})")
            return False
