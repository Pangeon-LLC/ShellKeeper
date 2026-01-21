#!/bin/bash
# ShellKeeper Installation Script
# Safe to run multiple times - idempotent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_RC="$HOME/.zshrc"

# Use bashrc if zshrc doesn't exist
if [ ! -f "$SHELL_RC" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

# Check if shell rc is writable, make it writable if needed
MADE_WRITABLE=false
if [ -f "$SHELL_RC" ] && [ ! -w "$SHELL_RC" ]; then
    echo "Making $SHELL_RC writable..."
    chmod u+w "$SHELL_RC"
    MADE_WRITABLE=true
fi

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

# 3. Add to PATH
echo "Checking PATH in $SHELL_RC..."
if grep -q "ShellKeeper/bin" "$SHELL_RC" 2>/dev/null; then
    echo "  [OK] PATH already configured"
else
    echo "" >> "$SHELL_RC"
    echo "# ShellKeeper" >> "$SHELL_RC"
    echo "export PATH=\"\$PATH:$SCRIPT_DIR/bin\"" >> "$SHELL_RC"
    echo "  [OK] Added to PATH"
fi

# 4. Set up prompt (setup-sk-prompt.sh is already idempotent)
echo "Setting up automatic prompt..."
"$SCRIPT_DIR/lib/setup-sk-prompt.sh"

# 5. Add aliases
echo "Checking aliases in $SHELL_RC..."
if grep -q "shellkeeper-aliases.sh" "$SHELL_RC" 2>/dev/null; then
    echo "  [OK] Aliases already configured"
else
    echo "" >> "$SHELL_RC"
    echo "# ShellKeeper aliases" >> "$SHELL_RC"
    echo "source \"$SCRIPT_DIR/lib/shellkeeper-aliases.sh\"" >> "$SHELL_RC"
    echo "  [OK] Added aliases"
fi

# 6. Set up autostart
echo "Setting up GNOME autostart..."
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

# Restore original permissions if we changed them
if [ "$MADE_WRITABLE" = true ]; then
    echo "Restoring $SHELL_RC permissions..."
    chmod u-w "$SHELL_RC"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Reload your shell to activate:"
echo "  exec \$SHELL"
echo ""
echo "Then try:"
echo "  sk new                          # Create a session"
echo "  sk profiles list                # See GNOME Terminal profiles"
echo "  sk new --profile=\"ProfileName\"  # Create with specific profile"
echo ""
echo "Remember: Detach with Ctrl+\\ (not Ctrl+C)"
