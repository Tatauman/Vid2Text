#!/usr/bin/env python3
import os
import subprocess
import sys

def run(cmd):
    print(f"➡️ {cmd}")
    subprocess.check_call(cmd, shell=True)

def check_command(command):
    """Check if a command exists"""
    return subprocess.call(f"type {command}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

# Update apt
run("sudo apt update -y")

# Install system packages
packages = ["ffmpeg", "wget", "python3-pip", "git"]
for pkg in packages:
    run(f"sudo apt install -y {pkg}")

# Upgrade pip
run("python3 -m pip install --upgrade pip")

# Install Python packages
run("python3 -m pip install git+https://github.com/openai/whisper.git")
run("python3 -m pip install argos-translate-files yt-dlp")

# Install yt-dlp binary (if not already)
yt_dlp_path = os.path.expanduser("~/.local/bin/yt-dlp")
os.makedirs(os.path.dirname(yt_dlp_path), exist_ok=True)
if not check_command("yt-dlp"):
    run(f"wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O {yt_dlp_path}")
    run(f"chmod a+rx {yt_dlp_path}")

# Make sure ~/.local/bin is on PATH
bashrc_path = os.path.expanduser("~/.bashrc")
with open(bashrc_path, "a") as f:
    f.write("\nexport PATH=$PATH:$HOME/.local/bin\n")

print("\n✅ Installation complete!")
print("Please run: source ~/.bashrc")
print("Then run your tool with: video-translator or python cli.py")
