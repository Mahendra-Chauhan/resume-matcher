"""
chatbot.py — answers recruiter questions about processed resumes.
Rule-based: parses the question for skill names and a year number,
then filters the database. No AI required for this to work correctly.
"""

import re
from services.parser import SKILL_KEYWORDS


def answer_query(question, resumes):
    """
    resumes: list of dicts like {"filename": ..., "raw_text": ..., "skills": [...], "experience": ...}
    Returns a plain-text answer.
    """
    question_lower = question.lower()

    # Find which known skills are mentioned in the question.
    mentioned_skills = [s for s in SKILL_KEYWORDS if s in question_lower]

    # Find a "X years" requirement in the question, if any.
    year_match = re.search(r"(\d+)\+?\s*years?", question_lower)
    min_years = int(year_match.group(1)) if year_match else None

    if not mentioned_skills and min_years is None:
        return ("I couldn't find a specific skill or experience requirement in "
                "that question. Try something like: "
                "'List candidates proficient in Python with over 2 years experience.'")

    # Filter candidates matching ALL mentioned skills (and experience, if given).
    matches = []
    for r in resumes:
        candidate_skills = set(r.get("skills", []))
        has_all_skills = all(s in candidate_skills for s in mentioned_skills)
        meets_experience = (min_years is None) or (
            r.get("experience") is not None and r["experience"] >= min_years
        )
        if has_all_skills and meets_experience:
            matches.append(r)

    if not matches:
        return "No candidates matched that query."

    lines = [f"{len(matches)} candidate(s) match:"]
    for r in matches:
        exp_str = f"{r['experience']} yrs" if r.get("experience") is not None else "experience unknown"
        skills_str = ", ".join(r.get("skills", [])) or "no skills detected"
        lines.append(f"- {r['filename']}: {exp_str}, skills: {skills_str}")

    return "\n".join(lines)