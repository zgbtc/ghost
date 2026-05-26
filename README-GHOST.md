# Ghost Agent 👻

**Your digital twin with full computer control.**

Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT) with Ghost's cross-platform desktop control layer.

---

## What makes Ghost different

| Capability | Ghost | Hermes |
|-----------|-------|--------|
| Desktop control (Win/Mac/Linux) | ✅ Human-like | ❌ |
| Stealth browser | ✅ Anti-detection | ✅ Basic |
| Mouse bezier curves | ✅ | ❌ |
| Natural typing (WPM) | ✅ | ❌ |
| Emotional state (PAD) | ✅ | ❌ |
| Multi-agent parallel | ✅ | ✅ |
| 200+ LLM models | ✅ | ✅ |
| Telegram/Discord/Slack | ✅ | ✅ |
| Skills system | ✅ | ✅ |
| Cron scheduling | ✅ | ✅ |

---

## Install

### macOS / Linux (one line)

```bash
curl -fsSL https://raw.githubusercontent.com/zgbtc/ghost/main/scripts/install-ghost.sh | bash
```

Works on:
- macOS Apple Silicon (M1/M2/M3/M4)
- macOS Intel
- Ubuntu / Debian / Fedora / Arch
- WSL2

### Windows (PowerShell)

```powershell
iex (irm https://raw.githubusercontent.com/zgbtc/ghost/main/scripts/install-ghost.ps1)
```

Works on Windows 10/11 (x64).

### Manual install

```bash
git clone https://github.com/zgbtc/ghost.git ~/.ghost/ghost-agent
cd ~/.ghost/ghost-agent
uv venv .venv --python 3.11
uv pip install -e ".[all,ghost-desktop]"
# macOS/Linux:
uv pip install pyautogui mss pyperclip
# Windows (also):
uv pip install pygetwindow pywin32
# Stealth browser:
python -m playwright install chromium
```

---

## Quick start

```bash
# 1. Set your API key (Claude recommended)
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Start Ghost
ghost

# Or run setup wizard first
ghost setup
```

---

## Desktop control

Ghost can see your screen, move the mouse, and type — just like a human.

```
you: open Chrome and go to twitter.com, search for #AI and like the top 5 tweets

Ghost: [takes screenshot to see current state]
       [opens Chrome via desktop_window_focus or launch_app]
       [navigates to twitter.com using stealth browser]
       [searches #AI]
       [moves mouse along bezier curve to first tweet]
       [clicks like button with natural delay]
       [repeats for 5 tweets with random intervals]
```

### How it works

- **`desktop_capture`** — screenshot + Vision LLM analysis (finds coordinates)
- **`desktop_click`** — bezier curve mouse movement, not instant teleport
- **`desktop_type`** — realistic WPM with natural variance, rare typos
- **`desktop_paste`** — clipboard paste (fast, Unicode/CJK safe)
- **`desktop_scroll`** — multi-step natural scrolling
- **`desktop_window_list/focus`** — window management

### Platform requirements

| Platform | Requirements |
|----------|-------------|
| Windows | `pyautogui`, `mss`, `pygetwindow` (auto-installed) |
| macOS | `pyautogui`, `mss` + Accessibility permission in System Settings |
| Linux | `pyautogui`, `mss`, `xdotool` (auto-installed) |

---

## Stealth browser

Ghost's browser is designed to avoid bot detection:

- Removes `navigator.webdriver` flag
- Randomizes User-Agent (real Chrome versions)
- Bezier curve mouse movement inside browser
- Natural typing speed
- Persistent cookies (login once, stays logged in)

```
you: post a tweet saying "Hello from Ghost!"

Ghost: [opens stealth browser]
       [navigates to x.com/home]
       [clicks tweet box with natural mouse movement]
       [types text at human speed]
       [clicks Post button]
       [takes screenshot to confirm]
```

---

## Multi-agent

Ghost can spawn parallel sub-agents for complex tasks:

```
you: monitor 3 Twitter accounts simultaneously and reply to any mentions

Ghost: spawn_agents([
    {"id": "account-1", "prompt": "Monitor @user1 and reply to mentions"},
    {"id": "account-2", "prompt": "Monitor @user2 and reply to mentions"},
    {"id": "account-3", "prompt": "Monitor @user3 and reply to mentions"},
], parallel=true)
```

---

## Messaging channels

Control Ghost from anywhere:

```bash
ghost gateway telegram   # Telegram bot
ghost gateway discord    # Discord bot
ghost gateway feishu     # 飞书
ghost gateway dingtalk   # 钉钉
ghost gateway wecom      # 企业微信
```

---

## Scheduled tasks

```bash
# Run every day at 9am, send result to Telegram
ghost cron add morning-report "0 9 * * *" "Summarize today's news"

# Start the daemon
ghost daemon
```

Set in `.env`:
```
GHOST_CRON_NOTIFY=telegram
TELEGRAM_CHAT_ID=your_chat_id
```

---

## Configuration

Copy `.env.example` to `~/.ghost/.env`:

```bash
# Required: at least one LLM provider
ANTHROPIC_API_KEY=sk-ant-...

# Optional: messaging channels
TELEGRAM_BOT_TOKEN=...
DISCORD_BOT_TOKEN=...

# Optional: cron notifications
GHOST_CRON_NOTIFY=telegram
TELEGRAM_CHAT_ID=...
```

---

## Credits

Ghost is built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by NousResearch (MIT license).

Ghost adds:
- Cross-platform desktop control (Win/Mac/Linux)
- Human-like mouse movement (bezier curves)
- Natural typing simulation
- Stealth browser with anti-detection
- PAD emotional state system
