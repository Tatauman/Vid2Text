import os
import subprocess
import argostranslate.translate
import argostranslatefiles
import shutil

# Ensure PATH includes yt-dlp and whisper
os.environ["PATH"] += os.pathsep + os.path.expanduser("~/.local/bin")

# Define output folders
DOWNLOAD_DIR = "downloads"
TRANSCRIPT_DIR = "transcripts"
TRANSLATION_DIR = "translations"

# Create directories if not exist
for folder in [DOWNLOAD_DIR, TRANSCRIPT_DIR, TRANSLATION_DIR]:
    os.makedirs(folder, exist_ok=True)

def download_youtube():
    yturl = input("Enter YouTube URL: ")
    outname = input("Enter output filename: ")
    outfile = os.path.join(DOWNLOAD_DIR, outname + ".%(ext)s")
    subprocess.run(["yt-dlp", "-o", outfile, yturl], check=True)
    print(f"✅ Saved to {DOWNLOAD_DIR}")

def download_video():
    url = input("Enter direct video URL: ")
    outname = input("Enter output filename: ")
    outfile = os.path.join(DOWNLOAD_DIR, outname)
    subprocess.run(["wget", "-O", outfile, url], check=True)
    print(f"✅ Saved to {DOWNLOAD_DIR}")

def transcribe():
    # list current files for convenience
    print("\n📂 Available Videos to Transcribe/:")
    subprocess.call(f"ls {DOWNLOAD_DIR}", shell=True)
    
    filename = input("Enter video filename (without extension): ")
    ext = input("Enter file extension (e.g. mp4, webm): ")
    fmt = input("Enter transcript output format (txt, vtt, srt, tsv, json, all): ")

    infile = f"{filename}.{ext}"
    infile_path = os.path.join(DOWNLOAD_DIR, infile)
    subprocess.run(["whisper", infile_path, "--model", "tiny", "-f", fmt, "--output_dir", TRANSCRIPT_DIR], check=True)
    print(f"✅ Transcript saved to {TRANSCRIPT_DIR}")

def translate():
     print("\n📂 Available transcripts in transcripts/:")
     subprocess.call(f"ls {TRANSCRIPT_DIR}", shell=True)


     infile = input("Enter file name: ").strip()
     infile_path = os.path.join(TRANSCRIPT_DIR, infile)
     while not os.path.isfile(infile_path):
            print("❌ File does not exist.")
            subprocess.call(f"ls {TRANSCRIPT_DIR}", shell=True)
            infile = input("Enter file name: ").strip()
            infile_path = os.path.join(TRANSCRIPT_DIR, infile)

     outfile = os.path.join(TRANSLATION_DIR, "translated_" + infile)

     available_languages = ["aa","af","ak","sq","am","ar","an","hy","as","av","ae","ay","az","bm","ba","eu","be","bn","bh","bi","bs","br","bg","my","ca","ch","ce","ny","zh","cv","kw","co","cr","hr","cs","da","dv","nl","dz","en","eo","et","ee","fo","fj","fi","fr","ff","gl","ka","de","el","gn","gu","ht","ha","he","hz","hi","ho","hu","ia","id","ie","ga","ig","ik","io","is","it","iu","ja","jv","kl","kn","kr","ks","kk","km","ki","rw","ky","kv","kg","ko","ku","kj","la","lb","lg","li","ln","lo","lt","lu","lv","gv","mk","mg","ms","ml","mt","mi","mr","mh","mn","na","nv","nd","ne","ng","nb","nn","no","ii","nr","oc","oj","cu","om","or","os","pa","pi","fa","pl","ps","pt","qu","rm","rn","ro","ru","sa","sc","sd","se","sm","sg","sr","gd","sn","si","sk","sl","so","st","es","su","sw","ss","sv","ta","te","tg","th","ti","bo","tk","tl","tn","to","tr","ts","tt","tw","ty","ug","uk","ur","uz","ve","vi","vo","wa","cy","wo","fy","xh","yi","yo","za","zu"] 
     installed_dict = {"Afar": "aa","Afrikaans": "af","Akan": "ak","Shqip": "sq","Amharic": "am","Arabic": "ar","Aragonese": "an","Armenian": "hy","Assamese": "as","Avar, Magyar": "av","Avesta": "ae","Aymara": "ay","Azerbaijani, Turkish": "az","Bambara": "bm","Bashkir": "ba","Basque": "eu","Belarusian": "be","Bangla": "bn","Bhojpuri, hindi": "bh","Bislama": "bi","Bosnian": "bs","Breton": "br","Bulgarian": "bg","Burmese": "my","Catalan, Valencian": "ca","Chamoru": "ch","Chechen": "ce","Chewa": "ny","Chinese Traditional": "zh","Chuvash": "cv","Cornish": "kw","Corsican": "co","Cree": "cr","Croatian": "hr","Czech": "cs","danish": "da","Divehi": "dv","Dutch, Flemish": "nl","Dzongkha": "dz","English": "en","Esperanto": "eo","Estonian": "et","Ewe": "ee","Faroese": "fo","Fijian": "fj","Finnish": "fi","French": "fr","Fula": "ff","Galician": "gl","Georgian": "ka","German": "de","Greek": "el","Guarani": "gn","Gujarati": "gu","Haitian Creole": "ht","Hausa": "ha","Hebrew": "he","Herero": "hz","Hindi": "hi","Hiri Motu": "ho","Hungarian": "hu","Interlingua": "ia","Indonesian": "id","Interlingue": "ie","Irish": "ga","Igbo": "ig","Iñupiaq": "ik","Ido": "io","Icelandic": "is","Italian": "it","Inuktitut": "iu","Japanese": "ja","Tagalog": "jv","Greenlandic": "kl","Kannada": "kn","Kanuri": "kr","Kashmiri": "ks","Kazakh": "kk","Khmer": "km","Kikuyu": "ki","Rwandan": "rw","Kyrgyz": "ky","Komi": "kv","Kongo": "kg","korean": "ko","Kurdish": "ku","Kwanyama": "kj","Latin": "la","Luxembourgish": "lb","Ganda": "lg","Limburgish": "li","Lingala": "ln","Lao": "lo","Lithuanian": "lt","Luba-Katanga": "lu","Latvian": "lv","Manx": "gv","Macedonian": "mk","Malagasy": "mg","Malay": "ms","Malayalam": "ml","Maltese": "mt","Māori": "mi","Marathi": "mr","Marshallese": "mh","Mongolian": "mn","Nauruan": "na","Navajo": "nv","North Ndebele": "nd","Nepali": "ne","Ovambo": "ng","Bokmål": "nb","Nynorsk": "nn","Norwegian": "no","Nuosu": "ii","Ndebele": "nr","Occitan": "oc","Ojibwe": "oj","Church Slavonic": "cu","Oromo": "om","Odia": "or","Ossetian": "os","Punjabi": "pa","Hindi": "pi","Farsi": "fa","Polish": "pl","Pashto": "ps","Portuguese": "pt","Quechuan": "qu","Romansh": "rm","Rundi": "rn","Romanian, Moldavian": "ro","Russian": "ru","Sanskrit": "sa","Sardinian": "sc","Sindhi": "sd","Northern Sami": "se","Samoan": "sm","Sango": "sg","Serbian": "sr","Gaelic": "gd","Shona": "sn","Sinhala": "si","Slovak": "sk","Slovenian": "sl","Somali": "so","Sesotho": "st","Spanish": "es","Sundanese": "su","Swahili": "sw","Swazi": "ss","Swedish": "sv","Tamil": "ta","Telugu": "te","Tajik": "tg","Thai": "th","Tigrinya": "ti","Tibetan": "bo","Turkmen": "tk","Tagalog": "tl","Tswana": "tn","Tongan": "to","Turkish": "tr","Tsonga": "ts","Tatar": "tt","Twi": "tw","Tahitian": "ty","Uyghur": "ug","Ukrainian": "uk","Urdu": "ur","Uzbek": "uz","Venda": "ve","Vietnamese": "vi","Volapük": "vo","Walloon": "wa","Welsh": "cy","Wolof": "wo","Frisian": "fy","Xhosa": "xh","Yiddish": "yi","Yoruba": "yo","Zhuang": "za","Zulu": "zu"}
   # lang_codes = [lang.code for lang in installed_dict]
     print("Installed translation languages:", installed_dict)

     def get_lang_code(prompt):
     	while True:
           code = input(prompt).strip().lower()
           if code in available_languages:
               return code
           else:
               print("❌ Invalid code. Choose from:", installed_dict)

     from_code = get_lang_code("Enter source language code: ")
     to_code = get_lang_code("Enter target language code: ")


    
     from_lan = from_code
     to_lan = to_code
    
    

     installed_languages = argostranslate.translate.get_installed_languages()

     from_lang = list(filter(
	 lambda x: x.code == from_lan,
	 installed_languages))[0]
     to_lang = list(filter(
	 lambda x: x.code == to_lan,
	 installed_languages))[0]
     underlying_translation = from_lang.get_translation(to_lang) 


     argostranslatefiles.translate_file(
         underlying_translation,
         os.path.abspath(infile_path)
     )

   # Build translated filename with _ru before extension
     name, ext = os.path.splitext(infile)   # Split filename and extension
     translated_filename = f"{name}_{to_code}{ext}"  # Insert _ru
     translated_path = os.path.join(TRANSCRIPT_DIR, translated_filename)

    # Move translated file to translations folder
     os.makedirs(TRANSLATION_DIR, exist_ok=True)
     shutil.move(translated_path, os.path.join(TRANSLATION_DIR, translated_filename))
     print(f"✅ Translation moved to {TRANSLATION_DIR}/{translated_filename}")


def main():
    if input("Download YouTube video? (y/n): ").lower() == "y":
        download_youtube()
    if input("Download other video? (y/n): ").lower() == "y":
        download_video()
    if input("Transcribe video? (y/n): ").lower() == "y":
        transcribe()
    if input("Translate transcript? (y/n): ").lower() == "y":
        translate()


if __name__ == "__main__":
    main()
