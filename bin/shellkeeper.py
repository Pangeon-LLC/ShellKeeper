#!/usr/bin/env python3
"""
ShellKeeper - A terminal session manager with native scrolling support
Built on top of abduco/dtach for minimal overhead and maximum compatibility

Features:
- Session persistence with native terminal scrolling
- GNOME Terminal profile integration
- Session metadata tracking
- Profile-aware session restoration
"""

import os
import sys
import subprocess
import argparse
import json
import random
import string
import re
from pathlib import Path
from datetime import datetime


class SessionMetadata:
    """Manages session metadata storage"""

    def __init__(self, metadata_file):
        self.metadata_file = Path(metadata_file)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        """Load metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        """Save metadata to file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def set(self, session_name, profile_name=None, profile_uuid=None):
        """Set or update metadata for a session"""
        now = datetime.now().isoformat()
        if session_name not in self.data:
            self.data[session_name] = {
                "created": now,
            }
        self.data[session_name]["last_attached"] = now
        if profile_name is not None:
            self.data[session_name]["profile_name"] = profile_name
        if profile_uuid is not None:
            self.data[session_name]["profile_uuid"] = profile_uuid
        self._save()

    def get(self, session_name):
        """Get metadata for a session"""
        return self.data.get(session_name, {})

    def remove(self, session_name):
        """Remove metadata for a session"""
        if session_name in self.data:
            del self.data[session_name]
            self._save()

    def list_all(self):
        """List all session metadata"""
        return self.data

    def clean(self, active_sessions):
        """Remove metadata for sessions that no longer exist"""
        active_set = set(active_sessions)
        to_remove = [name for name in self.data if name not in active_set]
        for name in to_remove:
            del self.data[name]
        if to_remove:
            self._save()
        return to_remove


class GnomeProfiles:
    """Manages GNOME Terminal profile discovery"""

    DCONF_PATH = "/org/gnome/terminal/legacy/profiles:/"

    @classmethod
    def is_available(cls):
        """Check if GNOME Terminal profiles are available"""
        try:
            subprocess.run(
                ["gsettings", "get", "org.gnome.Terminal.ProfilesList", "list"],
                capture_output=True, check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @classmethod
    def list_profiles(cls):
        """List all GNOME Terminal profiles"""
        profiles = []
        try:
            # Get list of profile UUIDs
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.Terminal.ProfilesList", "list"],
                capture_output=True, text=True, check=True
            )
            # Parse the output: ['uuid1', 'uuid2', ...]
            uuid_str = result.stdout.strip()
            if uuid_str.startswith('[') and uuid_str.endswith(']'):
                # Remove brackets and quotes, split by comma
                uuid_list = uuid_str[1:-1].replace("'", "").replace(" ", "").split(",")
                uuid_list = [u for u in uuid_list if u]  # Remove empty strings

                for uuid in uuid_list:
                    name = cls.get_profile_name(uuid)
                    profiles.append({
                        "uuid": uuid,
                        "name": name or uuid
                    })
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return profiles

    @classmethod
    def get_profile_name(cls, uuid):
        """Get the visible name of a profile by UUID"""
        try:
            result = subprocess.run(
                ["gsettings", "get",
                 f"org.gnome.Terminal.Legacy.Profile:{cls.DCONF_PATH}:{uuid}/",
                 "visible-name"],
                capture_output=True, text=True, check=True
            )
            # Remove quotes from output
            name = result.stdout.strip().strip("'")
            return name
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    @classmethod
    def get_default_profile(cls):
        """Get the default GNOME Terminal profile"""
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.Terminal.ProfilesList", "default"],
                capture_output=True, text=True, check=True
            )
            uuid = result.stdout.strip().strip("'")
            name = cls.get_profile_name(uuid)
            return {"uuid": uuid, "name": name or uuid}
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    @classmethod
    def find_profile_by_name(cls, name):
        """Find a profile by name (case-insensitive)"""
        profiles = cls.list_profiles()
        name_lower = name.lower()
        for profile in profiles:
            if profile["name"].lower() == name_lower:
                return profile
        return None

    @classmethod
    def find_profile_by_uuid(cls, uuid):
        """Find a profile by UUID"""
        name = cls.get_profile_name(uuid)
        if name:
            return {"uuid": uuid, "name": name}
        return None


class ShellKeeper:
    def __init__(self):
        self.session_dir = Path.home() / ".shellkeeper" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = Path.home() / ".shellkeeper" / "config.json"
        self.metadata_file = Path.home() / ".shellkeeper" / "metadata.json"
        self.metadata = SessionMetadata(self.metadata_file)
        self.load_config()
        self.backend = self.detect_backend()

    def detect_backend(self):
        """Check if dtach is available"""
        try:
            subprocess.run(["which", "dtach"], check=True, capture_output=True)
            return "dtach"
        except subprocess.CalledProcessError:
            return None

    def check_dependencies(self):
        """Check if required dependencies are installed"""
        if self.backend is None:
            print("ERROR: dtach is not installed!")
            print("\nInstall it:")
            print("  Ubuntu/Debian: sudo apt-get install dtach")
            print("  Fedora/RHEL:   sudo dnf install dtach")
            print("  macOS:         brew install dtach")
            print("  From source:   https://github.com/crigler/dtach")
            sys.exit(1)

        # Check for lingering on Linux
        self.check_linger()

    def check_linger(self):
        """Check if loginctl linger is enabled (Linux only)"""
        if sys.platform != "linux":
            return

        try:
            result = subprocess.run(
                ["loginctl", "show-user", os.environ.get("USER", ""), "--property=Linger"],
                capture_output=True, text=True
            )
            if "Linger=no" in result.stdout:
                print("WARNING: Sessions may not survive logout!")
                print("Run: loginctl enable-linger $USER")
                print()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # loginctl not available, skip check

    def load_config(self):
        """Load or create default configuration"""
        default_config = {
            "default_shell": os.environ.get("SHELL", "/bin/bash"),
            "socket_dir": str(self.session_dir),
            "show_status": True,
            "status_position": "bottom",
            "keepalive": {
                "enabled": True,
                "interval": 60
            },
            "default_profile": None,
            "default_profile_uuid": None,
            "session_name_format": "{profile}-{date}-{time}-{random}"
        }

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    loaded = json.load(f)
                    # Merge with defaults to add any new keys
                    for key, value in default_config.items():
                        if key not in loaded:
                            loaded[key] = value
                    self.config = loaded
            except (json.JSONDecodeError, IOError):
                self.config = default_config
                self.save_config()
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

    def slugify(self, text):
        """Convert text to a URL-friendly slug"""
        if not text:
            return "default"
        # Convert to lowercase
        text = text.lower()
        # Replace spaces and special chars with hyphens
        text = re.sub(r'[^a-z0-9]+', '-', text)
        # Remove leading/trailing hyphens
        text = text.strip('-')
        # Limit length
        return text[:20] if text else "default"

    def generate_session_name(self, profile_name=None):
        """Generate a session name based on config format"""
        now = datetime.now()
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))

        profile_slug = self.slugify(profile_name) if profile_name else "default"

        fmt = self.config.get("session_name_format", "{profile}-{date}-{time}-{random}")

        name = fmt.format(
            profile=profile_slug,
            date=now.strftime("%Y%m%d"),
            time=now.strftime("%H%M%S"),
            random=random_suffix
        )

        return name

    def is_session_alive(self, socket_path):
        """Check if a session is alive by probing the socket"""
        if not socket_path.exists():
            return False

        try:
            import stat
            import socket as sock_module

            file_stat = socket_path.stat()
            if not stat.S_ISSOCK(file_stat.st_mode):
                return False

            test_sock = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
            test_sock.setblocking(False)
            try:
                test_sock.connect(str(socket_path))
                test_sock.close()
                return True
            except (sock_module.error, OSError):
                test_sock.close()
                return False
        except (OSError, IOError):
            return False

    def list_sessions(self, clean_dead=True):
        """List all active sessions"""
        sessions = []
        dead_sessions = []

        for sock_file in self.session_dir.glob("*.sock"):
            session_name = sock_file.stem

            if self.is_session_alive(sock_file):
                file_stat = sock_file.stat()
                mtime = datetime.fromtimestamp(file_stat.st_mtime)
                meta = self.metadata.get(session_name)

                sessions.append({
                    "name": session_name,
                    "socket": str(sock_file),
                    "last_active": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                    "profile_name": meta.get("profile_name"),
                    "profile_uuid": meta.get("profile_uuid"),
                    "created": meta.get("created")
                })
            else:
                dead_sessions.append(session_name)
                if clean_dead:
                    print(f"Removing dead session socket: {sock_file.name}")
                    sock_file.unlink(missing_ok=True)

        # Clean metadata for dead sessions
        if clean_dead and dead_sessions:
            for name in dead_sessions:
                self.metadata.remove(name)

        return sorted(sessions, key=lambda x: x["last_active"], reverse=True)

    def create_session(self, session_name=None, profile_name=None, profile_uuid=None, match_current=False):
        """Create a new session"""
        # Handle --match flag
        if match_current:
            current_session = os.environ.get("SHELLKEEPER_SESSION")
            if current_session:
                current_meta = self.metadata.get(current_session)
                if current_meta:
                    profile_name = profile_name or current_meta.get("profile_name")
                    profile_uuid = profile_uuid or current_meta.get("profile_uuid")

        # Resolve profile by name if only name provided
        if profile_name and not profile_uuid:
            profile = GnomeProfiles.find_profile_by_name(profile_name)
            if profile:
                profile_uuid = profile["uuid"]
                profile_name = profile["name"]

        # Resolve profile by uuid if only uuid provided
        if profile_uuid and not profile_name:
            profile = GnomeProfiles.find_profile_by_uuid(profile_uuid)
            if profile:
                profile_name = profile["name"]

        # Use default profile from config if none specified
        if not profile_name and not profile_uuid:
            if self.config.get("default_profile_uuid"):
                profile_uuid = self.config["default_profile_uuid"]
                profile = GnomeProfiles.find_profile_by_uuid(profile_uuid)
                if profile:
                    profile_name = profile["name"]
            elif self.config.get("default_profile"):
                profile = GnomeProfiles.find_profile_by_name(self.config["default_profile"])
                if profile:
                    profile_name = profile["name"]
                    profile_uuid = profile["uuid"]

        # Generate session name if not provided
        if not session_name:
            session_name = self.generate_session_name(profile_name)

        socket_path = self.get_socket_path(session_name)

        if socket_path.exists():
            print(f"Session '{session_name}' already exists")
            return False, session_name

        # Save metadata
        self.metadata.set(session_name, profile_name, profile_uuid)

        # Set environment variables for the session
        env = os.environ.copy()
        env['SHELLKEEPER_SESSION'] = session_name
        env['SHELLKEEPER_SOCKET'] = str(socket_path)

        keepalive_config = self.config.get('keepalive', {})
        env['SK_KEEPALIVE_ENABLED'] = str(keepalive_config.get('enabled', True)).lower()
        env['SK_KEEPALIVE_INTERVAL'] = str(keepalive_config.get('interval', 60))

        if profile_name:
            env['SK_PROFILE_NAME'] = profile_name
        if profile_uuid:
            env['SK_PROFILE_UUID'] = profile_uuid

        # Create wrapper script
        shell_name = os.path.basename(self.config["default_shell"])
        wrapper_script = f"""#!/bin/bash
export SHELLKEEPER_SESSION="{session_name}"
export SHELLKEEPER_SOCKET="{socket_path}"
export SK_KEEPALIVE_ENABLED="{env['SK_KEEPALIVE_ENABLED']}"
export SK_KEEPALIVE_INTERVAL="{env['SK_KEEPALIVE_INTERVAL']}"
export SK_PROFILE_NAME="{profile_name or ''}"
export SK_PROFILE_UUID="{profile_uuid or ''}"

exec {self.config["default_shell"]}
"""

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(wrapper_script)
            wrapper_path = f.name

        os.chmod(wrapper_path, 0o755)

        # Build dtach command
        cmd = [
            "dtach", "-c", str(socket_path),
            "-e", "^\\",
            "-r", "winch",
            wrapper_path
        ]

        print(f"Creating session: {session_name}")
        if profile_name:
            print(f"Profile: {profile_name}")
        print(f"*** DETACH WITH Ctrl+\\ (NOT Ctrl+C) ***")

        try:
            subprocess.run(cmd, env=env)
        finally:
            try:
                os.unlink(wrapper_path)
            except:
                pass

        return True, session_name

    def attach_session(self, session_name):
        """Attach to an existing session"""
        socket_path = self.get_socket_path(session_name)

        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False

        if not self.is_session_alive(socket_path):
            print(f"Session '{session_name}' is dead")
            socket_path.unlink(missing_ok=True)
            self.metadata.remove(session_name)
            return False

        # Update last_attached in metadata
        meta = self.metadata.get(session_name)
        self.metadata.set(session_name, meta.get("profile_name"), meta.get("profile_uuid"))

        env = os.environ.copy()
        env['SHELLKEEPER_SESSION'] = session_name
        env['SHELLKEEPER_SOCKET'] = str(socket_path)

        cmd = [
            "dtach", "-a", str(socket_path),
            "-e", "^\\",
            "-r", "winch"
        ]

        print(f"Attaching to session: {session_name}")
        print(f"*** DETACH WITH Ctrl+\\ (NOT Ctrl+C) ***")

        subprocess.run(cmd, env=env)
        return True

    def kill_session(self, session_name):
        """Kill a session"""
        socket_path = self.get_socket_path(session_name)

        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False

        socket_path.unlink()
        self.metadata.remove(session_name)
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

        # Rename socket
        old_socket.rename(new_socket)

        # Update metadata
        old_meta = self.metadata.get(old_name)
        if old_meta:
            self.metadata.remove(old_name)
            self.metadata.set(new_name, old_meta.get("profile_name"), old_meta.get("profile_uuid"))

        print(f"Session renamed: {old_name} -> {new_name}")
        return True

    def get_session_info(self, session_name):
        """Get detailed info about a session"""
        socket_path = self.get_socket_path(session_name)

        if not socket_path.exists():
            return None

        meta = self.metadata.get(session_name)
        alive = self.is_session_alive(socket_path)

        try:
            file_stat = socket_path.stat()
            mtime = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        except:
            mtime = None

        return {
            "name": session_name,
            "socket": str(socket_path),
            "alive": alive,
            "last_modified": mtime,
            "profile_name": meta.get("profile_name"),
            "profile_uuid": meta.get("profile_uuid"),
            "created": meta.get("created"),
            "last_attached": meta.get("last_attached")
        }

    def restore_session(self, session_name):
        """Restore a session in a new terminal with its profile"""
        socket_path = self.get_socket_path(session_name)

        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False

        if not self.is_session_alive(socket_path):
            print(f"Session '{session_name}' is dead")
            return False

        meta = self.metadata.get(session_name)
        profile_uuid = meta.get("profile_uuid")

        # Get the sk script path
        sk_path = Path(__file__).parent / "sk"

        # Build terminal command
        if profile_uuid and GnomeProfiles.is_available():
            cmd = [
                "gnome-terminal",
                f"--profile={profile_uuid}",
                "--title", f"SK: {session_name}",
                "--", str(sk_path), "attach", session_name
            ]
        else:
            cmd = [
                "gnome-terminal",
                "--title", f"SK: {session_name}",
                "--", str(sk_path), "attach", session_name
            ]

        subprocess.Popen(cmd, start_new_session=True)
        print(f"Restoring session: {session_name}")
        return True

    def restore_all_sessions(self):
        """Restore all active sessions with their profiles"""
        sessions = self.list_sessions(clean_dead=True)

        if not sessions:
            print("No active sessions to restore")
            return

        print(f"Restoring {len(sessions)} session(s)...")

        for session in sessions:
            self.restore_session(session["name"])
            import time
            time.sleep(0.5)  # Small delay between windows

        print("Done!")

    def open_terminal(self, profile_name=None, profile_uuid=None, match_current=False):
        """Open a new terminal with a new session"""
        # Handle --match flag
        if match_current:
            current_session = os.environ.get("SHELLKEEPER_SESSION")
            if current_session:
                current_meta = self.metadata.get(current_session)
                if current_meta:
                    profile_name = profile_name or current_meta.get("profile_name")
                    profile_uuid = profile_uuid or current_meta.get("profile_uuid")

        # Resolve profile
        if profile_name and not profile_uuid:
            profile = GnomeProfiles.find_profile_by_name(profile_name)
            if profile:
                profile_uuid = profile["uuid"]
                profile_name = profile["name"]

        if profile_uuid and not profile_name:
            profile = GnomeProfiles.find_profile_by_uuid(profile_uuid)
            if profile:
                profile_name = profile["name"]

        # Use default profile from config if none specified
        if not profile_name and not profile_uuid:
            if self.config.get("default_profile_uuid"):
                profile_uuid = self.config["default_profile_uuid"]
                profile = GnomeProfiles.find_profile_by_uuid(profile_uuid)
                if profile:
                    profile_name = profile["name"]
            elif self.config.get("default_profile"):
                profile = GnomeProfiles.find_profile_by_name(self.config["default_profile"])
                if profile:
                    profile_name = profile["name"]
                    profile_uuid = profile["uuid"]

        # Generate session name
        session_name = self.generate_session_name(profile_name)

        # Pre-create metadata
        self.metadata.set(session_name, profile_name, profile_uuid)

        # Get the sk script path
        sk_path = Path(__file__).parent / "sk"

        # Build terminal command
        if profile_uuid and GnomeProfiles.is_available():
            cmd = [
                "gnome-terminal",
                f"--profile={profile_uuid}",
                "--title", f"SK: {session_name}",
                "--", str(sk_path), "new", session_name,
            ]
            if profile_name:
                cmd.extend(["--profile", profile_name])
        else:
            cmd = [
                "gnome-terminal",
                "--title", f"SK: {session_name}",
                "--", str(sk_path), "new", session_name
            ]

        subprocess.Popen(cmd, start_new_session=True)
        print(f"Opening terminal with session: {session_name}")
        if profile_name:
            print(f"Profile: {profile_name}")
        return session_name

    def setup_autostart(self):
        """Set up autostart for session restoration"""
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)

        sk_autostart_path = Path(__file__).parent / "sk-autostart"

        desktop_entry = f"""[Desktop Entry]
Type=Application
Name=ShellKeeper Session Restore
Comment=Check for surviving ShellKeeper sessions on login
Exec={sk_autostart_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""

        desktop_file = autostart_dir / "shellkeeper.desktop"
        desktop_file.write_text(desktop_entry)

        print(f"Created autostart entry: {desktop_file}")
        print("ShellKeeper will now check for surviving sessions on login.")


def main():
    parser = argparse.ArgumentParser(
        description="ShellKeeper - Terminal session manager with native scrolling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sk new                    Create new auto-named session
  sk new project            Create session named 'project'
  sk new --profile="Dark"   Create session with GNOME Terminal profile
  sk new --match            Create session with same profile as current
  sk ls                     List all sessions
  sk project                Attach to session 'project'
  sk kill project           Kill session 'project'
  sk info project           Show session details
  sk restore project        Restore session in new terminal
  sk restore-all            Restore all sessions
  sk terminal               Open new terminal with new session
  sk terminal --match       Open terminal with same profile as current
  sk profiles list          List GNOME Terminal profiles
  sk profiles default       Show default profile
  sk clean                  Clean up dead session sockets
  sk setup-autostart        Set up session restore on login

Inside a session:
  Ctrl+\\              Detach from session (keeps it running)
  Ctrl+C              KILLS the session - use Ctrl+\\ instead!
  exit                Terminate session completely
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List sessions
    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List sessions")

    # Create session
    create_parser = subparsers.add_parser("new", aliases=["create"], help="Create new session")
    create_parser.add_argument("name", nargs="?", help="Session name (auto-generated if not provided)")
    create_parser.add_argument("--profile", "-p", help="GNOME Terminal profile name or UUID")
    create_parser.add_argument("--match", "-m", action="store_true", help="Inherit current session's profile")

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

    # Session info
    info_parser = subparsers.add_parser("info", help="Show session details")
    info_parser.add_argument("name", nargs="?", help="Session name (current if not provided)")

    # Restore session
    restore_parser = subparsers.add_parser("restore", help="Restore session in new terminal")
    restore_parser.add_argument("name", nargs="?", help="Session name (most recent if not provided)")

    # Restore all sessions
    restore_all_parser = subparsers.add_parser("restore-all", help="Restore all sessions")

    # Open terminal with new session
    terminal_parser = subparsers.add_parser("terminal", aliases=["term"], help="Open new terminal with new session")
    terminal_parser.add_argument("--profile", "-p", help="GNOME Terminal profile name or UUID")
    terminal_parser.add_argument("--match", "-m", action="store_true", help="Inherit current session's profile")

    # Profiles subcommand
    profiles_parser = subparsers.add_parser("profiles", help="Manage GNOME Terminal profiles")
    profiles_sub = profiles_parser.add_subparsers(dest="profiles_command")
    profiles_list = profiles_sub.add_parser("list", help="List profiles")
    profiles_default = profiles_sub.add_parser("default", help="Show default profile")

    # Metadata subcommand
    metadata_parser = subparsers.add_parser("metadata", help="Manage session metadata")
    metadata_sub = metadata_parser.add_subparsers(dest="metadata_command")
    metadata_list = metadata_sub.add_parser("list", help="List all metadata")
    metadata_clean = metadata_sub.add_parser("clean", help="Clean orphaned metadata")

    # Setup autostart
    autostart_parser = subparsers.add_parser("setup-autostart", help="Set up session restore on login")

    args = parser.parse_args()

    sk = ShellKeeper()
    sk.check_dependencies()

    if args.command in ["list", "ls"]:
        sessions = sk.list_sessions()
        if not sessions:
            print("No active sessions")
            if os.environ.get("SK_DEBUG"):
                print(f"\nDebug: Looking in {sk.session_dir}")
                print(f"Files found: {list(sk.session_dir.glob('*'))}")
        else:
            print("Active sessions:")
            for session in sessions:
                profile_str = f" [{session['profile_name']}]" if session.get('profile_name') else ""
                print(f"  {session['name']:<30}{profile_str:<20} (last: {session['last_active']})")

    elif args.command in ["new", "create"]:
        sk.create_session(args.name, profile_name=args.profile, match_current=args.match)

    elif args.command in ["attach", "a"]:
        sk.attach_session(args.name)

    elif args.command == "kill":
        sk.kill_session(args.name)

    elif args.command == "rename":
        sk.rename_session(args.old_name, args.new_name)

    elif args.command == "clean":
        print("Cleaning up dead sessions...")
        sk.list_sessions(clean_dead=True)
        sk.metadata.clean([s["name"] for s in sk.list_sessions(clean_dead=False)])
        print("Done.")

    elif args.command == "last":
        sessions = sk.list_sessions()
        if sessions:
            print(f"Attaching to most recent session: {sessions[0]['name']}")
            sk.attach_session(sessions[0]['name'])
        else:
            print("No active sessions found")

    elif args.command == "info":
        session_name = args.name or os.environ.get("SHELLKEEPER_SESSION")
        if not session_name:
            print("No session specified and not in a session")
            sys.exit(1)

        info = sk.get_session_info(session_name)
        if info:
            print(f"Session: {info['name']}")
            print(f"  Socket: {info['socket']}")
            print(f"  Status: {'alive' if info['alive'] else 'dead'}")
            print(f"  Profile: {info.get('profile_name') or 'none'}")
            print(f"  Profile UUID: {info.get('profile_uuid') or 'none'}")
            print(f"  Created: {info.get('created') or 'unknown'}")
            print(f"  Last attached: {info.get('last_attached') or 'unknown'}")
        else:
            print(f"Session '{session_name}' not found")

    elif args.command == "restore":
        if args.name:
            sk.restore_session(args.name)
        else:
            sessions = sk.list_sessions()
            if sessions:
                sk.restore_session(sessions[0]['name'])
            else:
                print("No sessions to restore")

    elif args.command == "restore-all":
        sk.restore_all_sessions()

    elif args.command in ["terminal", "term"]:
        sk.open_terminal(profile_name=args.profile, match_current=args.match)

    elif args.command == "profiles":
        if not GnomeProfiles.is_available():
            print("GNOME Terminal profiles not available")
            sys.exit(1)

        if args.profiles_command == "list":
            profiles = GnomeProfiles.list_profiles()
            if profiles:
                print("GNOME Terminal profiles:")
                for p in profiles:
                    print(f"  {p['name']:<30} {p['uuid']}")
            else:
                print("No profiles found")

        elif args.profiles_command == "default":
            default = GnomeProfiles.get_default_profile()
            if default:
                print(f"Default profile: {default['name']} ({default['uuid']})")
            else:
                print("Could not determine default profile")

        else:
            profiles_parser.print_help()

    elif args.command == "metadata":
        if args.metadata_command == "list":
            meta = sk.metadata.list_all()
            if meta:
                print("Session metadata:")
                for name, data in meta.items():
                    profile = data.get('profile_name', 'none')
                    created = data.get('created', 'unknown')
                    print(f"  {name}: profile={profile}, created={created}")
            else:
                print("No metadata stored")

        elif args.metadata_command == "clean":
            sessions = sk.list_sessions(clean_dead=False)
            active_names = [s["name"] for s in sessions]
            removed = sk.metadata.clean(active_names)
            if removed:
                print(f"Removed metadata for {len(removed)} dead session(s): {', '.join(removed)}")
            else:
                print("No orphaned metadata to clean")

        else:
            metadata_parser.print_help()

    elif args.command == "setup-autostart":
        sk.setup_autostart()

    else:
        # If no command, show usage or attach to last session
        sessions = sk.list_sessions()
        if sessions and len(sys.argv) == 1:
            print(f"No command specified. Attaching to most recent session: {sessions[0]['name']}")
            sk.attach_session(sessions[0]['name'])
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
