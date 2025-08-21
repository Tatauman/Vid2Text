from setuptools import setup, find_packages

setup(
    name="video-translator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "yt-dlp",
        "openai-whisper",
        "argostranslate",
        "argostranslate-files"
    ],
    entry_points={
        "console_scripts": [
            "video-translator=translator.main:main",
        ],
    },
    author="Your Name",
    description="A CLI tool to download, transcribe, and translate videos.",
    url="https://github.com/yourusername/video-translator",
    python_requires=">=3.8",
)
