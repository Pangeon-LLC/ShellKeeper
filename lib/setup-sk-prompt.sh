#!/bin/bash
# Setup script to make SK prompt automatic

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SK_BIN_DIR="$(cd "$SCRIPT_DIR/../bin" && pwd)"

echo "Setting up automatic ShellKeeper prompt..."

# Add to .zshrc if not already there
if ! grep -q "sk-prompt" ~/.zshrc 2>/dev/null; then
    echo "" >> ~/.zshrc
    echo "# ShellKeeper automatic prompt" >> ~/.zshrc
    echo 'if [ -n "$SHELLKEEPER_SESSION" ]; then' >> ~/.zshrc
    echo "    source $SK_BIN_DIR/sk-prompt >/dev/null 2>&1" >> ~/.zshrc
    echo 'fi' >> ~/.zshrc
    echo "✓ Added SK prompt to ~/.zshrc"
else
    echo "✓ SK prompt already in ~/.zshrc"
fi

# Add to .bashrc if not already there  
if ! grep -q "sk-prompt" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# ShellKeeper automatic prompt" >> ~/.bashrc
    echo 'if [ -n "$SHELLKEEPER_SESSION" ]; then' >> ~/.bashrc
    echo "    source $SK_BIN_DIR/sk-prompt >/dev/null 2>&1" >> ~/.bashrc
    echo 'fi' >> ~/.bashrc
    echo "✓ Added SK prompt to ~/.bashrc"
else
    echo "✓ SK prompt already in ~/.bashrc"
fi

echo ""
echo "Setup complete! New SK sessions will automatically show [sk:name] in the prompt."