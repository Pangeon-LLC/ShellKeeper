# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ShellKeeper is a lightweight terminal session manager using `dtach` as a backend. It provides persistent sessions like screen/tmux but preserves native terminal scrolling. Features GNOME Terminal profile integration for macOS-style session restoration.

## Project Structure

```
bin/
├── sk                  # Main CLI wrapper (bash)
├── shellkeeper.py      # Core Python implementation
├── sk-init.sh          # Session initialization (prompt + keepalive)
├── sk-prompt           # Manual prompt update script
├── sk-info             # Check if in session (legacy, use `sk info`)
├── sk-reconnect        # Interactive reconnection tool
├── sk-autostart        # GNOME autostart session check
├── sk-session-restore  # Interactive session restore picker
├── sk-keepalive        # Background keepalive daemon
└── sk-keepalive-stop   # Stop keepalive daemon

lib/
├── shellkeeper-aliases.sh  # Shell aliases (sn, sl, skt, etc.)
└── setup-sk-prompt.sh      # One-time .bashrc/.zshrc setup

tests/
└── test-zsh-prompt.sh      # Test zsh prompt behavior
```

## Development Commands

```bash
# Run directly (no build needed)
python3 bin/shellkeeper.py [command]
./bin/sk [command]

# Test profile discovery
./bin/sk profiles list
./bin/sk profiles default

# Debug sessions
SK_DEBUG=1 ./bin/sk ls
```

## Architecture

### Core Classes (shellkeeper.py)

**SessionMetadata**: Manages `~/.shellkeeper/metadata.json`
- Tracks profile_name, profile_uuid, created, last_attached per session
- `set()`, `get()`, `remove()`, `clean()`, `list_all()`

**GnomeProfiles**: GNOME Terminal profile discovery via gsettings
- `list_profiles()`: Returns list of {uuid, name}
- `get_default_profile()`: Returns default profile
- `find_profile_by_name()`: Case-insensitive lookup
- `is_available()`: Checks if GNOME Terminal is present

**ShellKeeper**: Main session manager
- `detect_backend()`: Checks for dtach
- `check_linger()`: Warns if `loginctl enable-linger` needed
- `generate_session_name()`: Creates `{profile}-{date}-{time}-{random}` names
- `create_session()`: Handles --profile and --match flags
- `restore_session()`: Opens gnome-terminal with `--profile=UUID`
- `open_terminal()`: `sk terminal` implementation

### Session Flow

1. `sk new [name] [--profile=X] [--match]`
   - Resolves profile (by name, UUID, or from current session)
   - Generates session name with profile slug if auto-naming
   - Saves metadata to `~/.shellkeeper/metadata.json`
   - Creates temp wrapper script with env vars
   - Runs `dtach -c` with socket in `~/.shellkeeper/sessions/`

2. `sk [name]` or `sk attach [name]`
   - Runs `dtach -a` to attach
   - Updates last_attached in metadata

3. `sk restore [name]` / `sk restore-all`
   - Looks up profile_uuid from metadata
   - Launches `gnome-terminal --profile=UUID -- sk attach <name>`

4. `sk terminal [--profile=X] [--match]`
   - Pre-creates metadata with profile
   - Launches `gnome-terminal --profile=UUID -- sk new <name>`

### Data Files

- `~/.shellkeeper/sessions/*.sock` - Session sockets
- `~/.shellkeeper/metadata.json` - Session metadata (profiles, timestamps)
- `~/.shellkeeper/config.json` - User configuration
- `/tmp/sk-keepalive-{session}.pid` - Keepalive daemon PID files

### Environment Variables (set within sessions)

- `SHELLKEEPER_SESSION`: Session name
- `SHELLKEEPER_SOCKET`: Path to socket
- `SK_KEEPALIVE_ENABLED`: "true"/"false"
- `SK_KEEPALIVE_INTERVAL`: Seconds between keepalive signals
- `SK_PROFILE_NAME`: GNOME Terminal profile name
- `SK_PROFILE_UUID`: GNOME Terminal profile UUID

### Configuration (`~/.shellkeeper/config.json`)

```json
{
  "default_shell": "/bin/zsh",
  "keepalive": { "enabled": true, "interval": 60 },
  "default_profile": "My Profile",
  "default_profile_uuid": "uuid-here",
  "session_name_format": "{profile}-{date}-{time}-{random}"
}
```

## Key Commands

```bash
# Profile-aware session creation
sk new --profile="Forest Canopy"
sk new --match                    # Inherit current session's profile

# Profile discovery
sk profiles list
sk profiles default

# Open new terminal with session
sk terminal
sk terminal --profile="Dark"
sk terminal --match

# Restore sessions with profiles
sk restore myproject              # Single session
sk restore-all                    # All sessions

# Session info
sk info [name]
sk metadata list

# Setup autostart
sk setup-autostart
```

## System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install dtach

# Critical for session survival on Linux
loginctl enable-linger $USER
```

## Implementation Notes

1. **Backend**: Uses dtach exclusively, configured with `-e "^\\"` for Ctrl+\ detach
2. **Profile resolution**: Accepts name or UUID, case-insensitive name lookup
3. **Session naming**: `slugify()` converts "Forest Canopy" → "forest-canopy"
4. **Liveness check**: `is_session_alive()` probes socket with non-blocking connect
5. **Autostart**: Creates `~/.config/autostart/shellkeeper.desktop` pointing to `sk-autostart`
