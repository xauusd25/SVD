#!/data/data/com.termux/files/usr/bin/bash

set -e

R='\033[0;31m'
G='\033[0;32m'
N='\033[0m'

TOTAL_STEPS=7
STEP=0

run_step() {
    STEP=$((STEP + 1))
    local msg="$1" cmd="$2" output

    printf "[%d/%d] %s... " "$STEP" "$TOTAL_STEPS" "$msg"

    if output=$(bash -c "$cmd" 2>&1); then
        echo -e "${G}✔${N}"
    else
        echo -e "${R}✘${N}"
        echo -e "${R}Error occurred during: $msg${N}"
        echo "$output"
        exit 1
    fi
}

if [ ! -d "$HOME/storage" ]; then
    echo -e "\nGrant permission: termux-setup-storage\nThen rerun the command.\n"
    exit 1
fi


run_step "Updating system & fixing broken packages" \
    "yes | apt --fix-broken install && yes | apt update && yes | apt upgrade"

run_step "Installing Python" \
    "yes | pkg install python"
    
run_step "Installing Git" \
    "yes | pkg install git"

run_step "Installing FFMpeg" \
    "yes | pkg install ffmpeg"

run_step "Installing YT-DLP" \
    "pip install -U yt-dlp && yes | pkg install yt-dlp"
    
run_step "Installing FFMpeg-Python" \
    "pip install -U ffmpeg-python"

run_step "Installing Social_Video_Downloader" \
    "git clone https://github.com/xauusd25/Social_Video_Downloader.git"

echo -e "\n${G}✔ Installation completed successfully${N}"
echo -e "\nRun command: ${G} python Social_Video_Downloader/main.py${N}\n"