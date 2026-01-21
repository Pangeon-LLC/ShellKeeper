#!/bin/bash
# Setup script to make SK prompt automatic
# Safe to run multiple times - idempotent

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SK_BIN_DIR="$(cd "$SCRIPT_DIR/../bin" && pwd)"

# Add to .zshrc if not already there
if [ -f ~/.zshrc ]; then
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
fi

# Add to .bashrc if not already there
if [ -f ~/.bashrc ]; then
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
fi
