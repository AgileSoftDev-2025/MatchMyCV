!pip install pytesseract pdf2image pillow spacy
!apt install tesseract-ocr
!pip install transformers
!pip install pdfplumber
!pip install tabulate
!pip install pymupdf

import fitz
from google.colab import files
from tabulate import tabulate
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

# ----------------- 1. Load NER models -----------------
ner_general = pipeline("ner", model="cahya/bert-base-indonesian-NER", grouped_entities=True)
ner_skill = pipeline("ner", model="iqbalrahmananda/my-indo-bert-skill", aggregation_strategy="simple")

# ----------------- 2. Load Similarity model -----------------
model_sim = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
