# 🪪 MatchMyCV — Website Rekomendasi Lowongan Kerja Berbasis Analisis CV

**MatchMyCV** adalah platform berbasis web yang membantu pengguna menganalisis *Curriculum Vitae (CV)* secara otomatis dan memberikan rekomendasi pekerjaan yang relevan berdasarkan isi CV (keahlian, pengalaman, pendidikan) serta preferensi lokasi pengguna.

Proyek ini menggunakan *Natural Language Processing (NLP)* dengan model **IndoBERT** dan **Cosine Similarity** untuk mencocokkan makna semantik antara CV dan deskripsi pekerjaan.

---

## 🎯 Tujuan Proyek
- Mengembangkan sistem rekomendasi kerja berbasis IndoBERT dan Cosine Similarity.  
- Membantu pengguna menemukan lowongan kerja yang relevan dengan CV mereka.  
- Mengatasi keterbatasan sistem pencarian kerja berbasis kata kunci (*keyword matching*).  
- Mengoptimalkan proses pencarian kerja agar lebih cepat, efisien, dan akurat.  

---

## 🔥 Fitur Utama
1. **Analisis CV Otomatis**  
   - Pengguna dapat mengunggah CV untuk mendapatkan rekomendasi pekerjaan relevan.  
   - Sistem menganalisis *skills*, *education*, dan *experience* menggunakan NLP.  
   - Hasil rekomendasi diambil dari hasil *scraping* situs JobStreet.  

2. **Upload CV Format PDF (Multi-Language)**  
   - Mendukung CV dalam berbagai bahasa (Indonesia & Inggris).  

3. **Sistem Autentikasi Pengguna (Login & Register)**  
   - Menggunakan Django Authentication.  

4. **Antarmuka Modern & Responsif**  
   - Dibangun menggunakan Tailwind CSS.  

---

## 🧩 Teknologi yang Digunakan
- Backend: Django, Python (NLP, IndoBERT, Cosine Similarity)
- Frontend: HTML, Tailwind CSS
- Database: SQLite (Default Development DB) 
- Scraping: Jobstreet Custom Bot
- Authentication: Django Auth
- Tools: VSCode, Git, Figma
- Testing: Behave + Selenium (BDD Scenarios)

---


## ⚙️ Instalasi & Setup Development
```bash
1️⃣ Clone Repository
git clone https://github.com/<username>/MatchMyCV.git
cd MatchMyCV/matchmycv_website

2️⃣ Setup Virtual Environment
python -m venv env
source env/Scripts/activate   # Untuk Windows

3️⃣ Install Dependencies Backend
pip install -r requirements.txt

4️⃣ Install Dependencies Frontend (Tailwind CSS)
npm install

5️⃣ Jalankan Tailwind Watcher
npm run dev

6️⃣ Jalankan Server Django
python manage.py runserver
```
## 🧠 Cara Menjalankan Komponen Tambahan
### Scraping JobStreet
```bash
cd job_street_scrapper
python scrapping_jobstreet_re.py
```

### Testing (BDD - Behave + Selenium)
```bash
cd bdd_testing
behave features/<nama-feature>/<nama-feature>.feature
```

## 👥 Tim Pengembang MatchMyCV

| NIM | Nama | Role |
|-----|------|------|
| 187231010 | **Adelia** | Project Manager |
| 187231011 | **Cokorda Istri Trisna Shanti Maharani Pemayun** | UI/UX & Front-End Developer |
| 187231026 | **Muhammad Iqbal Rahmananda** | Machine Learning Engineer |
| 187231051 | **Virgie Septia Ferdy** | UI/UX & Front-End Developer |
| 187231077 | **Raditya Nauval Ramadhan Putra Wibowo** | Machine Learning Engineer |

## ⭐ Star this repo!
Jika project ini bermanfaat, bantu support dengan memberi:

## Terima kasih 🙌
— Tim MatchMyCV

