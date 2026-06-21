import os
import sys
import time
import json
import hashlib
import logging
import threading
import subprocess
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import requests
    from colorama import init, Fore, Style
    import ctypes
    from win32com.client import Dispatch
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import Image, ImageTk, ImageDraw
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install requests colorama pywin32 pillow")
    sys.exit(1)

try:
    from pypresence import Presence
    DISCORD_RPC_AVAILABLE = True
except ImportError:
    DISCORD_RPC_AVAILABLE = False

init(autoreset=True)
logging.basicConfig(
    filename='launcher.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

LAUNCHER_VERSION = "1.3"
LAUNCHER_VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/LauncherVersion.txt"
LAUNCHER_DOWNLOAD_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AmongUsLauncher.exe"
VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/main/Version.txt"
MESSAGE_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/message.txt"
PATCHES_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/Patches.xml"
SOURCE_CODE_URL = "https://github.com/jogamerforgames2021/BootstrapperTEST/blob/main/my_script.py"
GITHUB_REPO = "jogamerforgames2021/AmongUsLauncherNew"
AUNLOCKER_JSON_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AUnlockerStuff/Versions.json"
DISCORD_CLIENT_ID = "1378503147768647821"
DISCORD_INVITE = "https://discord.gg/7Vvj2vpT6S"
REQUEST_TIMEOUT = 10
CHUNK_SIZE = 8192

class Colors:
    """Centralized color definitions"""
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.CYAN
    HIGHLIGHT = Fore.MAGENTA
    GOLD = Fore.YELLOW + Style.BRIGHT
    RESET = Style.RESET_ALL

@dataclass
class GameVersion:
    """Game version information"""
    version: str
    url: str
    checksum: Optional[str] = None

class LauncherState(Enum):
    """Launcher state management"""
    INITIALIZING = "Initializing"
    CHECKING_UPDATES = "Checking for updates"
    DOWNLOADING = "Downloading"
    EXTRACTING = "Extracting"
    READY = "Ready"
    RUNNING_GAME = "Running game"
    ERROR = "Error"

class Config:
    """Configuration manager"""
    def __init__(self):
        self.appdata_dir = Path(os.environ["APPDATA"]) / "AmongUsShadowSlime"
        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.appdata_dir / "current_version.txt"
        self.game_path_file = self.appdata_dir / "game_path.txt"
        self.config_file = self.appdata_dir / "config.json"
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        """Load launcher settings"""
        default_settings = {
            "auto_update": True,
            "create_shortcuts": True,
            "discord_rpc": True,
            "minimize_on_game_start": False,
            "check_integrity": True,
            "ui_mode": "gui"
        }
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return {**default_settings, **json.load(f)}
        except Exception as e:
            logging.error(f"Failed to load settings: {e}")
        return default_settings

    def save_settings(self):
        """Save launcher settings"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def get_version(self) -> Optional[str]:
        """Get installed game version"""
        try:
            if self.version_file.exists():
                return self.version_file.read_text().strip()
        except Exception as e:
            logging.error(f"Failed to read version: {e}")
        return None

    def set_version(self, version: str):
        """Set installed game version"""
        try:
            self.version_file.write_text(version)
        except Exception as e:
            logging.error(f"Failed to write version: {e}")

    def get_game_path(self) -> Optional[Path]:
        """Get game installation path"""
        try:
            if self.game_path_file.exists():
                path = Path(self.game_path_file.read_text().strip())
                if path.exists():
                    return path
        except Exception as e:
            logging.error(f"Failed to read game path: {e}")
        return None

    def set_game_path(self, path: Path):
        """Set game installation path"""
        try:
            self.game_path_file.write_text(str(path))
        except Exception as e:
            logging.error(f"Failed to write game path: {e}")

class NetworkManager:
    """Handle all network operations"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'AmongUsLauncher/{LAUNCHER_VERSION}'
        })

    def is_connected(self) -> bool:
        """Check internet connectivity"""
        try:
            self.session.get("https://www.google.com", timeout=3)
            return True
        except:
            return False

    def fetch_text(self, url: str) -> Optional[str]:
        """Fetch text content from URL"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text.strip()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def download_file(self, url: str, output_path: Path, progress_callback=None) -> bool:
        """Download file with progress tracking"""
        try:
            start_time = time.time()
            with self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size:
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                progress_callback(downloaded, total_size, speed)
            return True
        except requests.RequestException as e:
            logging.error(f"Download failed: {e}")
            return False

    def get_releases(self) -> List[GameVersion]:
        """Fetch available game versions from GitHub"""
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            releases = response.json()
            versions = []
            for release in releases:
                for asset in release.get("assets", []):
                    if asset["name"] == "app.zip":
                        versions.append(GameVersion(
                            version=release.get("tag_name"),
                            url=asset["browser_download_url"]
                        ))
            return versions
        except Exception as e:
            logging.error(f"Failed to fetch releases: {e}")
            return []

class FileManager:
    """Handle file operations"""
    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logging.error(f"Failed to calculate checksum: {e}")
            return ""

    @staticmethod
    def extract_zip(zip_path: Path, extract_to: Path, progress_callback=None) -> bool:
        """Extract zip file with progress"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                members = zip_ref.infolist()
                total = len(members)
                for i, member in enumerate(members):
                    zip_ref.extract(member, extract_to)
                    if progress_callback:
                        progress_callback(i + 1, total)
            return True
        except zipfile.BadZipFile as e:
            logging.error(f"Corrupt zip file: {e}")
            return False
        except Exception as e:
            logging.error(f"Extraction failed: {e}")
            return False

    @staticmethod
    def remove_readonly(func, path, exc_info):
        """Remove read-only flag and retry"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    @staticmethod
    def safe_delete(path: Path) -> bool:
        """Safely delete file or directory"""
        try:
            if not path.exists():
                return True
            if path.is_dir():
                shutil.rmtree(path, onerror=FileManager.remove_readonly)
            else:
                path.unlink()
            return True
        except Exception as e:
            logging.error(f"Failed to delete {path}: {e}")
            return False

    @staticmethod
    def format_size(bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"
class DiscordRPC:
    """Discord Rich Presence manager"""
    def __init__(self):
        self.rpc: Optional[Presence] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Discord RPC"""
        if not DISCORD_RPC_AVAILABLE:
            return False
        try:

            if self.connected and self.rpc:
                try:
                    self.rpc.close()
                except:
                    pass

            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()
            self.connected = True
            self.update_status("In Launcher", "Browsing Menu")
            return True
        except Exception as e:
            logging.error(f"Discord RPC failed: {e}")
            self.connected = False
            return False

    def update_status(self, state: str, details: str, large_text: str = "Among Us Shadow Slime"):
        """Update Discord status"""
        if self.connected and self.rpc:
            try:
                self.rpc.update(
                    state=state,
                    details=details,
                    large_image="amongus",
                    large_text=large_text
                )
            except Exception as e:
                logging.error(f"Failed to update RPC: {e}")
                self.connected = False

    def disconnect(self):
        """Disconnect from Discord RPC"""
        if self.connected and self.rpc:
            try:
                self.rpc.close()
                self.connected = False
            except:
                pass

class GameManager:
    """Manage game installation and updates"""
    def __init__(self, config: Config, network: NetworkManager):
        self.config = config
        self.network = network

    def get_install_path(self) -> Optional[Path]:
        """Get game installation path with user selection"""
        self.ui.print("\n[*] Choose installation location:", Colors.INFO)
        self.ui.print("  [1] Custom folder (recommended)")
        self.ui.print("  [2] Default 'GAME' folder")

        choice = self.ui.get_input("Your choice (1/2): ")

        if choice == '1':
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                selected = filedialog.askdirectory(title="Select Among Us Install Folder")
                root.destroy()
                if selected:
                    return Path(selected)
            except Exception as e:
                logging.error(f"Folder selection failed: {e}")

        return Path.cwd() / "GAME"

    def download_and_install(self, version: str, url: str, install_path: Path) -> bool:
        """Download and install game"""
        zip_file = Path("game.zip")

        self.ui.print(f"\n[*] Downloading version {version}...", Colors.INFO)
        def progress(current, total, speed):
            self.ui.show_progress_bar(current, total, "Downloading", speed)

        if not self.network.download_file(url, zip_file, progress):
            self.ui.print("\n[ERROR] Download failed!", Colors.ERROR)
            return False

        print()

        if self.config.settings.get("check_integrity"):
            self.ui.print("[*] Verifying file integrity...", Colors.INFO)

        self.ui.print("[*] Extracting files...", Colors.INFO)
        install_path.mkdir(parents=True, exist_ok=True)

        def extract_progress(current, total):
            self.ui.show_progress_bar(current, total, "Extracting")

        if not FileManager.extract_zip(zip_file, install_path, extract_progress):
            self.ui.print("\n[ERROR] Extraction failed!", Colors.ERROR)
            return False

        print()

        FileManager.safe_delete(zip_file)

        self.config.set_version(version)
        self.config.set_game_path(install_path)

        self.ui.print("[✓] Installation complete!", Colors.SUCCESS)
        return True

    def update_game(self, current_version: str, latest_version: str) -> bool:
        """Update game to latest version"""
        url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest_version}/app.zip"
        game_path = self.config.get_game_path()

        if not game_path:
            self.ui.print("[ERROR] Game path not found!", Colors.ERROR)
            return False

        if not self.ui.confirm(f"Update from {current_version} to {latest_version}?"):
            return False

        return self.download_and_install(latest_version, url, game_path)

    def launch_game(self) -> bool:
        """Launch the game"""
        game_path = self.config.get_game_path()
        if not game_path:
            self.ui.print("[ERROR] Game not installed!", Colors.ERROR)
            return False

        exe_path = game_path / "Among Us.exe"
        if not exe_path.exists():
            self.ui.print("[ERROR] Game executable not found!", Colors.ERROR)
            return False

        try:
            subprocess.Popen([str(exe_path)], cwd=str(game_path))
            self.ui.print("[✓] Game launched!", Colors.SUCCESS)
            return True
        except Exception as e:
            logging.error(f"Failed to launch game: {e}")
            self.ui.print(f"[ERROR] Failed to launch: {e}", Colors.ERROR)
            return False
    """Discord Rich Presence manager"""
    def __init__(self):
        self.rpc: Optional[Presence] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Discord RPC"""
        if not DISCORD_RPC_AVAILABLE:
            return False
        try:
            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()
            self.connected = True
            self.update_status("In Launcher", "Browsing Menu")
            return True
        except Exception as e:
            logging.error(f"Discord RPC failed: {e}")
            return False

    def update_status(self, state: str, details: str):
        """Update Discord status"""
        if self.connected and self.rpc:
            try:
                self.rpc.update(
                    state=state,
                    details=details,
                    large_image="amongus",
                    large_text="Among Us Shadow Slime"
                )
            except Exception as e:
                logging.error(f"Failed to update RPC: {e}")

    def disconnect(self):
        """Disconnect from Discord RPC"""
        if self.connected and self.rpc:
            try:
                self.rpc.close()
            except:
                pass

class ModernUI:
    """Modern GUI Launcher Interface"""
    def __init__(self, config: Config, network: NetworkManager):
        self.config = config
        self.network = network
        self.discord = DiscordRPC()

        self.root = tk.Tk()
        self.root.title(f"Among Us Launcher v{LAUNCHER_VERSION}")
        self.root.geometry("1100x700")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#1a1a1a")

        self.menu_expanded = tk.BooleanVar(value=True)
        self.current_version = tk.StringVar(value="Not Installed")
        self.latest_version = tk.StringVar(value="Checking...")
        self.status_text = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.current_tab = tk.StringVar(value="game")

        self.bg_dark = "#1a1a1a"
        self.bg_medium = "#252525"
        self.bg_light = "#2f2f2f"
        self.bg_hover = "#363636"
        self.accent_green = "#00d26a"
        self.accent_blue = "#0098ff"
        self.accent_red = "#ff4757"
        self.accent_purple = "#a55eea"
        self.accent_orange = "#ffa502"
        self.text_color = "#ffffff"
        self.text_dim = "#8e8e8e"
        self.shadow = "#0d0d0d"

        self.setup_ui()
        self.load_initial_data()

    def setup_ui(self):
        """Setup the main UI components"""

        self.sidebar_container = tk.Frame(self.root, bg=self.bg_medium, width=280)
        self.sidebar_container.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_container.pack_propagate(False)

        self.sidebar_canvas = tk.Canvas(
            self.sidebar_container,
            bg=self.bg_medium,
            highlightthickness=0,
            width=280
        )

        sidebar_scrollbar = ttk.Scrollbar(
            self.sidebar_container,
            orient="vertical",
            command=self.sidebar_canvas.yview
        )

        self.sidebar_frame = tk.Frame(self.sidebar_canvas, bg=self.bg_medium)
        self.sidebar_frame.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        )

        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_frame, anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.sidebar_canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", self.sidebar_canvas))
        self.sidebar_canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))

        title_frame = tk.Frame(self.sidebar_frame, bg=self.bg_medium, height=120)
        title_frame.pack(fill=tk.X, padx=15, pady=15)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="AMONG US",
            font=("Segoe UI", 20, "bold"),
            bg=self.bg_medium,
            fg=self.accent_green
        ).pack(anchor=tk.W, pady=(10, 0))

        tk.Label(
            title_frame,
            text="Shadow Slime Launcher",
            font=("Segoe UI", 10),
            bg=self.bg_medium,
            fg=self.text_dim
        ).pack(anchor=tk.W, pady=(0, 5))

        tk.Label(
            title_frame,
            text=f"v{LAUNCHER_VERSION}",
            font=("Segoe UI", 9),
            bg=self.bg_medium,
            fg=self.accent_purple
        ).pack(anchor=tk.W)

        tk.Frame(self.sidebar_frame, bg=self.bg_light, height=2).pack(fill=tk.X, padx=15, pady=10)

        nav_frame = tk.Frame(self.sidebar_frame, bg=self.bg_medium)
        nav_frame.pack(fill=tk.X, padx=15, pady=10)

        self.tab_buttons = {}
        tabs = [
            ("🎮 Game", "game", self.accent_green),
            ("📰 News", "news", self.accent_blue)
        ]

        for text, tab_id, color in tabs:
            btn = self.create_tab_button(nav_frame, text, tab_id, color)
            btn.pack(fill=tk.X, pady=3)
            self.tab_buttons[tab_id] = btn

        tk.Frame(self.sidebar_frame, bg=self.bg_light, height=1).pack(fill=tk.X, padx=15, pady=10)

        self.create_menu_section("🛠️ TOOLS", [
            ("Install AUnlocker", self.install_aunlocker, self.accent_blue),
            ("Create Shortcut", self.create_shortcut, self.text_dim),
            ("Open Folder", self.open_folder, self.text_dim),
            ("Change Location", self.change_location, self.text_dim)
        ])

        self.create_menu_section("⚙️ SETTINGS", [
            ("Preferences", self.show_settings, self.accent_green),
            ("Reinstall Game", self.reinstall_game, self.accent_blue),
            ("Uninstall", self.uninstall_game, self.accent_red)
        ])

        social_frame = tk.Frame(self.sidebar_frame, bg=self.bg_medium)
        social_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20)

        self.create_hover_button(
            social_frame,
            "🎮 Join Discord",
            lambda: os.system(f"start {DISCORD_INVITE}"),
            self.accent_purple
        ).pack(fill=tk.X, pady=3)

        self.create_hover_button(
            social_frame,
            "📺 YouTube Channel",
            lambda: os.system("start https://www.youtube.com/@ShadowSlimeDEV"),
            self.accent_red
        ).pack(fill=tk.X, pady=3)

        self.create_hover_button(
            social_frame,
            "💻 Source Code",
            lambda: os.system(f"start {SOURCE_CODE_URL}"),
            self.accent_orange
        ).pack(fill=tk.X, pady=3)

        self.content_frame = tk.Frame(self.root, bg=self.bg_dark)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.game_tab = tk.Frame(self.content_frame, bg=self.bg_dark)
        self.news_tab = tk.Frame(self.content_frame, bg=self.bg_dark)

        self.setup_game_tab()
        self.setup_news_tab()

        self.switch_tab("game")

        self.setup_styles()

    def create_tab_button(self, parent, text, tab_id, accent_color):
        """Create a tab navigation button"""
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_light,
            fg=self.text_color,
            activebackground=accent_color,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.switch_tab(tab_id),
            anchor=tk.W,
            padx=15,
            pady=12,
            borderwidth=0
        )

        def on_enter(e):
            if self.current_tab.get() != tab_id:
                btn.config(bg=self.bg_hover)

        def on_leave(e):
            if self.current_tab.get() != tab_id:
                btn.config(bg=self.bg_light)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def switch_tab(self, tab_id):
        """Switch between tabs"""
        self.current_tab.set(tab_id)

        self.game_tab.pack_forget()
        self.news_tab.pack_forget()

        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                if tid == "game":
                    btn.config(bg=self.accent_green, fg="white")
                else:
                    btn.config(bg=self.accent_blue, fg="white")
            else:
                btn.config(bg=self.bg_light, fg=self.text_color)

        if tab_id == "game":
            self.game_tab.pack(fill=tk.BOTH, expand=True)
        elif tab_id == "news":
            self.news_tab.pack(fill=tk.BOTH, expand=True)

    def setup_game_tab(self):
        """Setup the game management tab"""

        header_frame = tk.Frame(self.game_tab, bg=self.bg_medium, height=100)
        header_frame.pack(fill=tk.X, padx=25, pady=25)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Game Management",
            font=("Segoe UI", 24, "bold"),
            bg=self.bg_medium,
            fg=self.text_color
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        tk.Label(
            header_frame,
            text="Install, update, and manage your Among Us installation",
            font=("Segoe UI", 10),
            bg=self.bg_medium,
            fg=self.text_dim
        ).pack(anchor=tk.W, padx=20)

        card_frame = tk.Frame(self.game_tab, bg=self.bg_medium)
        card_frame.pack(fill=tk.X, padx=25, pady=10)

        info_container = tk.Frame(card_frame, bg=self.bg_medium)
        info_container.pack(padx=30, pady=25)

        current_frame = tk.Frame(info_container, bg=self.bg_light, highlightbackground=self.accent_green, highlightthickness=2)
        current_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")

        inner_current = tk.Frame(current_frame, bg=self.bg_light)
        inner_current.pack(padx=25, pady=20)

        tk.Label(
            inner_current,
            text="📦 Installed Version",
            font=("Segoe UI", 11),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)

        tk.Label(
            inner_current,
            textvariable=self.current_version,
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_light,
            fg=self.accent_green
        ).pack(anchor=tk.W, pady=(8, 0))

        latest_frame = tk.Frame(info_container, bg=self.bg_light, highlightbackground=self.accent_blue, highlightthickness=2)
        latest_frame.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        inner_latest = tk.Frame(latest_frame, bg=self.bg_light)
        inner_latest.pack(padx=25, pady=20)

        tk.Label(
            inner_latest,
            text="🌐 Latest Version",
            font=("Segoe UI", 11),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)

        tk.Label(
            inner_latest,
            textvariable=self.latest_version,
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_light,
            fg=self.accent_blue
        ).pack(anchor=tk.W, pady=(8, 0))

        action_frame = tk.Frame(self.game_tab, bg=self.bg_dark)
        action_frame.pack(pady=20)

        self.main_button = tk.Button(
            action_frame,
            text="INSTALL GAME",
            font=("Segoe UI", 15, "bold"),
            bg=self.accent_green,
            fg="white",
            activebackground="#00b359",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.main_action,
            padx=50,
            pady=18,
            borderwidth=0
        )
        self.main_button.grid(row=0, column=0, padx=10)

        check_btn = tk.Button(
            action_frame,
            text="Check Updates",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_light,
            fg=self.text_color,
            activebackground=self.bg_hover,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.check_updates,
            padx=20,
            pady=15,
            borderwidth=0
        )
        check_btn.grid(row=0, column=1, padx=10)

        version_btn = tk.Button(
            action_frame,
            text="Install Specific",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_light,
            fg=self.text_color,
            activebackground=self.bg_hover,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.install_specific,
            padx=20,
            pady=15,
            borderwidth=0
        )
        version_btn.grid(row=0, column=2, padx=10)

        self.main_button.bind("<Enter>", lambda e: self.main_button.config(bg="#00b359"))
        self.main_button.bind("<Leave>", lambda e: self.main_button.config(bg=self.accent_green))
        check_btn.bind("<Enter>", lambda e: check_btn.config(bg=self.accent_blue, fg="white"))
        check_btn.bind("<Leave>", lambda e: check_btn.config(bg=self.bg_light, fg=self.text_color))
        version_btn.bind("<Enter>", lambda e: version_btn.config(bg=self.accent_purple, fg="white"))
        version_btn.bind("<Leave>", lambda e: version_btn.config(bg=self.bg_light, fg=self.text_color))

        progress_container = tk.Frame(self.game_tab, bg=self.bg_dark)
        progress_container.pack(fill=tk.X, padx=60, pady=20)

        progress_bg = tk.Frame(progress_container, bg=self.bg_medium, height=10)
        progress_bg.pack(fill=tk.X, pady=15)

        self.progress_bar = ttk.Progressbar(
            progress_bg,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.BOTH, expand=True)

        status_frame = tk.Frame(progress_container, bg=self.bg_dark)
        status_frame.pack()

        self.status_icon = tk.Label(
            status_frame,
            text="●",
            font=("Segoe UI", 14),
            bg=self.bg_dark,
            fg=self.accent_green
        )
        self.status_icon.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            status_frame,
            textvariable=self.status_text,
            font=("Segoe UI", 11),
            bg=self.bg_dark,
            fg=self.text_dim
        ).pack(side=tk.LEFT)

    def setup_news_tab(self):
        """Setup the news and patches tab"""

        header_frame = tk.Frame(self.news_tab, bg=self.bg_medium, height=100)
        header_frame.pack(fill=tk.X, padx=25, pady=25)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="📰 Game Updates & News",
            font=("Segoe UI", 24, "bold"),
            bg=self.bg_medium,
            fg=self.text_color
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        tk.Label(
            header_frame,
            text="Stay up to date with the latest patches and updates",
            font=("Segoe UI", 10),
            bg=self.bg_medium,
            fg=self.text_dim
        ).pack(anchor=tk.W, padx=20)

        patches_container = tk.Frame(self.news_tab, bg=self.bg_dark)
        patches_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)

        patches_canvas = tk.Canvas(
            patches_container,
            bg=self.bg_dark,
            highlightthickness=0
        )

        patches_scrollbar = ttk.Scrollbar(
            patches_container,
            orient="vertical",
            command=patches_canvas.yview
        )

        self.patches_frame = tk.Frame(patches_canvas, bg=self.bg_dark)
        self.patches_frame.bind(
            "<Configure>",
            lambda e: patches_canvas.configure(scrollregion=patches_canvas.bbox("all"))
        )

        patches_canvas.create_window((0, 0), window=self.patches_frame, anchor="nw", width=750)
        patches_canvas.configure(yscrollcommand=patches_scrollbar.set)

        patches_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        patches_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        patches_canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", patches_canvas))
        patches_canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))

        self.load_patches()

    def load_patches(self):
        """Load and display patches from XML"""
        def fetch_and_display():
            try:

                for widget in self.patches_frame.winfo_children():
                    widget.destroy()

                xml_data = self.network.fetch_text(PATCHES_URL)
                if not xml_data:
                    self.show_patch_error("Failed to load patches")
                    return

                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_data)
                patches = root.findall('.//patch')

                if not patches:
                    self.show_patch_error("No patches found")
                    return

                for i, patch in enumerate(patches):
                    title = patch.find('Title')
                    text = patch.find('Text')
                    link = patch.find('Link')

                    if title is not None and text is not None:
                        self.create_patch_card(
                            title.text or "Unknown Version",
                            text.text or "No description",
                            link.text if link is not None and link.text else None,
                            i
                        )

            except Exception as e:
                logging.error(f"Failed to load patches: {e}")
                self.show_patch_error(f"Error loading patches: {str(e)}")

        threading.Thread(target=fetch_and_display, daemon=True).start()

    def create_patch_card(self, title, description, link, index):
        """Create a patch card"""

        colors = [self.accent_blue, self.accent_purple, self.accent_green, self.accent_orange]
        accent = colors[index % len(colors)]

        card = tk.Frame(
            self.patches_frame,
            bg=self.bg_medium,
            highlightbackground=accent,
            highlightthickness=2
        )
        card.pack(fill=tk.X, padx=10, pady=8)

        content_frame = tk.Frame(card, bg=self.bg_medium)
        content_frame.pack(fill=tk.BOTH, padx=20, pady=15)

        title_frame = tk.Frame(content_frame, bg=self.bg_medium)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        badge = tk.Label(
            title_frame,
            text=f"{title}",
            font=("Segoe UI", 11, "bold"),
            bg=accent,
            fg="white",
            padx=12,
            pady=5
        )
        badge.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            title_frame,
            text="Shadow Slime Update",
            font=("Segoe UI", 10),
            bg=self.bg_medium,
            fg=self.text_dim
        ).pack(side=tk.LEFT)

        tk.Label(
            content_frame,
            text=description,
            font=("Segoe UI", 11),
            bg=self.bg_medium,
            fg=self.text_color,
            wraplength=650,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 10))

        if link and link.strip():
            link_btn = tk.Button(
                content_frame,
                text="📄 Read More",
                font=("Segoe UI", 9, "bold"),
                bg=self.bg_light,
                fg=accent,
                activebackground=accent,
                activeforeground="white",
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda: os.system(f"start {link}"),
                padx=15,
                pady=8,
                borderwidth=0
            )
            link_btn.pack(anchor=tk.W)

            link_btn.bind("<Enter>", lambda e: link_btn.config(bg=accent, fg="white"))
            link_btn.bind("<Leave>", lambda e: link_btn.config(bg=self.bg_light, fg=accent))

    def show_patch_error(self, message):
        """Show error message in patches tab"""
        error_frame = tk.Frame(self.patches_frame, bg=self.bg_dark)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=40)

        tk.Label(
            error_frame,
            text="⚠️",
            font=("Segoe UI", 48),
            bg=self.bg_dark,
            fg=self.accent_red
        ).pack(pady=20)

        tk.Label(
            error_frame,
            text=message,
            font=("Segoe UI", 14),
            bg=self.bg_dark,
            fg=self.text_dim
        ).pack()

    def create_hover_button(self, parent, text, command, accent_color):
        """Create a button with hover animation"""
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_light,
            fg=self.text_color,
            activebackground=accent_color,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=command,
            anchor=tk.W,
            padx=15,
            pady=10,
            borderwidth=0
        )

        def on_enter(e):
            btn.config(bg=accent_color, fg="white")

        def on_leave(e):
            btn.config(bg=self.bg_light, fg=self.text_color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=self.bg_medium,
            background=self.accent_green,
            borderwidth=0,
            thickness=10
        )

        style.configure(
            "TScrollbar",
            background=self.bg_medium,
            troughcolor=self.bg_dark,
            borderwidth=0,
            arrowcolor=self.text_color
        )

    def create_menu_section(self, title: str, items: List[Tuple[str, callable, str]]):
        """Create a menu section with animated buttons"""
        section_frame = tk.Frame(self.sidebar_frame, bg=self.bg_medium)
        section_frame.pack(fill=tk.X, padx=15, pady=10)

        header = tk.Label(
            section_frame,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_medium,
            fg=self.text_dim,
            anchor=tk.W
        )
        header.pack(anchor=tk.W, pady=(0, 8))

        for text, command, accent in items:
            btn = self.create_hover_button(section_frame, text, command, accent)
            btn.pack(fill=tk.X, pady=2)

        self.sidebar_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        social_frame = tk.Frame(self.sidebar_frame, bg=self.bg_medium)
        social_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20)

        self.create_hover_button(
            social_frame,
            "🎮 Join Discord",
            lambda: os.system(f"start {DISCORD_INVITE}"),
            self.accent_purple
        ).pack(fill=tk.X, pady=3)

        self.create_hover_button(
            social_frame,
            "📺 YouTube Channel",
            lambda: os.system("start https://www.youtube.com/@ShadowSlimeDEV"),
            self.accent_red
        ).pack(fill=tk.X, pady=3)

        self.content_frame = tk.Frame(self.root, bg=self.bg_dark)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(self.content_frame, bg=self.bg_medium, height=100)
        header_frame.pack(fill=tk.X, padx=25, pady=25)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Game Status",
            font=("Segoe UI", 22, "bold"),
            bg=self.bg_medium,
            fg=self.text_color
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        tk.Label(
            header_frame,
            text="Manage your Among Us installation",
            font=("Segoe UI", 10),
            bg=self.bg_medium,
            fg=self.text_dim
        ).pack(anchor=tk.W, padx=20)

        card_frame = tk.Frame(self.content_frame, bg=self.bg_medium)
        card_frame.pack(fill=tk.X, padx=25, pady=10)

        info_container = tk.Frame(card_frame, bg=self.bg_medium)
        info_container.pack(padx=30, pady=25)

        current_frame = tk.Frame(info_container, bg=self.bg_light)
        current_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")

        inner_current = tk.Frame(current_frame, bg=self.bg_light)
        inner_current.pack(padx=20, pady=15)

        tk.Label(
            inner_current,
            text="📦 Installed Version",
            font=("Segoe UI", 10),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)

        tk.Label(
            inner_current,
            textvariable=self.current_version,
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_light,
            fg=self.accent_green
        ).pack(anchor=tk.W, pady=(5, 0))

        latest_frame = tk.Frame(info_container, bg=self.bg_light)
        latest_frame.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        inner_latest = tk.Frame(latest_frame, bg=self.bg_light)
        inner_latest.pack(padx=20, pady=15)

        tk.Label(
            inner_latest,
            text="🌐 Latest Version",
            font=("Segoe UI", 10),
            bg=self.bg_light,
            fg=self.text_dim
        ).pack(anchor=tk.W)

        tk.Label(
            inner_latest,
            textvariable=self.latest_version,
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_light,
            fg=self.accent_blue
        ).pack(anchor=tk.W, pady=(5, 0))

        button_container = tk.Frame(self.content_frame, bg=self.bg_dark)
        button_container.pack(pady=25)

        self.main_button = tk.Button(
            button_container,
            text="INSTALL GAME",
            font=("Segoe UI", 15, "bold"),
            bg=self.accent_green,
            fg="white",
            activebackground="#00b359",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.main_action,
            padx=50,
            pady=18,
            borderwidth=0
        )
        self.main_button.pack()

        self.main_button.bind("<Enter>", lambda e: self.main_button.config(bg="#00b359"))
        self.main_button.bind("<Leave>", lambda e: self.main_button.config(bg=self.accent_green))

        progress_container = tk.Frame(self.content_frame, bg=self.bg_dark)
        progress_container.pack(fill=tk.X, padx=60, pady=15)

        progress_bg = tk.Frame(progress_container, bg=self.bg_medium, height=8)
        progress_bg.pack(fill=tk.X, pady=10)

        self.progress_bar = ttk.Progressbar(
            progress_bg,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.BOTH, expand=True)

        status_frame = tk.Frame(progress_container, bg=self.bg_dark)
        status_frame.pack()

        self.status_icon = tk.Label(
            status_frame,
            text="●",
            font=("Segoe UI", 12),
            bg=self.bg_dark,
            fg=self.accent_green
        )
        self.status_icon.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(
            status_frame,
            textvariable=self.status_text,
            font=("Segoe UI", 10),
            bg=self.bg_dark,
            fg=self.text_dim
        ).pack(side=tk.LEFT)

        kebab_frame = tk.Frame(self.content_frame, bg=self.bg_dark)
        kebab_frame.pack(side=tk.BOTTOM, anchor=tk.SE, padx=25, pady=25)

        self.kebab_btn = tk.Button(
            kebab_frame,
            text="⋮",
            font=("Segoe UI", 24, "bold"),
            bg=self.bg_light,
            fg=self.text_color,
            activebackground=self.bg_hover,
            activeforeground=self.text_color,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.show_kebab_menu,
            width=2,
            height=1,
            borderwidth=0
        )
        self.kebab_btn.pack()

        self.kebab_btn.bind("<Enter>", lambda e: self.kebab_btn.config(bg=self.bg_hover))
        self.kebab_btn.bind("<Leave>", lambda e: self.kebab_btn.config(bg=self.bg_light))

        self.setup_styles()

    def _on_mousewheel(self, event):
        """Unified mousewheel handler for scrollable canvases"""
        try:
            canvas = getattr(self, "_active_scroll_canvas", None) or getattr(self, "sidebar_canvas", None)
            if not canvas:
                return

            delta = int(-1 * (event.delta / 120))
            canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def create_hover_button(self, parent, text, command, accent_color):
        """Create a button with hover animation"""
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_light,
            fg=self.text_color,
            activebackground=accent_color,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=command,
            anchor=tk.W,
            padx=15,
            pady=10,
            borderwidth=0
        )

        def on_enter(e):
            btn.config(bg=accent_color, fg="white")

        def on_leave(e):
            btn.config(bg=self.bg_light, fg=self.text_color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=self.bg_medium,
            background=self.accent_green,
            borderwidth=0,
            thickness=8
        )

        style.configure(
            "TScrollbar",
            background=self.bg_medium,
            troughcolor=self.bg_dark,
            borderwidth=0,
            arrowcolor=self.text_color
        )

    def create_menu_section(self, title: str, items: List[Tuple[str, callable, str]]):
        """Create a menu section with animated buttons"""
        section_frame = tk.Frame(self.sidebar_frame, bg=self.bg_medium)
        section_frame.pack(fill=tk.X, padx=15, pady=10)

        header = tk.Label(
            section_frame,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_medium,
            fg=self.text_dim,
            anchor=tk.W
        )
        header.pack(anchor=tk.W, pady=(0, 8))

        for text, command, accent in items:
            btn = self.create_hover_button(section_frame, text, command, accent)
            btn.pack(fill=tk.X, pady=2)

    def load_initial_data(self):
        """Load initial data in background"""
        def load():

            version = self.config.get_version()
            if version:
                self.current_version.set(version)
                self.update_main_button()

            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version.set(latest)
                self.update_main_button()

            if self.config.settings.get("discord_rpc"):
                self.discord.connect()

        threading.Thread(target=load, daemon=True).start()

    def update_main_button(self):
        """Update the main button based on game state with smooth color transitions"""
        current = self.current_version.get()
        latest = self.latest_version.get()
        game_path = self.config.get_game_path()

        if current == "Not Installed" or not game_path or not (game_path / "Among Us.exe").exists():
            self.main_button.config(text="INSTALL GAME", bg=self.accent_green)
            self.main_button.bind("<Enter>", lambda e: self.main_button.config(bg="#00b359"))
            self.main_button.bind("<Leave>", lambda e: self.main_button.config(bg=self.accent_green))
        elif current != latest and latest != "Checking...":
            self.main_button.config(text="UPDATE AVAILABLE", bg=self.accent_blue)
            self.main_button.bind("<Enter>", lambda e: self.main_button.config(bg="#007acc"))
            self.main_button.bind("<Leave>", lambda e: self.main_button.config(bg=self.accent_blue))
        else:
            self.main_button.config(text="LAUNCH GAME", bg=self.accent_green)
            self.main_button.bind("<Enter>", lambda e: self.main_button.config(bg="#00b359"))
            self.main_button.bind("<Leave>", lambda e: self.main_button.config(bg=self.accent_green))

    def main_action(self):
        """Main button action"""
        button_text = self.main_button.cget("text")

        if "INSTALL" in button_text:
            self.download_latest()
        elif "UPDATE" in button_text:
            self.download_latest()
        elif "LAUNCH" in button_text:
            self.launch_game()

    def show_kebab_menu(self):
        """Show kebab menu with additional options"""
        menu = tk.Menu(self.root, tearoff=0, bg=self.bg_light, fg=self.text_color)
        menu.add_command(label="Verify Game Files", command=self.verify_files)
        menu.add_command(label="View Logs", command=self.view_logs)
        menu.add_separator()
        menu.add_command(label="About", command=self.show_about)

        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()

    def download_latest(self):
        """Download latest game version"""
        def download():
            self.status_text.set("Preparing download...")
            self.main_button.config(state=tk.DISABLED)

            latest = self.latest_version.get()
            if latest == "Checking...":
                latest = self.network.fetch_text(VERSION_URL)
                if not latest:
                    self.status_text.set("Failed to fetch version info")
                    self.main_button.config(state=tk.NORMAL)
                    return

            game_path = self.config.get_game_path()
            if not game_path:
                game_path = self.select_install_location()
                if not game_path:
                    self.status_text.set("Installation cancelled")
                    self.main_button.config(state=tk.NORMAL)
                    return

            url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest}/app.zip"
            zip_file = Path("game.zip")

            self.status_text.set(f"Downloading version {latest}...")

            def progress(current, total, speed):
                percent = (current / total * 100) if total else 0
                self.progress_var.set(percent)
                speed_str = FileManager.format_size(speed) + "/s"
                self.status_text.set(f"Downloading: {percent:.1f}% - {speed_str}")

            if not self.network.download_file(url, zip_file, progress):
                self.status_text.set("Download failed!")
                self.main_button.config(state=tk.NORMAL)
                return

            self.status_text.set("Extracting files...")
            game_path.mkdir(parents=True, exist_ok=True)

            def extract_progress(current, total):
                percent = (current / total * 100) if total else 0
                self.progress_var.set(percent)
                self.status_text.set(f"Extracting: {percent:.1f}%")

            if not FileManager.extract_zip(zip_file, game_path, extract_progress):
                self.status_text.set("Extraction failed!")
                self.main_button.config(state=tk.NORMAL)
                return

            FileManager.safe_delete(zip_file)
            self.config.set_version(latest)
            self.config.set_game_path(game_path)
            self.current_version.set(latest)

            self.progress_var.set(100)
            self.status_text.set("Installation complete!")
            self.main_button.config(state=tk.NORMAL)
            self.update_main_button()

            messagebox.showinfo("Success", f"Game version {latest} installed successfully!")

        threading.Thread(target=download, daemon=True).start()

    def check_updates(self):
        """Check for game updates"""
        def check():
            self.status_text.set("Checking for updates...")
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version.set(latest)
                current = self.current_version.get()
                if current == latest:
                    messagebox.showinfo("Up to Date", "You have the latest version!")
                else:
                    messagebox.showinfo("Update Available", f"New version available: {latest}")
                self.update_main_button()
            else:
                messagebox.showerror("Error", "Failed to check for updates")
            self.status_text.set("Ready")

        threading.Thread(target=check, daemon=True).start()

    def install_specific(self):
        """Install specific game version"""
        versions_window = tk.Toplevel(self.root)
        versions_window.title("Install Specific Version")
        versions_window.geometry("400x500")
        versions_window.configure(bg=self.bg_dark)
        versions_window.transient(self.root)

        tk.Label(
            versions_window,
            text="Available Versions",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_dark,
            fg=self.text_color
        ).pack(pady=10)

        listbox_frame = tk.Frame(versions_window, bg=self.bg_dark)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            listbox_frame,
            bg=self.bg_medium,
            fg=self.text_color,
            selectbackground=self.accent_blue,
            selectforeground="white",
            font=("Segoe UI", 10),
            yscrollcommand=scrollbar.set
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        versions = self.network.get_releases()
        for v in versions:
            listbox.insert(tk.END, v.version)

        def install_selected():
            selection = listbox.curselection()
            if selection:
                selected = versions[selection[0]]
                versions_window.destroy()
                self.install_version(selected)

        ttk.Button(
            versions_window,
            text="Install Selected",
            command=install_selected
        ).pack(pady=10)

    def install_version(self, version: GameVersion):
        """Install a specific version"""
        def install():
            game_path = self.config.get_game_path() or self.select_install_location()
            if not game_path:
                return

            self.status_text.set(f"Installing version {version.version}...")
            self.main_button.config(state=tk.DISABLED)

            zip_file = Path("game.zip")

            def progress(current, total, speed):
                percent = (current / total * 100) if total else 0
                self.progress_var.set(percent)
                self.status_text.set(f"Downloading: {percent:.1f}%")

            if self.network.download_file(version.url, zip_file, progress):
                game_path.mkdir(parents=True, exist_ok=True)
                FileManager.extract_zip(zip_file, game_path)
                FileManager.safe_delete(zip_file)
                self.config.set_version(version.version)
                self.config.set_game_path(game_path)
                self.current_version.set(version.version)
                messagebox.showinfo("Success", f"Version {version.version} installed!")
            else:
                messagebox.showerror("Error", "Installation failed!")

            self.main_button.config(state=tk.NORMAL)
            self.status_text.set("Ready")
            self.update_main_button()

        threading.Thread(target=install, daemon=True).start()

    def launch_game(self):
        """Launch the game"""
        game_path = self.config.get_game_path()
        if not game_path:
            messagebox.showerror("Error", "Game not installed!")
            return

        exe_path = game_path / "Among Us.exe"
        if not exe_path.exists():
            messagebox.showerror("Error", "Game executable not found!")
            return

        try:
            subprocess.Popen([str(exe_path)], cwd=str(game_path))
            self.status_text.set("Game launched!")
            if self.config.settings.get("minimize_on_game_start"):
                self.root.iconify()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch game: {e}")

    def install_aunlocker(self):
        """Install AUnlocker"""
        version = self.config.get_version()
        game_path = self.config.get_game_path()

        if not version or not game_path:
            messagebox.showerror("Error", "Game not installed!")
            return

        def install():
            self.status_text.set("Checking AUnlocker compatibility...")
            data = self.network.fetch_text(AUNLOCKER_JSON_URL)

            if not data:
                messagebox.showerror("Error", "Failed to fetch AUnlocker data")
                return

            try:
                versions = json.loads(data).get("versions", [])
                for entry in versions:
                    if entry["version"] == version:
                        zip_path = Path("AUnlocker.zip")
                        self.status_text.set("Downloading AUnlocker...")
                        if self.network.download_file(entry["link"], zip_path):
                            FileManager.extract_zip(zip_path, game_path)
                            FileManager.safe_delete(zip_path)
                            messagebox.showinfo("Success", "AUnlocker installed!")
                            self.status_text.set("Ready")
                            return
                messagebox.showwarning("Not Found", "No compatible AUnlocker for this version")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid AUnlocker data")

            self.status_text.set("Ready")

        threading.Thread(target=install, daemon=True).start()

    def create_shortcut(self):
        """Create desktop shortcut"""
        game_path = self.config.get_game_path()
        if not game_path:
            messagebox.showerror("Error", "Game not installed!")
            return

        exe = game_path / "Among Us.exe"
        version = self.config.get_version()

        try:
            desktop = Path.home() / "Desktop"
            shortcut_path = desktop / f"Among Us {version}.lnk"
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(exe)
            shortcut.WorkingDirectory = str(game_path)
            shortcut.IconLocation = str(exe)
            shortcut.save()
            messagebox.showinfo("Success", "Shortcut created on desktop!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create shortcut: {e}")

    def open_folder(self):
        """Open game folder"""
        game_path = self.config.get_game_path()
        if game_path and game_path.exists():
            os.startfile(game_path)
        else:
            messagebox.showerror("Error", "Game folder not found!")

    def change_location(self):
        """Change game installation location"""
        new_path = self.select_install_location()
        if not new_path:
            return

        old_path = self.config.get_game_path()
        if old_path and old_path.exists():
            if messagebox.askyesno("Move Files", "Move existing game files to new location?"):
                try:
                    shutil.move(str(old_path), str(new_path))
                    messagebox.showinfo("Success", "Game files moved successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to move files: {e}")

        self.config.set_game_path(new_path)
        messagebox.showinfo("Success", f"Location changed to: {new_path}")

    def show_settings(self):
        """Show settings window with modern design"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x450")
        settings_window.configure(bg=self.bg_dark)
        settings_window.transient(self.root)
        settings_window.resizable(False, False)

        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (450 // 2)
        settings_window.geometry(f"500x450+{x}+{y}")

        header_frame = tk.Frame(settings_window, bg=self.bg_medium, height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="⚙️ Launcher Settings",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_medium,
            fg=self.text_color
        ).pack(anchor=tk.W, padx=25, pady=20)

        container = tk.Frame(settings_window, bg=self.bg_dark)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)

        settings_canvas = tk.Canvas(container, bg=self.bg_dark, highlightthickness=0)
        settings_scrollbar = ttk.Scrollbar(container, orient="vertical", command=settings_canvas.yview)
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

        settings_inner = tk.Frame(settings_canvas, bg=self.bg_dark)
        settings_inner.bind(
            "<Configure>",
            lambda e: settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
        )
        window_id = settings_canvas.create_window((0, 0), window=settings_inner, anchor="nw")

        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        settings_canvas.bind("<Configure>", lambda e: settings_canvas.itemconfig(window_id, width=e.width))

        settings_canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", settings_canvas))
        settings_canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))

        settings = self.config.settings

        options = [
            ("🔄 Auto-update game", "auto_update", "Automatically download game updates"),
            ("🎮 Discord Rich Presence", "discord_rpc", "Show what you're doing on Discord"),
            ("✓ Verify file integrity", "check_integrity", "Check file checksums after download"),
            ("▼ Minimize on game start", "minimize_on_game_start", "Hide launcher when game starts")
        ]

        vars = {}
        for i, (label, key, desc) in enumerate(options):

            option_frame = tk.Frame(settings_inner, bg=self.bg_medium)
            option_frame.pack(fill=tk.X, pady=8)

            var = tk.BooleanVar(value=settings.get(key, False))
            vars[key] = var

            cb_frame = tk.Frame(option_frame, bg=self.bg_medium)
            cb_frame.pack(fill=tk.X, padx=20, pady=15)

            cb = tk.Checkbutton(
                cb_frame,
                text=label,
                variable=var,
                bg=self.bg_medium,
                fg=self.text_color,
                selectcolor=self.bg_light,
                activebackground=self.bg_medium,
                activeforeground=self.text_color,
                font=("Segoe UI", 11, "bold"),
                cursor="hand2",
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0
            )
            cb.pack(anchor=tk.W)

            tk.Label(
                cb_frame,
                text=desc,
                font=("Segoe UI", 9),
                bg=self.bg_medium,
                fg=self.text_dim
            ).pack(anchor=tk.W, padx=(25, 0), pady=(3, 0))

            def on_enter(e, frame=option_frame):
                frame.config(bg=self.bg_light)
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Frame):
                        widget.config(bg=self.bg_light)
                        for child in widget.winfo_children():
                            if hasattr(child, 'config'):
                                try:
                                    child.config(bg=self.bg_light)
                                except:
                                    pass

            def on_leave(e, frame=option_frame):
                frame.config(bg=self.bg_medium)
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Frame):
                        widget.config(bg=self.bg_medium)
                        for child in widget.winfo_children():
                            if hasattr(child, 'config'):
                                try:
                                    child.config(bg=self.bg_medium)
                                except:
                                    pass

            option_frame.bind("<Enter>", on_enter)
            option_frame.bind("<Leave>", on_leave)

        button_frame = tk.Frame(settings_window, bg=self.bg_dark)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=25, pady=20)

        def save_settings():
            for key, var in vars.items():
                settings[key] = var.get()
            self.config.save_settings()

            if settings.get("discord_rpc") and not self.discord.connected:
                self.discord.connect()
            elif not settings.get("discord_rpc") and self.discord.connected:
                self.discord.disconnect()

            messagebox.showinfo("Success", "Settings saved successfully!")
            settings_window.destroy()

        save_btn = tk.Button(
            button_frame,
            text="Save Settings",
            font=("Segoe UI", 12, "bold"),
            bg=self.accent_green,
            fg="white",
            activebackground="#00b359",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=save_settings,
            padx=30,
            pady=12,
            borderwidth=0
        )
        save_btn.pack()

        save_btn.bind("<Enter>", lambda e: save_btn.config(bg="#00b359"))
        save_btn.bind("<Leave>", lambda e: save_btn.config(bg=self.accent_green))

    def reinstall_game(self):
        """Reinstall the game"""
        if not messagebox.askyesno("Confirm", "This will delete and reinstall the game. Continue?"):
            return

        game_path = self.config.get_game_path()
        if game_path and game_path.exists():
            FileManager.safe_delete(game_path)

        self.current_version.set("Not Installed")
        self.download_latest()

    def uninstall_game(self):
        """Uninstall the game"""
        if not messagebox.askyesno("Confirm", "This will remove all game files and launcher data. Continue?"):
            return

        game_path = self.config.get_game_path()
        if game_path and game_path.exists():
            if FileManager.safe_delete(game_path):
                messagebox.showinfo("Success", "Game files removed")
            else:
                messagebox.showerror("Error", "Failed to remove game files")

        if FileManager.safe_delete(self.config.appdata_dir):
            messagebox.showinfo("Success", "Launcher data removed")
        else:
            messagebox.showerror("Error", "Failed to remove launcher data")

        self.current_version.set("Not Installed")
        self.update_main_button()

    def verify_files(self):
        """Verify game files integrity"""
        messagebox.showinfo("Info", "File verification coming soon!")

    def view_logs(self):
        """Open log file"""
        log_file = Path("launcher.log")
        if log_file.exists():
            os.startfile(log_file)
        else:
            messagebox.showinfo("Info", "No log file found")

    def show_about(self):
        """Show about dialog"""
        about_text = f"""Among Us Launcher v{LAUNCHER_VERSION}

Made by Shadow Slime

A modern launcher for Among Us
with auto-updates and mod support.

© 2024 Shadow Slime Productions"""
        messagebox.showinfo("About", about_text)

    def select_install_location(self) -> Optional[Path]:
        """Show folder selection dialog"""
        folder = filedialog.askdirectory(
            title="Select Among Us Installation Folder",
            initialdir=str(Path.cwd())
        )
        return Path(folder) if folder else None

    def run(self):
        """Start the GUI"""
        self.root.mainloop()
        if self.discord.connected:
            self.discord.disconnect()

def check_launcher_update(network: NetworkManager) -> bool:
    """Check for launcher updates before starting"""
    try:
        print(f"{Colors.INFO}Checking for launcher updates...{Colors.RESET}")
        latest = network.fetch_text(LAUNCHER_VERSION_URL)

        if latest and latest != LAUNCHER_VERSION:
            print(f"{Colors.WARNING}Launcher update available: {latest} (current: {LAUNCHER_VERSION}){Colors.RESET}")
            response = input(f"{Colors.HIGHLIGHT}Download and install update? (yes/no): {Colors.RESET}").lower()

            if response in ['yes', 'y']:
                new_exe = Path(f"AmongUsLauncher_{latest}.exe")
                print(f"{Colors.INFO}Downloading update...{Colors.RESET}")

                if network.download_file(LAUNCHER_DOWNLOAD_URL, new_exe):
                    print(f"{Colors.SUCCESS}Update downloaded! Please run the new launcher.{Colors.RESET}")
                    subprocess.Popen([str(new_exe)])
                    return False
                else:
                    print(f"{Colors.ERROR}Update download failed. Continuing with current version.{Colors.RESET}")
        else:
            print(f"{Colors.SUCCESS}Launcher is up to date{Colors.RESET}")

        return True
    except Exception as e:
        logging.error(f"Launcher update check failed: {e}")
        print(f"{Colors.WARNING}Could not check for updates. Continuing...{Colors.RESET}")
        return True

def is_admin():
    """Check if running with admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    """Request admin privileges if not already admin"""
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                f'"{os.path.abspath(__file__)}"',
                None, 1
            )
            sys.exit()
        except Exception as e:
            logging.error(f"Failed to request admin: {e}")
            print(f"{Colors.ERROR}Failed to request administrator privileges.{Colors.RESET}")
            return False
    return True

if __name__ == "__main__":
    print(f"{Colors.INFO}Starting Among Us Launcher...{Colors.RESET}\n")

    while True:
        try:

            config = Config()
            network = NetworkManager()

            if not network.is_connected():
                print(f"{Colors.ERROR}No internet connection detected!{Colors.RESET}")
                print(f"{Colors.WARNING}Please connect to the internet and restart the launcher.{Colors.RESET}")
                input("\nPress Enter to exit...")
                break

            if not check_launcher_update(network):
                break

            print(f"\n{Colors.SUCCESS}Launching GUI...{Colors.RESET}\n")
            time.sleep(0.5)
            app = ModernUI(config, network)
            app.run()

            logging.info("Launcher closed normally")
            break

        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}[!] Launcher interrupted by user{Colors.RESET}")
            logging.info("Launcher interrupted by user")
            break

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.critical(error_msg, exc_info=True)
            print(f"\n{Colors.ERROR}╔════════════════════════════════════════════════╗{Colors.RESET}")
            print(f"{Colors.ERROR}║          CRITICAL ERROR OCCURRED               ║{Colors.RESET}")
            print(f"{Colors.ERROR}╚════════════════════════════════════════════════╝{Colors.RESET}")
            print(f"{Colors.ERROR}Error: {str(e)}{Colors.RESET}")
            print(f"{Colors.INFO}Full error details saved to launcher.log{Colors.RESET}\n")

            retry = input(f"{Colors.WARNING}Press Enter to restart launcher, or type 'exit' to quit: {Colors.RESET}").strip().lower()
            if retry == 'exit':
                logging.info("User chose to exit after error")
                break

            print(f"\n{Colors.INFO}Restarting launcher...{Colors.RESET}\n")

    print(f"\n{Colors.INFO}═══════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.GOLD}Thanks for using Among Us Shadow Slime Launcher!{Colors.RESET}")
    print(f"{Colors.INFO}═══════════════════════════════════════════════════{Colors.RESET}\n")
    input("Press Enter to close...")
