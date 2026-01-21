#!/bin/bash
# Setup script to make SK prompt automatic
# Safe to run multiple times - idempotent

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SK_BIN_DIR="$(cd "$SCRIPT_DIR/../bin" && pwd)"

# Helper to make file writable if needed, returns true if we changed it
make_writable() {
    local file="$1"
    if [ -f "$file" ] && [ ! -w "$file" ]; then
        chmod u+w "$file"
        return 0
    fi
    return 1
}

# Helper to restore read-only
restore_readonly() {
    local file="$1"
    chmod u-w "$file"
}

# Add to .zshrc if not already there
if [ -f ~/.zshrc ]; then
    made_writable=false
    if make_writable ~/.zshrc; then
        made_writable=true
    fi

    if ! grep -q "sk-prompt" ~/.zshrc 2>/dev/null; then
        echo "" >> ~/.zshrc
        echo "# ShellKeeper automatic prompt" >> ~/.zshrc
        echo 'if [ -n "$SHELLKEEPER_SESSION" ]; then' >> ~/.zshrc
        echo "    source $SK_BIN_DIR/sk-prompt >/dev/null 2>&1" >> ~/.zshrc
        echo 'fi' >> ~/.zshrc
        echo "  [OK] Added SK prompt to ~/.zshrc"
    else
        echo "  [OK] SK prompt already in ~/.zshrc"
    fi

    if [ "$made_writable" = true ]; then
        restore_readonly ~/.zshrc
    fi
fi

# Add to .bashrc if not already there
if [ -f ~/.bashrc ]; then
    made_writable=false
    if make_writable ~/.bashrc; then
        made_writable=true
    fi

    if ! grep -q "sk-prompt" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# ShellKeeper automatic prompt" >> ~/.bashrc
        echo 'if [ -n "$SHELLKEEPER_SESSION" ]; then' >> ~/.bashrc
        echo "    source $SK_BIN_DIR/sk-prompt >/dev/null 2>&1" >> ~/.bashrc
        echo 'fi' >> ~/.bashrc
        echo "  [OK] Added SK prompt to ~/.bashrc"
    else
        echo "  [OK] SK prompt already in ~/.bashrc"
    fi

    if [ "$made_writable" = true ]; then
        restore_readonly ~/.bashrc
    fi
fi
