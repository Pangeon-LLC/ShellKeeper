#!/bin/bash
# ShellKeeper aliases for quick access
# Add to your ~/.bashrc or ~/.zshrc:
# source /path/to/shellkeeper-aliases.sh

# Quick session commands
alias sn='sk new'          # Create new session
alias sl='sk ls'           # List sessions
alias sa='sk attach'       # Attach to session
alias ski='sk-info'        # Check if in session
alias sc='sk clean'        # Clean dead sessions
alias skp='source sk-prompt' # Update prompt in current session
alias skr='sk-reconnect'   # Auto-reconnect to last session
alias skl='sk last'        # Quick reconnect to most recent
alias skks='sk-keepalive-stop' # Stop keepalive in current session

# Reminder function
skhelp() {
    echo "ShellKeeper Quick Commands:"
    echo "  sk         - Attach to most recent session"
    echo "  sk NAME    - Attach to named session"
    echo "  sn [NAME]  - Create new session"
    echo "  sl         - List sessions"
    echo "  sc         - Clean dead sessions"
    echo "  ski        - Check if in session"
    echo "  skp        - Update prompt to show session name"
    echo "  skr        - Auto-reconnect (interactive)"
    echo "  skl        - Quick reconnect to last session"
    echo "  skks       - Stop keepalive in current session"
    echo ""
    echo "Inside session:"
    echo "  Ctrl+\\     - DETACH (keep running)"
    echo "  Ctrl+C     - Stops current process (normal)"
    echo "  Ctrl+Z     - Suspends current process (normal)"
    echo "  exit       - End session"
}

# Auto-reconnect function for SSH sessions
sk_auto() {
    # This function can be added to your .bashrc/.zshrc after the SSH connection
    # to automatically reconnect to your last ShellKeeper session
    if [ -n "$SSH_CONNECTION" ] && [ -z "$SHELLKEEPER_SESSION" ]; then
        echo "Checking for ShellKeeper sessions..."
        if command -v sk >/dev/null 2>&1; then
            sessions=$(sk ls 2>/dev/null | grep -c '^\s\+\S\+')
            if [ "$sessions" -gt 0 ]; then
                echo "Found $sessions ShellKeeper session(s)."
                echo "Run 'skr' to reconnect or 'skl' for quick reconnect to last session."
            fi
        fi
    fi
}

# Show reminder when sourced
echo "ShellKeeper aliases loaded. Type 'skhelp' for commands."