# browser_utils.py
import re
import time
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DEFAULT_VIEWPORT = {"width": 1366, "height": 900}
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

def click_button_in_order(page, label: str, step_idx: int, timeout_ms: int = 12000) -> bool:
    """
    指定ラベルのボタン/テキストを（iframe含め）探索してクリック。成功で True。
    - ボタン(role=button → get_by_text → CSS) の順に探索
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
                loc = fr.get_by_text(pattern, exact=False)
                if loc.count() > 0 and loc.first.is_visible():
                    appeared = loc.first
                    break
            except Exception:
                pass
            try:
                loc2 = fr.locator(f'button:has-text("{label}")')
                if loc2.count() > 0:
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


def run_popup_sequence(page, labels, wait_between_ms=500, button_timeout_ms=12000):
    """
    複数のポップアップボタンを順に処理。1つでも見つからなければそこで終了。
    """
    for i, label in enumerate(labels, start=1):
        handled = click_button_in_order(page, label, step_idx=i, timeout_ms=button_timeout_ms)
        if handled:
            page.wait_for_timeout(wait_between_ms)
        else:
            break


@contextmanager
def playwright_page(
    headless: bool = True,
    locale: str = "ja-JP",
    viewport: dict = None,
    user_agent: str = None,
    extra_http_headers: dict = None,
):
    """
    Playwright のページコンテキストをコンテキストマネージャで提供。
    例:
        with playwright_page() as page:
            page.goto("https://example.com")
    """
    if viewport is None:
        viewport = DEFAULT_VIEWPORT
    if user_agent is None:
        user_agent = DEFAULT_UA
    if extra_http_headers is None:
        extra_http_headers = {"Accept-Language": "ja,en;q=0.8"}

    with sync_playwright() as p:
        print("▶ ブラウザを起動中...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale=locale,
            viewport=viewport,
            user_agent=user_agent,
            extra_http_headers=extra_http_headers,
        )
        page = context.new_page()
        try:
            yield page
        finally:
            browser.close()


def goto_and_wait(page, url: str, timeout_ms: int = 30000, wait_state: str = "load"):
    """
    URLへ移動して所定のロード状態まで待機。
    - wait_state: "domcontentloaded" / "load" / "networkidle"
    """
    print("▶ ページにアクセス中...")
    try:
        page.goto(url, timeout=timeout_ms)
        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        print("🌐 到達URL:", page.url)
        page.wait_for_load_state(wait_state, timeout=timeout_ms)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        raise
