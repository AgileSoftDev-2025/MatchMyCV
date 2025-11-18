# 🧠 MatchMyCV — AI-powered Smart CV Analyzer & Job Recommendation Platform

MatchMyCV adalah platform berbasis web yang membantu pengguna menganalisis Curriculum Vitae (CV) secara otomatis dan memberikan rekomendasi pekerjaan berdasarkan profil kompetensi, pengalaman, serta latar belakang akademik. Platform ini dirancang untuk mendukung mahasiswa, fresh graduate, dan profesional dalam meningkatkan peluang karier mereka.

---

## 📌 Tujuan Proyek
- Membantu pengguna menganalisis CV dengan mudah
- Mengidentifikasi kekuatan & kelemahan CV
- Menyediakan rekomendasi pekerjaan yang relevan
- Meningkatkan performa CV terhadap Applicant Tracking System (ATS)
- Memberikan insight objektif terhadap profil kandidat

---

## 🔥 Fitur Utama
✅ Upload CV format PDF  
✅ Analisis konten CV (skills, education, experience)  
✅ Rekomendasi pekerjaan berbasis kompetensi  
✅ UI modern berbasis Tailwind CSS  
✅ Sistem autentikasi (Login & Register)  
✅ Tampilan hasil analisis yang user-friendly  

---

## 🧩 Teknologi yang Digunakan

| Layer | Teknologi |
|-------|----------|
| Frontend | Django Templates, HTML, CSS, Tailwind CSS |
| Backend | Python 3, Django |
| Database | SQLite (Default Development DB) |
| Authentication | Django Auth |
| Deployment | Local Development |
| Tools | VSCode, Git, Figma |

---

## 🧱 Arsitektur Sistem (High Level)

```mermaid
flowchart TD
A[User Upload CV] --> B[Django Backend]
B --> C[NLP Parsing Module]
C --> D[Skill Extraction]
C --> E[Experience Detection]
C --> F[Education Analysis]
D --> G[Job Recommendation Engine]
E --> G
F --> G
G --> H[Recommendation Output]
🗂️ Struktur Project
text
Copy code
matchmycv/
└─ matchmycv_website/
   ├─ cv_analyzer/               # Modul analisis CV
   ├─ information_pages/         # Landing page, FAQ, About
   ├─ user_authentication/       # Login & Register
   ├─ static/                    # Asset CSS, images, Tailwind
   │  ├─ css/
   │  └─ src/
   ├─ templates/                 # Base template Django
   │  ├─ base.html
   │  └─ navigation/
   ├─ tailwind.config.js         # Config Tailwind
   ├─ package.json               # Build tools frontend
   ├─ manage.py
   └─ settings.py
🏁 Instalasi & Setup Development
1️⃣ Clone Repository
bash
Copy code
git clone https://github.com/<username>/MatchMyCV.git
cd MatchMyCV/matchmycv_website
2️⃣ Setup Virtual Environment
bash
Copy code
python -m venv env
source env/Scripts/activate   # Windows
3️⃣ Install Dependencies Backend
bash
Copy code
pip install -r requirements.txt
4️⃣ Install Dependency Frontend (Tailwind CSS)
bash
Copy code
npm install
5️⃣ Jalankan Tailwind Watcher
bash
Copy code
npm run dev
6️⃣ Jalankan Server Django
bash
Copy code
python manage.py runserver
Akses website melalui:

cpp
Copy code
http://127.0.0.1:8000/
📄 Halaman Utama Aplikasi
Halaman	URL
Landing Page	/
Tentang Kami	/tentang-kami/
FAQ	/faq/
Analisis CV	/analisis-cv/
Hasil Rekomendasi	/analisis-cv/hasil-rekomendasi/
Login	/login/
Register	/register/

🧪 Status Pengembangan
Status	Fase
✅ UI Template	Completed
✅ Authentication
✅ CV Parsing Engine	Completed
✅ Job Recommendation Engine Completed
🔜 Export PDF Result	Planned
🔜 AI LLM Integration	Planned

📌 Roadmap Sprint
📍 Sprint 1 (Week 10–11)
Setup Django project

Landing page, FAQ, About

Authentication

📍 Sprint 2 (Week 12–13)
Upload CV page

Basic job recommendation logic

📍 Sprint 3 (Week 14–15)
Polishing UI

Enhancement recommendation engine

UAT & documentation

🧭 Known Issues
⚠ Tailwind CLI perlu environment Windows yang stabil
⚠ CV parsing masih dummy (prototype)
⚠ Hasil rekomendasi terbatas (early-stage model)

👥 Tim Pengembang MatchMyCV
NIM	Nama	Role
187231010	Adelia	Project Manager
187231011	Cokorda Istri Trisna Shanti Maharani Pemayun	Research & UI Writer
187231026	Muhammad Iqbal Rahmananda	Backend Developer
187231051	Virgie Septia Ferdy	Data Engineer / Analyzer
187231077	Raditya Nauval Ramadhan Putra Wibowo	Frontend Developer

Tim berkolaborasi melalui GitHub, Figma, dan komunikasi rutin.

🛠️ Tools Lingkungan Pengembangan
Tools	Kegunaan
VSCode	Code Editor
GitHub	Version Control
Figma	UI/UX Wireframing
Postman	API Testing (fase lanjut)

🔐 Security Notes
Tidak menyimpan data pengguna sensitif

Tidak menyimpan berkas CV di server (development mode)

Menggunakan hashing bawaan Django

🧬 Enhancement di Masa Depan
Dukungan format DOCX

Scoring ATS berbasis AI

Integrasi rekomendasi LinkedIn API

Export laporan rekomendasi PDF

Grafik skill radar chart

🤝 Kontribusi
Pull Request dipersilakan:

bash
Copy code
git checkout -b new-feature
git commit -m "Add feature X"
git push origin new-feature
Lalu buat Pull Request ✅

📧 Kontak & Bantuan
📨 Email: adelia.si@example.com (dummy akademik)
🛟 Bug report: Open GitHub issue

📜 License
MIT License — boleh digunakan untuk keperluan edukasi

⭐ Star this repo!
Jika project ini bermanfaat, bantu support dengan memberi:

mathematica
Copy code
⭐ Star
Terima kasih 🙌
— Tim MatchMyCV

