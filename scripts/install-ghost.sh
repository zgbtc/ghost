#!/bin/bash
# ============================================================================
# Ghost Agent Installer — Linux & macOS (Apple Silicon + Intel)
# ============================================================================
#
# One-line install:
#   curl -fsSL https://raw.githubusercontent.com/zgbtc/ghost/main/scripts/install-ghost.sh | bash
#
# ============================================================================

set -e

# Guard against environment leakage
[ -n "${PYTHONPATH:-}" ] && unset PYTHONPATH
[ -n "${PYTHONHOME:-}" ] && unset PYTHONHOME
export UV_NO_CONFIG=1

# ── Colors ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠${NC} $*"; }
error()   { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${BOLD}${CYAN}── $* ──${NC}"; }

# ── Config ──────────────────────────────────────────────────────────
REPO_URL="https://github.com/zgbtc/ghost.git"
GHOST_HOME="${GHOST_HOME:-$HOME/.ghost}"
INSTALL_DIR="${GHOST_INSTALL_DIR:-$HOME/.ghost/ghost-agent}"
PYTHON_VERSION="3.11"

# ── Detect OS ───────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin)
    PLATFORM="macos"
    case "$ARCH" in
      arm64)  CHIP="Apple Silicon (M-series)" ;;
      x86_64) CHIP="Intel" ;;
      *)      CHIP="$ARCH" ;;
    esac
    info "Detected: macOS $CHIP"
    ;;
  Linux)
    PLATFORM="linux"
    info "Detected: Linux $ARCH"
    ;;
  *)
    error "Unsupported OS: $OS. Use install-ghost.ps1 on Windows."
    ;;
esac

echo ""
echo -e "${BOLD}${GREEN}"
echo "  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗"
echo " ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝"
echo " ██║  ███╗███████║██║   ██║███████╗   ██║   "
echo " ██║   ██║██╔══██║██║   ██║╚════██║   ██║   "
echo " ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   "
echo "  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   "
echo -e "${NC}"
echo -e "  ${CYAN}Your digital twin with full computer control${NC}"
echo ""

# ── Check / install uv ──────────────────────────────────────────────
section "Checking dependencies"

if ! command -v uv &>/dev/null; then
  info "Installing uv (fast Python package manager)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi
info "uv: $(uv --version)"

# ── Check git ───────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  if [ "$PLATFORM" = "macos" ]; then
    warn "git not found. Installing via Xcode Command Line Tools..."
    xcode-select --install 2>/dev/null || true
    error "Please install git and re-run this script."
  else
    warn "git not found. Installing..."
    if command -v apt-get &>/dev/null; then
      sudo apt-get install -y git
    elif command -v dnf &>/dev/null; then
      sudo dnf install -y git
    elif command -v pacman &>/dev/null; then
      sudo pacman -S --noconfirm git
    else
      error "Please install git manually and re-run."
    fi
  fi
fi
info "git: $(git --version)"

# ── Clone / update repo ─────────────────────────────────────────────
section "Installing Ghost"

mkdir -p "$(dirname "$INSTALL_DIR")"

if [ -d "$INSTALL_DIR/.git" ]; then
  info "Updating existing installation at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only origin main 2>/dev/null || \
    git -C "$INSTALL_DIR" fetch origin main
else
  info "Cloning Ghost to $INSTALL_DIR"
  git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ── Create venv + install ────────────────────────────────────────────
section "Setting up Python environment"

uv venv .venv --python "$PYTHON_VERSION" --quiet
info "Python venv created"

# Install Ghost with desktop control extras
info "Installing Ghost + dependencies (this takes ~1 min)..."
uv pip install -e ".[all,ghost-desktop]" --quiet

# Platform-specific desktop extras
if [ "$PLATFORM" = "macos" ]; then
  uv pip install pyautogui mss pyperclip --quiet
  info "macOS desktop control: pyautogui + mss installed"
  # Check accessibility permissions
  echo ""
  warn "macOS: Ghost needs Accessibility permission to control the desktop."
  warn "Go to: System Settings → Privacy & Security → Accessibility"
  warn "Add your Terminal app (or iTerm2) to the allowed list."
  echo ""
elif [ "$PLATFORM" = "linux" ]; then
  uv pip install pyautogui mss pyperclip --quiet
  # Try to install xdotool for window management
  if command -v apt-get &>/dev/null; then
    sudo apt-get install -y xdotool python3-tk python3-dev scrot 2>/dev/null || true
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y xdotool python3-tkinter 2>/dev/null || true
  fi
  info "Linux desktop control: pyautogui + mss + xdotool installed"
fi

# ── Install Playwright (stealth browser) ────────────────────────────
section "Setting up stealth browser"

uv pip install playwright --quiet
.venv/bin/python -m playwright install chromium --quiet 2>/dev/null || \
  warn "Playwright browser install failed — browser tools will be unavailable"
info "Stealth browser (Playwright + Chromium) ready"

# ── Create ghost command ─────────────────────────────────────────────
section "Creating ghost command"

GHOST_BIN=""
if [ -w "/usr/local/bin" ]; then
  GHOST_BIN="/usr/local/bin/ghost"
elif [ -d "$HOME/.local/bin" ]; then
  GHOST_BIN="$HOME/.local/bin/ghost"
  mkdir -p "$HOME/.local/bin"
else
  mkdir -p "$HOME/bin"
  GHOST_BIN="$HOME/bin/ghost"
fi

cat > "$GHOST_BIN" << GHOSTSCRIPT
#!/bin/bash
# Ghost Agent launcher
export GHOST_HOME="\${GHOST_HOME:-$GHOST_HOME}"
cd "$INSTALL_DIR"
exec .venv/bin/python -m hermes_cli.main "\$@"
GHOSTSCRIPT

chmod +x "$GHOST_BIN"
info "ghost command installed at $GHOST_BIN"

# Also create hermes alias for compatibility
HERMES_BIN="$(dirname "$GHOST_BIN")/hermes"
ln -sf "$GHOST_BIN" "$HERMES_BIN" 2>/dev/null || cp "$GHOST_BIN" "$HERMES_BIN"
info "hermes alias created"

# ── Shell config ─────────────────────────────────────────────────────
section "Configuring shell"

SHELL_RC=""
case "$SHELL" in
  */zsh)  SHELL_RC="$HOME/.zshrc" ;;
  */bash) SHELL_RC="$HOME/.bashrc" ;;
  *)      SHELL_RC="$HOME/.profile" ;;
esac

GHOST_ENV_BLOCK="
# Ghost Agent
export GHOST_HOME=\"$GHOST_HOME\"
export PATH=\"$(dirname "$GHOST_BIN"):\$PATH\"
"

if ! grep -q "Ghost Agent" "$SHELL_RC" 2>/dev/null; then
  echo "$GHOST_ENV_BLOCK" >> "$SHELL_RC"
  info "Added Ghost to $SHELL_RC"
fi

# ── Create .ghost directory ──────────────────────────────────────────
mkdir -p "$GHOST_HOME"/{skills,failures,sessions,demonstrations}

# ── Setup wizard ─────────────────────────────────────────────────────
section "Setup"

echo ""
echo -e "${BOLD}Ghost is installed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Reload your shell:  source $SHELL_RC"
echo "  2. Run setup:          ghost setup"
echo "  3. Start Ghost:        ghost"
echo ""
echo "Or set your API key directly:"
echo "  export ANTHROPIC_API_KEY=sk-ant-..."
echo "  ghost"
echo ""

# Offer to run setup now if interactive
if [ -t 0 ]; then
  read -p "Run 'ghost setup' now? [Y/n] " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    export PATH="$(dirname "$GHOST_BIN"):$PATH"
    export GHOST_HOME="$GHOST_HOME"
    ghost setup
  fi
fi

info "Installation complete. Run 'ghost' to start."
