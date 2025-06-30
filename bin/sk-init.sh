#!/bin/bash
# ShellKeeper initialization script
# This is sourced by new sessions to set up the prompt

if [ -n "$SHELLKEEPER_SESSION" ]; then
    # For bash
    if [ -n "$BASH_VERSION" ]; then
        # Override PROMPT_COMMAND if it exists to ensure our prompt stays
        if [ -n "$PROMPT_COMMAND" ]; then
            export SHELLKEEPER_ORIG_PROMPT_COMMAND="$PROMPT_COMMAND"
            export PROMPT_COMMAND="export PS1='[sk:$SHELLKEEPER_SESSION] \${PS1_BASE:-\\u@\\h:\\w\\$ }'; $PROMPT_COMMAND"
        else
            export PS1="[sk:$SHELLKEEPER_SESSION] ${PS1:-\\u@\\h:\\w\\$ }"
        fi
        export PS1_BASE="${PS1:-\\u@\\h:\\w\\$ }"
    # For zsh
    elif [ -n "$ZSH_VERSION" ]; then
        export PS1="[sk:$SHELLKEEPER_SESSION] ${PS1:-%n@%m:%~%# }"
    fi
    
    # Start keepalive if enabled
    if [ "${SK_KEEPALIVE_ENABLED:-true}" = "true" ]; then
        # Get the directory where this script is located
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -x "$SCRIPT_DIR/sk-keepalive" ]; then
            "$SCRIPT_DIR/sk-keepalive" >/dev/null 2>&1
        fi
    fi
fi