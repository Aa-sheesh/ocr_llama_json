import torch
from IndicTransToolkit.processor import IndicProcessor # NOW IMPLEMENTED IN CYTHON !!
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
device = "cuda" if torch.cuda.is_available() else "cpu"

ip = IndicProcessor(inference=True)
tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True)
model = AutoModelForSeq2SeqLM.from_pretrained("ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True).to(device)

sentences = [
    "This is a test sentence.",
    "This is another longer different test sentence.",
    "Please send an SMS to 9876543210 and an email on newemail123@xyz.com by 15th October, 2023.",
]

batch = ip.preprocess_batch(sentences, src_lang="eng_Latn", tgt_lang="hin_Deva", visualize=False) # set it to visualize=True to print a progress bar
batch = tokenizer(batch, padding="longest", truncation=True, max_length=256, return_tensors="pt").to(device)

with torch.inference_mode():
    outputs = model.generate(**batch, num_beams=5, num_return_sequences=1, max_length=256)

outputs = tokenizer.batch_decode(outputs, skip_special_tokens=True, clean_up_tokenization_spaces=True)
outputs = ip.postprocess_batch(outputs, lang="hin_Deva")
print(outputs)