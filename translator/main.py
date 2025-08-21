import os
import subprocess
import argostranslate.translate
import argostranslatefiles

# Ensure PATH includes yt-dlp and whisper
os.environ["PATH"] += os.pathsep + os.path.expanduser("~/.local/bin")

def download_youtube():
    yturl = input("Enter YouTube URL: ")
    outname = input("Enter output filename: ")
    subprocess.call(["yt-dlp", "-o", outname, yturl])

def download_video():
    url = input("Enter direct video URL: ")
    outname = input("Enter output filename: ")
    subprocess.call(["wget", "-O", outname, url])

def transcribe():
    filename = input("Enter video filename (with extension): ")
    fmt = input("Output format (txt, vtt, srt, tsv, json, all): ")
    subprocess.call(["whisper", filename, "-f", fmt])

def translate():
    installed_languages = argostranslate.translate.get_installed_languages()
    print("Installed:", [f"{lang.code} ({lang.name})" for lang in installed_languages])

    from_code = input("Source language code: ")
    to_code = input("Target language code: ")
    infile = input("Path to transcript file: ")
    outfile = "translated_" + os.path.basename(infile)

    from_lang = next(lang for lang in installed_languages if lang.code == from_code)
    to_lang = next(lang for lang in installed_languages if lang.code == to_code)

    translation = from_lang.get_translation(to_lang)
    argostranslatefiles.translate_file(
        translation,
        os.path.abspath(infile),
        output_path=outfile
    )

    print(f"✅ Translated file saved as {outfile}")

def main():
    if input("Download YouTube video? (y/n): ").lower() == "y":
        download_youtube()
    if input("Download other video? (y/n): ").lower() == "y":
        download_video()
    if input("Transcribe video? (y/n): ").lower() == "y":
        transcribe()
    if input("Translate transcript? (y/n): ").lower() == "y":
        translate()

