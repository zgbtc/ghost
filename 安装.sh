#!/bin/bash
# Ghost Agent 一键安装脚本 (macOS / Linux)
# 用法：在源码目录里执行 bash 安装.sh

set -e

# 颜色
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 源码目录 = 本脚本所在目录
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}  Ghost Agent 一键安装${NC}"
echo -e "  源码目录: $SRC_DIR"
echo ""

# ── 1. 安装 uv ────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "→ 安装 uv（Python 包管理器）..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    echo -e "${GREEN}✓ uv 安装完成${NC}"
else
    echo -e "${GREEN}✓ uv 已安装: $(uv --version)${NC}"
fi

# ── 2. 创建虚拟环境 ───────────────────────────────────────────
echo "→ 创建 Python 3.11 虚拟环境..."
cd "$SRC_DIR"
uv venv .venv --python 3.11 --quiet
echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"

# ── 3. 安装依赖 ───────────────────────────────────────────────
echo "→ 安装依赖（约 2-3 分钟，需要联网）..."
uv pip install -e ".[cron,cli,pty,mcp]" --quiet
uv pip install pyautogui mss pyperclip --quiet
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# ── 4. 安装 Playwright 浏览器 ─────────────────────────────────
echo "→ 安装浏览器（约 1 分钟）..."
uv pip install playwright --quiet
.venv/bin/python -m playwright install chromium --quiet 2>/dev/null || \
    echo -e "${YELLOW}⚠ 浏览器安装失败，之后可手动运行: playwright install chromium${NC}"
echo -e "${GREEN}✓ 浏览器安装完成${NC}"

# ── 5. 复制配置文件 ───────────────────────────────────────────
mkdir -p ~/.hermes
cp "$SRC_DIR/ghost_hermes.env"  ~/.hermes/.env
cp "$SRC_DIR/ghost_config.yaml" ~/.hermes/config.yaml
echo -e "${GREEN}✓ 配置文件已复制到 ~/.hermes/${NC}"

# ── 6. 创建 ghost 命令 ────────────────────────────────────────
# 选择安装位置
if [ -w "/usr/local/bin" ]; then
    BIN_DIR="/usr/local/bin"
else
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

cat > "$BIN_DIR/ghost" << SCRIPT
#!/bin/bash
cd "$SRC_DIR"
exec .venv/bin/python -m hermes_cli.main "\$@"
SCRIPT
chmod +x "$BIN_DIR/ghost"

# 创建 g 快捷命令
cat > "$BIN_DIR/g" << SCRIPT
#!/bin/bash
cd "$SRC_DIR"
exec .venv/bin/python -m hermes_cli.main "\$@"
SCRIPT
chmod +x "$BIN_DIR/g"

echo -e "${GREEN}✓ 命令 ghost 和 g 已创建${NC}"

# ── 7. 写入 shell 配置 ────────────────────────────────────────
SHELL_RC=""
case "$SHELL" in
    */zsh)  SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="$HOME/.bashrc" ;;
    *)      SHELL_RC="$HOME/.profile" ;;
esac

# 只在 BIN_DIR 不是 /usr/local/bin 时才需要加 PATH
if [ "$BIN_DIR" != "/usr/local/bin" ]; then
    if ! grep -q "ghost" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Ghost Agent" >> "$SHELL_RC"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
    fi
fi

# ── 8. 提示开辅助功能权限 ─────────────────────────────────────
echo ""
echo -e "${YELLOW}══════════════════════════════════════${NC}"
echo -e "${GREEN}  安装完成！${NC}"
echo -e "${YELLOW}══════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠ 重要：需要开辅助功能权限才能控制鼠标键盘${NC}"
echo ""
echo "  系统设置 → 隐私与安全性 → 辅助功能"
echo "  → 点 + 号 → 添加你的终端（Terminal 或 iTerm2）"
echo "  → 打开开关"
echo ""
echo "  开完权限后，重新打开终端，输入："
echo ""
echo -e "      ${YELLOW}g${NC}"
echo ""
echo "  即可启动 Ghost"
echo ""

# 询问是否立即打开系统设置
read -p "是否现在打开系统设置？[Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || \
    open "/System/Library/PreferencePanes/Security.prefPane" 2>/dev/null || true
fi
