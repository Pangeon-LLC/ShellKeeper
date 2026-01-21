# Changelog

## v2.1.0 (2026-01-21)

### New Features

- **Metadata Export/Import**: Backup and restore session-to-profile mappings
  - `sk metadata export > backup.json`
  - `sk metadata import < backup.json` (use `--force` to overwrite)

- **Configuration Command**: View and modify settings
  - `sk config show` - Display current configuration
  - `sk config set-default-profile <name>` - Set default terminal profile

- **Man Page**: Full documentation available via `man sk`

- **Improved Installer**: Colorful output with progress indicators

### Changes

- INSTALL.sh now uses symlinks to `~/.local/bin` (no .zshrc modifications needed)
- Cleaner installer output with Unicode symbols and colors

---

## v2.0.0 (2026-01-21)

### New Features

- **GNOME Terminal Profile Integration**: Sessions remember their terminal profile
  - `sk new --profile="Profile Name"` - Create session with specific profile
  - `sk new --match` - Inherit current terminal's profile

- **Session Restoration**: Restore sessions in their original terminal profiles
  - `sk restore [name]` - Restore single session in new terminal window
  - `sk restore-all` - Restore all sessions after crash/reboot

- **Profile Management**:
  - `sk profiles list` - List available GNOME Terminal profiles
  - `sk profiles default` - Show default profile

- **Session Metadata**: Track profile, creation time for each session
  - `sk metadata list` - View all session metadata
  - `sk metadata clean` - Remove orphaned metadata

- **Session Info**: `sk info [name]` - Detailed session information

- **Terminal Command**: `sk terminal [--profile=NAME] [--match]` - Open new terminal with session

- **Autostart**: `sk setup-autostart` - Configure login session restoration

- **Profile-Aware Naming**: Auto-generated names include profile (e.g., `forest-canopy-20260121-153102-a7f2`)

### Environment Variables

Sessions now set:
- `SHELLKEEPER_SESSION` - Session name
- `SHELLKEEPER_SOCKET` - Socket path
- `SK_PROFILE_NAME` - GNOME Terminal profile name
- `SK_PROFILE_UUID` - GNOME Terminal profile UUID

### Files

- `~/.shellkeeper/config.json` - User configuration
- `~/.shellkeeper/metadata.json` - Session metadata
- `~/.shellkeeper/sessions/` - Session sockets

---

## v1.0.0 (2026-01-21)

Initial release.

### Features

- Lightweight terminal session manager using dtach
- Native terminal scrolling (unlike screen/tmux)
- Sessions persist across disconnections
- Basic commands: `new`, `attach`, `ls`, `kill`, `clean`, `rename`
- Detach with `Ctrl+\`

### Prerequisites

- `dtach` package
- `loginctl enable-linger $USER` for session survival on logout
