from __future__ import annotations

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


CUSTOM_STOP_WORDS = ENGLISH_STOP_WORDS.union(
    {
        "applicant",
        "candidate",
        "description",
        "job",
        "need",
        "needed",
        "needs",
        "position",
        "preferred",
        "require",
        "required",
        "requirement",
        "requirements",
        "responsibilities",
        "role",
        "team",
        "work",
    }
)


def extract_keywords(text: str) -> list[str]:
    """Extract the top 30 relevant keywords from text using TF-IDF."""
    if not text or not text.strip():
        return []

    vectorizer = TfidfVectorizer(
        stop_words=list(CUSTOM_STOP_WORDS),
        max_features=200,
        ngram_range=(1, 1),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b",
    )

    try:
        matrix = vectorizer.fit_transform([text])
    except ValueError:
        return []

    terms = vectorizer.get_feature_names_out()
    scores = matrix.toarray()[0]
    ranked_terms = sorted(zip(terms, scores, strict=False), key=lambda item: item[1], reverse=True)

    keywords: list[str] = []
    for term, _score in ranked_terms:
        normalized = term.strip().lower()
        if _is_valid_keyword(normalized) and normalized not in keywords:
            keywords.append(normalized)
        if len(keywords) == 30:
            break

    return keywords


def calculate_ats_score(resume_text: str, job_description: str) -> dict[str, float | int | list[str]]:
    """Calculate an ATS keyword match score for a resume against a job description."""
    keywords = extract_keywords(job_description or "")
    if not keywords:
        return {
            "score": 0.0,
            "matched_keywords": [],
            "missing_keywords": [],
            "total_keywords": 0,
            "keyword_density": 0.0,
        }

    resume = resume_text or ""
    frequencies = {keyword: _keyword_frequency(resume, keyword) for keyword in keywords}
    matched_keywords = [keyword for keyword, count in frequencies.items() if count > 0]
    missing_keywords = [keyword for keyword, count in frequencies.items() if count == 0]

    score = (len(matched_keywords) / len(keywords)) * 100
    keyword_density = (
        sum(frequencies[keyword] for keyword in matched_keywords) / len(matched_keywords)
        if matched_keywords
        else 0.0
    )

    return {
        "score": round(score, 2),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "total_keywords": len(keywords),
        "keyword_density": round(keyword_density, 2),
    }


def compare_scores(before: dict[str, float | int | list[str]], after: dict[str, float | int | list[str]]) -> dict[str, float]:
    """Compare two ATS score dictionaries."""
    before_score = float(before.get("score", 0.0) or 0.0)
    after_score = float(after.get("score", 0.0) or 0.0)
    improvement = after_score - before_score
    improvement_pct = (improvement / before_score) * 100 if before_score else (100.0 if after_score else 0.0)

    return {
        "before_score": round(before_score, 2),
        "after_score": round(after_score, 2),
        "improvement": round(improvement, 2),
        "improvement_pct": round(improvement_pct, 2),
    }


def keyword_in_text(text: str, keyword: str) -> bool:
    """Return True when a keyword or phrase appears in text, case-insensitively."""
    return _keyword_frequency(text, keyword) > 0


def _is_valid_keyword(keyword: str) -> bool:
    tokens = keyword.split()
    if not tokens:
        return False
    return all(len(token) >= 3 and not token.isdigit() for token in tokens)


def _keyword_frequency(text: str, keyword: str) -> int:
    if not text or not keyword:
        return 0

    normalized_text = text.lower()
    normalized_keyword = keyword.lower()
    pattern = rf"(?<![\w+#.-]){re.escape(normalized_keyword)}(?![\w+#.-])"
    return len(re.findall(pattern, normalized_text))
