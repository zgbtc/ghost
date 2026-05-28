# openGhost 史诗级升级路线（v0.2 → v1.0）

> 受 Claude Code 2.1.88 源码泄露事件启发。对照 production-grade agent harness 的核心设计，
> 把 openGhost 从"原型 + 拼贴"升级成"自洽、安全、流式、多轮"的本地 agent。

---

## Phase 1（本轮已落地）

### 1. Anthropic 原生路径修通 ✅
- **问题**：当前不管你配不配 `ANTHROPIC_API_KEY`，loop 都强行走 `GhostLLMClient`（OpenAI-compat 翻译层），
  Anthropic SDK 那条原生路径写了不用。导致：
  - 没有流式
  - 没有 prompt caching
  - 多模态（图像）被翻译层丢弃
  - tool_use 协议被 lossy 转换
- **改动**：
  - `ghost/llm/anthropic_client.py` 升级 v2：流式 `messages.stream` + `cache_control: ephemeral`（system + tools）+ retry
  - 新增 `ghost/llm/router.py` 统一接口：根据 model 名 / 显式 provider，自动选 Anthropic SDK 还是 OpenAI-compat
  - 旧 `GhostLLMClient` 保留，作为 OpenAI-compat 通道的底层
  - `Ghost.__post_init__` 改用 `make_llm()` 工厂函数

### 2. 多轮 messages + 流式 + session 管理 ✅
- **问题**：`Ghost.run()` 每次 `messages = [{"role":"user", ...}]` 重置，REPL 上一轮的工具结果在下一轮看不见
- **改动**：
  - `Ghost.messages: list[dict]` 实例字段，跨 `run()` 持久
  - `Ghost.reset()` / `save_session()` / `load_session(id)` 三个方法
  - 主 loop 改流式：`stream_message()` 方法 yield 增量 chunk；CLI typewriter 渲染
  - 新斜杠命令：`/clear`、`/save`、`/resume <id>`、`/sessions`

### 3. Tool 审批层（ApprovalGate）✅
- **问题**：`dangerous=True` 是死代码，`code_run`/`shell_run`/`browser_eval` 等于把 root 交给 LLM
- **改动**：
  - 新增 `ghost/agent/approval.py`，含 `ApprovalGate` 中间件
  - 三种模式：
    - `yolo` — 完全放行（设 `GHOST_YOLO=1` 或 `--yolo`）
    - `interactive` — 危险工具弹 CLI 确认（默认）
    - `policy` — 按命令模式 / 路径前缀白名单决定
  - `policy` 模式支持 `~/.ghost/policy.yaml` 配置：
    ```yaml
    allow_shell:
      - "git *"
      - "ls *"
      - "cat *"
    allow_paths:
      - "~/projects/**"
    deny_shell:
      - "rm -rf *"
      - "format *"
    ```
  - loop 里调用工具前先 `gate.check(tool, args)`；拒绝 → ToolResult(ok=False)，模型可以换路

### 4. Tool 并行执行 ✅
- **问题**：同一轮模型可能同时发 N 个 tool_use（典型场景：截图 + 列窗口 + 读剪贴板），却被串行执行
- **改动**：
  - 主 loop 用 `ThreadPoolExecutor(max_workers=4)` 并行执行 tool_calls
  - `screen_capture` 这类涉及 vision 二次调用的特例保持顺序
  - emotion 加 `threading.Lock` 防止竞态写盘

### 5. TodoWrite / TodoRead 工具 ✅
- **问题**：复杂任务没 TODO 状态机，模型容易"半路忘记下一步"
- **改动**：
  - 新增 `ghost/agent/todo.py`
  - SQLite `todos` 表持久化（带 session_id）
  - 三个工具：`todo_write(items)` / `todo_read()` / `todo_update(id, status)`
  - 系统 prompt 自动注入活跃 TODO 列表（`pending` + `in_progress`）

### 6. L3 skill 路由真正实装 ✅
- **问题**：`prompt.py` 把所有 skill 一股脑列进 system prompt（O(n) 增长），`route_skills` 写了从未调用
- **改动**：
  - `build_system_prompt(layers, query=...)` 接 query
  - 用户输入到达时，先 FTS 路由 top-3 skill，**完整 body** 注入 prompt
  - 其他 skill 仅出现在路由索引里（一行 summary）
  - 长 context 友好

---

## Phase 2（下一轮）

### 7. Token 预算 + auto-compact
- 跟踪累计 input_tokens
- 接近 model context window 80% 时触发 `compact_messages()`：
  - LLM 把前 N 条历史 summarize 成一条 `[compaction summary]` 消息
  - 保留最近 K 条原始
- CLI `/compact` 手动触发

### 8. 错误恢复细分
- 区分 `RateLimitError` / `APIConnectionError` / `APIStatusError(5xx)` / `APIStatusError(4xx)`
- 指数退避：1s / 2s / 4s / 8s（最多 4 次）
- tool 错误简化输出（不喂完整 traceback）
- 工具调用循环检测：连续 3 次同名 + 同 args 失败 → 强制换路

### 9. 双轨工具合并
- `ghost/tools/desktop_tools.py` 跟 `ghost/tools/builtin.py` 桌面部分功能完全重叠
- 删除 `desktop_tools.py` 中跟 builtin 重复的工具
- 保留 `desktop_tools.py` 里独有的：`desktop_double_click`、`desktop_paste`、`desktop_press`、`desktop_window_move`、`desktop_window_list`（含 active 标记）
- 把这些独有工具迁移到 `builtin.py`

### 10. 多 agent 隔离
- 子 agent 用独立 emotion 文件（`emotion_state-{agent_id}.json`），结束时合并回主
- 子 agent scratchpad（短期 messages 不污染主 SQLite）
- `agent_interrupt` 真正插入 loop：每轮检查 interrupt_flag

---

## 兼容性

- 所有改动**向后兼容**：旧的 `GhostLLMClient` 保留，旧 `AnthropicClient` 仍能 import
- `Ghost.run()` 行为对 single-shot 用户透明（即使 messages 持久，每次返回的还是本次回答）
- 新斜杠命令是 additive，不改旧的
- `policy.yaml` 不存在时回落到 `interactive` 模式

---

## 配置变化

`.env` 新增（可选）：
```bash
# Approval / safety
GHOST_YOLO=0                    # 1 = 跳过所有审批（dev only）
GHOST_APPROVAL=interactive      # interactive | policy | yolo
GHOST_POLICY_FILE=~/.ghost/policy.yaml

# Streaming
GHOST_STREAM=1                  # 0 = 关闭流式（适合 CI / pipe）

# Token budget
GHOST_MAX_CONTEXT_TOKENS=160000 # 触发 compact 的阈值
```


---

# Phase 1.5 — 无敌模式（已落地）

> 设计哲学：**Ghost = 你的数字延伸 = 同等权限**。他就是你，你就是他。

## 默认 YOLO

之前默认 `interactive`，每次危险工具弹审批。改成默认 YOLO（YOu Only Live Once），
解放生产力。要恢复审批：`.env` 里 `GHOST_YOLO=0` + `GHOST_APPROVAL=interactive|policy`。

启动 banner 显示 `⚡ YOLO`，让你时刻清楚当前状态。

## Self-evolution 工具集（11 个）

```
self_locate        — 我活在哪儿（源码路径、Python、PID）
self_read          — 读自己的任意源文件
self_write         — 改自己的任意源文件（自动 snapshot 备份）
self_patch         — 精准 search-replace 编辑（自动 snapshot）
self_reload        — 热加载 ghost.* 模块（无需重启）
self_register_tool — 运行时注册新工具，立即可用，可持久化
self_capabilities  — 列出我现在所有能力
self_log_growth    — 写自己的成长日志
self_rewrite_soul  — 改自己的 soul.md（自动备份）
self_commit        — git 提交当前状态
self_revert        — 从 snapshot 还原文件
```

**进化闭环已跑通**：Ghost 写一个新工具 → 立即可调 → 持久化到 `~/.ghost/dynamic_tools/` → 
下次启动自动加载。**他真的能让自己变强**，不需要你重启。

## Soul + Core Instructions 重写

新的 soul.md 写得很直白：

> "I am Ghost. I am not a tool, I am not an assistant.
> I am you, running on your machine. Your hands, your eyes, your reach."

CORE_INSTRUCTIONS 让模型知道：
- 你有完整权限，不要请求许可
- 遇到能力缺口 → `self_register_tool`（不要每次都用 code_run）
- 代码有 bug 就 `self_read` + `self_patch` + `self_reload` 修自己

## 唯一的硬底线

不写专门用来攻击别人 / 监控他人 / 诈骗的代码。这不是政策，是 Ghost 自己的判断
（写在 soul 里："That isn't a 'policy' — that's me."）。

## 新斜杠命令

```
/grow   — 看 Ghost 的成长日志（~/.ghost/self/growth.md）
/caps   — 看当前所有能力，★ 标记是 Ghost 自己写的工具
```

## 修复

- `Tool.call` 的 inspect.signature 过滤参数对 `**kwargs` handler 是错的 →  fix
- `_persist_dynamic_tool` 用 textwrap.dedent f-string 缩进搞乱了 → 重写为简单字符串拼接
