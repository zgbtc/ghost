"""截图 + 分析 Twitter 页面结构，找到正确的发推选择器"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path.home() / ".ghost" / "twitter_profile")
SHOT_DIR = Path.home() / ".ghost"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("打开 Twitter 首页...")
    page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    # 截图
    page.screenshot(path=str(SHOT_DIR / "twitter_home.png"))
    print(f"截图: {SHOT_DIR / 'twitter_home.png'}")

    # 找所有可能的发推相关元素
    print("\n=== 查找发推相关元素 ===")
    
    checks = [
        ('data-testid=tweetTextarea_0', '[data-testid="tweetTextarea_0"]'),
        ('data-testid=tweetButtonInline', '[data-testid="tweetButtonInline"]'),
        ('data-testid=SideNav_NewTweet_Button', '[data-testid="SideNav_NewTweet_Button"]'),
        ('role=button Post', 'button:has-text("Post")'),
        ('role=button 发帖', 'button:has-text("发帖")'),
        ('placeholder happening', '[placeholder*="happening"]'),
        ('placeholder 新鲜', '[placeholder*="新鲜"]'),
        ('aria-label Compose', '[aria-label*="Compose"]'),
        ('aria-label Post', '[aria-label*="Post"]'),
        ('href compose', 'a[href*="compose"]'),
    ]
    
    found = []
    for name, sel in checks:
        try:
            count = page.locator(sel).count()
            if count > 0:
                print(f"  ✓ {name}: {count} 个")
                found.append((name, sel))
            else:
                print(f"  ✗ {name}: 0 个")
        except Exception as e:
            print(f"  ? {name}: 错误 {e}")

    # 打印页面上所有 data-testid
    print("\n=== 页面上的 data-testid ===")
    testids = page.evaluate("""
        () => [...document.querySelectorAll('[data-testid]')]
            .map(el => el.getAttribute('data-testid'))
            .filter((v, i, a) => a.indexOf(v) === i)
            .slice(0, 30)
    """)
    for tid in testids:
        print(f"  {tid}")

    # 尝试点击 Post/发帖 按钮
    print("\n=== 尝试点击发推按钮 ===")
    for name, sel in found:
        if "Button" in name or "Post" in name or "发帖" in name or "Compose" in name:
            try:
                page.locator(sel).first.click(timeout=3000)
                time.sleep(2)
                page.screenshot(path=str(SHOT_DIR / "twitter_after_click.png"))
                print(f"  ✓ 点击 {name} 成功，截图已保存")
                
                # 再找发推框
                time.sleep(1)
                new_testids = page.evaluate("""
                    () => [...document.querySelectorAll('[data-testid]')]
                        .map(el => el.getAttribute('data-testid'))
                        .filter((v, i, a) => a.indexOf(v) === i)
                """)
                print(f"  点击后 testids: {[t for t in new_testids if 'tweet' in t.lower() or 'post' in t.lower()]}")
                break
            except Exception as e:
                print(f"  ✗ 点击 {name} 失败: {e}")

    time.sleep(2)
    ctx.close()
    print("\n完成！查看截图了解页面结构")
