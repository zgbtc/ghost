"""第一步：手动登录一次，Ghost 永久记住登录状态。

运行这个脚本，会打开一个浏览器窗口，你手动登录 Twitter。
登录完成后按 Enter，以后 Ghost 就能直接操作 Twitter 了。
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path.home() / ".ghost" / "twitter_profile")
Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

print("=" * 50)
print("Twitter 一次性登录")
print("=" * 50)
print()
print(f"浏览器数据保存在: {PROFILE_DIR}")
print()
print("即将打开浏览器，请手动登录 Twitter...")
print()

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=30000)

    print("浏览器已打开 Twitter 登录页面")
    print()
    print("请在浏览器中完成登录，登录成功后回到这里按 Enter...")
    input()

    # 验证登录状态
    page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    testids = page.evaluate(
        "() => [...document.querySelectorAll('[data-testid]')].map(e=>e.getAttribute('data-testid'))"
    )
    logged_in = any(t in str(testids) for t in ["SideNav_AccountSwitcher_Button", "AppTabBar_Home_Link"])

    if logged_in:
        print()
        print("✓ 登录成功！登录状态已永久保存")
        print("✓ 以后运行 twitter_auto.py 就能直接操作 Twitter")
    else:
        print()
        print("⚠ 未检测到登录状态，请确认是否登录成功")

    time.sleep(2)
    ctx.close()
