import os
import torch
import fasttext
import streamlit as st
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from utils.IndicTransToolkit.IndicTransToolkit.processor import IndicProcessor

class IndicTranslatorApp:
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    ISO2_TO_TAG = {
        "en": "eng_Latn", "as": "asm_Beng", "bn": "ben_Beng", "brx": "brx_Deva", "doi": "doi_Deva",
        "gom": "gom_Deva", "gu": "guj_Gujr", "hi": "hin_Deva", "kn": "kan_Knda", "kas": "kas_Arab",
        "kas_Deva": "kas_Deva", "mai": "mai_Deva", "ml": "mal_Mlym", "mni": "mni_Beng",
        "mni_Mtei": "mni_Mtei", "mr": "mar_Deva", "ne": "npi_Deva", "or": "ory_Orya",
        "pa": "pan_Guru", "sa": "san_Deva", "sat": "sat_Olck", "snd": "snd_Arab", "snd_Deva": "snd_Deva",
        "ta": "tam_Taml", "te": "tel_Telu", "ur": "urd_Arab"
    }
    LANG_NAME_MAP = {
        "English": "eng_Latn", "Assamese": "asm_Beng", "Bengali": "ben_Beng", "Bodo": "brx_Deva", "Dogri": "doi_Deva",
        "Konkani": "gom_Deva", "Gujarati": "guj_Gujr", "Hindi": "hin_Deva", "Kannada": "kan_Knda", "Kashmiri": "kas_Arab",
        "Kashmiri (Dev)": "kas_Deva", "Maithili": "mai_Deva", "Malayalam": "mal_Mlym", "Manipuri": "mni_Beng",
        "Manipuri (Meitei)": "mni_Mtei", "Marathi": "mar_Deva", "Nepali": "npi_Deva", "Odia": "ory_Orya",
        "Punjabi": "pan_Guru", "Sanskrit": "san_Deva", "Santali": "sat_Olck", "Sindhi": "snd_Arab",
        "Sindhi (Dev)": "snd_Deva", "Tamil": "tam_Taml", "Telugu": "tel_Telu", "Urdu": "urd_Arab"
    }
    INDIC_LANG_TAGS = set(LANG_NAME_MAP.values()) - {"eng_Latn"}
    LANG_NAMES_SORTED = sorted(["English"] + list(set(LANG_NAME_MAP.keys()) - {"English"}))

    def __init__(self):
        self.processor = IndicProcessor(inference=True)
        self.fasttext_model = self.load_fasttext_model()

    def load_fasttext_model(self):
        path = "./models/lid.176.bin"
        if not os.path.exists(path):
            st.error("FastText model not found. Download it:\nhttps://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin")
            return None
        return fasttext.load_model(path)

    def load_translation_model(self, model_name):
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.DEVICE == "cuda" else torch.float32,
            attn_implementation="flash_attention_2" if self.DEVICE == "cuda" else None
        ).to(self.DEVICE)
        return tokenizer, model

    def detect_language(self, text):
        pred, conf = self.fasttext_model.predict(text.strip().replace("\n", " "), k=1)
        iso2 = pred[0].replace("__label__", "")
        src_tag = self.ISO2_TO_TAG.get(iso2)
        return iso2, src_tag, conf[0]

    def select_model_name(self, src_tag, tgt_tag):
        if src_tag == "eng_Latn" and tgt_tag in self.INDIC_LANG_TAGS:
            return "ai4bharat/indictrans2-en-indic-dist-200M"
        elif src_tag in self.INDIC_LANG_TAGS and tgt_tag == "eng_Latn":
            return "ai4bharat/indictrans2-indic-en-dist-200M"
        elif src_tag in self.INDIC_LANG_TAGS and tgt_tag in self.INDIC_LANG_TAGS:
            return "ai4bharat/indictrans2-indic-indic-dist-320M"
        return None

    def translate(self, input_text, src_tag, tgt_tag):
        model_name = self.select_model_name(src_tag, tgt_tag)
        if not model_name:
            raise ValueError("Unsupported source-target language combination.")

        tokenizer, model = self.load_translation_model(model_name)
        processed = self.processor.preprocess_batch([input_text], src_lang=src_tag, tgt_lang=tgt_tag)
        batch = tokenizer(processed, truncation=True, padding="longest", return_tensors="pt").to(self.DEVICE)

        with torch.inference_mode():
            tokens = model.generate(**batch, use_cache=True, min_length=0, max_length=256, num_beams=5)

        decoded = tokenizer.batch_decode(tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return self.processor.postprocess_batch(decoded, lang=tgt_tag)[0]

    def run(self):
        st.title("IndicTrans2 Translator (Auto Language Detection)")
        input_text = st.text_area("Enter text to translate", height=160)
        tgt_lang_name = st.selectbox("Select Target Language", self.LANG_NAMES_SORTED)
        translate_btn = st.button("Translate")

        if translate_btn and input_text.strip():
            with st.spinner("Translating..."):
                if not self.fasttext_model:
                    st.stop()

                iso2, src_tag, confidence = self.detect_language(input_text)
                tgt_tag = self.LANG_NAME_MAP.get(tgt_lang_name)

                if not src_tag or not tgt_tag:
                    st.error(f"Unsupported language mapping: {iso2} → {tgt_lang_name}")
                    st.stop()

                st.write(f"Detected Language: `{iso2}` → `{src_tag}` (Confidence: {confidence:.2f})")
                st.write(f"Target Language Tag: `{tgt_tag}`")

                try:
                    result = self.translate(input_text, src_tag, tgt_tag)
                    st.success("Translation Complete:")
                    st.text_area("Translated Text", result, height=200)
                except Exception as e:
                    st.error(f"Translation failed: {e}")

if __name__ == "__main__":
    app = IndicTranslatorApp()
    app.run()
