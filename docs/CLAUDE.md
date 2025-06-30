# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Directory Structure

```
shellkeeper/
├── bin/          # Main executables
│   ├── sk                  # Main CLI wrapper
│   ├── shellkeeper.py      # Core Python implementation
│   ├── sk-init.sh          # Session initialization
│   ├── sk-prompt           # Prompt management
│   ├── sk-info             # Session status checker
│   ├── sk-debug.sh         # Debug utilities
│   ├── sk-reconnect        # Interactive reconnection tool
│   ├── sk-keepalive        # Keepalive daemon
│   └── sk-keepalive-stop   # Stop keepalive daemon
├── lib/          # Supporting libraries
│   ├── shellkeeper-aliases.sh  # Shell aliases
│   └── setup-sk-prompt.sh      # One-time setup script
├── tests/        # Test scripts
│   └── test-zsh-prompt.sh
└── docs/         # Documentation
    ├── README.md
    ├── CLAUDE.md
    └── shell-keeper-design.md
```

## Project Overview

ShellKeeper is a lightweight terminal session manager that solves scrolling issues in traditional terminal multiplexers. It uses `dtach` as a backend with a Python wrapper for easy session management.

## Key Commands

### Development & Testing
```bash
# Run ShellKeeper directly
python3 shellkeeper/bin/shellkeeper.py [command]

# Test the wrapper script
./shellkeeper/bin/sk [command]

# Test Zsh prompt functionality
./shellkeeper/tests/test-zsh-prompt.sh

# Debug session issues
./shellkeeper/bin/sk-debug.sh
```

### Installation Check
```bash
# Verify dtach is installed (required dependency)
which dtach

# Check if ShellKeeper is in PATH
which sk
```

## Architecture

### Core Components
- **shellkeeper.py**: Main implementation using Python standard library only
  - SessionManager class handles all operations
  - Uses dtach subprocess calls for session persistence
  - Socket files stored in ~/.shellkeeper/sessions/
  - Supports keepalive configuration and environment setup

- **sk**: Bash wrapper providing the main CLI interface
  - Calls shellkeeper.py with appropriate arguments
  - Handles environment setup
  - Dynamic path resolution using readlink

- **sk-init.sh**: Session initialization script
  - Sources prompt customization
  - Sets up shell environment within sessions
  - Starts keepalive daemon if enabled (default: true)

### Reconnection Tools
- **sk-reconnect**: Interactive reconnection script
  - Shows most recent session
  - Offers options for multiple sessions
  - Provides session listing

- **sk last command**: Quick reconnect to most recent session
  - Added to shellkeeper.py as a subcommand
  - Used by aliases `skl` for quick access

### Keepalive System
- **sk-keepalive**: Background daemon preventing idle disconnections
  - Sends silent terminal control sequences every 60s (configurable)
  - One instance per session with PID tracking
  - Started automatically by sk-init.sh

- **sk-keepalive-stop**: Stops the keepalive daemon
  - Cleans up PID file
  - Available as `skks` alias

### Session Management Flow
1. User runs `sk new [name]` → Creates dtach socket in ~/.shellkeeper/sessions/
2. User runs `sk [name]` → Attaches to existing dtach session
3. User presses Ctrl+\ → Detaches from session (keeps it running)
4. Session cleanup via `sk kill [name]` or `sk clean` for dead sockets

### No Build Process
- Scripts are directly executable
- No external Python dependencies
- Only system requirement: `dtach` package

## Important Implementation Notes

1. **Session Detection**: The `is_alive()` method in shellkeeper.py attempts socket connection to verify session status

2. **Prompt Integration**: 
   - sk-prompt script sets PS1/PROMPT with [sk:name] prefix
   - Must be sourced in shell for prompt updates

3. **Configuration**: JSON config at ~/.shellkeeper/config.json with defaults:
   - default_shell: /bin/bash
   - socket_dir: ~/.shellkeeper/sessions
   - show_status: true
   - status_position: bottom
   - keepalive.enabled: true
   - keepalive.interval: 60

4. **Critical User Warning**: Users must detach with Ctrl+\ not Ctrl+C (which kills the session)

5. **Path Updates**: After reorganization, hardcoded paths were updated:
   - setup-sk-prompt.sh now uses dynamic path resolution
   - README.md updated with new paths
   - Main wrapper script created at /home/bizon/tools/sk for compatibility

6. **Environment Variables**:
   - SHELLKEEPER_SESSION: Current session name
   - SHELLKEEPER_SOCKET: Path to dtach socket
   - SK_KEEPALIVE_ENABLED: Whether to start keepalive
   - SK_KEEPALIVE_INTERVAL: Seconds between keepalive signals