#!/usr/bin/env python3
"""
Video Transcription & Translation Tool (GUI)

Upgrades vs your original:
- No shell=True (safer subprocess usage)
- Runs long tasks in a background thread (GUI stays responsive)
- Better Whisper CLI usage (--output_format, --model, --language, --task)
- Optional "Download direct URL" uses Python (no wget needed)
- Transcript/translation lists show only relevant files
- Translation supports TXT / SRT / VTT while preserving timestamps/cues
- Language dropdowns are populated from INSTALLED Argos languages (so you don't pick unsupported codes)
- Graceful error messages + better logging
"""

import os
import re
import sys
import json
import time
import queue
import shutil
import threading
import subprocess
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import argostranslate.translate

# -------------------------- Paths / folders --------------------------
APP_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(APP_DIR, "downloads")
TRANSCRIPT_DIR = os.path.join(APP_DIR, "transcripts")
TRANSLATION_DIR = os.path.join(APP_DIR, "translations")

for folder in (DOWNLOAD_DIR, TRANSCRIPT_DIR, TRANSLATION_DIR):
    os.makedirs(folder, exist_ok=True)

# Ensure PATH includes ~/.local/bin (yt-dlp / whisper often here)
os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + os.path.expanduser("~/.local/bin")


# -------------------------- Helpers --------------------------
def which(cmd: str) -> str | None:
    """Cross-platform-ish which."""
    return shutil.which(cmd)

def safe_filename(name: str) -> str:
    """Make a filesystem-friendly name."""
    name = name.strip()
    name = re.sub(r"[^\w\-. ]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or f"file_{int(time.time())}"

def human_err(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"


# -------------------------- Translation helpers (preserve cues) --------------------------
SRT_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}")
VTT_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}")

def translate_text_block(translator, text: str) -> str:
    # Argos can be slow; keep it simple.
    return translator.translate(text)

def translate_txt(translator, src_path: str, dst_path: str):
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    out = translate_text_block(translator, content)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(out)

def translate_srt(translator, src_path: str, dst_path: str):
    out_lines = []
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.rstrip("\n")
            if not s.strip():
                out_lines.append("")
                continue
            if s.strip().isdigit():
                out_lines.append(s)
                continue
            if SRT_TIME_RE.match(s.strip()):
                out_lines.append(s)
                continue
            # translate subtitle text lines
            out_lines.append(translate_text_block(translator, s))
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")

def translate_vtt(translator, src_path: str, dst_path: str):
    out_lines = []
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.rstrip("\n")
            if not s.strip():
                out_lines.append("")
                continue
            # Keep WEBVTT header and NOTE blocks as-is
            if s.strip().upper().startswith("WEBVTT"):
                out_lines.append(s)
                continue
            if s.strip().upper().startswith("NOTE"):
                out_lines.append(s)
                continue
            if VTT_TIME_RE.match(s.strip()):
                out_lines.append(s)
                continue
            # Some VTT cues can have "00:00.000 --> 00:02.000" (mm:ss.xxx) — preserve those too
            if "-->" in s and re.search(r"\d{1,2}:\d{2}\.\d{3}\s-->\s\d{1,2}:\d{2}\.\d{3}", s.strip()):
                out_lines.append(s)
                continue
            out_lines.append(translate_text_block(translator, s))
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")

def translate_file_by_ext(translator, src_path: str, dst_path: str):
    ext = os.path.splitext(src_path)[1].lower()
    if ext == ".txt":
        translate_txt(translator, src_path, dst_path)
    elif ext == ".srt":
        translate_srt(transator=translator, src_path=src_path, dst_path=dst_path)  # type: ignore
    elif ext == ".vtt":
        translate_vtt(translator, src_path, dst_path)
    else:
        raise ValueError(f"Unsupported transcript format for translation: {ext} (supported: .txt .srt .vtt)")


# NOTE: typo-proof wrapper (fixes accidental keyword mismatch above if edited)
def translate_srt(transator=None, translator=None, src_path=None, dst_path=None):  # noqa
    if translator is None:
        translator = transator
    if translator is None or src_path is None or dst_path is None:
        raise ValueError("translate_srt internal argument error")
    out_lines = []
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.rstrip("\n")
            if not s.strip():
                out_lines.append("")
                continue
            if s.strip().isdigit():
                out_lines.append(s)
                continue
            if SRT_TIME_RE.match(s.strip()):
                out_lines.append(s)
                continue
            out_lines.append(translate_text_block(translator, s))
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")


# -------------------------- GUI App --------------------------
class VideoTranslatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Transcription & Translation Tool")
        self.geometry("820x600")

        # Worker queue for thread-safe log updates
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._task_running = False

        # Tabs
        tab_control = ttk.Notebook(self)
        self.download_tab = ttk.Frame(tab_control)
        self.transcribe_tab = ttk.Frame(tab_control)
        self.translate_tab = ttk.Frame(tab_control)

        tab_control.add(self.download_tab, text="Download")
        tab_control.add(self.transcribe_tab, text="Transcribe")
        tab_control.add(self.translate_tab, text="Translate")
        tab_control.pack(expand=1, fill="both")

        # UI
        self.create_download_tab()
        self.create_transcribe_tab()
        self.create_translate_tab()

        # Log
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=False, padx=8, pady=6)

        ttk.Label(log_frame, text="Output Log:").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=10, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status.pack(fill="x", padx=8, pady=(0, 6))

        # Periodically flush queued logs
        self.after(100, self._drain_log_queue)

        # Initial list refresh
        self.refresh_video_list()
        self.refresh_transcript_list()
        self.refresh_installed_languages()

        self._check_deps()

    # -------------------------- Logging / threading --------------------------
    def log(self, msg: str):
        self._log_queue.put(msg)

    def _drain_log_queue(self):
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def set_status(self, s: str):
        self.status_var.set(s)

    def run_in_thread(self, target, *args, **kwargs):
        if self._task_running:
            messagebox.showinfo("Busy", "A task is already running. Please wait for it to finish.")
            return

        def wrapper():
            self._task_running = True
            try:
                target(*args, **kwargs)
            except Exception as e:
                self.log(f"❌ {human_err(e)}")
                messagebox.showerror("Error", human_err(e))
            finally:
                self._task_running = False
                self.set_status("Ready")

        t = threading.Thread(target=wrapper, daemon=True)
        t.start()

    # -------------------------- Dependency check --------------------------
    def _check_deps(self):
        yt = which("yt-dlp")
        wh = which("whisper")
        ff = which("ffmpeg")

        if not yt:
            self.log("⚠️ yt-dlp not found on PATH. YouTube download will fail until installed.")
        else:
            self.log(f"✅ Found yt-dlp: {yt}")

        if not wh:
            self.log("⚠️ whisper CLI not found on PATH. Transcription will fail until installed (pip install openai-whisper).")
        else:
            self.log(f"✅ Found whisper: {wh}")

        if not ff:
            self.log("⚠️ ffmpeg not found on PATH. Whisper may still run, but ffmpeg is strongly recommended.")
        else:
            self.log(f"✅ Found ffmpeg: {ff}")

    # -------------------------- Download Tab --------------------------
    def create_download_tab(self):
        frame = ttk.Frame(self.download_tab, padding=10)
        frame.pack(fill="both", expand=True)

        # YouTube
        yt_box = ttk.LabelFrame(frame, text="YouTube Download (yt-dlp)", padding=10)
        yt_box.pack(fill="x", pady=(0, 10))

        ttk.Label(yt_box, text="YouTube URL:").grid(row=0, column=0, sticky="w")
        self.youtube_url = ttk.Entry(yt_box, width=70)
        self.youtube_url.grid(row=0, column=1, sticky="we", padx=8, pady=3)

        ttk.Label(yt_box, text="Output base name:").grid(row=1, column=0, sticky="w")
        self.youtube_outname = ttk.Entry(yt_box, width=30)
        self.youtube_outname.grid(row=1, column=1, sticky="w", padx=8, pady=3)

        ttk.Button(yt_box, text="Download YouTube Video", command=self.download_youtube).grid(
            row=2, column=1, sticky="w", padx=8, pady=8
        )

        yt_box.columnconfigure(1, weight=1)

        # Direct URL
        direct_box = ttk.LabelFrame(frame, text="Direct Video URL Download (Python)", padding=10)
        direct_box.pack(fill="x")

        ttk.Label(direct_box, text="Direct URL:").grid(row=0, column=0, sticky="w")
        self.video_url = ttk.Entry(direct_box, width=70)
        self.video_url.grid(row=0, column=1, sticky="we", padx=8, pady=3)

        ttk.Label(direct_box, text="Output filename (with extension):").grid(row=1, column=0, sticky="w")
        self.video_outname = ttk.Entry(direct_box, width=40)
        self.video_outname.grid(row=1, column=1, sticky="w", padx=8, pady=3)

        ttk.Button(direct_box, text="Download Direct URL", command=self.download_video).grid(
            row=2, column=1, sticky="w", padx=8, pady=8
        )

        ttk.Button(direct_box, text="Open Downloads Folder", command=lambda: self.open_folder(DOWNLOAD_DIR)).grid(
            row=2, column=1, sticky="e", padx=8, pady=8
        )

        direct_box.columnconfigure(1, weight=1)

    def download_youtube(self):
        url = self.youtube_url.get().strip()
        outname = safe_filename(self.youtube_outname.get().strip())
        if not url or not outname:
            messagebox.showerror("Error", "Provide both URL and output base name.")
            return
        if not which("yt-dlp"):
            messagebox.showerror("Missing dependency", "yt-dlp not found. Install it and try again.")
            return

        # Template keeps original extension
        outfile_template = os.path.join(DOWNLOAD_DIR, outname + ".%(ext)s")

        def task():
            self.set_status("Downloading YouTube...")
            self.log(f"➡️ yt-dlp: {url}")
            cmd = ["yt-dlp", "-o", outfile_template, url]
            self.run_command(cmd)
            self.refresh_video_list()

        self.run_in_thread(task)

    def download_video(self):
        url = self.video_url.get().strip()
        outname = self.video_outname.get().strip()
        if not url or not outname:
            messagebox.showerror("Error", "Provide both URL and output filename.")
            return

        outname = safe_filename(outname)
        outpath = os.path.join(DOWNLOAD_DIR, outname)

        def task():
            self.set_status("Downloading direct URL...")
            self.log(f"➡️ Downloading: {url}")
            try:
                with urllib.request.urlopen(url) as r, open(outpath, "wb") as f:
                    total = r.headers.get("Content-Length")
                    total = int(total) if total and total.isdigit() else None
                    downloaded = 0
                    chunk = 1024 * 256
                    while True:
                        data = r.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        downloaded += len(data)
                        if total:
                            pct = (downloaded / total) * 100
                            self.set_status(f"Downloading... {pct:.1f}%")
                self.log(f"✅ Saved to: {outpath}")
            except Exception as e:
                # Remove partial file
                if os.path.exists(outpath):
                    try:
                        os.remove(outpath)
                    except Exception:
                        pass
                raise e
            finally:
                self.set_status("Ready")
            self.refresh_video_list()

        self.run_in_thread(task)

    # -------------------------- Transcribe Tab --------------------------
    def create_transcribe_tab(self):
        frame = ttk.Frame(self.transcribe_tab, padding=10)
        frame.pack(fill="both", expand=True)

        top = ttk.Frame(frame)
        top.pack(fill="x")

        ttk.Button(top, text="Refresh Video List", command=self.refresh_video_list).pack(side="left")
        ttk.Button(top, text="Add Local Video...", command=self.add_local_video).pack(side="left", padx=8)
        ttk.Button(top, text="Open Downloads Folder", command=lambda: self.open_folder(DOWNLOAD_DIR)).pack(side="right")

        self.video_listbox = tk.Listbox(frame, height=10)
        self.video_listbox.pack(fill="both", expand=True, pady=8)

        opts = ttk.LabelFrame(frame, text="Whisper Options", padding=10)
        opts.pack(fill="x")

        ttk.Label(opts, text="Model:").grid(row=0, column=0, sticky="w")
        self.whisper_model = ttk.Combobox(opts, values=["tiny", "base", "small", "medium", "large"], width=12, state="readonly")
        self.whisper_model.set("base")
        self.whisper_model.grid(row=0, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(opts, text="Task:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.whisper_task = ttk.Combobox(opts, values=["transcribe", "translate"], width=12, state="readonly")
        self.whisper_task.set("transcribe")
        self.whisper_task.grid(row=0, column=3, sticky="w", padx=8, pady=2)

        ttk.Label(opts, text="Language (optional, e.g. en, es):").grid(row=1, column=0, sticky="w")
        self.whisper_lang = ttk.Entry(opts, width=15)
        self.whisper_lang.grid(row=1, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(opts, text="Output format:").grid(row=1, column=2, sticky="w", padx=(20, 0))
        self.transcript_format = ttk.Combobox(opts, values=["txt", "srt", "vtt", "tsv", "json", "all"], width=12, state="readonly")
        self.transcript_format.set("txt")
        self.transcript_format.grid(row=1, column=3, sticky="w", padx=8, pady=2)

        ttk.Label(opts, text="Extra args (optional):").grid(row=2, column=0, sticky="w")
        self.whisper_extra = ttk.Entry(opts, width=60)
        self.whisper_extra.grid(row=2, column=1, columnspan=3, sticky="we", padx=8, pady=2)

        opts.columnconfigure(3, weight=1)

        ttk.Button(frame, text="Transcribe Selected Video", command=self.transcribe).pack(pady=8)
        ttk.Button(frame, text="Open Transcripts Folder", command=lambda: self.open_folder(TRANSCRIPT_DIR)).pack()

    def refresh_video_list(self):
        self.video_listbox.delete(0, tk.END)
        try:
            files = sorted(os.listdir(DOWNLOAD_DIR))
        except Exception as e:
            self.log(f"❌ Could not list downloads: {human_err(e)}")
            return
        for f in files:
            self.video_listbox.insert(tk.END, f)
        self.log(f"🔄 Videos: {len(files)} item(s)")

    def add_local_video(self):
        path = filedialog.askopenfilename(
            title="Select a local video/audio file",
            filetypes=[("Media files", "*.mp4 *.mkv *.mov *.webm *.mp3 *.wav *.m4a *.aac *.flac"), ("All files", "*.*")]
        )
        if not path:
            return
        base = safe_filename(os.path.basename(path))
        dest = os.path.join(DOWNLOAD_DIR, base)
        try:
            shutil.copy2(path, dest)
            self.log(f"✅ Copied to downloads: {dest}")
            self.refresh_video_list()
        except Exception as e:
            messagebox.showerror("Error", human_err(e))

    def transcribe(self):
        if not which("whisper"):
            messagebox.showerror("Missing dependency", "whisper CLI not found. Install: pip install openai-whisper")
            return

        sel = self.video_listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select a video to transcribe.")
            return

        filename = self.video_listbox.get(sel[0])
        infile_path = os.path.join(DOWNLOAD_DIR, filename)

        model = self.whisper_model.get().strip()
        task = self.whisper_task.get().strip()
        outfmt = self.transcript_format.get().strip()
        lang = self.whisper_lang.get().strip()
        extra = self.whisper_extra.get().strip()

        def task_fn():
            self.set_status("Transcribing...")
            self.log(f"➡️ Whisper input: {infile_path}")
            cmd = ["whisper", infile_path, "--model", model, "--task", task, "--output_dir", TRANSCRIPT_DIR, "--output_format", outfmt]

            # Optional: language hint
            if lang:
                cmd.extend(["--language", lang])

            # If you’re on CPU, fp16 may error; force off for safety
            cmd.extend(["--fp16", "False"])

            # Extra args: naive split (space-delimited)
            if extra:
                cmd.extend(extra.split())

            self.run_command(cmd)
            self.refresh_transcript_list()

        self.run_in_thread(task_fn)

    # -------------------------- Translate Tab --------------------------
    def create_translate_tab(self):
        frame = ttk.Frame(self.translate_tab, padding=10)
        frame.pack(fill="both", expand=True)

        top = ttk.Frame(frame)
        top.pack(fill="x")

        ttk.Button(top, text="Refresh Transcript List", command=self.refresh_transcript_list).pack(side="left")
        ttk.Button(top, text="Open Transcripts Folder", command=lambda: self.open_folder(TRANSCRIPT_DIR)).pack(side="left", padx=8)
        ttk.Button(top, text="Open Translations Folder", command=lambda: self.open_folder(TRANSLATION_DIR)).pack(side="right")

        self.transcript_listbox = tk.Listbox(frame, height=10)
        self.transcript_listbox.pack(fill="both", expand=True, pady=8)

        lang_box = ttk.LabelFrame(frame, text="Argos Translate (Installed languages only)", padding=10)
        lang_box.pack(fill="x")

        ttk.Label(lang_box, text="Source language:").grid(row=0, column=0, sticky="w")
        self.source_lang = ttk.Combobox(lang_box, values=[], width=12, state="readonly")
        self.source_lang.grid(row=0, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(lang_box, text="Target language:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.target_lang = ttk.Combobox(lang_box, values=[], width=12, state="readonly")
        self.target_lang.grid(row=0, column=3, sticky="w", padx=8, pady=2)

        ttk.Button(lang_box, text="Refresh Installed Languages", command=self.refresh_installed_languages).grid(
            row=1, column=1, sticky="w", padx=8, pady=8
        )

        ttk.Label(lang_box, text="Note: translation supports .txt, .srt, .vtt and preserves timestamps/cues.").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

        ttk.Button(frame, text="Translate Selected Transcript", command=self.translate).pack(pady=10)

    def refresh_transcript_list(self):
        self.transcript_listbox.delete(0, tk.END)
        try:
            files = sorted(os.listdir(TRANSCRIPT_DIR))
        except Exception as e:
            self.log(f"❌ Could not list transcripts: {human_err(e)}")
            return

        # Only show typical output formats
        allowed = {".txt", ".srt", ".vtt", ".tsv", ".json"}
        show = [f for f in files if os.path.splitext(f)[1].lower() in allowed]
        for f in show:
            self.transcript_listbox.insert(tk.END, f)
        self.log(f"🔄 Transcripts: {len(show)} item(s)")

    def refresh_installed_languages(self):
        try:
            langs = argostranslate.translate.get_installed_languages()
            codes = sorted({l.code for l in langs})
            self.source_lang["values"] = codes
            self.target_lang["values"] = codes

            # sensible defaults if possible
            if "en" in codes and not self.source_lang.get():
                self.source_lang.set("en")
            if "es" in codes and not self.target_lang.get():
                self.target_lang.set("es")

            self.log(f"🔄 Argos installed languages: {', '.join(codes) if codes else '(none)'}")
            if not codes:
                self.log("⚠️ No Argos language packages installed. Install packages before translating.")
        except Exception as e:
            self.log(f"❌ Failed to load Argos languages: {human_err(e)}")

    def translate(self):
        sel = self.transcript_listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select a transcript to translate.")
            return

        infile = self.transcript_listbox.get(sel[0])
        src_path = os.path.join(TRANSCRIPT_DIR, infile)

        from_code = self.source_lang.get().strip()
        to_code = self.target_lang.get().strip()
        if not from_code or not to_code:
            messagebox.showerror("Error", "Pick both source and target languages.")
            return
        if from_code == to_code:
            messagebox.showerror("Error", "Source and target languages must be different.")
            return

        ext = os.path.splitext(infile)[1].lower()
        if ext not in (".txt", ".srt", ".vtt"):
            messagebox.showerror("Unsupported", "Translation currently supports .txt, .srt, .vtt only.")
            return

        def task():
            self.set_status("Translating...")
            self.log(f"➡️ Translating: {infile} ({from_code} → {to_code})")

            installed = argostranslate.translate.get_installed_languages()
            from_lang = next((l for l in installed if l.code == from_code), None)
            to_lang = next((l for l in installed if l.code == to_code), None)

            if not from_lang or not to_lang:
                raise RuntimeError("Selected language(s) are not installed in Argos.")

            translator = from_lang.get_translation(to_lang)
            if translator is None:
                raise RuntimeError("No translation package found for this language pair in Argos.")

            name, ext = os.path.splitext(infile)
            out_name = f"{name}_{to_code}{ext}"
            dst_path = os.path.join(TRANSLATION_DIR, out_name)

            # Perform translation with cue-preserving translators
            translate_file_by_ext(translator, src_path, dst_path)

            self.log(f"✅ Translation saved: {dst_path}")

        self.run_in_thread(task)

    # -------------------------- Utilities --------------------------
    def run_command(self, cmd_list: list[str]):
        self.log("➡️ Running: " + " ".join(cmd_list))
        try:
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
        except FileNotFoundError:
            raise RuntimeError(f"Command not found: {cmd_list[0]}")

        assert process.stdout is not None
        for line in process.stdout:
            self.log(line.rstrip("\n"))

        rc = process.wait()
        if rc == 0:
            self.log("✅ Command completed successfully")
        else:
            raise RuntimeError(f"Command failed with exit code {rc}")

    def open_folder(self, path: str):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {human_err(e)}")


if __name__ == "__main__":
    app = VideoTranslatorGUI()
    app.mainloop()
