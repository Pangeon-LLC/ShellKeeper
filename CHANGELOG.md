# Changelog

## v2.3.0 (2026-01-21)

### New Features

- **Health Check**: `sk doctor` verifies system configuration
  - Checks dtach, jq, loginctl linger, autostart, GNOME profiles
  - Shows fix commands for any issues found

- **Session Logging**: Capture session output to files
  - `sk log <session>` - Log to ~/.shellkeeper/logs/
  - `sk log <session> --output=file.log` - Log to specific file

- **Interactive Dashboard**: TUI for session management
  - `sk dashboard` - Live view of all sessions
  - Navigate, attach, kill sessions with keyboard

- **Session Hooks**: Run scripts on session events
  - Configure `on_create`, `on_attach`, `on_detach` in config.json
  - Scripts receive `SK_SESSION` and `SK_HOOK` environment variables

- **Session Templates**: Predefined session configurations
  - `sk new --template=dev` - Create from template
  - Templates can specify profile, startup command, working directory

- **Profile Export**: Backup GNOME Terminal profiles
  - `sk profiles export` - Export all profiles to JSON

---

## v2.2.0 (2026-01-21)

### New Features

- **Session Notes**: Add notes to sessions for context
  - `sk note <session> "working on auth"` - Add a note
  - `sk note <session>` - Clear the note
  - Notes are displayed in `sk ls` output

- **Bulk Kill**: Kill multiple sessions at once
  - `sk kill --all` - Kill all sessions
  - `sk kill --pattern="test-*"` - Kill sessions matching a glob pattern

- **Idle Cleanup**: Automatically remove old sessions
  - `sk cleanup <days>` - Remove sessions idle for more than N days

- **Relative Time**: `sk ls` now shows relative time ("2h ago") instead of timestamps

- **Shell Completion**: Tab completion for bash and zsh
  - Bash: `source lib/sk-completion.bash`
  - Zsh: `source lib/sk-completion.zsh`

---

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
