#!/usr/bin/env python3
import os
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import argostranslate.translate
import argostranslatefiles

# Ensure PATH includes yt-dlp and whisper
os.environ["PATH"] += os.pathsep + os.path.expanduser("~/.local/bin")

# Folders
DOWNLOAD_DIR = "downloads"
TRANSCRIPT_DIR = "transcripts"
TRANSLATION_DIR = "translations"

for folder in [DOWNLOAD_DIR, TRANSCRIPT_DIR, TRANSLATION_DIR]:
    os.makedirs(folder, exist_ok=True)

# List of available languages
available_languages = [
    "aa","af","ak","sq","am","ar","an","hy","as","av","ae","ay","az","bm","ba","eu","be","bn","bh","bi","bs","br","bg","my","ca",
    "ch","ce","ny","zh","cv","kw","co","cr","hr","cs","da","dv","nl","dz","en","eo","et","ee","fo","fj","fi","fr","ff","gl","ka",
    "de","el","gn","gu","ht","ha","he","hz","hi","ho","hu","ia","id","ie","ga","ig","ik","io","is","it","iu","ja","jv","kl","kn",
    "kr","ks","kk","km","ki","rw","ky","kv","kg","ko","ku","kj","la","lb","lg","li","ln","lo","lt","lu","lv","gv","mk","mg","ms",
    "ml","mt","mi","mr","mh","mn","na","nv","nd","ne","ng","nb","nn","no","ii","nr","oc","oj","cu","om","or","os","pa","pi","fa",
    "pl","ps","pt","qu","rm","rn","ro","ru","sa","sc","sd","se","sm","sg","sr","gd","sn","si","sk","sl","so","st","es","su","sw",
    "ss","sv","ta","te","tg","th","ti","bo","tk","tl","tn","to","tr","ts","tt","tw","ty","ug","uk","ur","uz","ve","vi","vo","wa",
    "cy","wo","fy","xh","yi","yo","za","zu"
]

# GUI Application
class VideoTranslatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Transcription & Translation Tool")
        self.geometry("700x500")

        tab_control = ttk.Notebook(self)
        
        self.download_tab = ttk.Frame(tab_control)
        self.transcribe_tab = ttk.Frame(tab_control)
        self.translate_tab = ttk.Frame(tab_control)
        
        tab_control.add(self.download_tab, text='Download')
        tab_control.add(self.transcribe_tab, text='Transcribe')
        tab_control.add(self.translate_tab, text='Translate')
        tab_control.pack(expand=1, fill='both')
        
        self.create_download_tab()
        self.create_transcribe_tab()
        self.create_translate_tab()
        
        # Output log
        self.log_text = tk.Text(self, height=10)
        self.log_text.pack(fill='x', padx=5, pady=5)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    # ---------------- Download Tab ----------------
    def create_download_tab(self):
        ttk.Label(self.download_tab, text="YouTube URL:").pack(pady=5)
        self.youtube_url = tk.Entry(self.download_tab, width=50)
        self.youtube_url.pack()
        ttk.Label(self.download_tab, text="Output Filename:").pack(pady=5)
        self.youtube_outname = tk.Entry(self.download_tab, width=50)
        self.youtube_outname.pack()
        ttk.Button(self.download_tab, text="Download YouTube Video", command=self.download_youtube).pack(pady=10)
        
        ttk.Label(self.download_tab, text="Direct Video URL:").pack(pady=5)
        self.video_url = tk.Entry(self.download_tab, width=50)
        self.video_url.pack()
        ttk.Label(self.download_tab, text="Output Filename:").pack(pady=5)
        self.video_outname = tk.Entry(self.download_tab, width=50)
        self.video_outname.pack()
        ttk.Button(self.download_tab, text="Download Video", command=self.download_video).pack(pady=10)

    def download_youtube(self):
        url = self.youtube_url.get().strip()
        outname = self.youtube_outname.get().strip()
        if not url or not outname:
            messagebox.showerror("Error", "Provide both URL and filename")
            return
        outfile = os.path.join(DOWNLOAD_DIR, outname + ".%(ext)s")
        self.run_command(f'yt-dlp -o "{outfile}" "{url}"')

    def download_video(self):
        url = self.video_url.get().strip()
        outname = self.video_outname.get().strip()
        if not url or not outname:
            messagebox.showerror("Error", "Provide both URL and filename")
            return
        outfile = os.path.join(DOWNLOAD_DIR, outname)
        self.run_command(f'wget -O "{outfile}" "{url}"')

    # ---------------- Transcribe Tab ----------------
    def create_transcribe_tab(self):
        ttk.Button(self.transcribe_tab, text="Refresh Video List", command=self.refresh_video_list).pack(pady=5)
        self.video_listbox = tk.Listbox(self.transcribe_tab, width=50)
        self.video_listbox.pack()
        ttk.Label(self.transcribe_tab, text="Output Format (txt, srt, vtt, json, tsv, all):").pack(pady=5)
        self.transcript_format = tk.Entry(self.transcribe_tab, width=20)
        self.transcript_format.insert(0, "txt")
        self.transcript_format.pack()
        ttk.Button(self.transcribe_tab, text="Transcribe Selected Video", command=self.transcribe).pack(pady=10)

    def refresh_video_list(self):
        self.video_listbox.delete(0, tk.END)
        files = os.listdir(DOWNLOAD_DIR)
        for f in files:
            self.video_listbox.insert(tk.END, f)
        self.log(f"Refreshed video list: {files}")

    def transcribe(self):
        selection = self.video_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Select a video to transcribe")
            return
        filename = self.video_listbox.get(selection[0])
        fmt = self.transcript_format.get().strip()
        infile_path = os.path.join(DOWNLOAD_DIR, filename)
        self.run_command(f'whisper "{infile_path}" --model tiny -f {fmt} --output_dir {TRANSCRIPT_DIR}')

    # ---------------- Translate Tab ----------------
    def create_translate_tab(self):
        ttk.Button(self.translate_tab, text="Refresh Transcript List", command=self.refresh_transcript_list).pack(pady=5)
        self.transcript_listbox = tk.Listbox(self.translate_tab, width=50)
        self.transcript_listbox.pack()
        
        ttk.Label(self.translate_tab, text="Source Language Code:").pack(pady=5)
        self.source_lang = ttk.Combobox(self.translate_tab, values=available_languages)
        self.source_lang.pack()
        ttk.Label(self.translate_tab, text="Target Language Code:").pack(pady=5)
        self.target_lang = ttk.Combobox(self.translate_tab, values=available_languages)
        self.target_lang.pack()
        
        ttk.Button(self.translate_tab, text="Translate Selected Transcript", command=self.translate).pack(pady=10)

    def refresh_transcript_list(self):
        self.transcript_listbox.delete(0, tk.END)
        files = os.listdir(TRANSCRIPT_DIR)
        for f in files:
            self.transcript_listbox.insert(tk.END, f)
        self.log(f"Refreshed transcript list: {files}")

    def translate(self):
        selection = self.transcript_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Select a transcript to translate")
            return
        infile = self.transcript_listbox.get(selection[0])
        infile_path = os.path.join(TRANSCRIPT_DIR, infile)

        from_code = self.source_lang.get().strip()
        to_code = self.target_lang.get().strip()
        if not from_code or not to_code:
            messagebox.showerror("Error", "Select both source and target languages")
            return
        
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = list(filter(
         lambda x: x.code == from_lan,
         installed_languages))[0]
        to_lang = list(filter(
         lambda x: x.code == to_lan,
         installed_languages))[0]
         underlying_translation = from_lang.get_translation(to_lang)


    
        argostranslatefiles.translate_file(underlying_translation, os.path.abspath(infile_path))

        name, ext = os.path.splitext(infile)
        translated_filename = f"{name}_{to_code}{ext}"
        translated_path = os.path.join(TRANSLATION_DIR, translated_filename)
        shutil.move(os.path.join(TRANSCRIPT_DIR, translated_filename), translated_path)
        self.log(f"✅ Translation saved to {translated_path}")

    # ---------------- Utility ----------------
    def run_command(self, cmd):
        self.log(f"➡️ Running: {cmd}")
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            self.log(line.strip())
        process.wait()
        if process.returncode == 0:
            self.log("✅ Command completed successfully")
        else:
            self.log("❌ Command failed")

if __name__ == "__main__":
    app = VideoTranslatorGUI()
    app.mainloop()
