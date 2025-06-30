# Shell Keeper - Design Document

## Problem Statement
Existing terminal multiplexers (screen, tmux, byobu) have limitations:
- **screen/tmux**: No native scrolling support - requires entering copy mode
- **byobu**: Has scrolling but complex session management

## Solution: Shell Keeper

### Core Features
1. **Native Terminal Scrolling**: Pass through scroll events to the terminal emulator
2. **Simple Session Management**: Easy commands to create/switch sessions
3. **Persistent Sessions**: Survive SSH disconnections
4. **Minimal Overhead**: Lightweight and fast

### Technical Approach

#### 1. Terminal Pass-through Mode
- Use alternate screen buffer only when needed
- Keep main buffer for scrollback
- Intercept minimal key combinations

#### 2. Architecture Options

**Option A: Wrapper around existing tools**
- Build on top of tmux/screen but handle scrolling differently
- Pros: Reuse battle-tested session management
- Cons: May inherit limitations

**Option B: New implementation using PTY**
- Direct pseudo-terminal handling
- Full control over input/output
- Can implement exactly what we need

**Option C: Hybrid - Use `dtach` + custom UI**
- `dtach` for session persistence (simpler than screen/tmux)
- Custom wrapper for scrolling and session management
- Best of both worlds

### Recommended Approach: Option C

Using `dtach` as the backend provides:
- Minimal, focused tool for session persistence
- No terminal emulation overhead
- Native scrolling works by default

We'll build a wrapper that adds:
- Session listing and switching
- Status bar (optional)
- Configuration management