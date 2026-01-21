#!/bin/bash
# ShellKeeper Installation Script
# Safe to run multiple times - idempotent
#
# Note: Does NOT modify shell rc files. Add these to your .zshrc manually:
#   export PATH="$PATH:/home/graham/tools/ShellKeeper/bin"
#   source /home/graham/tools/ShellKeeper/lib/shellkeeper-aliases.sh
#   if [ -n "$SHELLKEEPER_SESSION" ]; then
#       source /home/graham/tools/ShellKeeper/bin/sk-prompt >/dev/null 2>&1
#   fi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== ShellKeeper Installation ==="
echo ""

# 1. Check/install dtach
echo "Checking for dtach..."
if command -v dtach &>/dev/null; then
    echo "  [OK] dtach is installed"
else
    echo "  Installing dtach..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y dtach
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y dtach
    elif command -v brew &>/dev/null; then
        brew install dtach
    else
        echo "  [ERROR] Could not install dtach. Please install manually."
        exit 1
    fi
    echo "  [OK] dtach installed"
fi

# 2. Enable loginctl linger (Linux only)
if [ "$(uname)" = "Linux" ]; then
    echo "Checking loginctl linger..."
    if loginctl show-user "$USER" 2>/dev/null | grep -q "Linger=yes"; then
        echo "  [OK] Linger already enabled"
    else
        echo "  Enabling linger for $USER..."
        sudo loginctl enable-linger "$USER"
        echo "  [OK] Linger enabled"
    fi
fi

# 3. Set up autostart
echo "Checking GNOME autostart..."
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/shellkeeper.desktop"
if [ -f "$AUTOSTART_FILE" ]; then
    echo "  [OK] Autostart already configured"
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
    echo "  [OK] Autostart configured"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Add these lines to your .zshrc:"
echo ""
echo "  export PATH=\"\$PATH:$SCRIPT_DIR/bin\""
echo "  source $SCRIPT_DIR/lib/shellkeeper-aliases.sh"
echo "  if [ -n \"\$SHELLKEEPER_SESSION\" ]; then"
echo "      source $SCRIPT_DIR/bin/sk-prompt >/dev/null 2>&1"
echo "  fi"
echo ""
echo "Then: exec \$SHELL"
