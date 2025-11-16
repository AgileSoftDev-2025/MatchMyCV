from django.shortcuts import render

def landing_page(request):
    return render(request, 'information_pages/landing_page.html')

def about_us(request):
    return render(request, 'information_pages/tentang_kami.html')

def faq(request):
    faq_items = [
        {
            "question": "How does MatchMyCV work?",
            "answer": "Users upload their CV in PDF format and provide their location. The system extracts data from the CV, analyzes it using machine learning, and matches it with job listings to produce personalized recommendations."
        },
        {
            "question": "What file format is supported for CV uploads?",
            "answer": "The system currently supports PDF files only to ensure consistent text extraction and processing quality."
        },
        {
            "question": "Is MatchMyCV free to use?",
            "answer": "Yes, MatchMyCV is completely free for job seekers. You can upload CVs, browse matches, and view recommendations without any cost."
        },
        {
            "question": "How accurate are the job recommendations?",
            "answer": "Recommendation accuracy depends on the clarity of your CV and the relevance of job listings. Machine learning improves results as more data is processed."
        },
        {
            "question": "How long does the CV analysis take?",
            "answer": "CV analysis typically takes a few seconds, depending on file size and server load."
        },
        {
            "question": "Do I need to create an account?",
            "answer": "Yes. you need to create an account before you can upload your CV and receive job recommendations."
        },
        {
            "question": "Is my data secure?",
            "answer": "Yes. Uploaded CVs are processed securely, and no personal information is stored permanently on the server."
        },
        {
            "question": "Can I update or re-upload my CV?",
            "answer": "Absolutely. You can upload a new CV anytime to receive updated job recommendations."
        }
    ]
    return render(request, "information_pages/faq.html", {"faq_items": faq_items})