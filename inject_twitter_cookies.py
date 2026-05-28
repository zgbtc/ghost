"""把 Twitter Cookie 注入到 Playwright profile，实现免登录操作。"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path.home() / ".ghost" / "twitter_profile")
Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

# Twitter 登录所需的核心 Cookie（从浏览器导出）
TWITTER_COOKIES = [
    {
        "name": "auth_token",
        "value": "e35b51f093d1a019398624e2748ddb35c3b5aa0b",
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "None",
    },
    {
        "name": "ct0",
        "value": "ef650376e8cc277129bb2175ffdabcb75cba3e1da78c252f0a00160e4160e0a5210573bbcbd1e146553cc64f96fa74b14bb60c0be4b256643164639f9e1cf5d13a56afc86b1d68bfbbca5c78a721ecfb",
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "sameSite": "Lax",
    },
    {
        "name": "twid",
        "value": "u%3D735844381",
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "sameSite": "None",
    },
    {
        "name": "kdt",
        "value": "zAUdzdKPDx9VveaArHqBMil1hrpJRvCCXs1rNKLB",
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "None",
    },
    {
        "name": "att",
        "value": "1-r5ga76SK30V7ogmUwhYBpFu2RaK5SmYrQi6I6yeo",
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "None",
    },
    {
        "name": "gt",
        "value": "2051333285737857205",
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "sameSite": "None",
    },
    {
        "name": "lang",
        "value": "zh-CN",
        "domain": "x.com",
        "path": "/",
        "secure": False,
        "httpOnly": False,
        "sameSite": "None",
    },
]

print("[inject] 注入 Twitter Cookie 到 Playwright profile...")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 先访问 x.com 建立域名上下文
    page.goto("https://x.com", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)

    # 注入 Cookie
    ctx.add_cookies(TWITTER_COOKIES)
    print(f"[inject] ✓ 注入 {len(TWITTER_COOKIES)} 个 Cookie")

    # 刷新页面验证登录状态
    page.reload(wait_until="domcontentloaded")
    time.sleep(3)

    current_url = page.url
    print(f"[inject] 当前 URL: {current_url}")

    # 截图
    shot = str(Path.home() / ".ghost" / "twitter_injected.png")
    page.screenshot(path=shot)
    print(f"[inject] 截图: {shot}")

    # 检查登录状态
    testids = page.evaluate("""
        () => [...document.querySelectorAll('[data-testid]')]
            .map(el => el.getAttribute('data-testid'))
            .filter((v, i, a) => a.indexOf(v) === i)
    """)
    print(f"[inject] 页面 testids: {testids[:20]}")

    if any(t in str(testids) for t in ["SideNav", "tweetTextarea", "NewTweet", "AppTabBar"]):
        print("[inject] ✓ 登录成功！Twitter 已就绪")
    elif "login" in current_url or "google_sign_in" in str(testids):
        print("[inject] ✗ 仍未登录，Cookie 可能已过期")
        print("[inject] 请手动在浏览器中登录一次")
    else:
        print(f"[inject] ? 状态不明，请查看截图: {shot}")

    time.sleep(2)
    ctx.close()
