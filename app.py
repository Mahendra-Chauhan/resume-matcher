"""
app.py — full application: upload, JD intake, ranking, and chatbot.
"""

import os
from flask import Flask, request, render_template
from models import db, Resume, JobDescription
from services.extractor import extract_text
from services.parser import extract_skills, extract_min_experience_years
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


@app.route("/rank")
def rank():
    # Uses the most recently submitted JD and all processed resumes.
    jd = JobDescription.query.order_by(JobDescription.id.desc()).first()
    if not jd:
        return "No job description submitted yet. Go to /jd first."

    resumes = Resume.query.filter(Resume.status.in_(["processed", "ocr_used"])).all()
    jd_skills = [s.strip() for s in (jd.required_skills or "").split(",") if s.strip()]

    ranked = []
    for r in resumes:
        resume_skills = extract_skills(r.raw_text or "")
        resume_exp = extract_min_experience_years(r.raw_text or "")
        score, matched, missing, resume_vec = compute_match_score(
            r.raw_text or "", resume_skills,
            jd.raw_text or "", jd_skills,
            jd.min_experience_years, resume_exp
        )
        # Cache the embedding so we don't recompute it every time.
        r.embedding = embedding_to_bytes(resume_vec)
        db.session.commit()

        ranked.append({
            "filename": r.filename,
            "score": score,
            "matched": matched,
            "missing": missing
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return render_template("results.html", ranked=ranked, answer=None)


@app.route("/chat", methods=["POST"])
def chat():
    question = request.form.get("question", "")

    resumes = Resume.query.filter(Resume.status.in_(["processed", "ocr_used"])).all()
    resume_data = []
    for r in resumes:
        resume_data.append({
            "filename": r.filename,
            "raw_text": r.raw_text,
            "skills": extract_skills(r.raw_text or ""),
            "experience": extract_min_experience_years(r.raw_text or "")
        })

    answer = answer_query(question, resume_data)

    # Re-render the ranked table too, so the page doesn't go blank.
    jd = JobDescription.query.order_by(JobDescription.id.desc()).first()
    ranked = []
    if jd:
        jd_skills = [s.strip() for s in (jd.required_skills or "").split(",") if s.strip()]
        for r in resume_data:
            score, matched, missing, _ = compute_match_score(
                r["raw_text"] or "", r["skills"],
                jd.raw_text or "", jd_skills,
                jd.min_experience_years, r["experience"]
            )
            ranked.append({"filename": r["filename"], "score": score, "matched": matched, "missing": missing})
        ranked.sort(key=lambda x: x["score"], reverse=True)

    return render_template("results.html", ranked=ranked, answer=answer)


if __name__ == "__main__":
    app.run(debug=True)