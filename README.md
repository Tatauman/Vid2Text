# 🎥 Video Translator

A standalone CLI tool to **download, transcribe, and translate videos** using:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)  
- [OpenAI Whisper](https://github.com/openai/whisper)  
- [Argos Translate](https://github.com/argosopentech/argos-translate)  

## 🚀 Features
- Download videos from YouTube (`yt-dlp`) or direct URLs (`wget`)
- Transcribe with **Whisper**
- Translate transcripts with **Argos Translate**

---

## 📦 Installation

Clone and install:

git clone https://github.com/Tatauman/Vid2Text.git
cd Vid2Text
python3 -m venv venv
source venv/bin/activate
python3 install.py


## 📦 Run CLI
source venv/bin/activate

video-translator
or
python cli.py

## 📦 Run GUI
source venv/bin/activate
python3 video_translator_gui.py
