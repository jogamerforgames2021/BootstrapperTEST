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

# Initialize colorama
init(autoreset=True)

def is_admin():
    """Check if the script is running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def download_file(url, local_filename):
    """Download a file from a given URL."""
    try:
        start_time = time.time()
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            chunk_size = 8192
            with open(local_filename, 'wb') as f:
                downloaded_size = 0
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        done = int(50 * downloaded_size / total_size)
                        percent = int(100 * downloaded_size / total_size)
                        elapsed_time = time.time() - start_time
                        speed = (downloaded_size / elapsed_time) / 1024  # KB/s
                        sys.stdout.write(f"\r[{Fore.GREEN}{'=' * done}{' ' * (50-done)}{Fore.RESET}] {percent}% -- {speed:.2f} KB/s")
                        sys.stdout.flush()
        print("\n")
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
        "gold": Fore.YELLOW + Style.BRIGHT,  # Gold-like color
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

def main():
    """Main function for the launcher."""
    print(f"{Fore.CYAN}=========== AMONG US GAME LAUNCHER ========{Style.RESET_ALL}\n")

    print_colored("[*] Checking for Game Updates...", "yellow")

    latest_version_url = "https://www.dropbox.com/scl/fi/ni6iand1d2kh1xpq02bim/app.zip?rlkey=qgrp9ixtd4cs6sjsfxm6ba4ax&dl=1"
    local_zip_file = "game.zip"
    current_version_file = "GAME/current_version.txt"

    # Check if game directory exists and determine version
    app_dir = "GAME"
    game_version = None
    if os.path.exists(app_dir):
        game_version = read_version_file(current_version_file)

    latest_version = get_latest_version()
    if latest_version is None:
        print_colored("[ERROR] Failed to retrieve latest version. Exiting...", "red")
        return

    # Prompt for game download or update
    if game_version is None:
        choice = input(f"{Fore.CYAN}[?] Game is not installed. Do you want to download it? (yes/no): ").lower()
        if choice == 'yes':
            print_colored("[!] Downloading game...", "green")
            download_file(latest_version_url, local_zip_file)
            os.makedirs(app_dir, exist_ok=True)
            print_colored("[#] Extracting game files...", "blue")
            extract_zip(local_zip_file, app_dir)
            os.remove(local_zip_file)
            with open(current_version_file, "w") as f:
                f.write(latest_version)
            print_colored("[^] Game installed successfully!", "green")

            # Ask about AUnlocker installation
            install_aunlocker = input(f"{Fore.CYAN}[?] Do you want to install AUnlocker? (yes/no): ").lower()
            if install_aunlocker == 'yes':
                aunlocker_url = "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/refs/heads/main/AUnlocker.zip"
                aunlocker_zip = "AUnlocker.zip"
                print_colored("[!] Downloading AUnlocker...", "green")
                download_file(aunlocker_url, aunlocker_zip)
                print_colored("[#] Extracting AUnlocker files...", "blue")
                extract_zip(aunlocker_zip, app_dir)
                os.remove(aunlocker_zip)
                print_colored("[^] AUnlocker installed successfully!", "green")
            else:
                print_colored("[!] AUnlocker installation skipped.", "red")

    elif game_version == latest_version:
        print_colored("[#] Latest version of the game is already installed", "blue")
    else:
        # Update detected
        print_colored(f"[!] Update detected! Would you like to update the game from {Fore.YELLOW + Style.BRIGHT + game_version + Style.RESET_ALL} to {Fore.YELLOW + Style.BRIGHT + latest_version + Style.RESET_ALL}? (yes/no): ", "cyan")
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

    # Adjust the path to the game executable
    executable_path = os.path.join(os.getcwd(), "GAME", "Among Us.exe")  # Ensure you are in the correct directory

    while True:
        show_options()
        choice = input("Enter your choice: ")

        if choice == '1':
            if os.path.exists(executable_path):
                subprocess.Popen([executable_path])
                break  # Exit after running the game
            else:
                print_colored("[ERROR] Game executable not found!", "red")
        elif choice == '2':
            print("Exiting...")
            return  # Return to exit the main loop and program
        elif choice == '3':
            os.system("start https://www.youtube.com/@ShadowSlimeDEV")  # YouTube channel
            return  # Return after opening the link
        elif choice == '4':
            os.system("start https://discord.com/invite/W9Mt7Dn9Cj")  # Discord server
            return  # Return after opening the link
        else:
            print_colored("[ERROR] Invalid choice, please try again.", "red")
            
if __name__ == "__main__":
    # Prevent the application from closing on error
    while True:
        try:
            if not is_admin():
                # Re-run the script with administrator privileges
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
                sys.exit()
            else:
                main()  # Call the main function
                break  # Exit if main completes successfully
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {str(e)}")
            input("Press Enter to try again...")