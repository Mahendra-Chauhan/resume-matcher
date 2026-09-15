# AI-Powered Resume Matcher with Chatbot

A Flask app that uploads resumes (PDF, with OCR fallback for scans), matches
them against a job description using sentence embeddings, ranks candidates,
and answers recruiter questions through a simple chatbot.

## Approach & Key Decisions
- **Text extraction:** pdfplumber first; falls back to Tesseract OCR only when
  a PDF returns almost no text (i.e. it's a scanned image).
- **Matching:** `sentence-transformers` (all-MiniLM-L6-v2) computes semantic
  similarity between resume and JD text, combined with keyword-based skill
  overlap and experience matching into one final score.
- **Chatbot:** rule-based (regex/keyword) query parsing — reliable and
  grounded in actual extracted data, no hallucination risk.
- **Storage:** SQLite — zero setup, no server needed, anyone can run this
  with just `pip install` and `flask run`.
- **Challenges:** OCR accuracy varies with scan quality; rule-based skill
  matching won't catch every synonym or phrasing.

## Libraries Used
| Library | Purpose |
|---|---|
| Flask | Web framework |
| Flask-SQLAlchemy | Database ORM |
| pdfplumber | PDF text extraction |
| pytesseract / pdf2image | OCR for scanned PDFs |
| sentence-transformers | Semantic embeddings |
| groq | Optional LLM enrichment (free tier) |

## Setup
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Install Tesseract OCR and Poppler (system-level, not pip):
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
python app.py
```

## Usage
1. Visit `http://127.0.0.1:5000/` — upload 10+ PDF resumes
2. Visit `/jd` — paste a job description
3. Visit `/rank` — see the ranked candidate list
4. Use the chat box on the results page to ask questions like
   "List candidates proficient in Python with over 2 years experience"

## Known Limitations
- Skill list is keyword-based (services/parser.py) — extend `SKILL_KEYWORDS`
  for domains beyond tech.
- OCR quality depends on scan clarity.