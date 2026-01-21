#!/bin/bash
# ShellKeeper Installation Script
# Safe to run multiple times - idempotent

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_BIN="$HOME/.local/bin"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Symbols
CHECK="${GREEN}✓${NC}"
ARROW="${BLUE}→${NC}"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  ShellKeeper Installer${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. Check/install dtach
echo -e "${ARROW} Checking dtach..."
if command -v dtach &>/dev/null; then
    echo -e "  ${CHECK} dtach installed"
else
    echo -e "  ${YELLOW}Installing dtach...${NC}"
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq dtach
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y -q dtach
    elif command -v brew &>/dev/null; then
        brew install dtach
    else
        echo -e "  ${YELLOW}Could not install dtach. Please install manually.${NC}"
        exit 1
    fi
    echo -e "  ${CHECK} dtach installed"
fi

# 2. Enable loginctl linger (Linux only)
if [ "$(uname)" = "Linux" ]; then
    echo -e "${ARROW} Checking session persistence..."
    if loginctl show-user "$USER" 2>/dev/null | grep -q "Linger=yes"; then
        echo -e "  ${CHECK} Linger enabled"
    else
        echo -e "  ${YELLOW}Enabling linger...${NC}"
        sudo loginctl enable-linger "$USER"
        echo -e "  ${CHECK} Linger enabled"
    fi
fi

# 3. Create ~/.local/bin if needed
echo -e "${ARROW} Setting up commands..."
if [ ! -d "$LOCAL_BIN" ]; then
    mkdir -p "$LOCAL_BIN"
fi

# 4. Create symlinks for commands
link_cmd() {
    local cmd="$1"
    if [ -L "$LOCAL_BIN/$cmd" ]; then
        current=$(readlink "$LOCAL_BIN/$cmd")
        if [ "$current" = "$SCRIPT_DIR/bin/$cmd" ]; then
            return 0  # Already correct
        fi
    fi
    ln -sf "$SCRIPT_DIR/bin/$cmd" "$LOCAL_BIN/$cmd"
    return 1  # Was updated
}

updated=0
for cmd in sk sk-info sk-reconnect sk-keepalive sk-keepalive-stop; do
    if ! link_cmd "$cmd"; then
        ((updated++)) || true
    fi
done

if [ "$updated" -gt 0 ]; then
    echo -e "  ${CHECK} Commands linked ($updated updated)"
else
    echo -e "  ${CHECK} Commands linked"
fi

# 5. Set up autostart
echo -e "${ARROW} Configuring autostart..."
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/shellkeeper.desktop"
if [ -f "$AUTOSTART_FILE" ]; then
    echo -e "  ${CHECK} Autostart configured"
else
    mkdir -p "$AUTOSTART_DIR"
    cat > "$AUTOSTART_FILE" << EOF
[Desktop Entry]
Type=Application
Name=ShellKeeper Session Restore
Comment=Check for surviving ShellKeeper sessions on login
Exec=$SCRIPT_DIR/bin/sk-autostart
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
    echo -e "  ${CHECK} Autostart configured"
fi

# 6. Install man page
echo -e "${ARROW} Installing documentation..."
MAN_DIR="$HOME/.local/share/man/man1"
mkdir -p "$MAN_DIR"
ln -sf "$SCRIPT_DIR/man/sk.1" "$MAN_DIR/sk.1" 2>/dev/null || true
echo -e "  ${CHECK} Man page installed"

# 7. Clean up old wrapper if it exists
OLD_WRAPPER="$HOME/tools/sk"
if [ -f "$OLD_WRAPPER" ] && [ ! -L "$OLD_WRAPPER" ]; then
    rm "$OLD_WRAPPER"
    echo -e "  ${CHECK} Cleaned old wrapper"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${DIM}Quick start:${NC}"
echo -e "    sk new              Create a session"
echo -e "    sk ls               List sessions"
echo -e "    man sk              Full documentation"
echo ""
echo -e "  ${DIM}Optional aliases - add to .zshrc:${NC}"
echo -e "    source $SCRIPT_DIR/lib/shellkeeper-aliases.sh"
echo ""
