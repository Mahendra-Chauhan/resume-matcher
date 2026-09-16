"""
app.py — full application: upload, JD intake, ranking, and chatbot.
"""

from dotenv import load_dotenv
load_dotenv()  # reads .env and makes GROQ_API_KEY etc. available via os.environ

import os
from flask import Flask, request, render_template
from models import db, Resume, JobDescription
from services.extractor import extract_text
from services.parser import (
    extract_skills, extract_min_experience_years, extract_name,
    extract_email, extract_phone
)
from services.matcher import compute_match_score, embedding_to_bytes
from services.chatbot import answer_query

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///resume_matcher.db"
db.init_app(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("upload.html", messages=None)


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("resumes")
    messages = []

    for file in files:
        if file.filename == "":
            continue
        if not file.filename.lower().endswith(".pdf"):
            messages.append(f"❌ {file.filename}: not a PDF, skipped")
            continue

        save_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(save_path)

        try:
            text, used_ocr = extract_text(save_path)
            status = "ocr_used" if used_ocr else "processed"
            resume = Resume(filename=file.filename, raw_text=text, status=status)
            db.session.add(resume)
            db.session.commit()
            ocr_note = " (via OCR)" if used_ocr else ""
            messages.append(f"✅ {file.filename}: processed{ocr_note}")
        except Exception as e:
            print(f"Extraction failed for {file.filename}: {e}")
            resume = Resume(filename=file.filename, status="failed")
            db.session.add(resume)
            db.session.commit()
            messages.append(f"❌ {file.filename}: processing failed")

    return render_template("upload.html", messages=messages)


@app.route("/jd", methods=["GET", "POST"])
def job_description():
    extracted = None
    if request.method == "POST":
        jd_text = request.form.get("jd_text", "")
        skills = extract_skills(jd_text)
        min_experience = extract_min_experience_years(jd_text)
        jd = JobDescription(
            raw_text=jd_text,
            required_skills=", ".join(skills),
            min_experience_years=min_experience
        )
        db.session.add(jd)
        db.session.commit()
        extracted = {"skills": skills, "min_experience": min_experience}
    return render_template("jd.html", extracted=extracted)


def build_candidates(jd):
    """
    The single source of truth for candidate data — used by BOTH the ranked
    table (/rank) and the chatbot (/chat), so they never fall out of sync.
    Returns a list of dicts with everything either feature needs: score,
    matched/missing skills, embedding vector (for semantic search), and
    contact info (for the chatbot's direct-lookup questions).
    """
    resumes = Resume.query.filter(Resume.status.in_(["processed", "ocr_used"])).all()
    jd_skills = [s.strip() for s in (jd.required_skills or "").split(",") if s.strip()] if jd else []

    candidates = []
    for r in resumes:
        text = r.raw_text or ""
        resume_skills = extract_skills(text)
        resume_exp = extract_min_experience_years(text)

        if jd:
            score, matched, missing, resume_vec = compute_match_score(
                text, resume_skills,
                jd.raw_text or "", jd_skills,
                jd.min_experience_years, resume_exp
            )
            # Cache the embedding so future requests don't recompute it.
            r.embedding = embedding_to_bytes(resume_vec)
            db.session.commit()
        else:
            score, matched, missing, resume_vec = None, [], [], None

        candidates.append({
            "name": extract_name(text) or r.filename,
            "filename": r.filename,
            "raw_text": text,
            "skills": resume_skills,
            "experience": resume_exp,
            "email": extract_email(text),
            "phone": extract_phone(text),
            "score": score,
            "matched": matched,
            "missing": missing,
            "embedding_vec": resume_vec,
        })

    candidates.sort(key=lambda c: c["score"] if c["score"] is not None else -1, reverse=True)
    return candidates


@app.route("/rank")
def rank():
    jd = JobDescription.query.order_by(JobDescription.id.desc()).first()
    if not jd:
        return "No job description submitted yet. Go to /jd first."

    ranked = build_candidates(jd)
    return render_template("results.html", ranked=ranked, answer=None)


@app.route("/chat", methods=["POST"])
def chat():
    question = request.form.get("question", "")
    jd = JobDescription.query.order_by(JobDescription.id.desc()).first()
    candidates = build_candidates(jd)

    answer = answer_query(question, candidates)

    return render_template("results.html", ranked=candidates, answer=answer)


if __name__ == "__main__":
    app.run(debug=True)