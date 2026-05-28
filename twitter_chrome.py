"""接管本地 Chrome 操作 Twitter — 无自动化标识，使用真实浏览器指纹。

使用前：
1. 关闭所有 Chrome 窗口
2. 运行 start_chrome_debug.bat（或手动执行）
3. 在打开的 Chrome 里确认 Twitter 已登录
4. 运行本脚本
"""

import time
import random
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright


def human_delay(a=0.8, b=2.5):
    time.sleep(random.uniform(a, b))


def human_type(page, text):
    """模拟真人打字速度"""
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.05, 0.15))


def connect_chrome():
    """连接本地调试模式的 Chrome，返回 (playwright, browser, page)"""
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        # 获取已有的页面，优先找 Twitter
        ctx = browser.contexts[0]
        pages = ctx.pages
        twitter_page = None
        for p in pages:
            if "x.com" in p.url or "twitter.com" in p.url:
                twitter_page = p
                break
        if not twitter_page:
            twitter_page = ctx.new_page()
        return pw, browser, twitter_page
    except Exception as e:
        pw.stop()
        raise RuntimeError(
            f"无法连接 Chrome: {e}\n"
            "请确认：\n"
            "1. 已关闭所有 Chrome 窗口\n"
            "2. 已运行 start_chrome_debug.bat\n"
            "3. Chrome 调试端口是 9222"
        )


def check_login(page) -> bool:
    """检查 Twitter 登录状态"""
    try:
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
        testids = page.evaluate(
            "() => [...document.querySelectorAll('[data-testid]')]"
            ".map(e => e.getAttribute('data-testid'))"
        )
        logged_in_ids = {
            "SideNav_AccountSwitcher_Button", "AppTabBar_Home_Link",
            "tweetTextarea_0", "SideNav_NewTweet_Button",
        }
        return bool(logged_in_ids & set(testids))
    except Exception:
        return False


# ── 功能一：发推文 ────────────────────────────────────────────────────

def post_tweet(text: str, dry_run: bool = True) -> bool:
    pw, browser, page = connect_chrome()
    try:
        print(f"[twitter] 当前页面: {page.url}")

        if not check_login(page):
            print("[twitter] ✗ 未登录，请先在 Chrome 里登录 Twitter")
            return False

        print("[twitter] ✓ 已登录")
        human_delay(1.5, 2.5)

        # 找发推框（多个选择器兼容不同版本）
        clicked = False
        for sel in [
            '[data-testid="tweetTextarea_0"]',
            '[data-testid="SideNav_NewTweet_Button"]',
            'a[href="/compose/post"]',
            '[aria-label="Post"]',
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click(timeout=5000)
                    clicked = True
                    print(f"[twitter] ✓ 点击发推框")
                    human_delay(0.8, 1.5)
                    break
            except Exception:
                continue

        if not clicked:
            # 截图帮助调试
            shot = str(Path.home() / ".ghost" / "twitter_debug.png")
            page.screenshot(path=shot)
            print(f"[twitter] ✗ 找不到发推框，截图: {shot}")
            return False

        # 确保焦点在输入框
        for sel in ['[data-testid="tweetTextarea_0"]', '[role="textbox"]']:
            try:
                page.locator(sel).first.click(timeout=3000)
                break
            except Exception:
                continue
        human_delay(0.3, 0.8)

        # 模拟真人打字
        print(f"[twitter] 输入内容: {text}")
        human_type(page, text)
        human_delay(1.0, 2.0)

        # 截图确认
        shot = str(Path.home() / ".ghost" / "twitter_ready.png")
        page.screenshot(path=shot)
        print(f"[twitter] 截图已保存: {shot}")

        if dry_run:
            print("[twitter] ✓ 测试模式 — 内容已输入，未发送")
            print("[twitter]   改 dry_run=False 可真实发送")
            return True

        # 点击发送
        for sel in [
            '[data-testid="tweetButtonInline"]',
            '[data-testid="tweetButton"]',
        ]:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0:
                    btn.click(timeout=5000)
                    human_delay(2.0, 3.0)
                    shot = str(Path.home() / ".ghost" / "twitter_sent.png")
                    page.screenshot(path=shot)
                    print("[twitter] ✓ 推文发送成功")
                    return True
            except Exception:
                continue

        print("[twitter] ✗ 找不到发送按钮")
        return False

    finally:
        browser.close()
        pw.stop()


# ── 功能二：搜索并点赞 ────────────────────────────────────────────────

def search_and_like(keyword: str, count: int = 3) -> int:
    pw, browser, page = connect_chrome()
    liked = 0
    try:
        if not check_login(page):
            print("[twitter] ✗ 未登录")
            return 0

        url = f"https://x.com/search?q={urllib.parse.quote(keyword)}&f=live"
        page.goto(url, wait_until="domcontentloaded")
        human_delay(2.5, 4.0)
        print(f"[twitter] 搜索: {keyword}")

        attempts = 0
        while liked < count and attempts < 30:
            attempts += 1
            try:
                buttons = page.locator('[data-testid="like"]').all()
                if buttons and liked < len(buttons):
                    buttons[liked].click()
                    liked += 1
                    print(f"[twitter] 点赞 {liked}/{count}")
                    human_delay(4.0, 9.0)
            except Exception:
                pass
            page.mouse.wheel(0, random.randint(300, 600))
            human_delay(1.5, 3.0)

        print(f"[twitter] ✓ 完成，共点赞 {liked} 条")
        return liked
    finally:
        browser.close()
        pw.stop()


# ── 功能三：查看通知 ──────────────────────────────────────────────────

def check_notifications() -> str:
    pw, browser, page = connect_chrome()
    try:
        if not check_login(page):
            return "未登录"
        page.goto("https://x.com/notifications", wait_until="domcontentloaded")
        human_delay(2.0, 3.0)
        shot = str(Path.home() / ".ghost" / "twitter_notifications.png")
        page.screenshot(path=shot)
        items = page.locator('[data-testid="cellInnerDiv"]').all_inner_texts()
        result = "\n".join(items[:8]) if items else "(无通知)"
        print(f"[twitter] 通知:\n{result}")
        return result
    finally:
        browser.close()
        pw.stop()


# ── 主测试 ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Twitter 自动运营 — 接管本地 Chrome")
    print("=" * 50)
    print()
    print("前置条件：")
    print("  1. 已关闭所有 Chrome 窗口")
    print("  2. 已运行 start_chrome_debug.bat")
    print("  3. Chrome 里 Twitter 已登录")
    print()

    # 测试发推（dry_run=True 只输入不发送）
    print("【测试】发推文（测试模式，不真实发送）")
    result = post_tweet(
        text="Testing Ghost AI automation 🤖 #AI #automation",
        dry_run=True,   # ← 改成 False 就会真实发送
    )
    print(f"结果: {'✓ 成功' if result else '✗ 失败'}")
