import fitz
import json
import re
import pandas as pd
import gdown
from google.colab import files
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer, util  # <-- pakai embedding semantic
import torch

# ----------------- Ambil Data Job dari Google Drive (Google Spreadsheet) -----------------
JOBSTREET_DRIVE_LINK = "https://docs.google.com/spreadsheets/d/1SasbACsxdJvFtZFxQFwQXZC05nQY3yX1/edit?gid=2108825113"

def get_drive_spreadsheet(drive_link, output_name):
    file_id = drive_link.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    gdown.download(export_url, output_name, quiet=False)
    return output_name

job_file = get_drive_spreadsheet(JOBSTREET_DRIVE_LINK, "data_jobstreet.xlsx")
df_jobs = pd.read_excel(job_file)

# ----------------- Load Models -----------------
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
        "pyth": "python", "phyton": "python", "ms excel": "excel", "microsoft excel": "excel",
        "msexcel": "excel", "msoffice": "word", "ms word": "word", "power point": "powerpoint",
        "power-point": "powerpoint", "ppt": "powerpoint", "html5": "html", "htm": "html",
        "coordination": "koordinasi", "communication": "komunikasi", "adaptif": "adaptive",
        "selfmanagement": "self management", "self-manage": "self management"
    }
    for key, val in mapping.items():
        if s == key or s.startswith(key):
            return val
    return s

# ----------------- Aman untuk teks panjang -----------------
def safe_ner_call(pipeline_func, text, tokenizer, max_tokens=512):
    tokens = tokenizer.tokenize(text)
    chunks = []
    step = max_tokens - 10
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
    ignore_keywords = [
        "toefl", "ielts", "elpt", "sertifikat", "certificate", "training",
        "pelatihan", "sma", "smk", "organisasi", "pramuka"
    ]

    pendidikan = []
    for i, line in enumerate(lines):
        if any(bad in line for bad in ignore_keywords):
            continue
        if any(word in line for word in edu_keywords):
            pendidikan.append(line)
    last_edu = pendidikan[-1].title() if pendidikan else "-"

    # Skills
    ents_skill = safe_ner_call(ner_skill, text, tokenizer_skill)
    detected_skills = [normalize_skill(ent["word"]) for ent in ents_skill if ent["entity_group"].upper() == "SKILL"]
    manual_skills = [
        "excel", "word", "powerpoint", "python", "html",
        "koordinasi", "adaptive", "self management", "komunikasi"
    ]
    all_skills = sorted(set(normalize_skill(s) for s in (detected_skills + manual_skills)))

    # Pengalaman
    pengalaman = [l for l in lines if any(x in l for x in ["internship", "magang", "pengalaman", "kerja"])]
    ents_general = safe_ner_call(ner_general, text, tokenizer_general)
    for ent in ents_general:
        if ent["entity_group"] in ["ORG", "MISC"] and "intern" in ent["word"].lower():
            pengalaman.append(ent["word"])
    pengalaman = list(dict.fromkeys(pengalaman))

    return {
        "pendidikan_terakhir": last_edu,
        "skills": all_skills,
        "pengalaman": pengalaman
    }

# ----------------- Upload CV -----------------
print("Silakan upload file CV (PDF) kamu:")
uploaded = files.upload()
for filename in uploaded.keys():
    cv_file = filename

cv_data = parse_cv(cv_file)
cv_data["lokasi"] = input("Masukkan Lokasi: ")

# ----------------- Gabungkan Data CV -----------------
cv_text = " ".join([
    cv_data.get("pendidikan_terakhir", ""),
    " ".join(cv_data.get("skills", [])),
    " ".join(cv_data.get("pengalaman", [])),
    cv_data.get("lokasi", "")
])

# ----------------- Gabungkan Job Text -----------------
df_jobs["job_text"] = df_jobs.apply(
    lambda row: f"{row.get('title', '')} {row.get('job_field', '')} "
                f"{row.get('requirement', '')} {row.get('kategori', '')} "
                f"{row.get('level', '')} {row.get('location', '')}",
    axis=1
)

# ----------------- Semantic Embedding -----------------
model_embed = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

job_embeddings = model_embed.encode(df_jobs["job_text"].tolist(), convert_to_tensor=True, normalize_embeddings=True)
cv_embedding = model_embed.encode(cv_text, convert_to_tensor=True, normalize_embeddings=True)

# Hitung cosine similarity (lebih cerdas daripada TF-IDF)
similarities = util.cos_sim(cv_embedding, job_embeddings)[0]

# Tambahkan ke DataFrame
df_jobs["Similarity_Score"] = similarities.cpu().numpy()
df_jobs_sorted = df_jobs.sort_values(by="Similarity_Score", ascending=False)

# ----------------- Output -----------------
print("\n=== HASIL KEC0C0KAN CV vs JOB (Semantic Matching) ===\n")
for idx, row in df_jobs_sorted.head(5).iterrows():
    print(f"Posisi: {row['title']}")
    print(f"Perusahaan: {row['company']}")
    print(f"Lokasi: {row['location']}")
    print(f"Bidang: {row['job_field']}")
    print(f"Kecocokan: {row['Similarity_Score']*100:.2f}%")
    print(f"Link: {row['link']}")
    print("-" * 80)

output_name = "Hasil_Kecocokan_Semantik_CV_vs_Job.xlsx"
df_jobs_sorted.to_excel(output_name, index=False)
print(f"\nHasil disimpan sebagai: {output_name}")
