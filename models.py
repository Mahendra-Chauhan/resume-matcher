"""
models.py — defines our database tables as Python classes.

Each class below = one table. Each class attribute = one column.
SQLAlchemy turns this into actual SQLite tables for us.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# This 'db' object is shared across the whole app — every model uses it,
# and app.py will connect it to our actual database file.
db = SQLAlchemy()


class Candidate(db.Model):
    """One row = one person who uploaded a resume."""
    id = db.Column(db.Integer, primary_key=True)  # auto-incrementing unique ID
    name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # This links a Candidate to their Resume row (one-to-one for now).
    resume = db.relationship("Resume", backref="candidate", uselist=False)


class Resume(db.Model):
    """One row = one uploaded resume file and everything we extracted from it."""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"))

    filename = db.Column(db.String(300))
    raw_text = db.Column(db.Text)  # full extracted text from the PDF

    # Status tells us what happened during processing — shown to the user.
    # Values we'll use: "processing", "processed", "ocr_used", "failed"
    status = db.Column(db.String(50), default="processing")

    # The embedding (a list of ~384 numbers representing the resume's meaning)
    # gets stored as raw bytes here. We convert it to/from a numpy array in code.
    embedding = db.Column(db.LargeBinary)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class JobDescription(db.Model):
    """One row = one job description a recruiter submitted."""
    id = db.Column(db.Integer, primary_key=True)
    raw_text = db.Column(db.Text)

    # Extracted fields — filled in by our parser later.
    required_skills = db.Column(db.Text)     # stored as comma-separated for now
    min_experience_years = db.Column(db.Float)

    embedding = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MatchScore(db.Model):
    """One row = how well one resume matched one job description."""
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume.id"))
    jd_id = db.Column(db.Integer, db.ForeignKey("job_description.id"))

    score = db.Column(db.Float)  # final 0-100 match score
    matched_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)