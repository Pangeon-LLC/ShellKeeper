#!/usr/bin/zsh
# This script tests what prompt variable your zsh uses

echo "=== ZSH Prompt Test ==="
echo "ZSH_VERSION: $ZSH_VERSION"
echo ""
echo "Current prompt variables:"
echo "PROMPT='$PROMPT'"
echo "PS1='$PS1'"
echo ""

# Test which one affects the display
echo "Testing PROMPT variable..."
ORIG_PROMPT="$PROMPT"
PROMPT="TEST1> "
echo -n ""  # Force prompt display
PROMPT="$ORIG_PROMPT"

echo "Testing PS1 variable..."
ORIG_PS1="$PS1"  
PS1="TEST2> "
echo -n ""  # Force prompt display
PS1="$ORIG_PS1"

# Show oh-my-zsh info if present
if [ -n "$ZSH_THEME" ]; then
    echo ""
    echo "Oh-my-zsh detected:"
    echo "ZSH_THEME='$ZSH_THEME'"
    echo "ZSH='$ZSH'"
fi