import os
import torch
import pytesseract
from PIL import Image
from ollama import Client
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from IndicTransToolkit.processor import IndicProcessor
import re

def clean_ocr_text(text):
    text = re.sub(r"[|_]+", "", text)  # Remove pipes, underscores
    text = re.sub(r"(?<=\S)-\n(?=\S)", "", text)  # Join hyphenated words broken by newline
    text = re.sub(r"\n+", "\n", text)  # Collapse multiple newlines
    text = re.sub(r"\s{2,}", " ", text)  # Collapse extra spaces
    return text.strip()


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OLLAMA_URL = "http://localhost:11434"
OUTPUT_DIR = "./output"

def img_grayscale(IMAGE_FILE):
    img = Image.open(IMAGE_FILE)
    bw = img.convert("L")
    bw.save(IMAGE_FILE)
    print(f"Converted {IMAGE_FILE} to grayscale")

def run_ocr_on_image(image_path, tess_lang):
    custom_config = (
        "--oem 1 "
        "--psm 4 "
        "-c preserve_interword_spaces=1 "
        "-c load_system_dawg=false "
        "-c load_freq_dawg=false "
        "-c tessedit_do_invert=0 "
        "-c textonly_pdf=1 "
        "-c char_blacklist=_{}[]<>|~^` "
    )
    try:
        image = Image.open(image_path)
        image = image.convert("L").point(lambda x: 0 if x < 180 else 255, '1')  # Binary threshold
        text = pytesseract.image_to_string(image, lang=tess_lang, config=custom_config)
        return text
    except Exception as e:
        print(f"\n[ERROR] Could not process image {image_path}: {e}")
        return ""


class IndicTranslator:
    ISO2_TO_TAG = {
        "en": "eng_Latn", "hi": "hin_Deva", "bn": "ben_Beng", "gu": "guj_Gujr",
        "mr": "mar_Deva", "ta": "tam_Taml", "te": "tel_Telu", "kn": "kan_Knda",
        "ml": "mal_Mlym", "pa": "pan_Guru", "or": "ory_Orya", "ur": "urd_Arab"
    }
    LANG_NAME_MAP = {
        "Hindi": "hin_Deva", "English": "eng_Latn", "Bengali": "ben_Beng", "Gujarati": "guj_Gujr",
        "Marathi": "mar_Deva", "Tamil": "tam_Taml", "Telugu": "tel_Telu", "Kannada": "kan_Knda",
        "Malayalam": "mal_Mlym", "Punjabi": "pan_Guru", "Odia": "ory_Orya", "Urdu": "urd_Arab"
    }
    INDIC_LANG_TAGS = set(LANG_NAME_MAP.values()) - {"eng_Latn"}

    def __init__(self):
        self.processor = IndicProcessor(inference=True)

    def select_model_name(self, src_tag, tgt_tag):
        if src_tag == "eng_Latn" and tgt_tag in self.INDIC_LANG_TAGS:
            return "ai4bharat/indictrans2-en-indic-dist-200M"
        elif src_tag in self.INDIC_LANG_TAGS and tgt_tag == "eng_Latn":
            return "ai4bharat/indictrans2-indic-en-dist-200M"
        elif src_tag in self.INDIC_LANG_TAGS and tgt_tag in self.INDIC_LANG_TAGS:
            return "ai4bharat/indictrans2-indic-indic-dist-320M"
        return None

    def load_translation_model(self, model_name):
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True)
        return tokenizer, model

    def translate(self, input_text, src_tag, tgt_tag):
        model_name = self.select_model_name(src_tag, tgt_tag)
        if not model_name:
            raise ValueError("Unsupported source-target language combination.")
        tokenizer, model = self.load_translation_model(model_name)
        processed = self.processor.preprocess_batch([input_text], src_lang=src_tag, tgt_lang=tgt_tag)
        batch = tokenizer(processed, truncation=True, padding="longest", return_tensors="pt")
        with torch.inference_mode():
            tokens = model.generate(**batch, use_cache=True, max_length=256, num_beams=5)
        decoded = tokenizer.batch_decode(tokens, skip_special_tokens=True)
        return self.processor.postprocess_batch(decoded, lang=tgt_tag)[0]

def summarize_with_ollama(text, host=OLLAMA_URL, model="gemma3:1b"):
    client = Client(host=host)
    prompt = (
        "You are a smart document assistant. "
        "Given this noisy OCR text from a newspaper article, do the following:\n"
        "1. Try to identify the article title (if present).\n"
        "2. Clean up the text by fixing formatting errors.\n"
        "3. Write a short summary.\n\n"
        "Return the result as a JSON object with fields: title, clean_text, summary.\n\n"
        f"ARTICLE OCR TEXT:\n{text}"
    )
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]

def save_output_files(src, ocr_text, translated_text, ollama_response):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, f"{src}+ocr_test.txt"), "w", encoding="utf-8") as f:
        f.write(ocr_text)
    with open(os.path.join(OUTPUT_DIR, f"{src}+translated_text_test.txt"), "w", encoding="utf-8") as f:
        f.write(translated_text)
    with open(os.path.join(OUTPUT_DIR, f"{src}+ollama_json_test.json"), "w", encoding="utf-8") as f:
        f.write(ollama_response)
    print(f"\nocr saved to: {OUTPUT_DIR}/{src}+ocr_test.txt")
    print(f"translation saved to: {OUTPUT_DIR}/{src}+translated_text_test.txt")
    print(f"JSON saved to: {OUTPUT_DIR}/{src}+ollama_json_test.json")

if __name__ == "__main__":
    src = "guj_Gujr"
    IMAGE_FILE = "guj_Gujr_img.jpg"
    TESS_LANG = f"{src.split('_')[0]}+eng"
    print("Turning into black and white... \n")
    img_grayscale(IMAGE_FILE)
    ocr_text = run_ocr_on_image(IMAGE_FILE, TESS_LANG)
    ocr_text=clean_ocr_text(ocr_text)
    print("OCR:\n", ocr_text)
    translator = IndicTranslator()
    translated_text = translator.translate(ocr_text, src, "eng_Latn")
    print("translation:\n", translated_text)
    ollama_response = summarize_with_ollama(translated_text)
    print("ollama:\n", ollama_response)
    save_output_files(src, ocr_text, translated_text, ollama_response)
