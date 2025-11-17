import fitz
import json
import re
import pandas as pd
import gdown
from google.colab import files
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer, util
import torch

JOBSTREET_DRIVE_LINK = "https://docs.google.com/spreadsheets/d/1SasbACsxdJvFtZFxQFwQXZC05nQY3yX1/edit?gid=2108825113"

def get_drive_spreadsheet(drive_link, output_name):
    file_id = drive_link.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    gdown.download(export_url, output_name, quiet=False)
    return output_name

job_file = get_drive_spreadsheet(JOBSTREET_DRIVE_LINK, "data_jobstreet.xlsx")
df_jobs = pd.read_excel(job_file)

print("Memuat model umum...")
model_general = AutoModelForTokenClassification.from_pretrained("cahya/bert-base-indonesian-NER")
tokenizer_general = AutoTokenizer.from_pretrained("cahya/bert-base-indonesian-NER")
ner_general = pipeline("ner", model=model_general, tokenizer=tokenizer_general, grouped_entities=True)

print("Memuat model skill...")
model_skill = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
tokenizer_skill = AutoTokenizer.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
ner_skill = pipeline("ner", model=model_skill, tokenizer=tokenizer_skill, aggregation_strategy="simple")

print("Memuat model IndoBERT khusus jurusan IT...")
model_major = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/bert-jurusan-it")
tokenizer_major = AutoTokenizer.from_pretrained("iqbalrahmananda/bert-jurusan-it")
ner_major = pipeline("ner", model=model_major, tokenizer=tokenizer_major, aggregation_strategy="simple")

jurusan_keywords = [
    "informatika","teknik informatika","ilmu komputer","computer science",
    "sistem informasi","information systems","information system",
    "teknologi informasi","information technology","it",
    "rekayasa perangkat lunak","software engineering",
    "data science","data analytics","data engineering","data analyst",
    "artificial intelligence","ai","machine learning","deep learning",
    "cyber security","keamanan siber","jaringan komputer","computer network",
    "cloud computing","komputasi awan","big data","internet of things","iot",
    "robotika","robotics","teknik komputer","computer engineering",
    "sistem komputer","system computer","teknologi digital","digital business",
    "bisnis digital","information management","manajemen informasi",
    "information management system","teknologi informasi dan komunikasi","ict",
    "information and communication technology","bioinformatics","bioinformatika",
    "computational science","komputasi ilmiah","geoinformatics","geoinformatika",
    "information security","security engineering","multimedia","animasi",
    "game development","pengembangan game","teknologi game","computer vision",
    "augmented reality","virtual reality","mixed reality","extended reality","xr",
    "software technology","teknologi perangkat lunak","teknologi informasi bisnis",
    "information technology management","smart system","sistem cerdas",
    "knowledge engineering","human computer interaction","interaksi manusia komputer","hci"
]

def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def safe_ner_call(pipeline_func, text, tokenizer, max_tokens=512):
    tokens = tokenizer.tokenize(text)
    step = max_tokens - 10
    results = []
    for i in range(0, len(tokens), step):
        chunk = tokenizer.convert_tokens_to_string(tokens[i:i+step])
        results.extend(pipeline_func(chunk))
    return results

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

def find_universities(text):
    patterns = [
        r"(universitas\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,4}\sUniversity)",
        r"(University\s+of\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(Institut\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(Politeknik\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(College\s+[A-Za-z0-9\.\-&' ]{2,60})"
    ]

    found = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            name = m.group(1).strip()
            name = re.sub(r"\s{2,}", " ", name)
            found.append((name, m.start(), m.end()))

    seen, result = {}, []
    for u, s, e in found:
        key = u.lower()
        if key not in seen:
            seen[key] = (u, s, e)
            result.append((u, s, e))
    return result

def extract_skills(full_text, skill_section_text, ner_pipeline, tokenizer):
    text_for_ner = skill_section_text if len(skill_section_text.strip()) > 5 else full_text
    ents_skill = safe_ner_call(ner_pipeline, text_for_ner, tokenizer)

    detected = []
    for ent in ents_skill:
        if ent.get("entity_group", "").upper() == "SKILL":
            w = ent["word"].replace("##", "").strip()
            w = re.sub(r"[^a-zA-Z0-9+\-# ]+", "", w)
            if len(w) > 1:
                w = normalize_skill(w)
                detected.append(w.lower())

    merged = []
    skip_next = False
    for i in range(len(detected)):
        if skip_next:
            skip_next = False
            continue
        if i + 1 < len(detected):
            two = detected[i] + detected[i + 1]
            if two in ["figma", "tableau", "vuejs", "reactjs"]:
                merged.append(two)
                skip_next = True
                continue
        merged.append(detected[i])
    detected = merged

    custom_map = {
        "table": "tableau",
        "fig": "figma",
        "au": "figma",
        "gma": "figma"
    }
    detected = [custom_map.get(s, s) for s in detected]

    detected = sorted(set(detected))
    if detected:
        return detected

    fallback_keywords = [
        "python","java","sql","excel","word","powerpoint","html","css","javascript","react",
        "tableau","canva","git","linux","docker","pandas","numpy","tensorflow","keras",
        "scikit","power bi","figma"
    ]
    text_low = full_text.lower()
    fallback_found = [kw for kw in fallback_keywords if re.search(rf"\b{re.escape(kw)}\b", text_low)]
    return sorted(set(normalize_skill(s) for s in fallback_found))

def parse_cv(pdf_path):
    text = extract_text_pymupdf(pdf_path)
    sections = split_sections(text)
    education_section = sections.get("education", "")
    skill_section = sections.get("skills", "")
    experience_section = sections.get("experience", "")

    ents_major = safe_ner_call(ner_major, education_section or text, tokenizer_major)
    jurusan_candidates = [ent["word"].strip() for ent in ents_major if "LABEL_1" in ent["entity_group"]]
    jurusan = None
    if jurusan_candidates:
        cleaned = [re.sub(r"(?i).*(majoring in|majors in|major in)\s*", "", j).strip() for j in jurusan_candidates]
        jurusan = max(cleaned, key=len).title()
    else:
        for key in jurusan_keywords:
            if key in text.lower():
                jurusan = key.title()
                break
    if not jurusan:
        jurusan = "Tidak Terdeteksi"

    unis = find_universities(education_section or text)
    chosen_uni = "-"
    if unis:
        if jurusan != "Tidak Terdeteksi":
            pos = text.lower().find(jurusan.lower())
            best, best_dist = None, None
            for u_name, u_start, u_end in unis:
                dist = abs(u_start - pos) if pos != -1 else 0
                if best is None or dist < best_dist:
                    best, best_dist = u_name, dist
            chosen_uni = best
        else:
            chosen_uni = unis[-1][0]
    chosen_uni = re.sub(r"\s+", " ", chosen_uni).strip().title() if chosen_uni else "-"

    pendidikan_parts = []
    if chosen_uni and chosen_uni != "-":
        pendidikan_parts.append(chosen_uni)
    if jurusan and jurusan != "Tidak Terdeteksi" and jurusan.lower() not in (chosen_uni or "").lower():
        pendidikan_parts.append(jurusan)
    pendidikan_final = " - ".join(pendidikan_parts) if pendidikan_parts else "-"

    skills_list = extract_skills(text, skill_section, ner_skill, tokenizer_skill)

    pengalaman = []
    source_text = experience_section if len(experience_section.strip()) > 10 else text
    for sent in re.split(r"[.\n]", source_text):
        if any(x in sent.lower() for x in ["intern", "magang", "staf", "staff", "project", "experience"]):
            pengalaman.append(sent.strip())
    pengalaman = [p for p in pengalaman if len(p) > 5]
    pengalaman = list(dict.fromkeys(pengalaman))

    return {
        "pendidikan_terakhir": pendidikan_final,
        "skills": skills_list,
        "pengalaman": pengalaman if pengalaman else ["Tidak Terdeteksi"],
        "lokasi": ""
    }

def calculate_weighted_similarity(cv_data, df_jobs, model_embed):
    """
    Menghitung similarity dengan bobot:
    - Pengalaman: 40%
    - Skills: 40% 
    - Lokasi: 20%
    """
    cv_text_weighted = " ".join([
        " ".join(cv_data.get("pengalaman", [])) * 2,  # 40%
        " ".join(cv_data.get("skills", [])) * 2,      # 40%
        cv_data.get("lokasi", "") * 1                 # 20%
    ])
    
    df_jobs["job_text_weighted"] = df_jobs.apply(
        lambda row: " ".join([
            f"{row.get('requirement', '')} {row.get('level', '')}" * 2,  # 40%
            f"{row.get('title', '')} {row.get('job_field', '')} {row.get('kategori', '')}" * 2,  # 40%
            str(row.get('location', '')) * 1  # 20%
        ]),
        axis=1
    )
    
    job_embeddings = model_embed.encode(
        df_jobs["job_text_weighted"].tolist(), 
        convert_to_tensor=True, 
        normalize_embeddings=True
    )
    cv_embedding = model_embed.encode(
        [cv_text_weighted], 
        convert_to_tensor=True, 
        normalize_embeddings=True
    )
    
    similarities = util.cos_sim(cv_embedding, job_embeddings)[0]
    return similarities

print("Silakan upload file CV (PDF) kamu:")
uploaded = files.upload()
for filename in uploaded.keys():
    cv_file = filename

cv_data = parse_cv(cv_file)
cv_data["lokasi"] = input("Masukkan Lokasi: ")

model_embed = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
weighted_scores = calculate_weighted_similarity(cv_data, df_jobs, model_embed)
df_jobs["Similarity_Score"] = weighted_scores.cpu().numpy()
df_jobs_sorted = df_jobs.sort_values(by="Similarity_Score", ascending=False)

print("\n OUTPUT JSON:")
print(json.dumps(cv_data, indent=2, ensure_ascii=False))

print(f"\n REKOMENDASI LOWONGAN DI {cv_data['lokasi'].upper()}:\n")

lokasi_user = cv_data["lokasi"].lower()
df_lokasi_cocok = df_jobs_sorted[
    df_jobs_sorted["location"].str.lower().str.contains(lokasi_user, na=False)
]

if len(df_lokasi_cocok) > 0:
    df_tampil = df_lokasi_cocok.head(5)
else:
    print(f"⚠️ Tidak ditemukan lowongan di {cv_data['lokasi']}, menampilkan semua lokasi:")
    df_tampil = df_jobs_sorted.head(5)

for idx, row in df_tampil.iterrows():
    lokasi_match = "✅" if cv_data["lokasi"].lower() in str(row['location']).lower() else "❌"
    
    print(f"Posisi: {row['title']}")
    print(f"Perusahaan: {row['company']}")
    print(f"Lokasi: {row['location']} {lokasi_match}")
    print(f"Bidang: {row['job_field']}")
    print(f"Kecocokan: {row['Similarity_Score']*100:.2f}%")
    print(f"Link: {row['link']}")
    print("-" * 80)