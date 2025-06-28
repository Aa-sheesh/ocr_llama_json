import os
import requests

# List of Indian language codes supported by Tesseract
indian_langs = [
    "asm",  # Assamese
    "ben",  # Bengali
    "guj",  # Gujarati
    "hin",  # Hindi
    "kan",  # Kannada
    "mal",  # Malayalam
    "mni",  # Meitei (Manipuri)
    "nep",  # Nepali
    "ori",  # Odia
    "pan",  # Punjabi
    "san",  # Sanskrit
    "sat",  # Santali
    "tam",  # Tamil
    "tel",  # Telugu
    "urd"   # Urdu
    "mar"   # Marathi
]

# Default tessdata directory on Windows
tessdata_dir = r"C:\Program Files\Tesseract-OCR\tessdata"

# Base URL for downloading traineddata files
base_url = "https://github.com/tesseract-ocr/tessdata/raw/main/{}.traineddata"

def download_traineddata(lang_code):
    url = base_url.format(lang_code)
    dest_path = os.path.join(tessdata_dir, f"{lang_code}.traineddata")

    if os.path.exists(dest_path):
        print(f"✅ {lang_code}.traineddata already exists.")
        return

    print(f"⬇️ Downloading {lang_code}.traineddata ...")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"✅ {lang_code}.traineddata saved.")
    else:
        print(f"❌ Failed to download {lang_code}. Status code: {response.status_code}")

if __name__ == "__main__":
    if not os.path.exists(tessdata_dir):
        print(f"❌ Tesseract tessdata folder not found at: {tessdata_dir}")
        print("👉 Please install Tesseract OCR or update the tessdata_dir path.")
    else:
        for lang in indian_langs:
            download_traineddata(lang)

        print("\n🎉 All Indian language traineddata files downloaded successfully.")
