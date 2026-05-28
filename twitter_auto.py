"""Twitter 自动运营 — Cookie 注入方式，模拟真人操作。"""

import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path.home() / ".ghost" / "twitter_profile")
Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

# 从 Hubstudio 导出的 x.com 登录 Cookie
TWITTER_COOKIES = [
    {"name": "auth_token",      "value": "e35b51f093d1a019398624e2748ddb35c3b5aa0b", "domain": ".x.com", "path": "/", "secure": True,  "httpOnly": True,  "sameSite": "None"},
    {"name": "ct0",             "value": "ef650376e8cc277129bb2175ffdabcb75cba3e1da78c252f0a00160e4160e0a5210573bbcbd1e146553cc64f96fa74b14bb60c0be4b256643164639f9e1cf5d13a56afc86b1d68bfbbca5c78a721ecfb", "domain": ".x.com", "path": "/", "secure": True,  "httpOnly": False, "sameSite": "Lax"},
    {"name": "twid",            "value": "u%3D735844381",                              "domain": ".x.com", "path": "/", "secure": True,  "httpOnly": False, "sameSite": "None"},
    {"name": "kdt",             "value": "zAUdzdKPDx9VveaArHqBMil1hrpJRvCCXs1rNKLB",  "domain": ".x.com", "path": "/", "secure": True,  "httpOnly": True,  "sameSite": "None"},
    {"name": "att",             "value": "1-r5ga76SK30V7ogmUwhYBpFu2RaK5SmYrQi6I6yeo","domain": ".x.com", "path": "/", "secure": True,  "httpOnly": True,  "sameSite": "None"},
    {"name": "_twitter_sess",   "value": "BAh7CCIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNoSGFzaHsABjoKQHVzZWR7ADofbGFzdF9wYXNzd29yZF9jb25maXJtYXRpb24iATE3NzkxOTc3MjAwNjQwMDA6HnBhc3N3b3JkX2NvbmZpcm1hdGlvbl91aWQiDjczNTg0NDM4MQ%253D%253D--a7dffa187949aa8396cebf532e3d6ab505987a80", "domain": ".x.com", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
    {"name": "gt",              "value": "2051333285737857205",                        "domain": ".x.com", "path": "/", "secure": True,  "httpOnly": False, "sameSite": "None"},
    {"name": "__cuid",          "value": "ab90c61ef587412594c079269a9ea3d6",           "domain": ".x.com", "path": "/", "secure": False, "httpOnly": False, "sameSite": "None"},
    {"name": "lang",            "value": "zh-CN",                                      "domain": "x.com",  "path": "/", "secure": False, "httpOnly": False, "sameSite": "None"},
]


def human_delay(a=0.8, b=2.5):
    time.sleep(random.uniform(a, b))


def human_type(page, text):
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.04, 0.13))


def get_page():
    """启动浏览器并注入 Cookie，返回已登录的 page。"""
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 先访问 x.com 建立域名上下文
    page.goto("https://x.com", wait_until="domcontentloaded", timeout=30000)
    time.sleep(1)

    # 注入 Cookie
    ctx.add_cookies(TWITTER_COOKIES)

    # 刷新使 Cookie 生效
    page.reload(wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    return pw, ctx, page


def check_login(page) -> bool:
    """检查是否已登录。"""
    url = page.url
    testids = page.evaluate(
        "() => [...document.querySelectorAll('[data-testid]')].map(e=>e.getAttribute('data-testid'))"
    )
    logged_in_ids = {"SideNav_AccountSwitcher_Button", "AppTabBar_Home_Link",
                     "tweetTextarea_0", "SideNav_NewTweet_Button"}
    return bool(logged_in_ids & set(testids)) and "login" not in url


# ── 功能一：发推文 ────────────────────────────────────────────────────

def post_tweet(text: str, dry_run: bool = True) -> bool:
    pw, ctx, page = get_page()
    try:
        if not check_login(page):
            print("[twitter] ✗ 未登录，Cookie 可能已过期")
            page.screenshot(path=str(Path.home() / ".ghost" / "twitter_login_fail.png"))
            return False

        print(f"[twitter] ✓ 已登录")
        page.goto("https://x.com/home", wait_until="domcontentloaded")
        human_delay(2.0, 3.5)

        # 找发推框
        clicked = False
        for sel in [
            '[data-testid="tweetTextarea_0"]',
            '[data-testid="SideNav_NewTweet_Button"]',
            'a[href="/compose/post"]',
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click(timeout=5000)
                    clicked = True
                    print(f"[twitter] 点击发推框: {sel}")
                    human_delay(0.8, 1.5)
                    break
            except Exception:
                continue

        if not clicked:
            print("[twitter] ✗ 找不到发推框，截图查看")
            page.screenshot(path=str(Path.home() / ".ghost" / "twitter_no_compose.png"))
            return False

        # 确保焦点在输入框
        for sel in ['[data-testid="tweetTextarea_0"]', '[role="textbox"]']:
            try:
                page.locator(sel).first.click(timeout=3000)
                break
            except Exception:
                continue
        human_delay(0.3, 0.8)

        # 打字
        print(f"[twitter] 输入: {text}")
        human_type(page, text)
        human_delay(1.0, 2.0)

        # 截图确认
        page.screenshot(path=str(Path.home() / ".ghost" / "twitter_ready_to_post.png"))
        print(f"[twitter] 截图: ~/.ghost/twitter_ready_to_post.png")

        if dry_run:
            print("[twitter] ✓ 测试模式 — 内容已输入，未发送（dry_run=True）")
            return True

        # 发送
        for sel in ['[data-testid="tweetButtonInline"]', '[data-testid="tweetButton"]']:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0:
                    btn.click(timeout=5000)
                    human_delay(2.0, 3.0)
                    page.screenshot(path=str(Path.home() / ".ghost" / "twitter_posted.png"))
                    print("[twitter] ✓ 推文发送成功")
                    return True
            except Exception:
                continue

        print("[twitter] ✗ 找不到发送按钮")
        return False

    finally:
        human_delay(1.0, 2.0)
        ctx.close()
        pw.stop()


# ── 功能二：搜索并点赞 ────────────────────────────────────────────────

def search_and_like(keyword: str, count: int = 3) -> int:
    pw, ctx, page = get_page()
    liked = 0
    try:
        if not check_login(page):
            print("[twitter] ✗ 未登录")
            return 0

        import urllib.parse
        url = f"https://x.com/search?q={urllib.parse.quote(keyword)}&f=live"
        page.goto(url, wait_until="domcontentloaded")
        human_delay(2.5, 4.0)

        attempts = 0
        while liked < count and attempts < 30:
            attempts += 1
            try:
                buttons = page.locator('[data-testid="like"]').all()
                if buttons and liked < len(buttons):
                    buttons[liked].click()
                    liked += 1
                    print(f"[twitter] 点赞 {liked}/{count}")
                    human_delay(4.0, 9.0)  # 点赞间隔要长，避免风控
            except Exception:
                pass
            page.mouse.wheel(0, random.randint(300, 600))
            human_delay(1.5, 3.0)

        print(f"[twitter] ✓ 完成，共点赞 {liked} 条")
        return liked
    finally:
        ctx.close()
        pw.stop()


# ── 功能三：查看通知 ──────────────────────────────────────────────────

def check_notifications() -> str:
    pw, ctx, page = get_page()
    try:
        if not check_login(page):
            return "未登录"
        page.goto("https://x.com/notifications", wait_until="domcontentloaded")
        human_delay(2.0, 3.0)
        page.screenshot(path=str(Path.home() / ".ghost" / "twitter_notifications.png"))
        items = page.locator('[data-testid="cellInnerDiv"]').all_inner_texts()
        result = "\n".join(items[:8]) if items else "(无通知)"
        print(f"[twitter] 通知:\n{result}")
        return result
    finally:
        ctx.close()
        pw.stop()


# ── 主测试 ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Twitter 自动运营测试")
    print("=" * 50)
    print()

    # 测试1：发推（dry_run=True 只输入不发送）
    print("【测试1】发推文（测试模式，不真实发送）")
    result = post_tweet(
        text="Testing Ghost AI automation 🤖 #AI #automation",
        dry_run=True   # 改成 False 就会真实发送
    )
    print(f"结果: {'✓ 成功' if result else '✗ 失败'}")
    print()
