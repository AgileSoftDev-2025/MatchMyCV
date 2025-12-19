import fitz  
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer, util
from django.conf import settings
import os

_models_loaded = False
_ner_general = None
_ner_skill = None
_ner_major = None
_model_embed = None
_tokenizer_general = None
_tokenizer_skill = None
_tokenizer_major = None

def load_models():
    """Load all ML models once at startup"""
    global _models_loaded, _ner_general, _ner_skill, _ner_major, _model_embed
    global _tokenizer_general, _tokenizer_skill, _tokenizer_major
    
    if _models_loaded:
        return
    
    print("Loading ML models...")
    
    # Load general NER model
    model_general = AutoModelForTokenClassification.from_pretrained("cahya/bert-base-indonesian-NER")
    _tokenizer_general = AutoTokenizer.from_pretrained("cahya/bert-base-indonesian-NER")
    _ner_general = pipeline("ner", model=model_general, tokenizer=_tokenizer_general, grouped_entities=True)
    
    # Load skill NER model
    model_skill = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
    _tokenizer_skill = AutoTokenizer.from_pretrained("iqbalrahmananda/my-indo-bert-skill")
    _ner_skill = pipeline("ner", model=model_skill, tokenizer=_tokenizer_skill, aggregation_strategy="simple")
    
    # Load major NER model
    model_major = AutoModelForTokenClassification.from_pretrained("iqbalrahmananda/bert-jurusan-it")
    _tokenizer_major = AutoTokenizer.from_pretrained("iqbalrahmananda/bert-jurusan-it")
    _ner_major = pipeline("ner", model=model_major, tokenizer=_tokenizer_major, aggregation_strategy="simple")
    
    # Load embedding model
    _model_embed = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    _models_loaded = True
    print("All models loaded successfully!")


JURUSAN_KEYWORDS = [
    "informatika", "teknik informatika", "ilmu komputer", "computer science",
    "sistem informasi", "information systems", "information system",
    "teknologi informasi", "information technology", "it",
    "rekayasa perangkat lunak", "software engineering",
    "data science", "data analytics", "data engineering", "data analyst",
    "artificial intelligence", "ai", "machine learning", "deep learning",
    "cyber security", "keamanan siber", "jaringan komputer", "computer network",
]


def extract_text_pymupdf(pdf_path):
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    doc.close()
    return text


def safe_ner_call(pipeline_func, text, tokenizer, max_tokens=512):
    """Split text into chunks for NER processing"""
    tokens = tokenizer.tokenize(text)
    step = max_tokens - 10
    results = []
    for i in range(0, len(tokens), step):
        chunk = tokenizer.convert_tokens_to_string(tokens[i:i+step])
        results.extend(pipeline_func(chunk))
    return results


def split_sections(text):
    """Split CV text into sections"""
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
    """Normalize skill names"""
    s = s.lower().strip()
    mapping = {
        "pyth": "python", "phyton": "python", "ms excel": "excel", 
        "microsoft excel": "excel", "msexcel": "excel", "msoffice": "word",
        "ms word": "word", "power point": "powerpoint", "power-point": "powerpoint",
        "ppt": "powerpoint", "html5": "html", "htm": "html",
    }
    for key, val in mapping.items():
        if s == key or s.startswith(key):
            return val
    return s


def find_universities(text):
    """Find university names in text"""
    patterns = [
        r"(universitas\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,4}\sUniversity)",
        r"(University\s+of\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(Institut\s+[A-Za-z0-9\.\-&' ]{2,60})",
        r"(Politeknik\s+[A-Za-z0-9\.\-&' ]{2,60})",
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


def extract_skills(full_text, skill_section_text):
    """Extract skills from CV with improved token merging"""
    text_for_ner = skill_section_text if len(skill_section_text.strip()) > 5 else full_text
    ents_skill = safe_ner_call(_ner_skill, text_for_ner, _tokenizer_skill)
    
    detected = []
    for ent in ents_skill:
        if ent.get("entity_group", "").upper() == "SKILL":
            w = ent["word"].replace("##", "").strip()
            w = re.sub(r"[^a-zA-Z0-9+\-# ]+", "", w)
            if len(w) > 1:
                w = normalize_skill(w)
                detected.append(w.lower())
    
    merged = []
    i = 0
    while i < len(detected):
        current = detected[i]
        
        if i + 1 < len(detected):
            next_token = detected[i + 1]
            combined = current + next_token
        
            multi_token_skills = {
                "tableau": ["table", "au", "tab", "leau"],
                "figma": ["fig", "ma", "fi", "gma"],
                "github": ["git", "hub"],
                "mongodb": ["mongo", "db"],
                "postgresql": ["postgre", "sql", "post"],
                "javascript": ["java", "script"],
                "powerpoint": ["power", "point"],
            }
            
            matched = False
            for skill_name, tokens in multi_token_skills.items():
                if current in tokens and next_token in tokens:
                    merged.append(skill_name)
                    i += 2
                    matched = True
                    break
            
            if not matched:
                merged.append(current)
                i += 1
        else:
            merged.append(current)
            i += 1
    
    detected = merged
    partial_map = {
        "table": "tableau",
        "au": "tableau",
        "tab": "tableau",
        "fig": "figma",
        "fi": "figma",
        "gma": "figma",
        "hub": "github",
        "mongo": "mongodb",
        "postgre": "postgresql",
    }
    
    detected = sorted(set(detected))
    
    if detected:
        return detected

    fallback_keywords = [
        "python", "java", "sql", "excel", "word", "powerpoint", "html", "css",
        "javascript", "react", "tableau", "canva", "git", "linux", "docker",
        "figma", "pandas", "numpy", "tensorflow", "vue", "angular", "nodejs"
    ]
    text_low = full_text.lower()
    fallback_found = [kw for kw in fallback_keywords if re.search(rf"\b{re.escape(kw)}\b", text_low)]
    return sorted(set(normalize_skill(s) for s in fallback_found))


def parse_cv(pdf_path):
    """Main CV parsing function"""
    load_models()  
    
    text = extract_text_pymupdf(pdf_path)
    sections = split_sections(text)
    education_section = sections.get("education", "")
    skill_section = sections.get("skills", "")
    experience_section = sections.get("experience", "")
    
    ents_major = safe_ner_call(_ner_major, education_section or text, _tokenizer_major)
    jurusan_candidates = [ent["word"].strip() for ent in ents_major if "LABEL_1" in ent["entity_group"]]
    jurusan = None
    if jurusan_candidates:
        cleaned = [re.sub(r"(?i).*(majoring in|majors in|major in)\s*", "", j).strip() for j in jurusan_candidates]
        jurusan = max(cleaned, key=len).title()
    else:
        for key in JURUSAN_KEYWORDS:
            if key in text.lower():
                jurusan = key.title()
                break
    if not jurusan:
        jurusan = "Tidak Terdeteksi"
    
    # Extract university
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

    skills_list = extract_skills(text, skill_section)
    
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
    }


def calculate_weighted_similarity(cv_data, df_jobs):
    """Calculate weighted similarity between CV and jobs"""
    load_models()  
    
    cv_text_weighted = " ".join([
        " ".join(cv_data.get("pengalaman", [])) * 2,  # 40%
        " ".join(cv_data.get("skills", [])) * 2,      # 40%
        cv_data.get("lokasi", "") * 1                 # 20%
    ])
    
    df_jobs["job_text_weighted"] = df_jobs.apply(
        lambda row: " ".join([
            f"{row.get('requirement', '')} {row.get('level', '')}" * 2,
            f"{row.get('title', '')} {row.get('job_field', '')} {row.get('kategori', '')}" * 2,
            str(row.get('location', '')) * 1
        ]),
        axis=1
    )
    
    job_embeddings = _model_embed.encode(
        df_jobs["job_text_weighted"].tolist(),
        convert_to_tensor=True,
        normalize_embeddings=True
    )
    cv_embedding = _model_embed.encode(
        [cv_text_weighted],
        convert_to_tensor=True,
        normalize_embeddings=True
    )
    
    similarities = util.cos_sim(cv_embedding, job_embeddings)[0]
    return similarities


def get_job_recommendations(cv_data, location, num_results=6):
    """Get job recommendations based on CV analysis"""
    job_file_path = r'C:\Users\adeli\MatchMyCV\job_street_scrapper\data_csv\jobs_data_jobstreet(2025-11-28 2383).xlsx'
    # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # job_file_path = os.path.join(
    #     BASE_DIR,
    #     "..", "..", "..", "..",
    #     "job_street_scrapper",
    #     "data_csv",
    #     "jobs_data_jobstreet(2025-11-28 2383).xlsx"
    # )

    # job_file_path = "../../../../../../job_street_scrapper/data_csv/jobs_data_jobstreet(2025-11-28 2383).xlsx"

    if not os.path.exists(job_file_path):
        raise FileNotFoundError(f"Job dataset not found at {job_file_path}")
    
    df_jobs = pd.read_excel(job_file_path)
    
    cv_data["lokasi"] = location
    
    weighted_scores = calculate_weighted_similarity(cv_data, df_jobs)
    df_jobs["Similarity_Score"] = weighted_scores.cpu().numpy()
    df_jobs_sorted = df_jobs.sort_values(by="Similarity_Score", ascending=False)
    
    if location.lower() != "all":
        df_lokasi_cocok = df_jobs_sorted[
            df_jobs_sorted["location"].str.lower().str.contains(location.lower(), na=False)
        ]
        if len(df_lokasi_cocok) > 0:
            df_tampil = df_lokasi_cocok.head(num_results)
        else:
            df_tampil = df_jobs_sorted.head(num_results)
    else:
        df_tampil = df_jobs_sorted.head(num_results)
    
    # Convert to list of dicts
    results = []
    for idx, row in df_tampil.iterrows():
        results.append({
            'title': row['title'],
            'company': row['company'],
            'location': row['location'],
            'job_field': row.get('job_field', 'N/A'),
            'similarity_score': float(row['Similarity_Score'] * 100),
            'link': row.get('link', '#'),
            'requirement': row.get('requirement', ''),
            'level': row.get('level', ''),
        })
    
    return results