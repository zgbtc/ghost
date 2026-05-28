# Ghost × Hermes 融合方案

> **核心思路：以 Hermes 为底座，Ghost 的桌面控制能力为独家武器**

---

## 为什么直接在 Hermes 上改？

Hermes 已经有：
- ✅ 完整的多 Agent 系统（delegate_tool + kanban swarm）
- ✅ 40+ 工具，完善的 toolset 系统
- ✅ 全平台消息渠道（Telegram/Discord/Slack/飞书/钉钉/企微/微信）
- ✅ 技能系统 + Skills Hub 社区
- ✅ 跨 session 记忆 + FTS5 搜索
- ✅ Cron 定时任务 + 渠道推送
- ✅ 流式输出 + TUI 界面
- ✅ 200+ 模型支持（OpenRouter）
- ✅ Docker/SSH/Modal/Daytona 多运行环境

Ghost 独有的：
- 🔥 **真人感桌面控制**（截图+鼠标贝塞尔曲线+自然打字）
- 🔥 **stealth 浏览器**（反检测，持久 Cookie）
- 🔥 **PAD 情感系统**（影响决策风格）
- 🔥 **示范学习**（录制人类操作 → 提炼技能）

**结论：把 Ghost 的桌面控制层移植到 Hermes，改名 Ghost，就是最强的 Agent。**

---

## 融合架构

```
Ghost (基于 Hermes 改造)
├── hermes 核心（保持不动）
│   ├── agent/          — 对话循环、记忆、技能
│   ├── tools/          — 40+ 工具
│   ├── gateway/        — 消息渠道
│   ├── cron/           — 定时任务
│   └── hermes_cli/     — CLI + TUI
│
└── ghost/ (新增模块)
    ├── desktop/        — 跨平台桌面控制 ← Ghost 独有
    │   ├── input.py    — 鼠标（贝塞尔曲线）+ 键盘（自然打字）
    │   ├── screen.py   — 截图（mss，跨平台）
    │   ├── window.py   — 窗口管理（Win/Mac/Linux）
    │   └── vision.py   — 截图 → Vision LLM 分析
    │
    ├── browser/        — stealth 浏览器 ← Ghost 独有
    │   └── session.py  — 反检测 Playwright + 人类行为
    │
    ├── emotion/        — PAD 情感系统 ← Ghost 独有
    │   └── state.py
    │
    └── tools/          — 注册到 Hermes toolset
        └── desktop_tools.py  — 把桌面工具注册进 Hermes
```

---

## 跨平台桌面控制方案

### Windows
- `pyautogui` — 鼠标/键盘基础
- `mss` — 截图（比 PIL 快 10x）
- `pygetwindow` — 窗口管理
- `win32api` (pywin32) — 底层 API，发送消息到后台窗口

### macOS (Apple Silicon + Intel 通用)
- `pyautogui` — 鼠标/键盘（需要辅助功能权限）
- `mss` — 截图
- `AppKit` / `Quartz` — 窗口管理，后台控制
- Hermes 已有的 `cua-driver` (MCP) — macOS 专用后台控制

### Linux
- `pyautogui` — X11
- `mss` — 截图
- `xdotool` (shell) — 窗口管理

### 统一抽象层
```python
# ghost/desktop/input.py
class DesktopInput:
    def click(x, y, human=True)      # 贝塞尔曲线移动
    def type(text, wpm=60)           # 自然打字速度
    def hotkey(*keys)                # 快捷键
    def scroll(amount, direction)    # 自然滚动

class DesktopScreen:
    def capture(monitor=0)           # 截图 → base64
    def analyze(b64)                 # Vision LLM 分析

class DesktopWindow:
    def list()                       # 列出所有窗口
    def focus(title)                 # 聚焦窗口
    def get_active()                 # 当前活跃窗口
```

---

## 实施步骤

### Phase 1 — 把 Ghost 桌面工具注册进 Hermes（1天）
1. 复制 `ghost/desktop/` 到 Hermes 项目
2. 创建 `tools/desktop_tool.py` 注册到 Hermes toolset
3. 在 `toolsets.py` 添加 `"ghost-desktop"` toolset
4. 测试：`hermes` CLI 里能调用 `desktop_capture`、`desktop_click` 等

### Phase 2 — stealth 浏览器整合（半天）
1. 复制 `ghost/browser/session.py` 到 Hermes
2. 创建 `tools/ghost_browser_tool.py`
3. 注册 20 个 browser_* 工具到 Hermes toolset

### Phase 3 — 情感系统整合（半天）
1. 复制 `ghost/memory/emotion.py`
2. 在 `agent/system_prompt.py` 里注入情感状态
3. 在 agent loop 里根据工具结果更新情感

### Phase 4 — 改名 + 定制 soul（1天）
1. 修改 `hermes_cli/default_soul.py` → Ghost soul
2. 修改 CLI 入口：`ghost` 命令替代 `hermes`
3. 修改 banner、配置目录 `~/.ghost`

### Phase 5 — 跨平台打包（2天）
1. Windows: `pyproject.toml` 加 `ghost-windows` extra
2. macOS: 加 `ghost-macos` extra（含 cua-driver 集成）
3. Linux: 加 `ghost-linux` extra
4. 一键安装脚本（参考 Hermes 的 install.sh/install.ps1）

---

## 工具命名规范（Ghost 版）

| Ghost 工具名 | 对应能力 | 平台 |
|-------------|---------|------|
| `desktop_capture` | 截图 + Vision 分析 | Win/Mac/Linux |
| `desktop_click` | 鼠标点击（贝塞尔曲线） | Win/Mac/Linux |
| `desktop_type` | 自然打字 | Win/Mac/Linux |
| `desktop_hotkey` | 快捷键 | Win/Mac/Linux |
| `desktop_scroll` | 自然滚动 | Win/Mac/Linux |
| `desktop_drag` | 拖拽 | Win/Mac/Linux |
| `desktop_window_list` | 列出窗口 | Win/Mac/Linux |
| `desktop_window_focus` | 聚焦窗口 | Win/Mac/Linux |
| `desktop_window_bg_click` | 后台点击（不抢焦点） | Win/Mac |
| `browser_goto` | stealth 浏览器导航 | 全平台 |
| `browser_click` | 浏览器点击（人类行为） | 全平台 |
| ... (20个 browser_* 工具) | | |

---

## 对比：融合前 vs 融合后

| 能力 | 当前 Ghost | 融合后 Ghost |
|------|-----------|-------------|
| 桌面控制 | ✅ | ✅ |
| stealth 浏览器 | ✅ | ✅ |
| 情感系统 | ✅ | ✅ |
| 多 Agent | 基础版 | ✅ Hermes 完整版 |
| 消息渠道 | Telegram+Discord | ✅ 全平台 10+ |
| 技能系统 | 基础版 | ✅ Skills Hub 社区 |
| 流式输出 | ❌ | ✅ |
| TUI 界面 | 基础 | ✅ 完整 TUI |
| 200+ 模型 | ❌ | ✅ OpenRouter |
| Kanban 多 Agent | ❌ | ✅ |
| macOS 后台控制 | ❌ | ✅ cua-driver |
| 跨平台安装 | 手动 | ✅ 一键脚本 |
