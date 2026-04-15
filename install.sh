#!/usr/bin/env bash
set -e

# ─────────────────────────────────────────────
# Multicoder Installer
# ─────────────────────────────────────────────

REPO_URL="https://raw.githubusercontent.com/YongfengX/Multicoder/main"
INSTALL_DIR="$HOME/.local/lib/multicoder"
BIN_DIR="$HOME/.local/bin"
SKILL_DIR="$HOME/.claude/skills/multicoder"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}→${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo "  Multicoder Installer"
echo "  ────────────────────────────────────"
echo ""

# ── 1. Check dependencies ─────────────────────
info "Checking dependencies..."

command -v python3 >/dev/null 2>&1 || error "python3 is required but not installed."
command -v pip3 >/dev/null 2>&1 || error "pip3 is required but not installed."

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED="3.11"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    success "Python $PYTHON_VERSION"
else
    error "Python 3.11+ required (found $PYTHON_VERSION)"
fi

# ── 2. Install Python packages ────────────────
info "Installing Python dependencies..."
pip3 install --quiet requests python-dotenv
success "requests, python-dotenv installed"

# ── 3. Download and install library files ─────
info "Installing Multicoder to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/multicoder/providers"

FILES=(
    "multicoder.py"
    "multicoder/__init__.py"
    "multicoder/config.py"
    "multicoder/fallback.py"
    "multicoder/session.py"
    "multicoder/providers/__init__.py"
    "multicoder/providers/base.py"
    "multicoder/providers/cli_provider.py"
    "multicoder/providers/api_provider.py"
    ".env.example"
    ".multicoder.json"
)

for file in "${FILES[@]}"; do
    dir=$(dirname "$INSTALL_DIR/$file")
    mkdir -p "$dir"
    curl -sSL "$REPO_URL/$file" -o "$INSTALL_DIR/$file"
done

success "Library files installed"

# ── 4. Create multicoder command ──────────────
info "Creating multicoder command..."
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/multicoder" << EOF
#!/usr/bin/env bash
# Multicoder wrapper — runs multicoder.py from the install directory
cd "\$PWD"
PYTHONPATH="$INSTALL_DIR" python3 "$INSTALL_DIR/multicoder.py" "\$@"
EOF

chmod +x "$BIN_DIR/multicoder"
success "Command created at $BIN_DIR/multicoder"

# ── 5. Install Claude Code skill ──────────────
if [ -d "$HOME/.claude" ]; then
    info "Installing Claude Code skill..."
    mkdir -p "$SKILL_DIR"
    curl -sSL "$REPO_URL/skills/multicoder/SKILL.md" -o "$SKILL_DIR/SKILL.md"
    success "Skill installed to $SKILL_DIR"
else
    warn "~/.claude not found — skipping skill install (Claude Code not detected)"
    warn "To install the skill manually later, run:"
    warn "  mkdir -p ~/.claude/skills/multicoder"
    warn "  curl -sSL $REPO_URL/skills/multicoder/SKILL.md -o ~/.claude/skills/multicoder/SKILL.md"
fi

# ── 6. Check PATH ─────────────────────────────
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR is not in your PATH."
    echo ""
    echo "  Add this to your ~/.zshrc or ~/.bashrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "  Then run: source ~/.zshrc"
fi

# ── 7. Print next steps ───────────────────────
echo ""
echo "  ────────────────────────────────────"
success "Multicoder installed!"
echo ""
echo "  Next steps:"
echo ""
echo "  1. In your project, create .multicoder.json:"
echo "     cp $INSTALL_DIR/.multicoder.json ./.multicoder.json"
echo ""
echo "  2. Set your API keys:"
echo "     cp $INSTALL_DIR/.env.example ./.env"
echo "     # Edit .env and fill in MINIMAX_API_KEY, DASHSCOPE_API_KEY"
echo ""
echo "  3. In Claude Code, use:"
echo "     /multicoder \"build a login page with JWT auth\""
echo ""
echo "  Docs: https://github.com/YongfengX/Multicoder"
echo ""
