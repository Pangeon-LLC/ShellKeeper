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
import fnmatch
from pathlib import Path
from datetime import datetime, timedelta


def relative_time(dt):
    """Convert datetime to relative time string like '2h ago'"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days}d ago"
    else:
        return dt.strftime("%Y-%m-%d")


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

    def set_note(self, session_name, note):
        """Set or update a note for a session"""
        if session_name in self.data:
            self.data[session_name]["note"] = note
            self._save()
            return True
        return False

    def get_note(self, session_name):
        """Get note for a session"""
        return self.data.get(session_name, {}).get("note")

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

    def export_data(self):
        """Export metadata in a portable format"""
        return {
            "version": 1,
            "exported": datetime.now().isoformat(),
            "sessions": self.data
        }

    def import_data(self, data, force=False):
        """Import metadata from exported format"""
        if "sessions" not in data:
            raise ValueError("Invalid export format: missing 'sessions' key")

        imported = 0
        skipped = 0
        for name, meta in data["sessions"].items():
            if name in self.data and not force:
                skipped += 1
            else:
                self.data[name] = meta
                imported += 1

        if imported > 0:
            self._save()

        return imported, skipped


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

    @classmethod
    def export_profiles(cls):
        """Export all GNOME Terminal profiles to JSON format"""
        profiles = cls.list_profiles()
        exported = []

        for profile in profiles:
            uuid = profile["uuid"]
            profile_data = {
                "uuid": uuid,
                "name": profile["name"],
                "settings": {}
            }

            # Export common settings
            settings_to_export = [
                "visible-name", "foreground-color", "background-color",
                "use-theme-colors", "palette", "font", "use-system-font",
                "cursor-shape", "cursor-blink-mode", "scrollback-lines",
                "scrollback-unlimited", "audible-bell"
            ]

            for setting in settings_to_export:
                try:
                    result = subprocess.run(
                        ["gsettings", "get",
                         f"org.gnome.Terminal.Legacy.Profile:{cls.DCONF_PATH}:{uuid}/",
                         setting],
                        capture_output=True, text=True, check=True
                    )
                    value = result.stdout.strip()
                    profile_data["settings"][setting] = value
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

            exported.append(profile_data)

        return {
            "version": 1,
            "exported": datetime.now().isoformat(),
            "profiles": exported
        }


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

    def is_linger_enabled(self):
        """Check if loginctl linger is enabled"""
        if sys.platform != "linux":
            return None  # Not applicable
        try:
            result = subprocess.run(
                ["loginctl", "show-user", os.environ.get("USER", ""), "--property=Linger"],
                capture_output=True, text=True
            )
            return "Linger=yes" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def is_autostart_configured(self):
        """Check if autostart is configured"""
        autostart_file = Path.home() / ".config" / "autostart" / "shellkeeper.desktop"
        return autostart_file.exists()

    def doctor(self):
        """Run health checks and report status"""
        checks = []

        # Check dtach
        dtach_ok = self.backend == "dtach"
        checks.append(("dtach installed", dtach_ok, "sudo apt install dtach"))

        # Check jq (optional, for JSON processing)
        try:
            subprocess.run(["which", "jq"], check=True, capture_output=True)
            jq_ok = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            jq_ok = False
        checks.append(("jq installed (optional)", jq_ok, "sudo apt install jq"))

        # Check loginctl linger
        linger = self.is_linger_enabled()
        if linger is None:
            checks.append(("loginctl linger", None, "Not applicable (non-Linux)"))
        else:
            checks.append(("loginctl linger enabled", linger, "sudo loginctl enable-linger $USER"))

        # Check autostart
        autostart_ok = self.is_autostart_configured()
        checks.append(("autostart configured", autostart_ok, "sk setup-autostart"))

        # Check GNOME profiles
        gnome_ok = GnomeProfiles.is_available()
        checks.append(("GNOME Terminal profiles", gnome_ok, "Install GNOME Terminal"))

        # Check config file
        config_ok = self.config_file.exists()
        checks.append(("config file exists", config_ok, "Will be created on first use"))

        # Check sessions directory
        sessions_ok = self.session_dir.exists()
        checks.append(("sessions directory exists", sessions_ok, "Will be created on first use"))

        return checks

    def run_hook(self, hook_name, session_name):
        """Run a configured hook script"""
        hooks = self.config.get("hooks", {})
        hook_script = hooks.get(hook_name)

        if hook_script and os.path.isfile(hook_script):
            env = os.environ.copy()
            env["SK_SESSION"] = session_name
            env["SK_HOOK"] = hook_name
            try:
                subprocess.Popen(
                    [hook_script],
                    env=env,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass  # Silently ignore hook failures

    def start_logging(self, session_name, log_file=None):
        """Start logging a session's output"""
        socket_path = self.get_socket_path(session_name)

        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False

        if not self.is_session_alive(socket_path):
            print(f"Session '{session_name}' is dead")
            return False

        # Default log file location
        if log_file is None:
            log_dir = Path.home() / ".shellkeeper" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_file = log_dir / f"{session_name}-{timestamp}.log"

        # Use script command to capture output
        cmd = [
            "script", "-q", "-a", str(log_file),
            "-c", f"dtach -a {socket_path} -e ^\\ -r winch"
        ]

        print(f"Logging session '{session_name}' to: {log_file}")
        print("Press Ctrl+\\ to detach (log continues until session ends)")

        subprocess.run(cmd)
        return True

    def get_templates(self):
        """Get configured session templates"""
        return self.config.get("templates", {})

    def create_session_from_template(self, template_name, session_name=None):
        """Create a session from a template"""
        templates = self.get_templates()

        if template_name not in templates:
            print(f"Template '{template_name}' not found")
            print("Available templates:")
            for name in templates:
                print(f"  {name}")
            return False, None

        template = templates[template_name]
        profile_name = template.get("profile")
        startup_cmd = template.get("command")
        working_dir = template.get("directory")

        # Create the session
        success, session_name = self.create_session(
            session_name=session_name,
            profile_name=profile_name,
            startup_command=startup_cmd,
            working_directory=working_dir
        )

        return success, session_name

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
            "session_name_format": "{profile}-{date}-{time}-{random}",
            "hooks": {
                "on_create": None,
                "on_attach": None,
                "on_detach": None
            },
            "templates": {}
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

    def create_session(self, session_name=None, profile_name=None, profile_uuid=None, match_current=False,
                       startup_command=None, working_directory=None):
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

        # Build wrapper script with optional working directory and startup command
        wrapper_lines = [
            "#!/bin/bash",
            f'export SHELLKEEPER_SESSION="{session_name}"',
            f'export SHELLKEEPER_SOCKET="{socket_path}"',
            f'export SK_KEEPALIVE_ENABLED="{env["SK_KEEPALIVE_ENABLED"]}"',
            f'export SK_KEEPALIVE_INTERVAL="{env["SK_KEEPALIVE_INTERVAL"]}"',
            f'export SK_PROFILE_NAME="{profile_name or ""}"',
            f'export SK_PROFILE_UUID="{profile_uuid or ""}"',
        ]

        if working_directory:
            wrapper_lines.append(f'cd "{working_directory}"')

        if startup_command:
            # Run startup command then drop into shell
            wrapper_lines.append(f'{startup_command}')
            wrapper_lines.append(f'exec {self.config["default_shell"]}')
        else:
            wrapper_lines.append(f'exec {self.config["default_shell"]}')

        wrapper_script = "\n".join(wrapper_lines) + "\n"

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

        # Run on_create hook
        self.run_hook("on_create", session_name)

        try:
            subprocess.run(cmd, env=env)
        finally:
            try:
                os.unlink(wrapper_path)
            except:
                pass
            # Run on_detach hook (session was detached or ended)
            self.run_hook("on_detach", session_name)

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

        # Run on_attach hook
        self.run_hook("on_attach", session_name)

        subprocess.run(cmd, env=env)

        # Run on_detach hook
        self.run_hook("on_detach", session_name)

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

    def kill_sessions_by_pattern(self, pattern):
        """Kill sessions matching a glob pattern"""
        sessions = self.list_sessions(clean_dead=False)
        killed = []
        for session in sessions:
            if fnmatch.fnmatch(session["name"], pattern):
                self.kill_session(session["name"])
                killed.append(session["name"])
        return killed

    def kill_all_sessions(self):
        """Kill all sessions"""
        sessions = self.list_sessions(clean_dead=False)
        killed = []
        for session in sessions:
            self.kill_session(session["name"])
            killed.append(session["name"])
        return killed

    def cleanup_idle_sessions(self, max_idle_days):
        """Remove sessions that have been idle for more than max_idle_days"""
        sessions = self.list_sessions(clean_dead=False)
        cutoff = datetime.now() - timedelta(days=max_idle_days)
        removed = []

        for session in sessions:
            meta = self.metadata.get(session["name"])
            last_attached_str = meta.get("last_attached")
            if last_attached_str:
                last_attached = datetime.fromisoformat(last_attached_str)
                if last_attached < cutoff:
                    self.kill_session(session["name"])
                    removed.append(session["name"])

        return removed

    def set_session_note(self, session_name, note):
        """Set a note on a session"""
        socket_path = self.get_socket_path(session_name)
        if not socket_path.exists():
            print(f"Session '{session_name}' not found")
            return False
        return self.metadata.set_note(session_name, note)

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


def run_dashboard(sk):
    """Run the interactive TUI dashboard"""
    import curses

    def dashboard_main(stdscr):
        curses.curs_set(0)  # Hide cursor
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)

        selected = 0
        refresh_interval = 2  # seconds

        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Header
            header = " ShellKeeper Dashboard "
            stdscr.attron(curses.A_BOLD | curses.color_pair(3))
            stdscr.addstr(0, (width - len(header)) // 2, header)
            stdscr.attroff(curses.A_BOLD | curses.color_pair(3))

            # Get sessions
            sessions = sk.list_sessions(clean_dead=False)

            if not sessions:
                stdscr.addstr(2, 2, "No active sessions", curses.color_pair(2))
                stdscr.addstr(4, 2, "Press 'n' to create new session, 'q' to quit")
            else:
                # Column headers
                stdscr.attron(curses.A_UNDERLINE)
                stdscr.addstr(2, 2, f"{'Session':<35} {'Profile':<20} {'Last Active':<15}")
                stdscr.attroff(curses.A_UNDERLINE)

                # List sessions
                for i, session in enumerate(sessions):
                    if i >= height - 6:  # Leave room for footer
                        break

                    meta = sk.metadata.get(session["name"])
                    profile = session.get("profile_name", "-")[:18] or "-"
                    last_attached = meta.get("last_attached")
                    time_str = relative_time(last_attached) if last_attached else "-"

                    name = session["name"][:33]
                    line = f"  {name:<35} {profile:<20} {time_str:<15}"

                    if i == selected:
                        stdscr.attron(curses.A_REVERSE)
                        stdscr.addstr(3 + i, 0, line[:width-1])
                        stdscr.attroff(curses.A_REVERSE)
                    else:
                        stdscr.addstr(3 + i, 0, line[:width-1])

                    note = meta.get("note")
                    if note and i == selected:
                        stdscr.addstr(3 + i, len(line), f' "{note[:20]}"', curses.color_pair(2))

            # Footer
            footer = " [Enter] Attach  [k] Kill  [n] New  [r] Refresh  [q] Quit "
            stdscr.attron(curses.A_REVERSE)
            stdscr.addstr(height - 1, 0, footer.ljust(width - 1))
            stdscr.attroff(curses.A_REVERSE)

            stdscr.refresh()

            # Handle input with timeout for auto-refresh
            stdscr.timeout(refresh_interval * 1000)
            try:
                key = stdscr.getch()
            except:
                continue

            if key == ord('q'):
                break
            elif key == ord('r') or key == -1:  # -1 is timeout
                continue
            elif key == ord('n'):
                curses.endwin()
                sk.create_session()
                curses.doupdate()
            elif key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and sessions and selected < len(sessions) - 1:
                selected += 1
            elif key == ord('\n') and sessions:
                curses.endwin()
                sk.attach_session(sessions[selected]["name"])
                curses.doupdate()
            elif key == ord('k') and sessions:
                session_name = sessions[selected]["name"]
                sk.kill_session(session_name)
                if selected > 0:
                    selected -= 1

    curses.wrapper(dashboard_main)


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
    create_parser.add_argument("--template", "-t", help="Use a session template")

    # Attach to session
    attach_parser = subparsers.add_parser("attach", aliases=["a"], help="Attach to session")
    attach_parser.add_argument("name", help="Session name")

    # Kill session
    kill_parser = subparsers.add_parser("kill", help="Kill session")
    kill_parser.add_argument("name", nargs="?", help="Session name")
    kill_parser.add_argument("--all", "-a", action="store_true", help="Kill all sessions")
    kill_parser.add_argument("--pattern", "-p", help="Kill sessions matching glob pattern (e.g., 'test-*')")

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

    # Session note
    note_parser = subparsers.add_parser("note", help="Add a note to a session")
    note_parser.add_argument("name", help="Session name")
    note_parser.add_argument("text", nargs="?", help="Note text (omit to clear)")

    # Cleanup idle sessions
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove sessions idle for N days")
    cleanup_parser.add_argument("days", type=int, help="Max idle days (sessions older are removed)")

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
    profiles_export = profiles_sub.add_parser("export", help="Export profiles to JSON")

    # Metadata subcommand
    metadata_parser = subparsers.add_parser("metadata", help="Manage session metadata")
    metadata_sub = metadata_parser.add_subparsers(dest="metadata_command")
    metadata_list = metadata_sub.add_parser("list", help="List all metadata")
    metadata_clean = metadata_sub.add_parser("clean", help="Clean orphaned metadata")
    metadata_export = metadata_sub.add_parser("export", help="Export metadata to stdout")
    metadata_import = metadata_sub.add_parser("import", help="Import metadata from stdin")
    metadata_import.add_argument("--force", "-f", action="store_true", help="Overwrite existing entries")

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_show = config_sub.add_parser("show", help="Show current configuration")
    config_set_profile = config_sub.add_parser("set-default-profile", help="Set default terminal profile")
    config_set_profile.add_argument("profile", help="Profile name")

    # Setup autostart
    autostart_parser = subparsers.add_parser("setup-autostart", help="Set up session restore on login")

    # Doctor - health check
    doctor_parser = subparsers.add_parser("doctor", help="Run health checks")

    # Log - capture session output
    log_parser = subparsers.add_parser("log", help="Capture session output to file")
    log_parser.add_argument("name", help="Session name")
    log_parser.add_argument("--output", "-o", help="Output file path (default: ~/.shellkeeper/logs/)")

    # Dashboard - TUI
    dashboard_parser = subparsers.add_parser("dashboard", help="Interactive session dashboard")

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
                meta = sk.metadata.get(session["name"])
                profile_str = f" [{session['profile_name']}]" if session.get('profile_name') else ""

                # Get relative time from last_attached
                last_attached = meta.get("last_attached")
                if last_attached:
                    time_str = relative_time(last_attached)
                else:
                    time_str = session['last_active']

                note = meta.get("note")
                note_str = f' "{note}"' if note else ""

                print(f"  {session['name']:<30}{profile_str:<20} ({time_str}){note_str}")

    elif args.command in ["new", "create"]:
        if args.template:
            sk.create_session_from_template(args.template, args.name)
        else:
            sk.create_session(args.name, profile_name=args.profile, match_current=args.match)

    elif args.command in ["attach", "a"]:
        sk.attach_session(args.name)

    elif args.command == "kill":
        if args.all:
            killed = sk.kill_all_sessions()
            if killed:
                print(f"Killed {len(killed)} session(s)")
            else:
                print("No sessions to kill")
        elif args.pattern:
            killed = sk.kill_sessions_by_pattern(args.pattern)
            if killed:
                print(f"Killed {len(killed)} session(s) matching '{args.pattern}'")
            else:
                print(f"No sessions matching '{args.pattern}'")
        elif args.name:
            sk.kill_session(args.name)
        else:
            print("Specify a session name, --all, or --pattern")
            sys.exit(1)

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
            meta = sk.metadata.get(session_name)
            if meta.get("note"):
                print(f"  Note: {meta['note']}")
        else:
            print(f"Session '{session_name}' not found")

    elif args.command == "note":
        if args.text:
            if sk.set_session_note(args.name, args.text):
                print(f"Note set for '{args.name}': {args.text}")
            else:
                sys.exit(1)
        else:
            # Clear note
            if sk.metadata.set_note(args.name, None):
                print(f"Note cleared for '{args.name}'")
            else:
                print(f"Session '{args.name}' not found")
                sys.exit(1)

    elif args.command == "cleanup":
        removed = sk.cleanup_idle_sessions(args.days)
        if removed:
            print(f"Removed {len(removed)} session(s) idle for more than {args.days} day(s):")
            for name in removed:
                print(f"  {name}")
        else:
            print(f"No sessions idle for more than {args.days} day(s)")

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

        elif args.profiles_command == "export":
            export_data = GnomeProfiles.export_profiles()
            print(json.dumps(export_data, indent=2))

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

        elif args.metadata_command == "export":
            export_data = sk.metadata.export_data()
            print(json.dumps(export_data, indent=2))

        elif args.metadata_command == "import":
            try:
                import_data = json.load(sys.stdin)
                imported, skipped = sk.metadata.import_data(import_data, force=args.force)
                print(f"Imported {imported} session(s)")
                if skipped > 0:
                    print(f"Skipped {skipped} existing session(s) (use --force to overwrite)")
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON input: {e}")
                sys.exit(1)
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

        else:
            metadata_parser.print_help()

    elif args.command == "config":
        if args.config_command == "show":
            print("Current configuration:")
            print(json.dumps(sk.config, indent=2))

        elif args.config_command == "set-default-profile":
            profile = GnomeProfiles.find_profile_by_name(args.profile)
            if profile:
                sk.config["default_profile"] = profile["name"]
                sk.config["default_profile_uuid"] = profile["uuid"]
                sk.save_config()
                print(f"Default profile set to: {profile['name']} ({profile['uuid']})")
            else:
                print(f"Profile '{args.profile}' not found")
                print("Available profiles:")
                for p in GnomeProfiles.list_profiles():
                    print(f"  {p['name']}")
                sys.exit(1)

        else:
            config_parser.print_help()

    elif args.command == "setup-autostart":
        sk.setup_autostart()

    elif args.command == "doctor":
        checks = sk.doctor()
        print("ShellKeeper Health Check")
        print("=" * 40)

        all_ok = True
        for name, status, fix in checks:
            if status is True:
                print(f"  \033[32m✓\033[0m {name}")
            elif status is False:
                print(f"  \033[31m✗\033[0m {name}")
                print(f"      Fix: {fix}")
                all_ok = False
            else:
                print(f"  \033[33m-\033[0m {name} ({fix})")

        print()
        if all_ok:
            print("\033[32mAll checks passed!\033[0m")
        else:
            print("\033[33mSome issues found. See fixes above.\033[0m")

    elif args.command == "log":
        output_file = args.output if hasattr(args, 'output') and args.output else None
        sk.start_logging(args.name, output_file)

    elif args.command == "dashboard":
        try:
            import curses
            run_dashboard(sk)
        except ImportError:
            print("Error: curses module not available")
            sys.exit(1)

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
