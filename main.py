#!/usr/bin/env python3
"""
Social Video Downloader
========================
A cross-platform command-line tool for saving videos, reels, and clips
from Facebook, Instagram, and X (Twitter) — powered by yt-dlp. Works
on Windows, macOS, Linux, and Termux (Android).

SETUP (run once):

    1. Install Python 3.9+  ->  https://python.org/downloads

    2. Install ffmpeg (needed to merge video+audio streams and for
       audio extraction):
         Windows : winget install ffmpeg        (or choco install ffmpeg)
         macOS   : brew install ffmpeg
         Linux   : sudo apt install ffmpeg      (Debian/Ubuntu)
                   sudo dnf install ffmpeg      (Fedora)
                   sudo pacman -S ffmpeg        (Arch)
         Termux  : pkg install ffmpeg

    3. Install yt-dlp:
         pip install --upgrade yt-dlp

RUN:
    python social_video_downloader.py

OPTIONAL — accessing content that requires being logged in:
    Some Instagram and X posts are only viewable while logged in to
    your own account. If you hit a login wall, export your browser's
    cookies for that site to a file named "cookies.txt" (the "Get
    cookies.txt" browser extension does this) and place it in the
    same folder as this script. It will be picked up automatically.

Notes:
- Only download content you have the right to download — your own
  posts, content licensed for reuse, or personal/offline use where
  permitted. Respect each platform's Terms of Service and copyright
  law in your country.
"""

import os
import sys
import platform
import shutil
import re
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("\n[!] yt-dlp is not installed.")
    print("    Install it with:  pip install --upgrade yt-dlp\n")
    sys.exit(1)


APP_NAME = "Social Video Downloader"
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIES_FILE = SCRIPT_DIR / "cookies.txt"

PLATFORM_PATTERNS = {
    "Facebook": re.compile(r"(https?://)?(www\.|m\.|web\.)?(facebook\.com|fb\.watch)/\S+", re.I),
    "Instagram": re.compile(r"(https?://)?(www\.)?instagram\.com/\S+", re.I),
    "X (Twitter)": re.compile(r"(https?://)?(www\.|mobile\.)?(twitter\.com|x\.com)/\S+", re.I),
}

RESOLUTION_LADDER = [
    (2160, "4K"),
    (1440, "2K / QHD"),
    (1080, "Full HD"),
    (720, "HD"),
    (480, "SD"),
    (360, "Low"),
    (240, "Very Low"),
]


# ---------------------------------------------------------------------
# Cross-platform ANSI color support
# ---------------------------------------------------------------------

def _enable_windows_ansi() -> bool:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(kernel32.SetConsoleMode(handle, mode))
    except Exception:
        return False


def _color_supported() -> bool:
    if not sys.stdout.isatty():
        return False
    if platform.system() == "Windows":
        return _enable_windows_ansi()
    return True


USE_COLOR = _color_supported()


def c(code: str) -> str:
    return code if USE_COLOR else ""


RESET = c("\033[0m")
BOLD = c("\033[1m")
MAGENTA = c("\033[95m")
BOLD_MAGENTA = c("\033[1;95m")
BLUE = c("\033[94m")
CYAN = c("\033[96m")
GREEN = c("\033[92m")
YELLOW = c("\033[93m")
GRAY = c("\033[90m")
RED = c("\033[91m")

PLATFORM_COLORS = {
    "Facebook": BLUE,
    "Instagram": MAGENTA,
    "X (Twitter)": CYAN,
}

QUALITY_COLORS = {
    2160: BOLD_MAGENTA,
    1440: YELLOW,
    1080: GREEN,
    720: CYAN,
    480: BLUE,
    360: GRAY,
    240: GRAY,
}


# ---------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------

def banner():
    line = "=" * 70
    print(f"\n{BOLD_MAGENTA}{line}{RESET}")
    print(f"{BOLD_MAGENTA}  {APP_NAME}{RESET}  {GRAY}— one tool, every platform{RESET}")
    print(f"{BOLD_MAGENTA}{line}{RESET}\n")
    print(
        f"{GRAY}Supports:{RESET} {PLATFORM_COLORS['Facebook']}Facebook{RESET}  "
        f"{PLATFORM_COLORS['Instagram']}Instagram{RESET}  "
        f"{PLATFORM_COLORS['X (Twitter)']}X{RESET}"
    )
    print(f"{GRAY}Runs on: {RESET}Windows · macOS · Linux · Termux\n")


def check_ffmpeg():
    if shutil.which("ffmpeg"):
        return
    print(f"{YELLOW}[!] ffmpeg was not found on your PATH.{RESET}")
    print("    Merging streams and audio extraction need it.")
    system = platform.system()
    if system == "Windows":
        print("    Install it with:  winget install ffmpeg   (or: choco install ffmpeg)")
    elif system == "Darwin":
        print("    Install it with:  brew install ffmpeg")
    else:
        print("    Install it with:  pkg install ffmpeg   (Termux)  or your distro's package manager")
    print()


def ensure_download_dir() -> str:
    candidates = [
        Path.home() / "storage" / "downloads" / "SocialVideoDownloader",  # Termux
        Path.home() / "Downloads" / "SocialVideoDownloader",              # Desktop
        Path.cwd() / "SVD_Downloads",                                     # Fallback
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return str(candidate)
        except OSError:
            continue
    return str(Path.cwd())


def detect_platform(url):
    for name, pattern in PLATFORM_PATTERNS.items():
        if pattern.match(url):
            return name
    return None


def get_url():
    supported = ", ".join(PLATFORM_PATTERNS.keys())
    while True:
        url = input(f"\nPaste a {supported} link: ").strip()
        platform_name = detect_platform(url)
        if platform_name:
            return url, platform_name
        print("[!] That doesn't look like a supported link. Try again.")


def base_ydl_opts():
    opts = {"quiet": True, "no_warnings": True}
    if COOKIES_FILE.is_file():
        opts["cookiefile"] = str(COOKIES_FILE)
    return opts


def probe_video(url):
    opts = {**base_ydl_opts(), "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def available_qualities(info):
    formats = info.get("formats", [])
    heights_present = {f.get("height") for f in formats if f.get("height")}

    found = [(h, label) for h, label in RESOLUTION_LADDER if h in heights_present]

    if not found and heights_present:
        for height in sorted(heights_present, reverse=True):
            found.append((height, f"{height}p"))

    return found


def build_format_string(height):
    return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"


def choose_quality(qualities):
    print(f"\n{BOLD}Options:{RESET}")
    print(f"  {BOLD}{GREEN}0. Best available{RESET} (auto — highest quality found)")

    if qualities:
        for i, (height, label) in enumerate(qualities, start=1):
            color = QUALITY_COLORS.get(height, GRAY)
            print(f"  {color}{i}. {height}p — {label}{RESET}")
        audio_index = len(qualities) + 1
    else:
        print(f"  {GRAY}   (Only a single stream was found for this link.){RESET}")
        audio_index = 1

    print(f"  {CYAN}{audio_index}. Audio only (MP3){RESET}")

    while True:
        choice = input(f"\nChoose an option [0-{audio_index}]: ").strip()
        if not choice.isdigit():
            print("[!] Enter a number.")
            continue
        choice = int(choice)
        if choice == 0:
            return ("video", None)
        if qualities and 1 <= choice <= len(qualities):
            return ("video", qualities[choice - 1][0])
        if choice == audio_index:
            return ("audio", None)
        print("[!] Invalid option.")


def progress_hook(d):
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        sys.stdout.write(f"\r    Downloading... {pct}  speed: {speed}  eta: {eta}   ")
        sys.stdout.flush()
    elif d["status"] == "finished":
        print("\n    Download finished, processing (merging/converting)...")


def download(url, mode, height, out_dir):
    outtmpl = os.path.join(out_dir, "%(uploader)s - %(title)s_%(upload_date)s")

    if mode == "audio":
        ydl_opts = {
            **base_ydl_opts(),
            "format": "bestaudio/best",
            "outtmpl": os.path.join(out_dir, "%(uploader)s - %(title)s_%(upload_date)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "progress_hooks": [progress_hook],
        }
    else:
        fmt = build_format_string(height) if height else "bestvideo+bestaudio/best"
        ydl_opts = {
            **base_ydl_opts(),
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "progress_hooks": [progress_hook],
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def explain_error(e):
    msg = str(e).lower()
    print(f"\n{RED}[!] Download failed: {e}{RESET}")
    if "login" in msg or "rate-limit" in msg or "private" in msg:
        print(
            f"{YELLOW}    This post may require being logged in. See the cookies.txt{RESET}\n"
            f"{YELLOW}    note at the top of this script for how to unlock it.{RESET}"
        )


def main():
    banner()
    check_ffmpeg()
    out_dir = ensure_download_dir()
    print(f"Saving downloads to: {out_dir}")

    while True:
        url, platform_name = get_url()
        pcolor = PLATFORM_COLORS.get(platform_name, GRAY)
        print(f"\nDetected: {pcolor}{platform_name}{RESET}")

        print("Fetching info...")
        try:
            info = probe_video(url)
        except yt_dlp.utils.DownloadError as e:
            explain_error(e)
            continue

        title = info.get("title") or info.get("description", "Untitled")[:60] or "Untitled"
        uploader = info.get("uploader", "Unknown")
        print(f"\n{BOLD}Title:{RESET} {title}")
        print(f"{BOLD}From:{RESET} {uploader}")

        qualities = available_qualities(info)
        mode, height = choose_quality(qualities)

        print()
        try:
            download(url, mode, height, out_dir)
            print(f"\n{GREEN}[✔] Done! Saved in: {out_dir}{RESET}")
        except yt_dlp.utils.DownloadError as e:
            explain_error(e)

        again = input("\nDownload another link? (y/n): ").strip().lower()
        if again != "y":
            print(f"\nThanks for using {APP_NAME}. Bye!")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Cancelled by user. Bye!")
        sys.exit(0)
