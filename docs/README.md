# ShellKeeper

A lightweight terminal session manager that solves the scrolling problem of traditional terminal multiplexers.

## Why ShellKeeper?

- **Native scrolling** - Unlike screen/tmux, your terminal's scroll functionality works normally
- **Simple session management** - Easy commands to create and switch between sessions
- **Minimal overhead** - Built on `dtach`, not a full terminal emulator
- **Persistent sessions** - Survive SSH disconnections and network issues

## Installation

1. Install `dtach` (required dependency):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install dtach
   
   # macOS
   brew install dtach
   
   # Fedora/RHEL
   sudo dnf install dtach
   ```

2. Add ShellKeeper to your PATH:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export PATH="$PATH:/home/bizon/tools/shellkeeper/bin"
   ```

3. Enable automatic prompt display:
   ```bash
   # Run this once to set up automatic prompts
   /home/bizon/tools/shellkeeper/lib/setup-sk-prompt.sh
   ```

4. (Optional) Add convenient aliases:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   source /home/bizon/tools/shellkeeper/lib/shellkeeper-aliases.sh
   ```

## Quick Start

```bash
# Create a new session (auto-named)
sk new

# Create a named session
sk new myproject

# List sessions
sk ls

# Attach to a session
sk myproject
# or
sk attach myproject

# IMPORTANT: Detach from current session
# Press Ctrl+\  (Control + Backslash)
# NOT Ctrl+C (that kills the session!)

# Kill a session
sk kill myproject

# Rename a session
sk rename oldname newname

# Clean up dead session sockets
sk clean
```

## Usage Patterns

### Quick session access
```bash
# Just type 'sk' to attach to most recent session
sk

# Or 'sk' + session name
sk frontend
sk backend
sk logs
```

### Persistent SSH sessions
```bash
# SSH to server
ssh myserver

# Start ShellKeeper session
sk new work

# Do your work...
# If connection drops, just reconnect and:
sk work  # You're back where you left off!
```

### Reconnecting after disconnection
```bash
# Quick reconnect to most recent session
sk           # Just type 'sk' with no arguments
# or
sk last      # Explicitly attach to last session
# or
skl          # Alias for 'sk last'

# Interactive reconnect (shows all sessions)
sk-reconnect
# or
skr          # Alias for sk-reconnect

# Auto-detect sessions on SSH login
# Add to your .bashrc/.zshrc:
source /home/bizon/tools/shellkeeper/lib/shellkeeper-aliases.sh
sk_auto      # Shows sessions if you're in SSH
```

## How It Works

ShellKeeper uses `dtach` as its backend, which provides:
- Session persistence without terminal emulation
- Minimal overhead (just process management)
- Native terminal features (including scrolling!)

The Python wrapper adds:
- Easy session management
- Automatic session discovery
- Simple command interface

## Advantages over alternatives

| Feature | screen/tmux | byobu | ShellKeeper |
|---------|-------------|-------|-------------|
| Native scrolling | ❌ | ✅ | ✅ |
| Simple commands | ❌ | ❌ | ✅ |
| Lightweight | ❌ | ❌ | ✅ |
| Persistent sessions | ✅ | ✅ | ✅ |

## Configuration

Configuration file: `~/.shellkeeper/config.json`

```json
{
  "default_shell": "/bin/bash",
  "socket_dir": "~/.shellkeeper/sessions",
  "show_status": true,
  "status_position": "bottom",
  "keepalive": {
    "enabled": true,
    "interval": 60
  }
}
```

### Keepalive Feature

ShellKeeper includes an automatic keepalive feature to prevent disconnection due to inactivity:

- **Enabled by default** - Sends silent signals every 60 seconds
- **Completely invisible** - No output or interference with your work
- **Automatic** - Starts with each new session

To disable keepalive:
```bash
# Edit ~/.shellkeeper/config.json and set:
"keepalive": {
  "enabled": false
}

# Or temporarily for one session:
SK_KEEPALIVE_ENABLED=false sk new mywork
```

To adjust the interval (default 60 seconds):
```json
"keepalive": {
  "enabled": true,
  "interval": 120  // 2 minutes
}
```

Manual keepalive control:
```bash
# Stop keepalive in current session
sk-keepalive-stop

# Manually start keepalive
sk-keepalive
```

## Tips

1. **Session naming**: Use descriptive names like `project-frontend`, `logs-prod`, etc.
2. **Detach safely**: Always use Ctrl+\ to detach (not Ctrl+C)
3. **Check sessions**: Run `sk ls` periodically to see active sessions
4. **Update prompt**: If prompt doesn't show `[sk:name]`, run `source sk-prompt` or `skp` alias

## Troubleshooting

**"Session not found" error**
- The session may have ended. Check with `sk ls`

**Can't create new session**
- Ensure `dtach` is installed: `which dtach`
- Check permissions on `~/.shellkeeper/`

**Scrolling still doesn't work**
- Make sure you're not inside another multiplexer (screen/tmux)
- Check your terminal emulator supports scrollback

**Stuck in a session / Ctrl+C doesn't work**
- Use `Ctrl+\` to detach (NOT Ctrl+C)
- Ctrl+C kills the session instead of detaching
- If you see dead sessions in `sk ls`, run `sk clean`

**Dead sessions showing up**
- Run `sk clean` to remove dead socket files
- This happens when sessions are killed with Ctrl+C instead of detached