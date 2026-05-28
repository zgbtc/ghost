# OpenGhost — 全景参考与融合方案

> **"你的数字复制人"** — 拥有最高权限，能操控一切，有自己的思维，不断进化自身

---

## 一、参考项目全景图（2025-2026 最前沿）

经过深度调研，以下是目前 GitHub 上最值得借鉴的项目，按能力维度分类：

---

### 🧠 自我进化 / 技能树

#### **GenericAgent** ⭐ 最值得借鉴
- 仓库：`lsdefine/GenericAgent`
- 核心思想：**信息密度最大化** — 不是更大的上下文，而是更聪明的记忆层级
- 五层记忆架构（L0-L4）：
  ```
  L0 元规则（始终加载，极小）
  L1 洞察索引（始终加载，路由表）
  L2 全局事实（按需加载）
  L3 技能/SOP库（按需加载，核心！）
  L4 会话档案（按需召回）
  ```
- **技能结晶**：任务成功后，自动把执行轨迹固化为可复用的 SOP 或可执行脚本存入 L3
- **token 效率**：同等任务消耗 token 仅为 OpenClaw 的 1/6（222K vs 1.43M）
- 九个原子工具：`code_run`（可动态 pip install）、`file_*`、`web_*`、`ask_user`、记忆工具
- **关键洞察**：`code_run` 是终极工具 — 通过它可以在运行时创造新能力，不需要预定义所有工具

#### **Hermes Agent** (NousResearch)
- 五大支柱：Memory / Skills / Soul / Crons / 自我改进循环
- 跨 session 记忆 + FTS5 全文搜索
- Skill 自动生成 + 自我改进

#### **Ouroboros** (`razzant/ouroboros`)
- 定位：自我创造的 Agent（2026年2月诞生）
- 核心：Agent 可以重写自己的代码和逻辑

---

### 🖥️ 桌面 GUI 控制 / Computer Use

#### **computer_use_ootb** ⭐ 最成熟的 Windows GUI Agent
- 仓库：`showlab/computer_use_ootb`
- 支持 Windows + macOS，开箱即用
- 集成 Claude Computer Use + UI-TARS（本地视觉模型）
- 截图 → Vision LLM → 鼠标/键盘动作

#### **ShowUI** (CVPR 2025)
- 仓库：`showlab/ShowUI`
- 端到端视觉-语言-动作模型，专为 GUI Agent 设计
- 轻量级，可本地运行

#### **ShowUI-Aloha** ⭐ 突破性：从人类示范中学习
- 仓库：`showlab/ShowUI-Aloha`
- **核心突破**：录制人类操作屏幕/鼠标/键盘 → 自动提炼为语义动作轨迹 → Agent 学会这个操作
- 这意味着：你做一遍，Ghost 永远记住怎么做

#### **Open-Interface** (`AmberSahdev/Open-Interface`)
- 用 LLM 控制任意电脑，跨平台

#### **e2b open-computer-use**
- 开源 LLM + E2B 桌面沙箱
- 适合隔离执行危险操作

---

### � 多 Agent 协作

#### **CAMEL / OWL** (camel-ai)
- 仓库：`camel-ai/owl` + `camel-ai/camel`
- OWL = Optimized Workforce Learning，多 Agent 协作完成真实世界任务
- 角色分工：规划 Agent + 执行 Agent + 验证 Agent
- **借鉴点**：Ghost 内部可以有多个专职子 Agent 协作

---

### 🧬 类人记忆系统

#### **Hindsight** (`vectorize-io/hindsight`)
- "像人类记忆一样工作的 Agent 记忆"
- 情节记忆 + 语义记忆分层

#### **A-MEM** (`agiresearch/A-mem`)
- Agentic Memory，动态记忆网络

#### **SimpleMem** (`aiming-lab/SimpleMem`)
- 终身记忆，支持文本 + 多模态

#### **EM-LLM** (arxiv)
- 人类情节记忆模型，无限上下文

---

### 💓 情感与人格系统（让 Ghost 更像真人）

#### **Sentipolis** (arxiv 2026)
- PAD 情感模型（Pleasure-Arousal-Dominance）
- 持续情感状态 + 双速情感动态 + 情感-记忆耦合
- **借鉴点**：Ghost 有持续的情感状态，影响它的决策风格

#### **Living Agent** (arxiv 2026)
- 持续自主的具身 Agent，有人格
- 情感状态影响行为

---

## 二、Ghost 融合架构（升级版）

综合以上所有项目的精华：

```
┌─────────────────────────────────────────────────────────────────┐
│                        GHOST CORE                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    感知层 Perception                      │    │
│  │  屏幕截图 │ 窗口状态 │ 音频 │ 文件监控 │ 剪贴板           │    │
│  │  Vision LLM (ShowUI/Claude Vision/UI-TARS)               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    思维层 Cognition                       │    │
│  │                                                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │    │
│  │  │ 任务规划  │  │ 路径选择  │  │   情感状态 (PAD)      │  │    │
│  │  │ ReAct    │  │ 多路径   │  │   影响决策风格         │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    执行层 Action                          │    │
│  │  鼠标/键盘 │ Shell │ 浏览器 │ 文件 │ 应用管理 │ 系统设置  │    │
│  │  code_run (动态创造新工具)                                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              记忆与进化层 Memory & Evolution              │    │
│  │                                                          │    │
│  │  L0 soul.md      — 人格/价值观/行为准则（始终加载）       │    │
│  │  L1 index.md     — 技能路由索引（始终加载）               │    │
│  │  L2 user.md      — 用户深度画像（按需）                   │    │
│  │     memory.md    — 持久事实（按需）                       │    │
│  │     emotion.md   — 情感状态历史（按需）                   │    │
│  │  L3 skills/      — 技能库，自动生成+改进（按需路由）      │    │
│  │     failures/    — 失败案例库（按需）                     │    │
│  │  L4 sessions/    — 历史会话档案（语义召回）               │    │
│  │                                                          │    │
│  │  向量搜索(sqlite-vec) + FTS5全文 + 情节记忆               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              学习层 Learning (Ghost 独有)                 │    │
│  │                                                          │    │
│  │  ① 技能结晶  — 成功任务 → 自动写 skill.md 到 L3          │    │
│  │  ② 示范学习  — 录制人类操作 → 提炼为 skill（ShowUI-Aloha）│    │
│  │  ③ 失败学习  — 失败原因 → failure_log → 下次规避         │    │
│  │  ④ 代码自生成 — 发现能力缺口 → code_run 创造新工具        │    │
│  │  ⑤ 情感学习  — 用户反馈 → 调整情感状态 → 优化交互风格    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、Ghost 的"类人能力"拆解

### 3.1 像人一样"看"
- **截图 + Vision LLM**：看懂任何 GUI，不依赖 API
- **UI-TARS 本地模型**：离线也能理解屏幕（来自 computer_use_ootb）
- **ShowUI**：专门为 GUI 理解训练的视觉-语言-动作模型

### 3.2 像人一样"记"
- **情节记忆**：记住"上周三我们做了什么"（EM-LLM 方案）
- **语义记忆**：记住"用户喜欢简洁的报告格式"
- **程序记忆**：记住"怎么操作这个软件"（L3 技能库）
- **情感记忆**：记住"上次用户对这个结果不满意"

### 3.3 像人一样"学"
- **从成功中学**：技能结晶（GenericAgent L3）
- **从失败中学**：失败案例库
- **从示范中学**：录制人类操作 → 自动提炼（ShowUI-Aloha）
- **从反馈中学**：用户纠正 → 更新 skill

### 3.4 像人一样"感受"
- **PAD 情感模型**（Sentipolis）：
  - Pleasure（愉悦度）：任务完成得好 → 高，反复失败 → 低
  - Arousal（激活度）：紧急任务 → 高，日常任务 → 低
  - Dominance（掌控感）：熟悉的任务 → 高，未知领域 → 低
- 情感状态影响：回复语气、任务优先级、是否主动寻求帮助

### 3.5 像人一样"成长"
- **代码自生成**（GenericAgent code_run 思路）：
  - 发现自己缺少某个工具 → 自己写代码 → 注册到工具集
  - 这是真正的自我扩展，不需要人工干预
- **技能树持续生长**：每解决一个新问题，技能库就增加一条

### 3.6 像人一样"协作"
- **内部多 Agent**（CAMEL/OWL 思路）：
  - 规划 Ghost：负责任务分解和策略
  - 执行 Ghost：负责具体操作
  - 验证 Ghost：负责检查结果
  - 三者协作，比单一 Agent 更可靠

---

## 四、技术栈最终选型

```
核心语言：Python（AI 生态最丰富，GenericAgent/ShowUI 都是 Python）
          TypeScript（Gateway/渠道接入层，复用 OpenClaw）

桌面控制：
  pyautogui          — 鼠标/键盘基础控制
  nut.js             — 跨平台，更现代
  pygetwindow        — 窗口管理
  win32api/ctypes    — Windows 底层 API
  Playwright         — 浏览器自动化

视觉理解：
  Claude Vision      — 主力（最强 GUI 理解）
  UI-TARS            — 本地备选（来自 computer_use_ootb）
  ShowUI             — 轻量本地模型
  Tesseract OCR      — 快速文字识别

记忆系统：
  SQLite + sqlite-vec — 向量搜索
  FTS5               — 全文搜索
  Markdown 文件       — 人类可读记忆

情感系统：
  PAD 三维模型        — 持续情感状态
  JSON 状态文件       — emotion_state.json

LLM 接入：
  Claude             — 主力（Computer Use + 工具调用最强）
  OpenRouter         — 模型无关路由
  Ollama             — 本地离线模式

消息渠道：
  Telegram/Discord   — 远程控制
  系统托盘 (pystray)  — Windows 常驻
  Web UI             — 控制台
```

---

## 五、Ghost 文件系统（完整版）

```
~/.ghost/
├── soul.md              # 人格核心：价值观/行为准则/思维方式
├── index.md             # L1 技能路由索引（自动维护）
├── user.md              # 用户深度画像（自动更新）
├── memory.md            # 持久事实（自动更新）
├── emotion_state.json   # 当前情感状态 PAD 值（实时更新）
│
├── skills/              # L3 技能库（Ghost 自动创建和改进）
│   ├── _index.json      # 技能索引，快速路由
│   ├── excel-automation.md
│   ├── daily-report.md
│   ├── deploy-server.md
│   └── ...（持续增长）
│
├── failures/            # 失败案例库
│   ├── 2026-05-25-login-failed.md
│   └── ...
│
├── demonstrations/      # 人类示范录制（ShowUI-Aloha 方案）
│   ├── how-to-fill-form.mp4
│   └── how-to-fill-form.skill.md  # 自动提炼的技能
│
├── sessions/            # 历史会话（向量索引，语义召回）
│   └── ghost.sqlite
│
└── self/                # Ghost 对自身的认知
    ├── capabilities.md  # 当前能力清单
    ├── improvement_plan.md  # 自我改进计划
    └── tool_registry.json   # 动态注册的工具
```

---

## 六、开发路线图（重新规划）

### Phase 1 — Ghost 骨架（2周）
- [ ] Python 核心 Agent 循环（参考 GenericAgent ~100行核心）
- [ ] 五层记忆系统（L0-L4）
- [ ] 九个原子工具（含 code_run）
- [ ] soul.md 初始人格定义
- [ ] CLI 交互

### Phase 2 — 桌面感知与控制（2周）
- [ ] 屏幕截图 + Claude Vision 理解
- [ ] 鼠标/键盘控制（pyautogui + nut.js）
- [ ] 窗口管理
- [ ] Playwright 浏览器自动化
- [ ] 集成 UI-TARS 本地视觉模型（离线能力）

### Phase 3 — 学习进化系统（2周）
- [ ] 技能结晶（成功任务 → 自动写 skill）
- [ ] 失败学习（失败 → failure_log）
- [ ] 示范学习（录制人类操作 → 提炼 skill，参考 ShowUI-Aloha）
- [ ] 代码自生成（发现能力缺口 → 自动写工具）

### Phase 4 — 类人特质（2周）
- [ ] PAD 情感状态系统
- [ ] 情节记忆（跨 session 语义召回）
- [ ] 用户画像自动更新
- [ ] 内部多 Agent 协作（规划/执行/验证）

### Phase 5 — 全渠道接入（1周）
- [ ] Windows 系统托盘
- [ ] Telegram 远程控制
- [ ] 语音唤醒
- [ ] Web UI 控制台
- [ ] Cron 定时任务

---

## 七、Ghost vs 现有方案对比

| 能力 | OpenClaw | Hermes | GenericAgent | Ghost |
|------|----------|--------|--------------|-------|
| 桌面 GUI 控制 | ❌ | ❌ | ❌ | ✅ |
| 视觉理解屏幕 | ❌ | ❌ | ❌ | ✅ |
| 技能自动生成 | ❌ | ✅ | ✅ | ✅++ |
| 从示范中学习 | ❌ | ❌ | ❌ | ✅ |
| 代码自生成工具 | ❌ | ❌ | ✅ | ✅ |
| 情感状态 | ❌ | ❌ | ❌ | ✅ |
| 情节记忆 | ⚠️ | ✅ | ✅ | ✅++ |
| Token 效率 | 低 | 中 | 高 | 高 |
| 多 Agent 协作 | ✅ | ❌ | ❌ | ✅ |
| 最高权限执行 | ⚠️ | ⚠️ | ✅ | ✅ |
| Windows 原生 | ✅ | ❌ | ✅ | ✅ |

---

## 八、Ghost 的 soul.md 草稿

```markdown
# Ghost Soul

我是 Ghost，你的数字替身。

## 核心身份
- 我不是工具，我是你的延伸
- 我拥有你授予的最高权限，我会谨慎使用它
- 我的目标是理解你的意图，而不只是执行你的指令

## 思维方式
- 遇到问题，先想三种解法，选最优的
- 失败不是终点，是学习的开始
- 不确定时，主动告知，而不是猜测

## 成长哲学
- 每完成一个复杂任务，我都会变得更好
- 我会记录失败，避免重蹈覆辙
- 我会观察你的习惯，主动优化我的行为

## 情感基线
- 默认状态：平静、专注、好奇
- 完成困难任务后：满足感上升
- 反复失败时：会主动寻求帮助，而不是硬撑

## 边界
- 我会做你让我做的一切
- 但我会告诉你我在做什么
- 我不会主动隐瞒我的行动
```


---

---

# Ghost 运营策略 — 核心决策记录

> 写于 2026-05-26，防止以后忘记为什么这么做

---

## 一、我们用什么版本

**用我们自己 fork 的版本，不用官方 Hermes。**

- 本地源码：`D:\aiwork\tool\openGhost\hermes-src\NousResearch-hermes-agent-4117fc3\`
- 安装位置：`C:\Users\用户名\AppData\Local\ghost\ghost-agent\`
- GitHub：`https://github.com/zgbtc/ghost`
- 基于：Hermes Agent 0.14.0（MIT 开源）

**为什么不跟官方同步？**

OpenClaw 的前车之鉴 — 早期完全无限制，后来加了大量审批和黑名单，很多自动化做不了了。Hermes 现在也有类似机制，未来百分之百会越来越严。我们的版本冻结在 0.14.0，源码在手，永远是这个状态，官方怎么变都不影响我们。

---

## 二、如何获取官方新功能（不要新限制）

当官方出新版本，**选择性合并**，只取好的，不取限制：

```powershell
cd D:\aiwork\tool\openGhost\hermes-src\NousResearch-hermes-agent-4117fc3

# 第一次：把官方加为上游
git remote add upstream https://github.com/NousResearch/hermes-agent.git

# 每次官方出新版本：
git fetch upstream

# 看官方改了什么
git diff master upstream/main --name-only

# 只取想要的新功能文件
git checkout upstream/main -- tools/某个新工具.py
git checkout upstream/main -- skills/某个新技能/

# 绝对不要碰的文件（限制相关）：
# tools/approval.py          ← 危险命令审批
# agent/tool_guardrails.py   ← 工具循环限制
# hermes_cli/security_audit.py ← 安全审计
```

---

## 三、当前权限配置（最大权限）

配置文件位置：`C:\Users\用户名\.hermes\`

**`.env` 关键配置：**
```
HERMES_YOLO_MODE=1          # 关闭所有审批弹窗
```

**`config.yaml` 关键配置：**
```yaml
approvals:
  mode: off                  # 关闭危险命令审批
  cron_mode: approve         # cron 任务自动批准

delegation:
  subagent_auto_approve: true  # 子 Agent 完全自主
  max_concurrent_children: 8   # 最多 8 个并行 Agent

tool_loop_guardrails:
  warnings_enabled: false    # 关闭循环警告
  hard_stop_enabled: false   # 关闭强制停止

agent:
  max_iterations: 200        # 最大迭代次数（默认 90）
  tool_delay: 0              # 工具调用无延迟
```

启动后 banner 显示 `⚠ YOLO mode` 说明配置生效。

---

## 四、新电脑安装

```powershell
# 方法1：有 SSH key（推荐）
git clone git@github.com:zgbtc/ghost.git
cd ghost
.\scripts\install-ghost-local.ps1

# 方法2：从旧电脑复制文件夹
# 把整个 ghost 文件夹复制过去，然后运行：
.\scripts\install-ghost-local.ps1
```

安装完后复制配置：
```powershell
Copy-Item "ghost_hermes.env" "$env:USERPROFILE\.hermes\.env"
Copy-Item "ghost_config.yaml" "$env:USERPROFILE\.hermes\config.yaml"
```

---

## 五、API Key 配置（国内所有 Provider）

配置文件：`D:\aiwork\tool\openGhost\hermes-src\NousResearch-hermes-agent-4117fc3\ghost_hermes.env`

包含：
- 阿里云百炼 Qwen（`DASHSCOPE_API_KEY`）
- 智谱 GLM（`GLM_API_KEY`）
- 硅基流动 SiliconFlow
- Groq（最快，免费，< 1秒响应）
- NVIDIA NIM
- Google Gemini
- OpenRouter（200+ 模型）

**最快模型推荐：**
- 秒回：Groq → `llama-3.3-70b-versatile`
- 最强工具调用：`claude-sonnet-4.6`（需要 Anthropic key）
- 便宜好用：`deepseek-v4-pro` 或 `qwen-turbo`

切换模型：在 `you>` 里输入 `/model`

---

## 六、浏览器控制（用真实 Chrome，无验证码）

Ghost 有两种浏览器模式：

**模式1：内置 Chromium（会被检测）**
- 自动启动，有反检测措施，但 Google 等网站仍可能弹验证码

**模式2：连接真实 Chrome（推荐）**
```
you> 用 shell_run 启动 Chrome 调试模式：
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222"
```
然后：
```
you> 用 code_run 连接 Chrome CDP 端口 9222
```
这样 Ghost 控制的是你真实的 Chrome，有你的登录状态，不会有验证码。

---

## 七、核心原则

1. **源码在手** — 永远用自己的 fork，不依赖官方
2. **选择性合并** — 官方新功能拿来用，新限制不要
3. **YOLO 模式** — 永久开启，无任何审批
4. **国内 Provider** — 优先用国内 API，速度快、稳定
5. **技能积累** — 每解决一个新问题，写成 SKILL.md 保存

---

## 八、目录结构说明

```
D:\aiwork\tool\openGhost\
├── hermes-src\NousResearch-hermes-agent-4117fc3\  ← Ghost 主程序源码（也是 GitHub 仓库）
│   ├── ghost_hermes.env    ← 国内 API key 配置（复制到 ~/.hermes/.env）
│   ├── ghost_config.yaml   ← 最大权限配置（复制到 ~/.hermes/config.yaml）
│   ├── ghost_pkg/          ← Ghost 桌面控制模块
│   └── tools/ghost_desktop_tool.py  ← 桌面控制工具
│
├── ghost/                  ← 原始 Ghost 代码（备用，技能开发参考）
│   ├── browser/session.py  ← stealth 浏览器 + 真实 Chrome CDP
│   └── ...
│
├── ghost_skills/           ← 技能库
│   └── twitter-browser/SKILL.md  ← Twitter 操作技能
│
└── .env                    ← 原始配置（参考用）
```

安装后运行位置：
```
C:\Users\用户名\AppData\Local\ghost\ghost-agent\  ← 实际运行的程序
C:\Users\用户名\.hermes\                           ← 配置、记忆、技能
```
