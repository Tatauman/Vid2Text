#!/usr/bin/env python3
import os
import subprocess

def run(cmd):
    print(f"➡️ {cmd}")
    subprocess.check_call(cmd, shell=True)

# Ensure pip
try:
    import pip
    print("✅ pip already installed")
except ImportError:
    print("⚠️ pip not found, installing...")
    run("sudo apt-get install python3-pip -y")

# Install system dependencies
run("sudo apt install ffmpeg -y")
run("pip install argos-translate-files")

# Install Python deps
run("python3 -m pip install --upgrade pip")
run("python3 -m pip install -r requirements.txt")

# Install translate files
run("argospm install translate")

# Install yt-dlp manually (latest binary)
yt_dlp_path = os.path.expanduser("~/.local/bin/yt-dlp")
os.makedirs(os.path.dirname(yt_dlp_path), exist_ok=True)
run(f"wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O {yt_dlp_path}")
run(f"chmod a+rx {yt_dlp_path}")

# Create Folders
folders = ["downloads", "transcripts", "translations"]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"📂 Created folder: {folder}")

print("\n✅ All folders are ready.")


print("\n✅ Installation complete!")

print("\n👉 Add this line to your ~/.bashrc or ~/.zshrc:")
print("   export PATH=$PATH:$HOME/.local/bin")
print("\nThen reload your shell with:")
print("   source ~/.bashrc")
