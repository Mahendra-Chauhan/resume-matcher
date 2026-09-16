"""
chatbot.py — answers recruiter questions about processed resumes.

Three layers, tried in order:
1. Score questions ("highest score", "score of X") — answered directly from
   the ranked data, no AI needed, always accurate.
2. Skill/experience questions ("Python with 2+ years") — rule-based keyword
   + regex matching, as before. Reliable, no hallucination risk.
3. Everything else ("deep search") — semantic search over resume embeddings
   finds the closest-matching resumes by MEANING, then (if GROQ_API_KEY is
   set) an LLM writes a natural-language answer grounded in only those
   resumes. If no API key, we just list the semantic matches directly —
   still grounded, just less conversational.
"""

import os
import re
from services.parser import SKILL_KEYWORDS
from services.matcher import semantic_search


def answer_query(question, candidates):
    """
    candidates: list of dicts, each with at least:
      name, filename, skills, experience, score, embedding_vec, raw_text
    """
    question_lower = question.lower()

    # --- Layer 1: contact info questions ---
    if any(word in question_lower for word in ["phone", "mobile", "contact number", "email", "address"]):
        return _answer_contact_question(question_lower, candidates)

    # --- Layer 2: score questions ---
    if "score" in question_lower or "best candidate" in question_lower \
            or "top candidate" in question_lower or "highest" in question_lower:
        return _answer_score_question(question_lower, candidates)

    # --- Layer 3: rule-based skill/experience questions ---
    mentioned_skills = [s for s in SKILL_KEYWORDS if s in question_lower]
    year_match = re.search(r"(\d+)\+?\s*years?", question_lower)
    min_years = int(year_match.group(1)) if year_match else None

    if mentioned_skills or min_years is not None:
        matches = []
        for c in candidates:
            candidate_skills = set(c.get("skills", []))
            has_all_skills = all(s in candidate_skills for s in mentioned_skills)
            meets_experience = (min_years is None) or (
                c.get("experience") is not None and c["experience"] >= min_years
            )
            if has_all_skills and meets_experience:
                matches.append(c)

        if matches:
            return _format_candidate_list(matches, "candidate(s) match")
        # If the rule-based filter found nothing, fall through to semantic
        # search below rather than saying "no match" outright — the resume
        # may describe the skill differently than our keyword list expects.

    # --- Layer 4: semantic search + optional LLM answer ("deep search") ---
    return _deep_search(question, candidates)


def _answer_contact_question(question_lower, candidates):
    """
    Handles direct lookups like "what is X's phone number" or "give me
    Priya's email". If no candidate name is mentioned, lists everyone's
    available contact info instead.
    """
    if not candidates:
        return "No processed resumes yet. Upload resumes first."

    # Try to find a specific candidate named in the question.
    named = None
    for c in candidates:
        name_lower = (c.get("name") or "").lower()
        if name_lower and name_lower in question_lower:
            named = c
            break

    wants_phone = "phone" in question_lower or "mobile" in question_lower or "contact" in question_lower
    wants_email = "email" in question_lower

    if named:
        parts = []
        if wants_phone or not wants_email:
            parts.append(f"phone: {named.get('phone') or 'not found in resume'}")
        if wants_email:
            parts.append(f"email: {named.get('email') or 'not found in resume'}")
        return f"{named['name']} — {', '.join(parts)}."

    # No specific name — list contact info for everyone.
    lines = ["Contact info for all candidates:"]
    for c in candidates:
        phone = c.get("phone") or "not found"
        email = c.get("email") or "not found"
        lines.append(f"- {c['name']} ({c['filename']}): phone {phone}, email {email}")
    return "\n".join(lines)


def _answer_score_question(question_lower, candidates):
    if not candidates:
        return "No ranked candidates yet — submit a job description and visit the ranking page first."

    scored = [c for c in candidates if c.get("score") is not None]
    if not scored:
        return "No scores available yet — submit a job description first."

    ranked = sorted(scored, key=lambda c: c["score"], reverse=True)

    # "highest score" / "best candidate" / "top candidate" -> just the #1
    if "highest" in question_lower or "best" in question_lower or "top" in question_lower:
        top = ranked[0]
        return f"{top['name']} ({top['filename']}) has the highest score: {top['score']}."

    # A specific numeric score mentioned, e.g. "who has score 82.3?"
    number_match = re.search(r"(\d+(\.\d+)?)", question_lower)
    if number_match and "score" in question_lower:
        target = float(number_match.group(1))
        # Allow a small tolerance for rounding.
        close = [c for c in scored if abs(c["score"] - target) < 0.5]
        if close:
            names = ", ".join(f"{c['name']} ({c['filename']})" for c in close)
            return f"Score {target} belongs to: {names}."
        return (f"No candidate has a score of exactly {target}. "
                f"Closest scores: " +
                ", ".join(f"{c['name']}: {c['score']}" for c in ranked[:3]))

    # Otherwise, try to find a specific candidate named in the question.
    for c in candidates:
        name_lower = (c.get("name") or "").lower()
        file_lower = (c.get("filename") or "").lower()
        if name_lower and name_lower in question_lower:
            return f"{c['name']} ({c['filename']})'s score is {c.get('score', '?')}."
        if file_lower and file_lower.replace(".pdf", "") in question_lower:
            return f"{c['name']} ({c['filename']})'s score is {c.get('score', '?')}."

    # No specific name found — show the full ranked list instead.
    lines = ["Here are all candidate scores:"]
    for c in ranked:
        lines.append(f"- {c['name']} ({c['filename']}): {c['score']}")
    return "\n".join(lines)


def _deep_search(question, candidates):
    matches = semantic_search(question, candidates, top_k=5)

    if not matches:
        return ("I couldn't find any processed resumes to search. "
                "Upload resumes and submit a job description first.")

    llm_answer = _try_groq_answer(question, matches)
    if llm_answer:
        return llm_answer

    # Fallback if no GROQ_API_KEY is set, or the API call failed —
    # still grounded and useful, just a plain list instead of prose.
    return _format_candidate_list(matches, "closest-matching candidate(s), by overall profile")


def _format_candidate_list(candidates, label):
    lines = [f"{len(candidates)} {label}:"]
    for c in candidates:
        exp_str = f"{c['experience']} yrs" if c.get("experience") is not None else "experience unknown"
        skills_str = ", ".join(c.get("skills", [])) or "no skills detected"
        score_str = f", score: {c['score']}" if c.get("score") is not None else ""
        lines.append(f"- {c['name']} ({c['filename']}): {exp_str}{score_str}, skills: {skills_str}")
    return "\n".join(lines)


def _try_groq_answer(question, candidates):
    """
    Uses Groq to write a natural-language answer, but ONLY grounded in the
    candidate summaries we hand it — this avoids hallucinated names/facts.
    Returns None if no API key is set or the call fails, so the caller can
    fall back to the plain list.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        context_lines = []
        for c in candidates:
            exp = c.get("experience", "unknown")
            skills = ", ".join(c.get("skills", [])) or "none detected"
            score = c.get("score", "unknown")
            context_lines.append(
                f"- {c['name']} (file: {c['filename']}, score: {score}, "
                f"experience: {exp} years, skills: {skills})"
            )
        context = "\n".join(context_lines)

        prompt = (
            "You are a recruiting assistant. Answer the recruiter's question "
            "using ONLY the candidate data listed below. Never invent a name, "
            "skill, or number that isn't present in this data. If the data "
            "doesn't answer the question, say so plainly.\n\n"
            f"Candidate data:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer concisely, in 2-4 sentences."
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Groq call failed, falling back to plain list: {e}")
        return None
    