#!/bin/bash
# Ghost Agent 一键安装脚本 (macOS / Linux)
# 兼容 macOS 12+ (Intel & Apple Silicon) 和 Ubuntu 20.04+
# 用法：bash 安装.sh

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}  Ghost Agent 一键安装${NC}"
echo -e "  源码目录: $SRC_DIR"
echo ""

# ── 0. 检查 git（macOS 可能没装）────────────────────────────
if ! command -v git &>/dev/null; then
    echo -e "${YELLOW}→ git 未安装，正在安装 Xcode Command Line Tools...${NC}"
    echo "  （会弹出安装窗口，点击"安装"，等待完成后重新运行本脚本）"
    xcode-select --install 2>/dev/null || true
    echo -e "${RED}✗ 请等待 Xcode Command Line Tools 安装完成后，重新运行本脚本${NC}"
    exit 1
fi

# ── 1. 安装 uv ────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "→ 安装 uv（Python 包管理器）..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # 加载 uv 到当前 session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        echo -e "${RED}✗ uv 安装失败，请检查网络后重试${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ uv: $(uv --version)${NC}"

# ── 2. 创建虚拟环境（尝试 3.11，失败则用 3.10）────────────────
cd "$SRC_DIR"

PYTHON_VER="3.11"
echo "→ 创建 Python $PYTHON_VER 虚拟环境..."
if ! uv venv .venv --python "$PYTHON_VER" --quiet 2>/dev/null; then
    echo -e "${YELLOW}⚠ Python 3.11 不可用，尝试 3.10...${NC}"
    PYTHON_VER="3.10"
    if ! uv venv .venv --python "$PYTHON_VER" --quiet 2>/dev/null; then
        echo -e "${YELLOW}⚠ Python 3.10 也不可用，尝试系统 Python...${NC}"
        # 用系统自带的 python3
        if command -v python3 &>/dev/null; then
            python3 -m venv .venv
            PYTHON_VER="$(python3 --version | cut -d' ' -f2)"
        else
            echo -e "${RED}✗ 找不到 Python，请先安装 Python 3.10+${NC}"
            echo "  macOS: brew install python@3.11"
            echo "  Ubuntu: sudo apt install python3.11 python3.11-venv"
            exit 1
        fi
    fi
fi
echo -e "${GREEN}✓ Python $PYTHON_VER 虚拟环境创建完成${NC}"

# ── 3. 安装依赖 ───────────────────────────────────────────────
echo "→ 安装依赖（约 2-3 分钟，需要联网）..."

# 确定 pip 路径
if [ -f ".venv/bin/pip" ]; then
    PIP=".venv/bin/pip"
elif command -v uv &>/dev/null; then
    PIP="uv pip"
else
    PIP=".venv/bin/python -m pip"
fi

# 用 uv pip 安装（更快）
if command -v uv &>/dev/null; then
    uv pip install -e ".[cron,cli,pty,mcp]" --quiet 2>/dev/null || \
    uv pip install -e ".[cron,cli,mcp]" --quiet 2>/dev/null || \
    uv pip install -e "." --quiet
    uv pip install pyautogui mss pyperclip --quiet 2>/dev/null || true
else
    .venv/bin/pip install -e ".[cron,cli,pty,mcp]" --quiet 2>/dev/null || \
    .venv/bin/pip install -e "." --quiet
    .venv/bin/pip install pyautogui mss pyperclip --quiet 2>/dev/null || true
fi
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# ── 4. 安装 Playwright 浏览器（可选，失败不影响）──────────────
echo "→ 安装浏览器..."
if command -v uv &>/dev/null; then
    uv pip install playwright --quiet 2>/dev/null || true
else
    .venv/bin/pip install playwright --quiet 2>/dev/null || true
fi
.venv/bin/python -m playwright install chromium --quiet 2>/dev/null || \
    echo -e "${YELLOW}⚠ 浏览器安装跳过（不影响基本功能，之后可运行: .venv/bin/python -m playwright install chromium）${NC}"
echo -e "${GREEN}✓ 浏览器步骤完成${NC}"

# ── 5. 复制配置文件 ───────────────────────────────────────────
mkdir -p ~/.hermes

if [ -f "$SRC_DIR/ghost_hermes.env" ]; then
    cp "$SRC_DIR/ghost_hermes.env" ~/.hermes/.env
    echo -e "${GREEN}✓ API Key 配置已复制${NC}"
else
    # 没有 ghost_hermes.env（从 git clone 安装的情况）
    if [ ! -f ~/.hermes/.env ]; then
        cat > ~/.hermes/.env << 'ENVEOF'
# Ghost Agent 配置
# 至少填一个 API Key，推荐 Groq（免费，最快）
# 获取地址：https://console.groq.com

GROQ_API_KEY=

# 或者阿里云百炼（国内稳定）
# DASHSCOPE_API_KEY=

# YOLO 模式（无审批）
HERMES_YOLO_MODE=1
ENVEOF
        echo -e "${YELLOW}⚠ 未找到 ghost_hermes.env，已创建模板 ~/.hermes/.env${NC}"
        echo -e "${YELLOW}  请编辑 ~/.hermes/.env 填入你的 API Key${NC}"
    fi
fi

if [ -f "$SRC_DIR/ghost_config.yaml" ]; then
    cp "$SRC_DIR/ghost_config.yaml" ~/.hermes/config.yaml
    echo -e "${GREEN}✓ 权限配置已复制${NC}"
fi

# ── 6. 创建 ghost 和 g 命令 ───────────────────────────────────
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/ghost" << SCRIPT
#!/bin/bash
cd "$SRC_DIR"
exec .venv/bin/python -m hermes_cli.main "\$@"
SCRIPT
chmod +x "$BIN_DIR/ghost"

cat > "$BIN_DIR/g" << SCRIPT
#!/bin/bash
cd "$SRC_DIR"
exec .venv/bin/python -m hermes_cli.main "\$@"
SCRIPT
chmod +x "$BIN_DIR/g"

# 也尝试放到 /usr/local/bin（如果有权限）
if [ -w "/usr/local/bin" ]; then
    cp "$BIN_DIR/ghost" /usr/local/bin/ghost
    cp "$BIN_DIR/g" /usr/local/bin/g
fi

echo -e "${GREEN}✓ 命令 ghost 和 g 已创建${NC}"

# ── 7. 写入 shell 配置 ────────────────────────────────────────
SHELL_RC=""
case "$SHELL" in
    */zsh)  SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="$HOME/.bashrc" ;;
    *)      SHELL_RC="$HOME/.profile" ;;
esac

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "\.local/bin" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Ghost Agent" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        echo -e "${GREEN}✓ PATH 已写入 $SHELL_RC${NC}"
    fi
fi

# ── 8. 完成 ───────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  安装完成！${NC}"
echo -e "${CYAN}══════════════════════════════════════${NC}"
echo ""

# macOS 提示辅助功能权限
if [ "$(uname -s)" = "Darwin" ]; then
    echo -e "${YELLOW}⚠ macOS 需要开辅助功能权限才能控制鼠标键盘${NC}"
    echo ""
    echo "  系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能"
    echo "  → 点锁头解锁 → 点 + 号 → 添加终端（Terminal 或 iTerm2）"
    echo ""
fi

echo "  重新打开终端，然后输入："
echo ""
echo -e "      ${YELLOW}g${NC}"
echo ""
echo "  即可启动 Ghost"

# 检查是否需要填 API Key
if [ -f ~/.hermes/.env ] && ! grep -q "^[A-Z].*_KEY=.\+" ~/.hermes/.env 2>/dev/null; then
    echo ""
    echo -e "${YELLOW}⚠ 还需要填入 API Key：${NC}"
    echo "  nano ~/.hermes/.env"
    echo "  推荐免费的 Groq：https://console.groq.com"
fi

echo ""
