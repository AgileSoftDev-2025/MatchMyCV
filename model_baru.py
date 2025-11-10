import fitz
import json
import re
import os
import pandas as pd
import gdown
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer, util


JOBSTREET_DRIVE_LINK = "https://docs.google.com/spreadsheets/d/1SasbACsxdJvFtZFxQFwQXZC05nQY3yX1/edit?gid=2108825113"
OUTPUT_EXCEL = "Hasil_Kecocokan_Semantik_CV_vs_Job.xlsx"

def get_drive_spreadsheet(drive_link: str, output_name: str):
    file_id = drive_link.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    print(f"Mengunduh data dari Google Drive...")
    gdown.download(export_url, output_name, quiet=False)
    return output_name

def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text("text") for page in doc)
    return text

def split_sections(text):
    sections = {}
    current = "general"
    for line in text.split("\n"):
        l = line.strip().lower()
        if any(h in l for h in ["education", "pendidikan"]):
            current = "education"
        elif any(h in l for h in ["experience", "pengalaman", "work"]):
            current = "experience"
        elif any(h in l for h in ["skill", "keahlian"]):
            current = "skills"
        sections.setdefault(current, []).append(line.strip())
    return {k: " ".join(v).strip() for k, v in sections.items()}

def normalize_skill(s):
    s = s.lower().strip()
    mapping = {
        "pyth": "python", "phyton": "python", "ms excel": "excel",
        "microsoft excel": "excel", "msexcel": "excel", "msoffice": "word",
        "ms word": "word", "power point": "powerpoint", "power-point": "powerpoint",
        "ppt": "powerpoint", "html5": "html", "htm": "html",
        "coordination": "koordinasi", "communication": "komunikasi",
        "adaptif": "adaptive", "selfmanagement": "self management",
        "self-manage": "self management"
    }
    for key, val in mapping.items():
        if s == key or s.startswith(key):
            return val
    return s

def safe_ner_call(pipeline_func, text, tokenizer, max_tokens=512):
    tokens = tokenizer.tokenize(text)
    step = max_tokens - 10
    results = []
    for i in range(0, len(tokens), step):
        chunk = tokenizer.convert_tokens_to_string(tokens[i:i+step])
        results.extend(pipeline_func(chunk))
    return results

def find_universities(text):
    patterns = [
        r"(universitas\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,4}\sUniversity)",
        r"(University\s+of\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(Institut\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(Politeknik\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(College\s+[A-Za-z0-9\.\-&' ]{2,60})"
    ]
    found, seen, result = [], {}, []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            name = re.sub(r"\s{2,}", " ", m.group(1).strip())
            if name.lower() not in seen:
                seen[name.lower()] = True
                result.append(name)
    return result

def extract_skills(full_text, skill_section_text, ner_pipeline, tokenizer):
    text_for_ner = skill_section_text if len(skill_section_text.strip()) > 5 else full_text
    ents_skill = safe_ner_call(ner_pipeline, text_for_ner, tokenizer)
    detected = [normalize_skill(ent["word"]) for ent in ents_skill if ent.get("entity_group","").upper()=="SKILL"]
    detected = sorted(set(detected))
    if detected:
        return detected
    fallback_keywords = [
        "python","java","sql","excel","word","powerpoint","html","css","javascript",
        "react","tableau","canva","git","linux","docker","pandas","numpy","tensorflow",
        "keras","scikit","power bi"
    ]
    text_low = full_text.lower()
    fallback_found = [kw for kw in fallback_keywords if re.search(rf"\b{re.escape(kw)}\b", text_low)]
    return sorted(set(normalize_skill(s) for s in fallback_found))

# ==============================================
# PARSER CV
# ==============================================
def parse_cv(pdf_path, ner_major, tokenizer_major, ner_skill, tokenizer_skill, jurusan_keywords):
    text = extract_text_pymupdf(pdf_path)
    sections = split_sections(text)
    education_section = sections.get("education", "")
    skill_section = sections.get("skills", "")
    experience_section = sections.get("experience", "")

    # Jurusan
    ents_major = safe_ner_call(ner_major, education_section or text, tokenizer_major)
    jurusan_candidates = [ent["word"].strip() for ent in ents_major if "LABEL_1" in ent["entity_group"]]
    jurusan = None
    if jurusan_candidates:
        jurusan = max(jurusan_candidates, key=len).title()
    else:
        for key in jurusan_keywords:
            if key in text.lower():
                jurusan = key.title()
                break
    jurusan = jurusan or "Tidak Terdeteksi"

    # Universitas
    unis = find_universities(education_section or text)
    chosen_uni = unis[-1] if unis else "-"
    pendidikan_final = f"{chosen_uni} - {jurusan}" if chosen_uni != "-" else jurusan

    # Skills
    skills_list = extract_skills(text, skill_section, ner_skill, tokenizer_skill)

    # Pengalaman
    pengalaman = [s.strip() for s in re.split(r"[.\n]", experience_section or text)
                  if any(x in s.lower() for x in ["intern","magang","staf","staff","project","experience"]) and len(s.strip()) > 5]
    pengalaman = list(dict.fromkeys(pengalaman)) or ["Tidak Terdeteksi"]

    return {
        "pendidikan_terakhir": pendidikan_final,
        "skills": skills_list,
        "pengalaman": pengalaman
    }

# ==============================================
# MAIN PROGRAM
# ==============================================
if __name__ == "__main__":
    job_file = get_drive_spreadsheet(JOBSTREET_DRIVE_LINK, "data_jobstreet.xlsx")
    df_jobs = pd.read_excel(job_file)

    print("Memuat model NER umum & khusus...")
    model_skill = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
    tokenizer_skill = AutoTokenizer.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
    ner_skill = pipeline("ner", model=model_skill, tokenizer=tokenizer_skill, aggregation_strategy="simple")

    model_major = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/bert-jurusan-it")
    tokenizer_major = AutoTokenizer.from_pretrained("iqbalrahmananda/bert-jurusan-it")
    ner_major = pipeline("ner", model=model_major, tokenizer=tokenizer_major, aggregation_strategy="simple")

    jurusan_keywords = ["informatika","teknik informatika","sistem informasi","data science","ai","machine learning"]

    pdf_path = input("Masukkan path file CV (PDF): ").strip()
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File {pdf_path} tidak ditemukan.")

    lokasi = input("Masukkan lokasi: ").strip()
    cv_data = parse_cv(pdf_path, ner_major, tokenizer_major, ner_skill, tokenizer_skill, jurusan_keywords)
    cv_data["lokasi"] = lokasi

    cv_text = " ".join([
        cv_data.get("pendidikan_terakhir", ""),
        " ".join(cv_data.get("skills", [])),
        " ".join(cv_data.get("pengalaman", [])),
        cv_data.get("lokasi", "")
    ])

    df_jobs["job_text"] = df_jobs.apply(
        lambda r: f"{r.get('title','')} {r.get('job_field','')} {r.get('requirement','')} {r.get('kategori','')} {r.get('level','')} {r.get('location','')}",
        axis=1
    )

    model_embed = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    job_embeddings = model_embed.encode(df_jobs["job_text"].tolist(), convert_to_tensor=True, normalize_embeddings=True)
    cv_embedding = model_embed.encode(cv_text, convert_to_tensor=True, normalize_embeddings=True)
    similarities = util.cos_sim(cv_embedding, job_embeddings)[0]
    df_jobs["Similarity_Score"] = similarities.cpu().numpy()
    df_jobs_sorted = df_jobs.sort_values(by="Similarity_Score", ascending=False)

    print(json.dumps(cv_data, indent=2, ensure_ascii=False))
    print("\n=== Hasil Kecocokan CV vs Job ===\n")
    for _, row in df_jobs_sorted.head(5).iterrows():
        print(f"{row['title']} | {row['company']} | {row['location']} | Skor: {row['Similarity_Score']*100:.2f}%")

    df_jobs_sorted.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Hasil disimpan ke {OUTPUT_EXCEL}")
