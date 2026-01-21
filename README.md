# ShellKeeper 🐚

A lightweight terminal session manager that gives you the persistence of GNU Screen or tmux, but with your terminal's native scrolling. Finally, you can have persistent sessions without giving up your scrollback buffer!

## The Problem

Traditional terminal multiplexers like GNU Screen and tmux are powerful, but they come with a significant limitation: they break your terminal's native scrolling. Instead of using your mouse wheel or trackpad naturally, you're forced to enter "copy mode" with arcane key combinations. This makes reviewing command output unnecessarily cumbersome.

## The Solution

ShellKeeper leverages `dtach` - a minimal program that only does session management without terminal emulation. This means:

- ✅ **Native terminal scrolling works perfectly** - Use your mouse wheel, trackpad, or scrollbar just like normal
- ✅ **Persistent sessions** - Survive SSH disconnections, network issues, or accidental terminal closures  
- ✅ **Minimal overhead** - No terminal emulation layer eating resources
- ✅ **Simple commands** - Intuitive interface without the complexity of tmux/screen
- ✅ **Automatic keepalive** - Prevents SSH timeouts with invisible background signals

## Quick Start

```bash
# Create a session
sk new myproject

# List sessions
sk ls

# Attach to a session
sk myproject

# Detach from current session
# Press Ctrl+\ (NOT Ctrl+C which kills the session)

# Quick reconnect after disconnect
sk          # Attaches to most recent
sk last     # Explicitly attach to last session
```

## Installation

### Prerequisites

ShellKeeper requires `dtach` (the minimal session backend):

```bash
# Ubuntu/Debian
sudo apt-get install dtach

# macOS
brew install dtach

# Fedora/RHEL
sudo dnf install dtach

# From source
git clone https://github.com/crigler/dtach
cd dtach && ./configure && make && sudo make install
```

### Critical: Enable Lingering Sessions (Linux)

On systemd-based Linux systems, sessions are killed when you log out unless you enable "lingering":

```bash
# Run this once - required for sessions to survive logout/crash
loginctl enable-linger $USER

# Verify it's enabled
loginctl show-user $USER | grep Linger
# Should show: Linger=yes
```

**Without this, all your ShellKeeper sessions will be terminated when you log out or if your desktop session crashes.**

### Install ShellKeeper

1. Clone the repository:
```bash
git clone https://github.com/Pangeon-LLC/ShellKeeper.git
cd ShellKeeper
```

2. Add to your PATH:
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:$(pwd)/bin"
```

3. Set up the enhanced prompt (optional but recommended):
```bash
# This adds [sk:sessionname] to your prompt
./lib/setup-sk-prompt.sh
```

4. Load convenient aliases (optional):
```bash
# Add to ~/.bashrc or ~/.zshrc  
source $(pwd)/lib/shellkeeper-aliases.sh
```

5. Reload your shell:
```bash
exec $SHELL
```

## Usage

### Basic Commands

```bash
sk new [name]           # Create new session (auto-named if no name given)
sk ls                   # List all sessions
sk [name]               # Attach to named session
sk                      # Attach to most recent session
sk kill [name]          # Terminate a session
sk rename [old] [new]   # Rename a session
sk clean                # Remove dead session sockets
```

### GNOME Terminal Profile Support

```bash
sk new --profile="My Profile"   # Create session with specific terminal profile
sk new --match                  # Inherit current session's profile
sk terminal                     # Open new terminal with new session
sk terminal --match             # Open new terminal, inherit profile
sk restore [name]               # Restore session with its original profile
sk restore-all                  # Restore all sessions with correct profiles
sk profiles list                # List available GNOME Terminal profiles
sk profiles default             # Show default profile
```

### Session Information

```bash
sk info [name]          # Show session details (profile, created time, etc.)
sk metadata list        # List all session metadata
```

### Detaching Safely

**IMPORTANT**: Always detach with `Ctrl+\` (Control + Backslash)
- `Ctrl+C` kills the entire session (and all processes in it)
- `Ctrl+\` safely detaches, leaving everything running

### SSH Workflow

Perfect for remote work that survives connection drops:

```bash
# SSH to your server
ssh myserver

# Start a ShellKeeper session
sk new work

# Do your work...
# If connection drops, just reconnect and:
sk work  # You're back exactly where you left off!
```

### Auto-reconnect on SSH

Add to your remote `.bashrc` or `.zshrc`:

```bash
# Auto-show sessions when SSH'ing in
source /path/to/ShellKeeper/lib/shellkeeper-aliases.sh
sk_auto  # Shows available sessions on SSH login
```

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
  },
  "default_profile": "Default",
  "default_profile_uuid": null,
  "session_name_format": "{profile}-{date}-{time}-{random}"
}
```

### Keepalive Feature

ShellKeeper includes automatic keepalive to prevent SSH timeouts:
- Sends invisible signals every 60 seconds (configurable)
- No output or interference with your work
- Disable with: `"enabled": false` in config

## Why ShellKeeper?

### vs GNU Screen/tmux

| Feature | Screen/tmux | ShellKeeper |
|---------|-------------|-------------|
| Native scrolling | ❌ Requires copy mode | ✅ Just works |
| Simple commands | ❌ Complex | ✅ Intuitive |
| Resource usage | Heavy (full terminal emulator) | Minimal (just dtach) |
| Learning curve | Steep | Gentle |
| Persistent sessions | ✅ | ✅ |

### vs No Session Manager

- **Never lose work to disconnections** - Network drops, SSH timeouts, accidental closures - your work persists
- **Context switching** - Jump between different projects/contexts instantly
- **Background processes** - Leave long-running commands without keeping terminal open

## Tips & Tricks

1. **Session Naming**: Use descriptive names like `frontend`, `backend`, `logs`
2. **Project Workflow**: Create a session per project: `sk new myapp-api`, `sk new myapp-frontend`  
3. **Monitoring**: Keep a `logs` session for `tail -f` commands
4. **Aliases**: The shellkeeper-aliases.sh file includes handy shortcuts:
   - `skl` = `sk last` (attach to most recent)
   - `skr` = `sk-reconnect` (interactive session picker)
   - `sks` = `sk ls` (list sessions)

## Troubleshooting

**"Session not found" error**
- The session may have ended. Check with `sk ls`

**Sessions die when I log out**
- Enable lingering: `loginctl enable-linger $USER`
- This is required on systemd-based Linux systems

**Can't create new session**
- Ensure dtach is installed: `which dtach`
- Check permissions on `~/.shellkeeper/`

**Prompt doesn't show [sk:name]**
- Run the setup script: `./lib/setup-sk-prompt.sh`
- Or manually: `source sk-prompt` in your session

**Accidentally killed session with Ctrl+C**
- Unfortunately the session is gone. Remember: always use `Ctrl+\` to detach!
- Run `sk clean` to remove dead socket files

**Profile restoration not working**
- Ensure you're using GNOME Terminal
- Check that the profile still exists: `sk profiles list`

## How It Works

ShellKeeper is a Python wrapper around `dtach` that adds:

1. **Session Management**: Easy create/list/attach/kill operations
2. **Smart Defaults**: Auto-naming with profile slugs, last-session memory, session discovery
3. **Shell Integration**: Prompt modification, environment variables, aliases
4. **Profile Support**: GNOME Terminal profile tracking and profile-aware restoration
5. **Metadata Storage**: Tracks profile, creation time, and other session info
6. **Keepalive**: Background process preventing timeouts
7. **Safety Features**: Socket cleanup, session verification, dependency checking

The magic is that abduco/dtach only handles process attachment/detachment - it doesn't touch your terminal emulation. Your terminal still renders everything, so scrolling, copy/paste, and all other native features work normally.

## Contributing

We welcome contributions! Feel free to:

- Report bugs or request features via [Issues](https://github.com/Pangeon-LLC/ShellKeeper/issues)
- Submit pull requests
- Share your use cases and feedback

## License

ShellKeeper is released under the MIT License. See [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on [dtach](https://github.com/crigler/dtach) by Ned T. Crigler
- Inspired by the persistent session features of GNU Screen and tmux
- Created for developers who love their terminal's native scrolling

---

Made with ❤️ for developers who want persistent sessions without sacrificing usability.