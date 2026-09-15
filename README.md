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

------------------------------
Details :-

## What happens when you run `python app.py`

1. Python loads `.env` (via `dotenv`) — makes `GROQ_API_KEY` available if you're using it.
2. Flask creates the `app` object and connects it to `resume_matcher.db` (SQLite).
3. The `sentence-transformers` model (`all-MiniLM-L6-v2`) loads into memory **once** — this is the one-time delay you see in the terminal ("Loading weights...").
4. Flask starts a local web server on `http://127.0.0.1:5000` and waits for browser requests.
5. Nothing else happens until you open that URL and start clicking — every button/form submit triggers one function in `app.py`.

## Role of every file

| File | Role |
|---|---|
| **`app.py`** | The traffic controller. Defines every URL (`/`, `/upload`, `/jd`, `/rank`, `/chat`) and what happens when each is visited — it doesn't do the actual work itself, it calls the `services/` files to do that. |
| **`models.py`** | The database blueprint. Defines 4 tables as Python classes: `Candidate`, `Resume` (file + extracted text + status), `JobDescription`, `MatchScore`. |
| **`services/extractor.py`** | Turns a PDF into plain text. Tries direct text extraction first; if a PDF is a scanned image (little/no text comes out), falls back to OCR (Tesseract) automatically. |
| **`services/parser.py`** | Turns raw text into structured facts: which skills are mentioned (`SKILL_KEYWORDS` list), years of experience, and the candidate's name (heuristic: first Title-Case line with no digits). |
| **`services/matcher.py`** | The scoring engine. Converts resume/JD text into embeddings (384-number vectors representing meaning), compares them with cosine similarity, blends that with skill overlap and experience match into one 0–100 score. |
| **`services/chatbot.py`** | Answers recruiter questions. Parses the question for skill names and a "X years" number, filters the processed resumes, returns a plain-text list of matches. |
| **`templates/*.html`** | What the browser actually displays — `base.html` is the shared layout (nav bar), the other three are the Upload, JD, and Results/Chat pages. |
| **`requirements.txt`** | The list of Python packages the project needs — `pip install -r requirements.txt` installs all of them at once. |

## What this app is actually for

It solves a recruiter's real bottleneck: given a job opening and a stack of resumes (10, 50, whatever), manually reading each one to shortlist candidates is slow. This app:
1. Ingests a batch of resumes at once — including scanned ones, via OCR
2. Takes the job description and figures out what it's actually asking for
3. Ranks every resume by how well it matches — not just keyword-matching, but semantic similarity, so a resume that says "trained TensorFlow models" still matches a JD asking for "deep learning experience"
4. Lets the recruiter ask follow-up questions in plain English instead of manually rereading resumes — "who knows Python with 2+ years" instantly filters the pool

## How someone else runs this on their own PC

This is basically your README, summarized:

1. Clone the repo: `git clone https://github.com/Mahendra-Chauhan/resume-matcher.git`
2. `cd resume-matcher`
3. Create + activate a venv:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   ```
4. `pip install -r requirements.txt`
5. Install Tesseract OCR and Poppler (system tools, links in your README) — only needed for scanned-PDF support
6. Create the database tables once: `python -c "from app import app, db; app.app_context().push(); db.create_all()"`
7. `python app.py`
8. Open `http://127.0.0.1:5000` in a browser — click through the nav bar: Upload → Job Description → Ranked Results & Chat

No account, no server, no deployment — it's entirely local, runs on their own machine, their own data never leaves their PC.
