#!/bin/bash

# ShellKeeper Installation Script
# This script sets up ShellKeeper to be available as 'sk' in your PATH

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if dtach is installed
if ! command -v dtach &> /dev/null; then
    echo "dtach is not installed. Installing..."
    
    # Try to install dtach based on the system
    if command -v apt-get &> /dev/null; then
        echo "Detected Debian/Ubuntu system. Installing dtach..."
        sudo apt-get update && sudo apt-get install -y dtach
    elif command -v yum &> /dev/null; then
        echo "Detected RHEL/CentOS system. Installing dtach..."
        sudo yum install -y dtach
    elif command -v brew &> /dev/null; then
        echo "Detected macOS with Homebrew. Installing dtach..."
        brew install dtach
    else
        echo -e "${RED}Error: Could not detect package manager${NC}"
        echo "Please install dtach manually:"
        echo "  Ubuntu/Debian: sudo apt-get install dtach"
        echo "  RHEL/CentOS: sudo yum install dtach"
        echo "  macOS: brew install dtach"
        exit 1
    fi
    
    # Check if installation was successful
    if ! command -v dtach &> /dev/null; then
        echo -e "${RED}Error: dtach installation failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}dtach installed successfully${NC}"
fi

# Detect shell configuration file
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    echo -e "${RED}Warning: Unknown shell. You may need to manually add ShellKeeper to your PATH${NC}"
    SHELL_RC="$HOME/.profile"
    SHELL_NAME="unknown"
fi

echo "Installing ShellKeeper..."
echo "Script directory: $SCRIPT_DIR"
echo "Shell: $SHELL_NAME"
echo "Configuration file: $SHELL_RC"

# Create symlink in user's local bin directory
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

# Remove existing symlink if it exists
if [ -L "$LOCAL_BIN/sk" ]; then
    rm "$LOCAL_BIN/sk"
fi

# Create new symlink
ln -s "$SCRIPT_DIR/bin/sk" "$LOCAL_BIN/sk"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo "Adding $LOCAL_BIN to PATH in $SHELL_RC"
    echo "" >> "$SHELL_RC"
    echo "# Added by ShellKeeper installer" >> "$SHELL_RC"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo "Please run: source $SHELL_RC"
    echo "Or start a new terminal session to use 'sk'"
else
    echo -e "${GREEN}Installation complete!${NC}"
    echo "'sk' command is now available"
fi

# Test the installation
if command -v sk &> /dev/null; then
    echo -e "${GREEN}✓ sk command is accessible${NC}"
else
    echo -e "${RED}Note: sk command will be available after reloading your shell${NC}"
fi

echo ""
echo "Usage: sk [create|attach|ls|kill] [session-name]"
echo "Detach from session: Ctrl+\\"