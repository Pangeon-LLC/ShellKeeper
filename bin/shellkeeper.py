#!/usr/bin/env python3
"""
ShellKeeper - A terminal session manager with native scrolling support
Built on top of dtach for minimal overhead and maximum compatibility
"""

import os
import sys
import subprocess
import argparse
import tempfile
from pathlib import Path
import signal
import tty
import termios
import select
import fcntl
import struct
import json
from datetime import datetime

class ShellKeeper:
    def __init__(self):
        self.session_dir = Path.home() / ".shellkeeper" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = Path.home() / ".shellkeeper" / "config.json"
        self.load_config()
        self.check_dependencies()
    
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        try:
            subprocess.run(["which", "dtach"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("ERROR: dtach is not installed!")
            print("\nInstall dtach using:")
            print("  Ubuntu/Debian: sudo apt-get install dtach")
            print("  Fedora/RHEL:  sudo dnf install dtach")
            print("  macOS:        brew install dtach")
            print("  From source:  https://github.com/crigler/dtach")
            sys.exit(1)
    
    def load_config(self):
        """Load or create default configuration"""
        default_config = {
            "default_shell": os.environ.get("SHELL", "/bin/bash"),
            "socket_dir": str(self.session_dir),
            "show_status": True,
            "status_position": "bottom",
            "keepalive": {
                "enabled": True,
                "interval": 60  # seconds
            }
        }
        
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_socket_path(self, session_name):
        """Get the socket path for a session"""
        return self.session_dir / f"{session_name}.sock"
    
    def list_sessions(self):
        """List all active sessions"""
        sessions = []
        for sock_file in self.session_dir.glob("*.sock"):
            # Check if socket exists and is a valid socket file
            if sock_file.exists():
                try:
                    # Check if it's a socket using stat
                    import stat
                    file_stat = sock_file.stat()
                    if stat.S_ISSOCK(file_stat.st_mode):
                        # Try to probe if session is actually alive
                        # by attempting a non-blocking connection
                        import socket
                        test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        test_sock.setblocking(False)
                        try:
                            test_sock.connect(str(sock_file))
                            # Connection succeeded, session is alive
                            test_sock.close()
                            
                            session_name = sock_file.stem
                            mtime = datetime.fromtimestamp(file_stat.st_mtime)
                            sessions.append({
                                "name": session_name,
                                "socket": str(sock_file),
                                "last_active": mtime.strftime("%Y-%m-%d %H:%M:%S")
                            })
                        except (socket.error, OSError) as e:
                            # Can't connect - session is dead
                            test_sock.close()
                            print(f"Removing dead session socket: {sock_file.name}")
                            sock_file.unlink(missing_ok=True)
                    else:
                        # Not a socket file, might be stale
                        sock_file.unlink(missing_ok=True)
                except (OSError, IOError) as e:
                    # Can't stat the file, might be dead
                    print(f"Error checking session {sock_file.name}: {e}")
        
        return sorted(sessions, key=lambda x: x["last_active"], reverse=True)
    
    def create_session(self, session_name=None):
        """Create a new session"""
        if not session_name:
            # Generate session name based on timestamp
            session_name = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        socket_path = self.get_socket_path(session_name)
        
        if socket_path.exists():
            print(f"Session '{session_name}' already exists")
            return False
        
        # Set environment variables for the session
        env = os.environ.copy()
        env['SHELLKEEPER_SESSION'] = session_name
        env['SHELLKEEPER_SOCKET'] = str(socket_path)
        
        # Add keepalive configuration
        keepalive_config = self.config.get('keepalive', {})
        env['SK_KEEPALIVE_ENABLED'] = str(keepalive_config.get('enabled', True)).lower()
        env['SK_KEEPALIVE_INTERVAL'] = str(keepalive_config.get('interval', 60))
        
        # Get the sk-init.sh path
        sk_init_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sk-init.sh")
        
        # Determine shell type
        shell_name = os.path.basename(self.config["default_shell"])
        
        # Create wrapper script based on shell type
        if shell_name == "bash":
            wrapper_script = f"""#!/bin/bash
export SHELLKEEPER_SESSION="{session_name}"
export SHELLKEEPER_SOCKET="{socket_path}"
export SK_KEEPALIVE_ENABLED="{env['SK_KEEPALIVE_ENABLED']}"
export SK_KEEPALIVE_INTERVAL="{env['SK_KEEPALIVE_INTERVAL']}"

# Run bash - the prompt will be set by .bashrc if user ran setup-sk-prompt.sh
exec {self.config["default_shell"]}
"""
        elif shell_name == "zsh":
            # Simple wrapper that sets environment and runs zsh
            wrapper_script = f"""#!/bin/bash
export SHELLKEEPER_SESSION="{session_name}"
export SHELLKEEPER_SOCKET="{socket_path}"
export SK_KEEPALIVE_ENABLED="{env['SK_KEEPALIVE_ENABLED']}"
export SK_KEEPALIVE_INTERVAL="{env['SK_KEEPALIVE_INTERVAL']}"

# Run zsh - the prompt will be set by .zshrc if user ran setup-sk-prompt.sh
exec {self.config["default_shell"]}
"""
        else:
            # Generic shell wrapper
            wrapper_script = f"""#!/bin/bash
export SHELLKEEPER_SESSION="{session_name}"
export SHELLKEEPER_SOCKET="{socket_path}"
export SK_KEEPALIVE_ENABLED="{env['SK_KEEPALIVE_ENABLED']}"
export SK_KEEPALIVE_INTERVAL="{env['SK_KEEPALIVE_INTERVAL']}"

# Try to set prompt for unknown shell
exec {self.config["default_shell"]} -c '
export SHELLKEEPER_SESSION="{session_name}"
export SHELLKEEPER_SOCKET="{socket_path}"
export SK_KEEPALIVE_ENABLED="{env['SK_KEEPALIVE_ENABLED']}"
export SK_KEEPALIVE_INTERVAL="{env['SK_KEEPALIVE_INTERVAL']}"
export PS1="[sk:{session_name}] ${{PS1:-$ }}"
exec {self.config["default_shell"]}
'
"""
        
        # Create temporary wrapper script
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(wrapper_script)
            wrapper_path = f.name
        
        os.chmod(wrapper_path, 0o755)
        
        # Create new dtach session with wrapper
        cmd = [
            "dtach", "-c", str(socket_path),
            "-e", "^\\",  # Escape character: Ctrl+\
            "-r", "winch",  # Redraw on window change
            wrapper_path
        ]
        
        print(f"Creating session: {session_name}")
        print(f"*** DETACH WITH Ctrl+\\ (NOT Ctrl+C) ***")
        
        try:
            # Run dtach
            subprocess.run(cmd, env=env)
        finally:
            # Clean up wrapper script
            try:
                os.unlink(wrapper_path)
                # Clean up any temp rc files (they have PID in name so glob them)
                import glob
                for pattern in [f"/tmp/sk_bashrc_{session_name}_*", 
                               f"/tmp/sk_zshrc_{session_name}_*",
                               f"/tmp/sk_zshenv_{session_name}_*",
                               f"/tmp/sk_init_{session_name}_*"]:
                    for temp_file in glob.glob(pattern):
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
            except:
                pass
        
        return True
    
    def attach_session(self, session_name):
        """Attach to an existing session"""
        socket_path = self.get_socket_path(session_name)
        
        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False
        
        # Set environment variables for the session
        env = os.environ.copy()
        env['SHELLKEEPER_SESSION'] = session_name
        env['SHELLKEEPER_SOCKET'] = str(socket_path)
        
        # Attach to dtach session
        cmd = [
            "dtach", "-a", str(socket_path),
            "-e", "^\\",  # Escape character: Ctrl+\
            "-r", "winch"  # Redraw on window change
        ]
        
        print(f"Attaching to session: {session_name}")
        print(f"*** DETACH WITH Ctrl+\\ (NOT Ctrl+C) ***")
        
        # Run dtach
        subprocess.run(cmd, env=env)
        return True
    
    def kill_session(self, session_name):
        """Kill a session"""
        socket_path = self.get_socket_path(session_name)
        
        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False
        
        # Remove socket file (this effectively kills the session)
        socket_path.unlink()
        print(f"Session '{session_name}' killed")
        return True
    
    def rename_session(self, old_name, new_name):
        """Rename a session"""
        old_socket = self.get_socket_path(old_name)
        new_socket = self.get_socket_path(new_name)
        
        if not old_socket.exists():
            print(f"Session '{old_name}' not found")
            return False
        
        if new_socket.exists():
            print(f"Session '{new_name}' already exists")
            return False
        
        old_socket.rename(new_socket)
        print(f"Session renamed: {old_name} -> {new_name}")
        return True

def main():
    parser = argparse.ArgumentParser(
        description="ShellKeeper - Terminal session manager with native scrolling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sk new              Create new auto-named session
  sk new project      Create session named 'project'
  sk ls               List all sessions
  sk project          Attach to session 'project'
  sk kill project     Kill session 'project'
  sk clean            Clean up dead session sockets
  
Inside a session:
  Ctrl+\\              Detach from session (keeps it running)
  Ctrl+C              KILLS the session - use Ctrl+\\ instead!
  exit                Terminate session completely
  
Check if in session:
  echo $SHELLKEEPER_SESSION
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List sessions
    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List sessions")
    
    # Create session
    create_parser = subparsers.add_parser("new", aliases=["create"], help="Create new session")
    create_parser.add_argument("name", nargs="?", help="Session name (auto-generated if not provided)")
    
    # Attach to session
    attach_parser = subparsers.add_parser("attach", aliases=["a"], help="Attach to session")
    attach_parser.add_argument("name", help="Session name")
    
    # Kill session
    kill_parser = subparsers.add_parser("kill", help="Kill session")
    kill_parser.add_argument("name", help="Session name")
    
    # Rename session
    rename_parser = subparsers.add_parser("rename", help="Rename session")
    rename_parser.add_argument("old_name", help="Current session name")
    rename_parser.add_argument("new_name", help="New session name")
    
    # Clean dead sessions
    clean_parser = subparsers.add_parser("clean", help="Clean up dead session sockets")
    
    # Attach to last/most recent session
    last_parser = subparsers.add_parser("last", help="Attach to most recent session")
    
    args = parser.parse_args()
    
    sk = ShellKeeper()
    
    if args.command in ["list", "ls"]:
        sessions = sk.list_sessions()
        if not sessions:
            print("No active sessions")
            # Debug info if no sessions found
            if os.environ.get("SK_DEBUG"):
                print(f"\nDebug: Looking in {sk.session_dir}")
                print(f"Files found: {list(sk.session_dir.glob('*'))}")
        else:
            print("Active sessions:")
            for session in sessions:
                print(f"  {session['name']:<20} (last active: {session['last_active']})")
    
    elif args.command in ["new", "create"]:
        sk.create_session(args.name)
    
    elif args.command in ["attach", "a"]:
        sk.attach_session(args.name)
    
    elif args.command == "kill":
        sk.kill_session(args.name)
    
    elif args.command == "rename":
        sk.rename_session(args.old_name, args.new_name)
    
    elif args.command == "clean":
        print("Cleaning up dead sessions...")
        # Force a list which will clean dead sockets
        sk.list_sessions()
        print("Done.")
    
    elif args.command == "last":
        sessions = sk.list_sessions()
        if sessions:
            print(f"Attaching to most recent session: {sessions[0]['name']}")
            sk.attach_session(sessions[0]['name'])
        else:
            print("No active sessions found")
    
    else:
        # If no command, show usage or attach to last session
        sessions = sk.list_sessions()
        if sessions and len(sys.argv) == 1:
            # Auto-attach to most recent session
            print(f"No command specified. Attaching to most recent session: {sessions[0]['name']}")
            sk.attach_session(sessions[0]['name'])
        else:
            parser.print_help()

if __name__ == "__main__":
    main()