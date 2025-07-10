# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShellKeeper is a lightweight terminal session manager that provides the persistence of GNU Screen or tmux, but with native terminal scrolling. It uses `dtach` as a backend with a Python wrapper for easy session management.

## Key Features

- Native terminal scrolling (no copy mode needed)
- Persistent sessions that survive disconnections
- Automatic keepalive to prevent SSH timeouts
- Simple, intuitive commands
- Minimal resource usage

## Development Guidelines

### Code Style
- Python code follows PEP 8 conventions
- Shell scripts use bash and are POSIX-compliant where possible
- All scripts should include appropriate error handling
- Comments should explain "why" not "what"

### Testing
- Test scripts are located in the `tests/` directory
- Run `./tests/test-zsh-prompt.sh` to test Zsh prompt functionality
- Manual testing is done by creating, attaching, detaching, and killing sessions

### Dependencies
- Core dependency: `dtach` (must be installed)
- Python 3.x (standard library only, no external packages)
- Bash shell for wrapper scripts

### Important Notes
- Users must detach with `Ctrl+\` not `Ctrl+C` (which kills the session)
- Session sockets are stored in `~/.shellkeeper/sessions/`
- Configuration is stored in `~/.shellkeeper/config.json`
- The keepalive daemon prevents SSH timeouts by sending invisible signals

## Common Tasks

### Running ShellKeeper
```bash
# Direct Python execution
python3 bin/shellkeeper.py [command]

# Using the wrapper
./bin/sk [command]
```

### Debugging
```bash
# Check session status
./bin/sk-debug.sh

# List all sessions
./bin/sk ls

# Check if dtach is installed
which dtach
```

## Architecture

See `docs/CLAUDE.md` for detailed architecture information and `docs/shell-keeper-design.md` for design decisions.