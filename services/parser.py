"""
parser.py — pulls structured info (skills, years of experience) out of
raw text, whether that's a resume or a job description.

This is rule-based (regex + keyword matching) — no AI needed for this part.
Simple, fast, and good enough for the assignment's scale.
"""

import re

# A starter list of common skills across several domains — not just tech.
# In a real product this would be a much bigger list, or a skills database —
# but for the assignment, a solid keyword list is enough.
# IMPORTANT: only skills in this list can ever show up in "matched/missing
# skills" — if a JD or resume is about a domain not covered here, that
# comparison will come back empty even though the semantic score still works.
# Add more terms below as needed for your test resumes/JDs.
SKILL_KEYWORDS = [
    # Tech / data
    "python", "java", "javascript", "sql", "generative ai", "agentic ai","langchain", "langgraph","data analysis", "data science","django", "flask", "fastapi"
    "react", "node.js", "tensorflow", "pytorch", "nlp",
    "machine learning", "deep learning", "aws", "docker", "kubernetes",
    "git", "html", "css", "c++", "excel", "power bi", "tableau",
    # Business / administration
    "business administration", "office administration", "data entry",
    "ms office", "microsoft office", "powerpoint", "word", "outlook",
    "scheduling", "record keeping", "documentation", "filing",
    "customer service", "front desk", "reception",
    # Management / soft skills
    "project management", "team management", "leadership",
    "communication", "negotiation", "problem solving", "time management",
    "organizational skills", "multitasking",
    # Marketing / sales
    "digital marketing", "social media", "seo", "content writing",
    "sales", "crm", "market research", "branding",
    # Finance / accounting
    "accounting", "bookkeeping", "budgeting", "financial analysis",
    "invoicing", "payroll", "sap",
    # Graphic Designer
    "graphic designer", "UI UX designer", "photoshop"
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


def extract_name(text):
    """
    Heuristic: a resume's name is almost always one of the first few lines,
    written in Title Case, with no digits or '@' (rules out phone/email lines).
    Returns None if nothing looks like a name — caller should fall back to
    the filename in that case.
    """
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:6]:  # only check the first few lines
        if "@" in line or any(ch.isdigit() for ch in line):
            continue  # skip emails, phone numbers, addresses with numbers

        words = line.split()
        if 1 <= len(words) <= 4:
            # Title Case check: each word starts with a capital letter
            if all(w[0].isupper() for w in words if w[0].isalpha()):
                return line

    return None  # nothing matched — caller falls back to filename


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