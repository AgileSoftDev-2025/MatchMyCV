pip install pytesseract pdf2image pillow spacy
apt install tesseract-ocr
pip install transformers
pip install tabulate
pip install sentence_transformers
pip install pymupdf
from sentence_transformers import SentenceTransformer, util
import fitz
import json
from google.colab import files
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import re

# ----------------- Load Models -----------------
# Gunakan AutoTokenizer dan AutoModelForTokenClassification agar model dan tokenizer cocok
model_general = AutoModelForTokenClassification.from_pretrained("cahya/bert-base-indonesian-NER")
tokenizer_general = AutoTokenizer.from_pretrained("cahya/bert-base-indonesian-NER")
ner_general = pipeline("ner", model=model_general, tokenizer=tokenizer_general, grouped_entities=True)

model_skill = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
tokenizer_skill = AutoTokenizer.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
ner_skill = pipeline("ner", model=model_skill, tokenizer=tokenizer_skill, aggregation_strategy="simple")

# ----------------- Extract Text -----------------
def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# ----------------- Normalisasi Skill -----------------
def normalize_skill(s):
    s = s.lower().strip()
    mapping = {
        "pyth": "python",
        "phyton": "python",
        "ms excel": "excel",
        "microsoft excel": "excel",
        "msexcel": "excel",
        "msoffice": "word",
        "ms word": "word",
        "power point": "powerpoint",
        "power-point": "powerpoint",
        "ppt": "powerpoint",
        "html5": "html",
        "htm": "html",
        "coordination": "koordinasi",
        "communication": "komunikasi",
        "adaptif": "adaptive",
        "selfmanagement": "self management",
        "self-manage": "self management"
    }
    for key, val in mapping.items():
        if s == key or s.startswith(key):
            return val
    return s

# ----------------- Potong Teks -----------------
def safe_ner_call(pipeline_func, text, tokenizer, max_tokens=512):
    """Potong teks agar tidak melebihi 512 token sebelum diproses NER"""
    tokens = tokenizer.tokenize(text)
    chunks = []
    step = max_tokens - 10  # sedikit lebih pendek untuk jaga-jaga
    for i in range(0, len(tokens), step):
        chunk = tokenizer.convert_tokens_to_string(tokens[i:i+step])
        chunks.append(chunk)
    results = []
    for chunk in chunks:
        results.extend(pipeline_func(chunk))
    return results

# ----------------- Parsing CV -----------------
def parse_cv(pdf_path):
    text = extract_text_pymupdf(pdf_path)
    text_lower = text.lower()
    lines = [re.sub(r"[^a-zA-Z0-9\s]", "", l.strip()) for l in text_lower.split("\n") if l.strip()]

    edu_keywords = ["universitas", "university", "institute", "institut", "college", "academy"]
    jurusan_keywords = [
        "informatika", "information system", "information systems", "computer science",
        "sistem informasi", "teknik informatika", "ilmu komputer", "data science",
        "teknologi informasi", "rekayasa perangkat lunak", "software engineering",
        "cyber security", "ai", "artificial intelligence"
    ]
    ignore_keywords = [
        "toefl", "ielts", "elpt", "sertifikat", "certificate", "training", "pelatihan",
        "sma", "smk", "lembaga", "organisasi", "himpunan", "pramuka", "kepramukaan",
        "lomba", "juara", "kompetisi", "seminar"
    ]

    # ----------------- Pendidikan -----------------
    pendidikan = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if any(bad in line for bad in ignore_keywords):
            i += 1
            continue

        if any(word in line for word in edu_keywords):
            full_line = line
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if not any(bad in next_line for bad in ignore_keywords) and any(k in next_line for k in jurusan_keywords):
                    full_line += " " + next_line
            pendidikan.append(full_line.strip())
        i += 1

    def capitalize_words(s):
        return " ".join([w.capitalize() for w in s.split()])

    last_edu = capitalize_words(pendidikan[-1]) if pendidikan else "-"

    # ----------------- Skills -----------------
    ents_skill = safe_ner_call(ner_skill, text, tokenizer_skill)
    detected_skills = [normalize_skill(ent["word"]) for ent in ents_skill if ent["entity_group"].upper() == "SKILL"]

    manual_skills = [
        "excel", "word", "powerpoint", "python", "html",
        "koordinasi", "adaptive", "self management", "komunikasi"
    ]
    all_skills = sorted(set(normalize_skill(s) for s in (detected_skills + manual_skills)))

    # ----------------- Pengalaman -----------------
    pengalaman = [l for l in lines if any(x in l for x in ["internship", "magang", "pengalaman", "kerja"])]
    ents_general = safe_ner_call(ner_general, text, tokenizer_general)
    for ent in ents_general:
        if ent["entity_group"] in ["ORG", "MISC"] and "intern" in ent["word"].lower():
            pengalaman.append(ent["word"])

    pengalaman = list(dict.fromkeys(pengalaman))  # hapus duplikat tapi jaga urutan

    return {
        "pendidikan_terakhir": last_edu,
        "skills": all_skills,
        "pengalaman": pengalaman
    }

# ----------------- Upload dan Eksekusi -----------------
uploaded = files.upload()
for filename in uploaded.keys():
    cv_file = filename

cv_data = parse_cv(cv_file)
user_workplace = input("Masukkan Lokasi: ")
cv_data["lokasi"] = user_workplace

print(json.dumps(cv_data, indent=2, ensure_ascii=False))
