---
name: twitter-browser
description: "通过浏览器操作 Twitter/X，模拟真人行为，避免 API 风控。支持发推、回复、点赞、搜索、关注、多账号并行。"
platforms: [windows, macos, linux]
triggers:
  - 发推
  - 发 tweet
  - 推特发帖
  - 搜索推特
  - 点赞推文
  - 转发推文
  - 回复推文
  - 关注用户
  - 查看推特
  - twitter post
  - tweet
  - 推特运营
  - 推特互动
  - 批量发推
  - 多账号推特
metadata:
  hermes:
    tags: [twitter, x, social-media, browser, stealth, multi-account]
    requires_tools: [browser_goto, browser_click, browser_fill, browser_screenshot, browser_snapshot, browser_wait, spawn_agents]
---

# Twitter/X 浏览器操作技能

## 核心原则
- **永远不用 API**，全程 Playwright 浏览器操作（Ghost 内置 stealth 浏览器）
- **模拟真人行为**：Ghost 的 `browser_*` 工具已内置随机延迟、贝塞尔曲线鼠标移动、自然打字速度
- **持久化登录**：Cookie 保存在 `~/.ghost/browser_profile`，不需要反复登录
- **遇到验证码立即停止**，截图告知用户
- **多账号并行**：用 `spawn_agents` 让多个 Ghost 同时操作不同账号

---

## 第一步：首次登录（手动操作一次）

```
browser_goto(url="https://x.com/login")
```

然后告诉 Ghost "我已经登录完成"，Ghost 会记住这个 session。

---

## 发推文

**工具调用顺序：**

1. `browser_goto(url="https://x.com/home")`
2. `browser_wait(seconds=2.0)`
3. `browser_screenshot()` — 截图确认页面状态
4. `browser_click(selector='[data-testid="tweetTextarea_0"]')`
5. `browser_wait(seconds=0.8)`
6. `browser_fill(selector='[data-testid="tweetTextarea_0"]', value="推文内容", human=true)`
7. `browser_wait(seconds=1.5)`
8. `browser_screenshot()` — 确认内容已输入
9. `browser_click(selector='[data-testid="tweetButtonInline"]')`
10. `browser_wait(seconds=2.0)`
11. `browser_screenshot()` — 确认发送成功

**备用选择器（如果主选择器失效）：**
- 推文框：`[placeholder*="happening"]` | `[placeholder*="新鲜"]` | `.public-DraftEditor-content`
- 发送按钮：`[data-testid="tweetButton"]` | `button:has-text("Post")` | `button:has-text("发布")`

---

## 搜索关键词

1. `browser_goto(url="https://x.com/search?q=关键词&f=live")`
2. `browser_wait(seconds=2.5)`
3. `browser_snapshot()` — 读取搜索结果
4. `browser_find_elements(selector='[data-testid="tweetText"]', max_results=10)` — 提取推文内容

---

## 点赞推文

1. 先搜索或打开目标页面
2. `browser_find_elements(selector='[data-testid="like"]', max_results=5)` — 找到点赞按钮
3. `browser_click(selector='[data-testid="like"]')` — 点第一个
4. `browser_wait(seconds=3.0)` — 点赞间隔要长，避免风控
5. 滚动后继续：`browser_scroll(direction="down", amount=400)`

**每日点赞上限：≤ 80 条，间隔 ≥ 3 秒**

---

## 回复推文

1. `browser_goto(url="推文URL")`
2. `browser_wait(seconds=2.0)`
3. `browser_click(selector='[data-testid="reply"]')` — 点回复按钮
4. `browser_wait(seconds=1.0)`
5. `browser_fill(selector='[data-testid="tweetTextarea_0"]', value="回复内容", human=true)`
6. `browser_wait(seconds=1.5)`
7. `browser_click(selector='[data-testid="tweetButton"]')`

---

## 转发推文

1. 打开推文页面
2. `browser_click(selector='[data-testid="retweet"]')`
3. `browser_wait(seconds=0.8)`
4. `browser_click(selector='[data-testid="retweetConfirm"]')` — 确认转发

---

## 关注用户

1. `browser_goto(url="https://x.com/用户名")`
2. `browser_wait(seconds=1.5)`
3. `browser_click(selector='[data-testid="followButton"]')`
4. `browser_wait(seconds=2.0)`

---

## 查看通知

1. `browser_goto(url="https://x.com/notifications")`
2. `browser_wait(seconds=2.0)`
3. `browser_snapshot()` — 读取通知内容
4. `browser_screenshot()` — 截图存档

---

## 多账号并行操作（spawn_agents）

用 `spawn_agents` 让多个 Ghost 同时操作不同账号：

```json
spawn_agents(tasks=[
  {
    "id": "account-A",
    "prompt": "打开浏览器，登录 Twitter 账号A（profile在 ~/.ghost/twitter_A），发一条推文：'今天天气真好 #生活'"
  },
  {
    "id": "account-B", 
    "prompt": "打开浏览器，登录 Twitter 账号B（profile在 ~/.ghost/twitter_B），搜索 '#AI' 并点赞前5条推文"
  },
  {
    "id": "account-C",
    "prompt": "打开浏览器，登录 Twitter 账号C，回复用户 @elonmusk 最新推文：'Great point!'"
  }
], parallel=true, timeout_per_task=120)
```

**注意：** 多账号需要为每个账号设置独立的 browser_profile 目录，在 `code_run` 里用不同的 `user_data_dir` 启动。

---

## 安全操作限制

| 操作 | 建议每日上限 | 最小间隔 |
|------|------------|---------|
| 发推 | ≤ 15 条 | 10 分钟 |
| 点赞 | ≤ 80 条 | 3 秒 |
| 转发 | ≤ 30 条 | 5 秒 |
| 回复 | ≤ 30 条 | 5 秒 |
| 关注 | ≤ 50 人 | 10 秒 |

Ghost 的 `browser_wait` 工具会自动添加随机延迟，但你仍需在高频操作之间手动加 `browser_wait(seconds=随机值)`。

---

## 常见问题排查

**登录状态丢失：**
- Cookie 存在 `~/.ghost/browser_profile`，一般不会丢失
- 如果丢失，重新执行首次登录步骤

**选择器失效（Twitter 经常改 DOM）：**
- 先 `browser_screenshot()` 看当前页面
- 用 `browser_eval(script="document.querySelectorAll('[data-testid]').length")` 检查
- 用 `browser_find_elements(selector='button', max_results=10)` 找按钮

**遇到验证码/人机验证：**
- 立即 `browser_screenshot()` 截图
- 告知用户手动处理
- 不要尝试绕过

**速率限制（Rate Limit）：**
- 停止操作，等待 15-30 分钟
- 用 `remember` 工具记录触发时间，下次规避
