#!/bin/bash
# ShellKeeper Installation Script
# Safe to run multiple times - idempotent
#
# Installs sk command via symlink to ~/.local/bin (no .zshrc changes needed)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_BIN="$HOME/.local/bin"

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

# 3. Create ~/.local/bin if needed
echo "Checking ~/.local/bin..."
if [ ! -d "$LOCAL_BIN" ]; then
    mkdir -p "$LOCAL_BIN"
    echo "  [OK] Created $LOCAL_BIN"
else
    echo "  [OK] $LOCAL_BIN exists"
fi

# 4. Create symlinks for commands
echo "Creating symlinks..."

# Main sk command
if [ -L "$LOCAL_BIN/sk" ]; then
    current_target=$(readlink "$LOCAL_BIN/sk")
    if [ "$current_target" = "$SCRIPT_DIR/bin/sk" ]; then
        echo "  [OK] sk already linked"
    else
        ln -sf "$SCRIPT_DIR/bin/sk" "$LOCAL_BIN/sk"
        echo "  [OK] sk updated (was: $current_target)"
    fi
else
    ln -sf "$SCRIPT_DIR/bin/sk" "$LOCAL_BIN/sk"
    echo "  [OK] sk linked"
fi

# Helper commands
for cmd in sk-info sk-reconnect sk-keepalive sk-keepalive-stop; do
    if [ -L "$LOCAL_BIN/$cmd" ]; then
        current_target=$(readlink "$LOCAL_BIN/$cmd")
        if [ "$current_target" = "$SCRIPT_DIR/bin/$cmd" ]; then
            echo "  [OK] $cmd already linked"
        else
            ln -sf "$SCRIPT_DIR/bin/$cmd" "$LOCAL_BIN/$cmd"
            echo "  [OK] $cmd updated"
        fi
    else
        ln -sf "$SCRIPT_DIR/bin/$cmd" "$LOCAL_BIN/$cmd"
        echo "  [OK] $cmd linked"
    fi
done

# 5. Set up autostart
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

# 6. Clean up old wrapper if it exists
OLD_WRAPPER="$HOME/tools/sk"
if [ -f "$OLD_WRAPPER" ] && [ ! -L "$OLD_WRAPPER" ]; then
    echo "Removing old wrapper script..."
    rm "$OLD_WRAPPER"
    echo "  [OK] Removed $OLD_WRAPPER"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "The 'sk' command is now available."
echo ""
echo "Optional: Add to .zshrc for aliases (sn, sl, skt, etc.) and prompt:"
echo "  source $SCRIPT_DIR/lib/shellkeeper-aliases.sh"
echo "  if [ -n \"\$SHELLKEEPER_SESSION\" ]; then"
echo "      source $SCRIPT_DIR/bin/sk-prompt >/dev/null 2>&1"
echo "  fi"
