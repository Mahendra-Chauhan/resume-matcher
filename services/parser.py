"""
parser.py — pulls structured info (skills, years of experience) out of
raw text, whether that's a resume or a job description.

This is rule-based (regex + keyword matching) — no AI needed for this part.
Simple, fast, and good enough for the assignment's scale.
"""

import re

# A starter list of common tech skills to look for.
# In a real product this would be a much bigger list, or a skills database —
# but for the assignment, a solid keyword list is enough.
SKILL_KEYWORDS = [
    "python", "java", "javascript", "sql", "django", "flask",
    "react", "node.js", "tensorflow", "pytorch", "nlp",
    "machine learning", "deep learning", "aws", "docker", "kubernetes",
    "git", "html", "css", "c++", "excel", "power bi", "tableau",
]


def extract_skills(text):
    """
    Returns a list of skills found in the text.
    Case-insensitive matching — "Python" and "python" both count.
    """
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)
    return found


def extract_min_experience_years(text):
    """
    Looks for patterns like "3+ years", "5 years of experience", etc.
    Returns the largest number found, or None if nothing matches.
    """
    # This regex looks for a number followed by "year" or "years",
    # optionally with a "+" sign in between.
    pattern = r"(\d+)\+?\s*years?"
    matches = re.findall(pattern, text.lower())

    if not matches:
        return None

    # If a JD mentions multiple numbers (e.g. "3-5 years"), take the highest
    # as a safe minimum bar.
    years = [int(m) for m in matches]
    return max(years)