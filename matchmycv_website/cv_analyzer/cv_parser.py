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
    
    # Basic cleanup
    s = re.sub(r"\s+\(.*?\)", "", s)  
    s = s.replace("\u2013", "-")
    s = s.replace("\u2014", "-")
    s = s.strip(". ,;:\")")

    # Common misspellings and variations
    mapping = {
        "pyth": "python", "phyton": "python", 
        "ms excel": "excel", "microsoft excel": "excel", "msexcel": "excel", 
        "msoffice": "office", "ms word": "word", 
        "power point": "powerpoint", "power-point": "powerpoint", "ppt": "powerpoint",
        "html5": "html", "htm": "html",
        "postgres": "postgresql", "postgre": "postgresql", "postgress": "postgresql",
        "node.js": "nodejs", "node js": "nodejs", 
        "react.js": "reactjs", "react js": "reactjs",
        "vue.js": "vuejs", "vue js": "vuejs",
        "tab": "tableau", "table": "tableau", "tableu": "tableau",
        "fig": "figma", "figm": "figma",
        "can": "canva", "canv": "canva",
        "nginx": "nginx",
    }

    for key, val in mapping.items():
        if s == key or s.startswith(key + " ") or s.startswith(key + "-"):
            return val

    # Fix some stray characters
    s = s.replace("/", " ")
    s = s.replace("\\", " ")
    s = re.sub(r"\s{2,}", " ", s)

    return s


def pretty_skill(s):
    """Return a readable display form for a normalized skill"""
    s = s or ""
    s_low = s.lower()
    
    # Acronyms that should be uppercase
    acronyms = {"sql", "html", "css", "aws", "api", "nlp", "ai", "ml", "db", "ios", "android", "js", "php", "c++", "c#", "r"}
    
    # Special formatting map
    pretty_map = {
        "nodejs": "Node.js",
        "reactjs": "React.js",
        "vuejs": "Vue.js",
        "postgresql": "PostgreSQL",
        "mongodb": "MongoDB",
        "powerpoint": "PowerPoint",
        "excel": "Microsoft Excel",
        "word": "Microsoft Word",
        "docker": "Docker",
        "git": "Git",
        "github": "GitHub",
        "gitlab": "GitLab",
        "tableau": "Tableau",
        "canva": "Canva",
        "figma": "Figma",
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "numpy": "NumPy",
        "pandas": "pandas",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "python": "Python",
        "java": "Java",
        "php": "PHP",
        "laravel": "Laravel",
        "django": "Django",
        "google sheets": "Google Sheets",
        "google docs": "Google Docs",
        "machine learning": "Machine Learning",
        "deep learning": "Deep Learning",
        "data science": "Data Science",
        "data analytics": "Data Analytics",
    }

    if s_low in pretty_map:
        return pretty_map[s_low]
    if s_low in acronyms:
        return s.upper()

    # Keep c++ and c# properly
    if s_low in {"c++", "c#"}:
        return s_low

    # Title case for multi-word skills
    return " ".join([w.upper() if w.lower() in acronyms else w.capitalize() for w in s_low.split()])

def split_skill_candidates(skill_section_text):
    """Split a skills section into candidate skill phrases."""
    if not skill_section_text:
        return []
    text = skill_section_text
    # normalize common bullet characters to newlines
    text = text.replace("•", "\n").replace("·", "\n").replace("\u2022", "\n")
    # replace slashes between tokens with commas to split later
    text = re.sub(r"\s*/\s*", ",", text)
    candidates = []
    for line in text.splitlines():
        # Remove leading bullet markers or numbers
        line = re.sub(r"^[\-\*\s\d\.]+", "", line).strip()
        if not line:
            continue
        # split by common separators
        parts = re.split(r"[,;\\|]", line)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # further split words connected with ' and '
            subparts = re.split(r"\band\b|\&", p, flags=re.I)
            for sp in subparts:
                sp = sp.strip()
                if len(sp) > 1:
                    candidates.append(sp)
    # preserve order but unique
    seen = set()
    out = []
    for c in candidates:
        c_norm = normalize_skill(re.sub(r"[^A-Za-z0-9+#\- ]", " ", c)).strip()
        if c_norm and c_norm not in seen:
            seen.add(c_norm)
            out.append(c_norm)
    return out


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
    """Extract skills from CV with improved token merging and readable output"""
    
    text_for_ner = skill_section_text if skill_section_text and len(skill_section_text.strip()) > 5 else full_text
    ents_skill = safe_ner_call(_ner_skill, text_for_ner, _tokenizer_skill)

    detected_with_pos = []
    # Collect from NER with available positions
    for idx, ent in enumerate(ents_skill):
        label = ent.get("entity_group") or ent.get("label") or ""
        if str(label).upper() in ("SKILL", "LABEL_1", "S"):
            word = ent.get("word", "").replace("##", "").strip()
            word = re.sub(r"[^A-Za-z0-9+#\-\. ]+", " ", word).strip()
            if not word or len(word) < 2:
                continue
            norm = normalize_skill(word)
            pos = ent.get("start", None) or ent.get("index", idx)
            detected_with_pos.append((pos, norm, word))  # Keep original too

    # Parse the skills section by splitting common separators
    section_candidates = split_skill_candidates(skill_section_text)

    # Merge split tokens that should be together
    merged_tokens = []
    i = 0
    while i < len(detected_with_pos):
        current_pos, current_norm, current_word = detected_with_pos[i]
        
        # Check if next token should be merged
        if i + 1 < len(detected_with_pos):
            next_pos, next_norm, next_word = detected_with_pos[i + 1]
            
            # Merge common patterns
            merged = None
            current_lower = current_norm.lower()
            next_lower = next_norm.lower()
            
            # Tableau = Table + au
            if current_lower in ["table", "tab"] and next_lower in ["au", "eau"]:
                merged = "tableau"
            # Figma = Fig + ma
            elif current_lower in ["fig", "fi"] and next_lower in ["ma", "gma"]:
                merged = "figma"
            # Canvas = Can + va/vas
            elif current_lower == "can" and next_lower in ["va", "vas"]:
                merged = "canva"
            # Google Sheets/Docs
            elif current_lower == "google" and next_lower in ["sheets", "sheet", "docs", "doc"]:
                merged = f"google {next_norm}"
            # Machine Learning
            elif current_lower == "machine" and next_lower == "learning":
                merged = "machine learning"
            # Deep Learning
            elif current_lower == "deep" and next_lower == "learning":
                merged = "deep learning"
            # Data Science
            elif current_lower == "data" and next_lower in ["science", "analytics", "analyst"]:
                merged = f"data {next_norm}"
            # Node.js
            elif current_lower == "node" and next_lower in ["js", "javascript"]:
                merged = "nodejs"
            # React.js
            elif current_lower == "react" and next_lower in ["js", "javascript"]:
                merged = "reactjs"
            
            if merged:
                merged_tokens.append(normalize_skill(merged))
                i += 2  # Skip next token
                continue
        
        # No merge, add current token
        merged_tokens.append(current_norm)
        i += 1

    # Add section-parsed candidates
    ordered = []
    seen = set()

    # Add merged NER-detected skills
    for val in merged_tokens:
        if not val:
            continue
        val_norm = val.lower()
        if val_norm not in seen and len(val_norm) > 1:
            seen.add(val_norm)
            ordered.append(val_norm)

    # Add section-parsed candidates
    for cand in section_candidates:
        cand_norm = cand.lower()
        if cand_norm not in seen and len(cand_norm) > 1:
            seen.add(cand_norm)
            ordered.append(cand_norm)

    # Fallback: scan whole text for common keywords if nothing found
    if not ordered:
        fallback_keywords = [
            "python", "java", "sql", "excel", "word", "powerpoint", "html", "css",
            "javascript", "react", "tableau", "canva", "git", "linux", "docker",
            "figma", "pandas", "numpy", "tensorflow", "vue", "angular", "nodejs",
            "machine learning", "deep learning", "data science", "google sheets",
            "google docs"
        ]
        text_low = full_text.lower()
        for kw in fallback_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text_low) and kw not in seen:
                seen.add(kw)
                ordered.append(kw)

    # Remove very short or invalid skills
    ordered = [s for s in ordered if len(s) > 1 and not s.isdigit()]

    # Final pretty formatting
    final = [pretty_skill(normalize_skill(s)) for s in ordered if s]
    
    # Remove duplicates while preserving order
    seen2 = set()
    pretty_unique = []
    for s in final:
        key = s.lower()
        # Filter out nonsense skills
        if key not in seen2 and len(key) > 1 and key not in ['au', 'ma', 'gma', 'fig', 'table']:
            seen2.add(key)
            pretty_unique.append(s)

    return pretty_unique

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


# cv_parser.py
import os
from pathlib import Path
from django.conf import settings
import pandas as pd

def get_job_recommendations(cv_data, location, num_results=6):
    """Get job recommendations based on CV analysis"""
    
    # Gunakan path dari settings
    job_file_path = settings.JOB_DATA_PATH
    
    # Validasi file exists
    if not os.path.exists(job_file_path):
        raise FileNotFoundError(
            f"Job dataset not found at: {job_file_path}\n"
            f"Current BASE_DIR: {settings.BASE_DIR}\n"
            f"Please ensure the file exists in the correct location."
        )
    
    try:
        df_jobs = pd.read_excel(job_file_path)
    except Exception as e:
        raise ValueError(f"Failed to read job dataset: {str(e)}")
    
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