import os
import requests
import zipfile
import sys
from colorama import init, Fore, Style
import time
import subprocess
import ctypes
import winshell
from win32com.client import Dispatch
import shutil
import stat
import json
try:
    from pypresence import Presence
except ImportError:
    Presence = None

init(autoreset=True)

def self_update_logic():
    """Handle self-update if launched with --update-self argument."""
    if len(sys.argv) > 1 and sys.argv[1] == "--update-self":
        old_launcher = os.path.join(os.getcwd(), "AmongUsLauncher.exe")
        new_launcher = os.path.join(os.getcwd(), "AmongUsLauncher_new.exe")

        for _ in range(10):
            try:
                os.remove(old_launcher)
                break
            except PermissionError:
                time.sleep(1)

        shutil.move(new_launcher, old_launcher)

        subprocess.Popen([old_launcher])
        sys.exit()

self_update_logic()

def is_admin():
    """Check if the script is running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def format_size(bytes):
    """Convert bytes to a human-readable string (KB, MB, GB)."""
    if bytes >= 1024 ** 3:
        return f"{bytes / 1024 ** 3:.2f} GB"
    elif bytes >= 1024 ** 2:
        return f"{bytes / 1024 ** 2:.2f} MB"
    elif bytes >= 1024:
        return f"{bytes / 1024:.2f} KB"
    else:
        return f"{bytes} B"

def download_file(url, local_filename):
    """Download a file from a given URL with an advanced progress bar."""
    try:
        start_time = time.time()
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            chunk_size = 8192
            with open(local_filename, 'wb') as f:
                downloaded_size = 0
                while True:
                    chunk = r.raw.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    percent = int(100 * downloaded_size / total_size) if total_size else 0
                    done = int(50 * downloaded_size / total_size) if total_size else 0
                    elapsed_time = time.time() - start_time
                    speed = (downloaded_size / elapsed_time) if elapsed_time > 0 else 0  
                    speed_mb = speed / (1024 * 1024)
                    size_str = f"{format_size(downloaded_size)}/{format_size(total_size)}"
                    sys.stdout.write(
                        f"\r[{Fore.GREEN}{'=' * done}{' ' * (50-done)}{Fore.RESET}] {percent}% "
                        f"| {size_str} | Speed: {speed_mb:.2f} MB/s"
                    )
                    sys.stdout.flush()
        print("\n")
        print_colored("[^] Download complete!", "green")
    except Exception as e:
        print_colored(f"[ERROR] Failed to download file: {str(e)}", "red")

def extract_zip(file_path, extract_to):
    """Extract a zip file to a given directory."""
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            for i, file in enumerate(zip_ref.infolist()):
                zip_ref.extract(file, extract_to)
                done = int(50 * (i + 1) / total_files)
                percent = int(100 * (i + 1) / total_files)
                sys.stdout.write(f"\r[{Fore.BLUE}{'=' * done}{' ' * (50-done)}{Fore.RESET}] {percent}% Extracting")
                sys.stdout.flush()
        print("\n")
    except Exception as e:
        print_colored(f"[ERROR] Failed to extract zip file: {str(e)}", "red")

def print_colored(text, color):
    """Print text in a specified color."""
    colors = {
        "yellow": Fore.YELLOW,
        "green": Fore.GREEN,
        "blue": Fore.BLUE,
        "red": Fore.RED,
        "purple": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "gold": Fore.YELLOW + Style.BRIGHT,  
        "reset": Style.RESET_ALL
    }
    if color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(f"{Fore.RED}[ERROR] Unknown color: {color}{Style.RESET_ALL}")

def print_boxed(text, color):
    """Print text in a boxed format."""
    border = "+" + "-" * (len(text) + 2) + "+"
    print(f"{color}{border}{Style.RESET_ALL}")
    print(f"{color}| {text} |{Style.RESET_ALL}")
    print(f"{color}{border}{Style.RESET_ALL}")

def get_latest_version():
    """Fetch the latest version of the game."""
    version_url = "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/main/Version.txt"
    try:
        response = requests.get(version_url)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print_colored(f"[ERROR] Failed to fetch latest version: {str(e)}", "red")
        return None

def read_version_file(file_path):
    """Read the current version from a file."""
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def create_shortcut(path, target='', wDir='', icon=''):
    """Create a desktop shortcut."""
    try:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = wDir
        if icon:
            shortcut.IconLocation = icon
        shortcut.save()
    except Exception as e:
        print(f"[ERROR] Failed to create desktop shortcut: {str(e)}")

def show_options():
    print(f"\n{Fore.CYAN}============================== OPTIONS ============================== {Style.RESET_ALL}")
    print_boxed("Press 1 to run the game", Fore.CYAN)
    print_boxed("Press 2 to exit", Fore.RED)
    print_boxed("Press 3 to visit our YouTube channel", Fore.BLUE)
    print_boxed("Press 4 to join our Discord server", Fore.GREEN)

def show_options_compact():
    print(f"\n{Fore.CYAN}==== OPTIONS ===={Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}[1]{Style.RESET_ALL} Run Game  "
        f"{Fore.YELLOW}[2]{Style.RESET_ALL} Exit  "
        f"{Fore.YELLOW}[3]{Style.RESET_ALL} YouTube  "
        f"{Fore.YELLOW}[4]{Style.RESET_ALL} Discord  "
        f"{Fore.YELLOW}[5]{Style.RESET_ALL} Create a Shortcut  "
        f"{Fore.YELLOW}[6]{Style.RESET_ALL} Open Folder  "
        f"{Fore.YELLOW}[7]{Style.RESET_ALL} Reinstall Among Us  "
        f"{Fore.RED}[8] Uninstall{Style.RESET_ALL}  "
        f"{Fore.YELLOW}[9]{Style.RESET_ALL} Install AUnlocker  "
        f"{Fore.YELLOW}[10]{Style.RESET_ALL} Change Game Folder Location "
        f"{Fore.YELLOW}[11]{Style.RESET_ALL} Install Specific Game Version "
    )

def get_appdata_version_file():
    """Return the path to the version file in AppData."""
    appdata_dir = os.path.join(os.environ["APPDATA"], "AmongUsShadowSlime")
    os.makedirs(appdata_dir, exist_ok=True)
    return os.path.join(appdata_dir, "current_version.txt")

def get_appdata_game_path_file():
    """Return the path to the game path file in AppData."""
    appdata_dir = os.path.join(os.environ["APPDATA"], "AmongUsShadowSlime")
    os.makedirs(appdata_dir, exist_ok=True)
    return os.path.join(appdata_dir, "game_path.txt")

LAUNCHER_VERSION = "1.2"
LAUNCHER_VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/LauncherVersion.txt"
LAUNCHER_DOWNLOAD_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AmongUsLauncher.exe"

def check_launcher_update():
    """Check for launcher updates and update if needed."""
    try:
        response = requests.get(LAUNCHER_VERSION_URL)
        response.raise_for_status()
        latest_version = response.text.strip()
        if latest_version != LAUNCHER_VERSION:
            print_colored(f"[!] Launcher update available: {latest_version} (current: {LAUNCHER_VERSION})", "yellow")
            new_launcher = f"AmongUsLauncher_{latest_version}.exe"
            print_colored("[*] Downloading new launcher...", "green")
            download_file(LAUNCHER_DOWNLOAD_URL, new_launcher)
            print_colored("[*] Launching updated launcher...", "blue")
            subprocess.Popen([sys.executable, new_launcher])
            print_colored("[*] Exiting old launcher...", "red")
            sys.exit()
        else:
            print_colored("[#] Launcher is up to date.", "green")
    except Exception as e:
        print_colored(f"[ERROR] Failed to check/update launcher: {str(e)}", "red")

def save_game_path(path):
    """Save the game folder path to AppData."""
    with open(get_appdata_game_path_file(), "w") as f:
        f.write(path)

def load_game_path():
    """Load the game folder path from AppData."""
    try:
        with open(get_appdata_game_path_file(), "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

def force_remove_readonly(func, path, excinfo):

    os.chmod(path, stat.S_IWRITE)
    func(path)

def get_available_game_versions(repo="jogamerforgames2021/AmongUsLauncherNew"):
    """Fetch all releases and their app.zip download URLs from GitHub."""
    url = f"https://api.github.com/repos/{repo}/releases"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        releases = response.json()
        versions = []
        for release in releases:
            version = release.get("tag_name")
            for asset in release.get("assets", []):
                if asset["name"] == "app.zip":
                    versions.append({
                        "version": version,
                        "url": asset["browser_download_url"]
                    })
        return versions
    except Exception as e:
        print_colored(f"[ERROR] Failed to fetch game versions: {e}", "red")
        return []

def fetch_shadow_message():
    """Fetch a message from Shadow from a remote URL."""
    url = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/message.txt"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print_colored(f"[ERROR] Failed to fetch message from Shadow: {e}", "red")
        return None

def start_discord_rich_presence():
    """Start Discord Rich Presence if pypresence is available."""
    if Presence is None:
        print_colored("[!] Discord Rich Presence not available. Install with 'pip install pypresence'", "yellow")
        return None
    try:
        client_id = "1378503147768647821"  
        RPC = Presence(client_id)
        RPC.connect()
        RPC.update(
            state="In the Launcher",
            details="Browsing Among Us Shadow Slime",
            large_image="amongus",  
            large_text="Among Us Shadow Slime Launcher"
        )
        return RPC
    except Exception as e:
        print_colored(f"[ERROR] Failed to start Discord Rich Presence: {e}", "red")
        return None

def install_aunlocker(game_version, app_dir):
    """Install AUnlocker for the current game version if available."""
    json_url = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AUnlockerStuff/Versions.json"
    try:
        print_colored("[*] Checking for AUnlocker compatibility...", "yellow")
        response = requests.get(json_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        for entry in data.get("versions", []):
            if entry["version"] == game_version:
                unlocker_url = entry["link"]
                zip_name = "AUnlocker.zip"
                print_colored(f"[*] Found AUnlocker for version {game_version}. Downloading...", "green")
                download_file(unlocker_url, zip_name)
                print_colored("[#] Extracting AUnlocker...", "blue")
                extract_zip(zip_name, app_dir)
                os.remove(zip_name)
                print_colored("[^] AUnlocker installed successfully!", "green")
                return
        print_colored("[!] No compatible AUnlocker found for your game version.", "red")
    except Exception as e:
        print_colored(f"[ERROR] Failed to install AUnlocker: {e}", "red")

def change_game_folder_location(app_dir, executable_path, current_version_file):
    """Change the game folder location and move files using a folder selection dialog."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()  
    print_colored("[*] Please select the new folder for Among Us.", "cyan")
    new_path = filedialog.askdirectory(title="Select New Among Us Folder")
    root.destroy()
    if not new_path:
        print_colored("[!] No folder selected. Operation cancelled.", "yellow")
        return app_dir, executable_path
    new_path = os.path.abspath(new_path)
    if new_path == app_dir:
        print_colored("[!] New path is the same as current path.", "yellow")
        return app_dir, executable_path
    try:
        os.makedirs(new_path, exist_ok=True)

        for item in os.listdir(app_dir):
            s = os.path.join(app_dir, item)
            d = os.path.join(new_path, item)
            shutil.move(s, d)
        print_colored(f"[#] Game files moved to: {new_path}", "green")
        save_game_path(new_path)
        executable_path = os.path.join(new_path, "Among Us.exe")
        app_dir = new_path
        return app_dir, executable_path
    except Exception as e:
        print_colored(f"[ERROR] Failed to move game files: {e}", "red")
        return app_dir, executable_path

def main():
    print_colored("[DEBUG] Launcher started!", "cyan")
    check_launcher_update()
    print(f"{Fore.CYAN}========== AMONG US GAME LAUNCHER v{LAUNCHER_VERSION} ========{Style.RESET_ALL}")
    print_colored("Made by Shadow Slime", "purple")

    message = fetch_shadow_message()
    if message:
        print_colored(f"A message from Shadow: {message}", "gold")

    rpc = start_discord_rich_presence()

    if not is_connected():
        print_colored("[ERROR] No internet connection detected. Please connect to the internet and restart the launcher.", "red")
        input("Press Enter to exit...")
        return

    print_colored("[*] Checking for Game Updates...", "yellow")

    latest_version = get_latest_version()
    if latest_version is None:
        print_colored("[ERROR] Failed to retrieve latest version. Exiting...", "red")
        return

    latest_version_url = f"https://github.com/jogamerforgames2021/AmongUsLauncherNew/releases/download/{latest_version}/app.zip"
    local_zip_file = "game.zip"
    current_version_file = get_appdata_version_file()

    app_dir = load_game_path() or os.path.abspath("GAME")
    executable_path = os.path.join(app_dir, "Among Us.exe")
    game_version = read_version_file(current_version_file)

    if not os.path.exists(executable_path):
        print_colored(f"[!] Among Us not found at saved location: {app_dir}", "red")
        choice = input(f"{Fore.CYAN}[?] Game is not installed or missing. Do you want to download it? (yes/no): ").lower()
        if choice == 'yes':
            print_colored(
                "[*] Choose install location:\n"
                "  [1] Custom - Select any folder (recommended)\n"
                "  [2] Directory - Use default 'GAME' folder next to the launcher\n"
                "Type 1 or 2 and press Enter.",
                "cyan"
            )
            loc_choice = input("Your choice (1/2): ").strip()
            if loc_choice == '1':

                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                print_colored("[*] Please select the folder where you want to install Among Us.", "cyan")
                selected_path = filedialog.askdirectory(title="Select Among Us Install Folder")
                root.destroy()
                if selected_path:
                    app_dir = os.path.abspath(selected_path)
                    executable_path = os.path.join(app_dir, "Among Us.exe")
                else:
                    print_colored("[!] No folder selected. Exiting...", "red")
                    input("Press Enter to exit...")
                    return
            else:

                app_dir = os.path.abspath("GAME")
                executable_path = os.path.join(app_dir, "Among Us.exe")
                print_colored(f"[*] Using default folder: {app_dir}", "cyan")
            print_colored("[!] Downloading game...", "green")
            download_file(latest_version_url, local_zip_file)
            os.makedirs(app_dir, exist_ok=True)
            print_colored("[#] Extracting game files...", "blue")
            extract_zip(local_zip_file, app_dir)
            os.remove(local_zip_file)
            with open(current_version_file, "w") as f:
                f.write(latest_version)
            save_game_path(app_dir)
            print_colored("[^] Game installed successfully!", "green")
            game_version = latest_version
        else:
            print_colored("[!] Game installation skipped. Exiting...", "red")
            input("Press Enter to exit...")
            return
    else:

        save_game_path(app_dir)

    if game_version == latest_version:
        print_colored("[#] Latest version of the game is already installed", "blue")
    else:
        print_colored(f"[!] Update detected! Would you like to update the game from {Fore.YELLOW + Style.BRIGHT + str(game_version) + Style.RESET_ALL} to {Fore.YELLOW + Style.BRIGHT + latest_version + Style.RESET_ALL}? (yes/no): ", "cyan")
        choice = input().lower()
        if choice == 'yes':
            print_colored("[v] Downloading latest game update...", "green")
            download_file(latest_version_url, local_zip_file)
            os.makedirs(app_dir, exist_ok=True)
            print_colored("[#] Extracting game files...", "blue")
            extract_zip(local_zip_file, app_dir)
            os.remove(local_zip_file)
            with open(current_version_file, "w") as f:
                f.write(latest_version)
            print_colored("[^] Game updated successfully!", "green")
        else:
            print_colored("[!] Game update canceled.", "red")

    print_boxed(f"Current Game Version: {game_version or 'Not installed'}", Fore.YELLOW)
    print_boxed(f"Launcher Version: {LAUNCHER_VERSION}", Fore.YELLOW)

    while True:
        show_options_compact()
        choice = input("Enter your choice: ")

        if choice == '1':
            if os.path.exists(executable_path):
                subprocess.Popen([executable_path])
                break  
            else:
                print_colored("[ERROR] Game executable not found!", "red")
        elif choice == '2':
            print("Exiting...")
        elif choice == '11':
            versions = get_available_game_versions()
            if not versions:
                print_colored("[ERROR] No versions found.", "red")
                continue
            print_colored("Available Game Versions:", "cyan")
            for idx, v in enumerate(versions, 1):
                print(f"{Fore.YELLOW}[{idx}]{Style.RESET_ALL} {v['version']}")
            sel = input("Select a version to install (number): ").strip()
            try:
                sel_idx = int(sel) - 1
                if sel_idx < 0 or sel_idx >= len(versions):
                    raise ValueError
            except ValueError:
                print_colored("[ERROR] Invalid selection.", "red")
                continue
            selected = versions[sel_idx]
            print_colored(f"[*] Downloading version {selected['version']}...", "green")
            download_file(selected['url'], local_zip_file)
            os.makedirs(app_dir, exist_ok=True)
            print_colored("[#] Extracting game files...", "blue")
            extract_zip(local_zip_file, app_dir)
            os.remove(local_zip_file)
            with open(current_version_file, "w") as f:
                f.write(selected['version'])
            save_game_path(app_dir)
            game_version = selected['version']
            print_colored(f"[^] Game version {selected['version']} installed successfully!", "green")
            return
        elif choice == '3':
            os.system("start https://www.youtube.com/@ShadowSlimeDEV")
            return
        elif choice == '4':
            os.system("start https://discord.com/invite/W9Mt7Dn9Cj")
            return
        elif choice == '5':
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            shortcut_name = f"Among Us ({latest_version}).lnk"
            shortcut_path = os.path.join(desktop, shortcut_name)
            icon_path = executable_path
            create_shortcut(shortcut_path, target=executable_path, wDir=os.path.dirname(executable_path), icon=icon_path)
            print_colored(f"[+] Shortcut created on desktop: {shortcut_name}", "green")
        elif choice == '6':
            if os.path.exists(app_dir):
                os.startfile(app_dir)
                print_colored(f"[#] Opened game folder: {app_dir}", "green")
            else:
                print_colored("[ERROR] Game folder does not exist!", "red")
        elif choice == '7':
            new_dir = os.path.abspath("GAME")
            print_colored(f"[!] Reinstalling game at: {new_dir}", "yellow")
            download_file(latest_version_url, local_zip_file)
            os.makedirs(new_dir, exist_ok=True)
            print_colored("[#] Extracting game files...", "blue")
            extract_zip(local_zip_file, new_dir)
            os.remove(local_zip_file)
            with open(current_version_file, "w") as f:
                f.write(latest_version)
            save_game_path(new_dir)
            app_dir = new_dir
            executable_path = os.path.join(app_dir, "Among Us.exe")
            print_colored("[^] Game reinstalled successfully!", "green")
        elif choice == '8':
            confirm = input("Are you sure you want to uninstall Among Us and remove all launcher data? (yes/no): ").lower()
            if confirm == 'yes':
                try:
                    if os.path.exists(app_dir):
                        shutil.rmtree(app_dir, onerror=force_remove_readonly)
                        print_colored("[#] Game folder deleted.", "green")
                except Exception as e:
                    print_colored(f"[ERROR] Failed to delete game folder: {e}", "red")
                    print_colored("[!] Try running the launcher as administrator and make sure no files are open.", "yellow")
                try:
                    appdata_dir = os.path.dirname(get_appdata_game_path_file())
                    if os.path.exists(appdata_dir):
                        shutil.rmtree(appdata_dir, onerror=force_remove_readonly)
                        print_colored("[#] Launcher data deleted from AppData.", "green")
                except Exception as e:
                    print_colored(f"[ERROR] Failed to delete AppData: {e}", "red")
                print_colored("[^] Uninstall complete. Exiting...", "green")
                input("Press Enter to exit...")
                return
            else:
                print_colored("[#] Uninstall cancelled.", "yellow")
        elif choice == '9':
            install_aunlocker(game_version, app_dir)
        elif choice == '10':
            app_dir, executable_path = change_game_folder_location(app_dir, executable_path, current_version_file)
        else:
            print_colored("[ERROR] Invalid choice, please try again.", "red")

if __name__ == "__main__":

    while True:
        try:
            if not is_admin():

                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1
                )
                sys.exit()
            else:
                if not is_connected():
                    print_colored("[ERROR] No internet connection detected. Please connect to the internet and restart the launcher.", "red")
                    input("Press Enter to exit...")
                    sys.exit()
                main()  
                break  
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {str(e)}")
            input("Press Enter to try again...")
