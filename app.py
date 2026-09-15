"""
app.py — entry point. Now extracts text from each uploaded PDF too.
"""

import os
from flask import Flask, request, render_template
from models import db, Resume
from services.extractor import extract_text

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

        # Try to extract text — wrapped in try/except so one bad/corrupt
        # PDF doesn't crash the whole batch.
        try:
            text, used_ocr = extract_text(save_path)
            status = "ocr_used" if used_ocr else "processed"
            resume = Resume(
                filename=file.filename,
                raw_text=text,
                status=status
            )
            db.session.add(resume)
            db.session.commit()

            ocr_note = " (via OCR)" if used_ocr else ""
            messages.append(f"✅ {file.filename}: processed{ocr_note}")

        except Exception as e:
            # Log the real error for us, show a friendly one to the user.
            print(f"Extraction failed for {file.filename}: {e}")
            resume = Resume(filename=file.filename, status="failed")
            db.session.add(resume)
            db.session.commit()
            messages.append(f"❌ {file.filename}: processing failed")

    return render_template("upload.html", messages=messages)


if __name__ == "__main__":
    app.run(debug=True)