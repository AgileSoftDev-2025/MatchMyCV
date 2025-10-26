pip install pytesseract pdf2image pillow spacy
apt install tesseract-ocr
pip install transformers
pip install tabulate
pip install sentence_transformers
pip install pymupdf
from sentence_transformers import SentenceTransformer, util

# ----------------- Load 2 model -----------------
# Model lama untuk pendidikan & pengalaman
ner_general = pipeline("ner", model="cahya/bert-base-indonesian-NER", grouped_entities=True)

# Model baru hasil fine-tune untuk skill
ner_skill = pipeline(
    "ner",
    model="iqbalrahmananda/my-indo-bert-skill",
    aggregation_strategy="simple"
)

# ----------------- Fungsi Extract Text (PyMuPDF) -----------------
def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# ----------------- Fungsi Parsing CV -----------------
def parse_cv(pdf_path):
    text = extract_text_pymupdf(pdf_path)

    # lowercase untuk konsistensi
    text_lower = text.lower()
    lines = [l.strip() for l in text_lower.split("\n") if l.strip()]

    # ---- Pendidikan ----
    pendidikan = []
    for line in lines:
        if "universitas" in line or "university" in line or "institute" in line:
            pendidikan.append(line)
    last_edu = pendidikan[-1] if pendidikan else None

    ents_general = ner_general(text)
    for ent in ents_general:
        if ent["entity_group"] == "ORG" and "universitas" in ent["word"].lower():
            last_edu = ent["word"]

    # ---- Skills (pakai model baru) ----
    ents_skill = ner_skill(text)
    for ent in ents_skill:
        print(ent)   # debug: lihat apa aja yang ketangkap
    skills = [ent["word"] for ent in ents_skill if ent["entity_group"] == "SKILL"]

    # ---- Pengalaman ----
    pengalaman = []
    for line in lines:
        if "internship" in line or "magang" in line or "pengalaman" in line:
            pengalaman.append(line)

    for ent in ents_general:
        if ent["entity_group"] in ["ORG", "MISC"] and "intern" in ent["word"].lower():
            pengalaman.append(ent["word"])

    return {
        "pendidikan_terakhir": last_edu,
        "skills": list(set(skills)),
        "pengalaman": list(set(pengalaman))
    }

# ----------------- Upload CV PDF -----------------
uploaded = files.upload()
for filename in uploaded.keys():
    cv_file = filename

cv_data = parse_cv(cv_file)

# ----------------- Input Lokasi Manual -----------------
user_workplace = input("Masukkan Lokasi Workplace: ")
cv_data["lokasi_workplace"] = user_workplace

# ----------------- Cetak Hasil Rapi -----------------
table = [
    ["Pendidikan Terakhir", cv_data["pendidikan_terakhir"] if cv_data["pendidikan_terakhir"] else "-"],
    ["Lokasi", cv_data["lokasi_workplace"] if cv_data["lokasi_workplace"] else "-"],
    ["Skills", ", ".join(cv_data["skills"]) if cv_data["skills"] else "-"],
    ["Pengalaman", ", ".join(cv_data["pengalaman"]) if cv_data["pengalaman"] else "-"]
]
print(tabulate(table, headers=["Kategori", "Hasil"], tablefmt="grid"))


# 1️⃣ Load model multilingual
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

# 2️⃣ Contoh input CV
cv_text = """
Lokasi Workplace: Jakarta
+---------------------+-------------------------------+
| Kategori            | Hasil                         |
+=====================+===============================+
| Pendidikan Terakhir | universitas airlangga         |
+---------------------+-------------------------------+
| Lokasi              | Jakarta                       |
+---------------------+-------------------------------+
| Skills              | pyth, powerpoint, html, excel |
+---------------------+-------------------------------+
| Pengalaman          | internship d’besto            |
+---------------------+-------------------------------+
"""

# 3️⃣ Contoh data lowongan (struktur dictionary)
job_descriptions = [
    {
        "title": "Data Scientist",
        "company": "PT. Teknologi Nusantara",
        "location": "Jakarta",
        "job_field": "Data & Analytics",
        "work_type": "Full-time",
        "salary": "Rp 10.000.000 - Rp 15.000.000",
        "requirement": "Menguasai Python, Machine Learning, dan analisis data",
        "posted": "3 hari lalu",
        "image": "https://example.com/logo1.png",
        "link": "https://example.com/job/123",
        "date_posted": "2025-09-25"
    },
    {
        "title": "Business Intelligence Analyst",
        "company": "PT. Data Inovasi",
        "location": "Surabaya",
        "job_field": "Business Intelligence",
        "work_type": "Hybrid",
        "salary": "Rp 8.000.000 - Rp 12.000.000",
        "requirement": "Kemampuan SQL dan PowerBI",
        "posted": "1 minggu lalu",
        "image": "https://example.com/logo2.png",
        "link": "https://example.com/job/456",
        "date_posted": "2025-09-18"
    },
    {
        "title": "Web Developer",
        "company": "Creative Studio",
        "location": "Bandung",
        "job_field": "Software Development",
        "work_type": "Remote",
        "salary": "Rp 7.000.000 - Rp 10.000.000",
        "requirement": "Pengalaman React dan Node.js",
        "posted": "5 hari lalu",
        "image": "https://example.com/logo3.png",
        "link": "https://example.com/job/789",
        "date_posted": "2025-09-22"
    }
]

# 4️⃣ Buat fungsi untuk gabungkan field penting jadi satu string (untuk similarity)
def build_job_text(job):
    return f"{job['title']} {job['company']} {job['location']} {job['job_field']} " \
           f"{job['work_type']} {job['salary']} {job['requirement']}"

# 5️⃣ Generate embeddings
cv_embedding = model.encode(cv_text, convert_to_tensor=True)
job_embeddings = [model.encode(build_job_text(job), convert_to_tensor=True) for job in job_descriptions]

# 6️⃣ Hitung cosine similarity
cosine_scores = [util.cos_sim(cv_embedding, job_emb).item() for job_emb in job_embeddings]

# 7️⃣ Threshold & Hasil
THRESHOLD = 0.3

print("=== HASIL REKOMENDASI LOWONGAN UNTUK CV ===")
for job, score in zip(job_descriptions, cosine_scores):
    status = "Cocok ✅" if score >= THRESHOLD else "Tidak Cocok ❌"
    print(f"\n🏢 {job['title']} - {job['company']}")
    print(f"📍 {job['location']} | 💼 {job['job_field']} | 💰 {job['salary']}")
    print(f"📝 Requirement: {job['requirement']}")
    print(f"🔗 {job['link']}")
    print(f"Similarity Score: {score:.4f} → {status}")
