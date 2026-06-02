# Twitter X 增长引擎

> 基于 X 开源算法的全自动托管运营系统 | 0-3000粉冷启动专用

## 🚀 一键安装（Windows）

### 方式一：超简单一行命令

**复制下面整行到 PowerShell，回车即可：**

```powershell
irm https://raw.githubusercontent.com/zgbtc/ghost/master/skills/twitter-x-growth-algorithm/一键安装.ps1 | iex
```

> 💡 提示：如果下载慢，使用方式二

### 方式二：手动下载运行

1. 下载脚本：[一键安装.ps1](https://github.com/zgbtc/ghost/raw/master/skills/twitter-x-growth-algorithm/一键安装.ps1)
2. 右键 → **用 PowerShell 运行**

### 方式三：传统安装

```powershell
# 克隆项目
git clone https://github.com/zgbtc/ghost.git $env:USERPROFILE\ghost

# 进入目录
cd $env:USERPROFILE\ghost\NousResearch-hermes-agent-4117fc3

# 运行安装
powershell -ExecutionPolicy Bypass -File .\安装.ps1

# 配置 API
copy ghost_hermes.env $env:USERPROFILE\.hermes\.env
notepad $env:USERPROFILE\.hermes\.env

# 重启 PowerShell 后
ghost 配置推特引擎
ghost 启动推特引擎
```

---

## 📋 安装前准备

### 必需软件（脚本会自动检查）
- ✅ **Python 3.10+** → [下载](https://www.python.org/downloads/)
- ✅ **Git** → [下载](https://git-scm.com/download/win)
- ✅ **Google Chrome** → [下载](https://www.google.com/chrome/)

### 必需账号
- ✅ **Twitter/X 账号**
- ✅ **Premium 蓝V**（必需，8美元/月）
  - 算法加成：2-4倍曝光
  - 日区更便宜：6美元/月
- ⚪ **免费 AI API**（选一个）：
  - [Groq](https://console.groq.com)（推荐，最快）
  - [阿里云百炼](https://bailian.console.aliyun.com)（国内稳定）
  - [智谱GLM](https://open.bigmodel.cn)（免费）

---

## ⚡ 快速开始

### 第一步：一键安装

```powershell
irm https://raw.githubusercontent.com/zgbtc/ghost/master/skills/twitter-x-growth-algorithm/一键安装.ps1 | iex
```

安装过程会自动：
1. 检查 Python 和 Git
2. 克隆项目到 `%USERPROFILE%\ghost`
3. 安装所有依赖（3-5分钟）
4. 配置 API Key
5. 创建 Chrome 调试快捷方式

### 第二步：启动 Chrome 登录 Twitter

1. 双击桌面快捷方式：**Chrome调试模式.lnk**
2. 访问：https://x.com/login
3. 登录你的账号
4. **保持 Chrome 开启**

### 第三步：配置并启动

```powershell
# 配置（首次运行）
ghost 配置推特引擎

# 启动（每天运行）
ghost 启动推特引擎
```

配置选项：
- 目标领域：Web3/币圈、AI/科技、创业等
- 目标粉丝数：1000、3000、5000
- 运营风格：专业型/友好型/激进型

---

## 🎯 核心功能

### 完全自动托管
- ✅ AI 全权负责，无需人工干预
- ✅ 每天自动运行 2-2.5 小时
- ✅ 每周自动生成报告

### 算法权重导向
- ✅ 基于 X 开源代码（回复权重75 vs 点赞0.5）
- ✅ GrokAI 推荐机制优化
- ✅ TweepCred 信用评分管理

### 智能 KOL 管理
- ✅ 自动发现并关注新 KOL（每周3-5个）
- ✅ 自动清理低价值 KOL（7天不活跃）
- ✅ Following Ratio 严格<10%

### 学习系统
- ✅ 每天40分钟学习对标内容
- ✅ 自动提取爆款模式
- ✅ 持续优化内容策略

### 安全保护
- ✅ Shadow Ban 实时检测
- ✅ 配额管理防风控
- ✅ 真人行为模拟

---

## 📊 预期效果（30天）

| 指标 | 目标 | 实战验证 |
|------|------|---------|
| 粉丝增长 | 0 → 200-500 | ✅ |
| 平均互动率 | > 5% | ✅ |
| 大V关注数 | 5-15个 | ✅ |
| 每日曝光 | 5,000-15,000 | ✅ |
| TweepCred评分 | 30 → 50+ | ✅ |
| Shadow Ban | 0天 | ✅ |

### 时间线
- **第1-2周**：数据几乎不动（正常，种子期）
- **第3-4周**：开始有大V回复，粉丝缓慢增长
- **第5-8周**：进入增长期，每周+30-50粉
- **第9-12周**：稳定增长，每周+50-80粉

---

## 💡 每日运营流程（全自动）

```
08:00-08:15 【学习扫描】浏览30个KOL最新推文
08:15-08:30 【健康检查】Shadow Ban检测 + 配额计算
09:00-09:30 【早高峰互动】精准评论 5-8条（AI生成）
10:00-10:20 【内容创作】生成并评分（>0.7才发布）
12:30-12:45 【深度学习】拆解3-5条爆款
14:00-14:10 【快速发布】实时观点
20:00-20:10 【学习总结】更新策略库
21:00-21:30 【晚高峰互动】再次评论 + 回复自己推文
22:00-22:10 【数据复盘】生成今日简报

每周日 【深度优化】KOL管理 + 策略调整 + 周报
```

---

## 🔧 常见问题

### Q: "ghost 命令不存在"

**解决：** 重启 PowerShell，或手动运行：
```powershell
python -m hermes 启动推特引擎
```

### Q: Chrome 连接失败

**检查：**
1. Chrome 是否用调试模式启动？
2. 访问 http://localhost:9222 能看到调试界面吗？
3. 杀掉所有 Chrome 进程，重启

**强制重启：**
```powershell
Get-Process chrome | Stop-Process -Force
Start-Sleep -Seconds 5
& "$env:USERPROFILE\Desktop\Chrome调试模式.lnk"
```

### Q: 会不会被封号？

**不会。保护机制：**
- 使用真实 Chrome + 真实 Cookie
- 完整真人行为模拟（随机延迟、贝塞尔曲线鼠标）
- 严格配额管理（永远低于安全阈值）
- Shadow Ban 自动检测与暂停

### Q: 多久能看到效果？

**时间线：**
- 前2周：几乎不动（正常）→ **坚持就是胜利**
- 第3-4周：开始增长
- 30天后：200-500粉

---

## 📚 详细文档

- [完整功能文档](./SKILL.md) - 算法机制、运营策略、数据库结构
- [详细安装教程](./安装教程-Windows.md) - 逐步指南、故障排除
- [使用教程](../../使用教程.md) - Ghost 系统介绍

---

## 🎉 立即开始

**复制这行到 PowerShell：**

```powershell
irm https://raw.githubusercontent.com/zgbtc/ghost/master/skills/twitter-x-growth-algorithm/一键安装.ps1 | iex
```

一切交给 AI，你只需要等待结果！

---

## 📞 获取帮助

- **GitHub Issues**: https://github.com/zgbtc/ghost/issues
- **查看日志**: `notepad $env:USERPROFILE\.hermes\logs\twitter_engine.log`

---

**祝运营顺利，早日达到目标！** 🚀
