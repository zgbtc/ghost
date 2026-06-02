# Twitter X 增长引擎 - Windows 10 安装教程

> 完整安装指南，从零开始，15-20分钟完成

---

## 📋 **前置准备**

### 必需软件
- ✅ **Python 3.10+** (推荐 3.10 或 3.11)
- ✅ **Google Chrome** (用于自动化操作)
- ✅ **Git** (用于拉取代码)
- ✅ **PowerShell** (Windows 自带)

### 必需账号
- ✅ **Twitter/X 账号** (已注册并登录)
- ✅ **Premium 蓝V** (必需，8美元/月，日区6美元)
- ⚪ **Telegram Bot** (可选，用于接收周报)

---

## 🚀 **完整安装步骤**

### **第一步：安装 Python**

#### 1.1 下载 Python

访问官网：https://www.python.org/downloads/

或直接下载：https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

#### 1.2 安装 Python

1. 双击下载的安装包
2. ⚠️ **重要**：勾选 **"Add Python to PATH"**
3. 点击 "Install Now"
4. 等待安装完成

#### 1.3 验证安装

打开 PowerShell（Win + X，选择 "Windows PowerShell"），输入：

```powershell
python --version
```

应该显示：`Python 3.11.9` 或类似版本

如果显示 "command not found"，需要重启电脑。

---

### **第二步：安装 Git**

#### 2.1 下载 Git

访问：https://git-scm.com/download/win

或直接下载：https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe

#### 2.2 安装 Git

1. 双击安装包
2. 一路 "Next"（使用默认选项）
3. 完成安装

#### 2.3 验证安装

```powershell
git --version
```

应该显示：`git version 2.44.0.windows.1` 或类似

---

### **第三步：克隆 Ghost 项目**

#### 3.1 选择安装目录

```powershell
# 创建工作目录（建议）
mkdir D:\ghost
cd D:\ghost
```

#### 3.2 克隆项目

```powershell
git clone https://github.com/zgbtc/ghost.git
cd ghost\NousResearch-hermes-agent-4117fc3
```

如果克隆失败（网络问题），可以：
1. 手动下载 ZIP：https://github.com/zgbtc/ghost/archive/refs/heads/master.zip
2. 解压到 `D:\ghost\`

---

### **第四步：安装 Ghost**

#### 4.1 运行安装脚本

```powershell
cd D:\ghost\NousResearch-hermes-agent-4117fc3
powershell -ExecutionPolicy Bypass -File .\安装.ps1
```

安装过程需要 3-5 分钟，会自动：
- 安装 uv（Python 包管理器）
- 创建虚拟环境
- 安装所有依赖
- 配置环境变量

#### 4.2 如果安装慢

国内网络可能较慢，可以先设置镜像：

```powershell
$env:UV_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
```

然后再运行安装脚本。

---

### **第五步：配置 API Key**

#### 5.1 复制配置文件

```powershell
copy ghost_hermes.env $env:USERPROFILE\.hermes\.env
```

#### 5.2 编辑配置文件

```powershell
notepad $env:USERPROFILE\.hermes\.env
```

推荐免费 API（选一个）：

**方案A：Groq（最快，推荐）**
```env
GROQ_API_KEY=你的key
GROQ_API_BASE=https://api.groq.com/openai/v1
DEFAULT_MODEL=groq/llama-3.3-70b-versatile
```
获取地址：https://console.groq.com

**方案B：阿里云百炼（国内稳定）**
```env
OPENAI_API_KEY=你的key
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_MODEL=qwen-turbo
```
获取地址：https://bailian.console.aliyun.com

**方案C：智谱GLM（免费）**
```env
OPENAI_API_KEY=你的key
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4/
DEFAULT_MODEL=glm-4-flash
```
获取地址：https://open.bigmodel.cn

保存后关闭记事本。

---

### **第六步：配置 Chrome 调试模式**

Twitter X 增长引擎需要控制真实的 Chrome 浏览器。

#### 6.1 创建 Chrome 快捷方式

1. 找到 Chrome 安装目录（通常在）：
   ```
   C:\Program Files\Google\Chrome\Application\chrome.exe
   ```

2. 创建快捷方式到桌面

3. 右键快捷方式 → 属性 → 目标，改为：
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebug"
   ```

4. 点击"确定"

#### 6.2 启动 Chrome 调试模式

1. **关闭所有 Chrome 窗口**（重要！）
2. 双击刚才创建的快捷方式
3. Chrome 会以调试模式启动

#### 6.3 登录 Twitter/X

1. 访问：https://x.com/login
2. 登录你的账号
3. **确保已开通 Premium 蓝V**（必需）
4. 保持 Chrome 开启

---

### **第七步：配置 Twitter 引擎**

#### 7.1 重启 PowerShell

关闭之前的 PowerShell，重新打开。

#### 7.2 启动配置向导

```powershell
ghost 配置推特引擎
```

如果提示 "ghost 命令不存在"，尝试：
```powershell
# 重新加载环境变量
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","Machine")

# 或者直接运行
python -m hermes 配置推特引擎
```

#### 7.3 配置选项

```
> 目标领域: Web3/币圈
  （输入你的垂直领域，例如：AI/科技、创业、投资等）

> 目标粉丝数: 3000
  （设定一个目标，例如：1000、3000、5000）

> 运营风格: 专业型
  （选择：专业型/友好型/激进型）

> Telegram 通知（可选，直接回车跳过）:
  Bot Token: 
  Chat ID: 
  
✅ 配置完成！
```

---

### **第八步：启动 Twitter 引擎**

#### 8.1 确保 Chrome 调试模式开启

检查：
- Chrome 正在运行
- 已登录 Twitter/X
- 地址栏能访问 http://localhost:9222

#### 8.2 启动引擎

```powershell
ghost 启动推特引擎
```

或创建快捷命令：
```powershell
# 添加到 PowerShell 配置
echo "function x { ghost 启动推特引擎 }" >> $PROFILE
```

重新打开 PowerShell 后，只需输入 `x` 即可启动。

#### 8.3 首次运行

首次运行会：
1. 检测 Shadow Ban（约15秒）
2. 初始化数据库
3. 分析30个种子KOL
4. 开始学习和互动

你会看到类似输出：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Twitter X 增长引擎启动

✅ Chrome连接成功 (CDP端口9222)
✅ 账号状态：正常
✅ Shadow Ban检测：正常
✅ 今日配额：0/3条推文, 0/8条评论

开始执行：
[08:15] 健康检查完成
[08:16] 开始浏览KOL推文...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎯 **日常使用**

### 每天启动（自动运行2-2.5小时）

```powershell
# 方式1：直接命令
ghost 启动推特引擎

# 方式2：如果设置了别名
x
```

### 查看运行状态

```powershell
# 查看今日数据
ghost 推特数据

# 查看本周报告
ghost 推特周报
```

### 停止运行

按 `Ctrl + C`

---

## ⚙️ **高级配置（可选）**

### 1. 设置定时自动运行

创建 Windows 任务计划：

```powershell
# 创建每天早上9点自动运行的任务
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-Command ghost 启动推特引擎"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "Twitter引擎-早上" -Action $action -Trigger $trigger
```

### 2. 调整配置

编辑配置文件：
```powershell
notepad $env:USERPROFILE\.hermes\twitter_growth_config.yml
```

可以修改：
- 运营风格
- 每日配额
- 通知设置
- 风险容忍度

### 3. 查看数据库

```powershell
# 安装 SQLite 查看器（可选）
sqlite3 $env:USERPROFILE\.hermes\twitter_growth.db

# 或使用在线工具
# 将数据库文件拖入：https://sqliteviewer.app/
```

---

## 🔧 **常见问题排查**

### Q1: "ghost 命令不存在"

**解决方案：**
```powershell
# 方案A：重启 PowerShell

# 方案B：手动加载路径
$env:PATH += ";$env:USERPROFILE\.hermes\bin"

# 方案C：直接用 Python
python -m hermes 启动推特引擎
```

### Q2: Chrome 连接失败

**检查清单：**
1. Chrome 是否在运行？
2. 是否用调试模式启动？（有 `--remote-debugging-port=9222`）
3. 访问 http://localhost:9222 能看到调试界面吗？
4. 是否有多个 Chrome 进程？（杀掉所有，重新启动）

**强制重启 Chrome：**
```powershell
# 杀掉所有 Chrome 进程
Get-Process chrome | Stop-Process -Force

# 等待5秒
Start-Sleep -Seconds 5

# 重新启动调试模式
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=C:\ChromeDebug"
```

### Q3: Twitter 登录状态丢失

**原因：** 清理了浏览器数据或重启了 Chrome

**解决：**
1. 保持 Chrome 开启不要关
2. 不要清理 `C:\ChromeDebug` 目录
3. 如果丢失，重新登录即可

### Q4: API 调用失败

**检查：**
```powershell
# 查看配置
notepad $env:USERPROFILE\.hermes\.env

# 测试 API
curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer 你的key"
```

如果 403/401，说明 API Key 无效，需要重新获取。

### Q5: Shadow Ban 检测误报

**正常现象：**
- 新账号前2周可能会有疑似限流
- 系统会自动降级运行
- 3-5天后通常恢复

**手动检查：**
1. 无痕模式打开 Twitter
2. 搜索：`from:你的用户名`
3. 能看到推文 = 正常

### Q6: 中文显示乱码

**解决：**
```powershell
# 设置 PowerShell 编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

---

## 📊 **查看效果**

### 第一周

**预期：**
- 粉丝：0 → 5-15
- 互动：几乎没有
- **这是正常的！** 前2周是种子期

**做什么：**
- 系统在学习和建立连接
- 不要着急，坚持运行

### 第二周

**预期：**
- 粉丝：15 → 30-50
- 开始有大V回复
- 评论被看到

### 第三-四周

**预期：**
- 粉丝：50 → 100-150
- 进入增长期
- 每天稳定增长

### 30天后

**目标：**
- 粉丝：200-500
- 互动率：5-8%
- 大V关注：5-15个

---

## 🎉 **成功标志**

当你看到这些，说明系统运行正常：

✅ 每天自动运行 2-2.5 小时
✅ 每周收到一次周报
✅ 粉丝稳定增长
✅ 大V开始回复你
✅ Shadow Ban 状态一直正常
✅ 不需要你手动操作任何东西

---

## 📞 **获取帮助**

如果遇到问题：

1. **查看日志：**
   ```powershell
   notepad $env:USERPROFILE\.hermes\logs\twitter_engine.log
   ```

2. **GitHub Issues：**
   https://github.com/zgbtc/ghost/issues

3. **社区讨论：**
   查看项目 README 中的社区链接

---

## 🔄 **更新系统**

定期更新以获取最新功能：

```powershell
cd D:\ghost\NousResearch-hermes-agent-4117fc3

# 拉取最新代码
git pull

# 更新依赖
uv sync
```

---

## 🚀 **开始使用**

完成上述步骤后，只需：

```powershell
ghost 启动推特引擎
```

一切交给 AI，你只需要等待结果！

---

**祝运营顺利，早日达到目标粉丝数！** 🎯
