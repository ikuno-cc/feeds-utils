import math
import re
from collections import Counter

_NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:,\d{3})*(?:\s*(?:million|billion|thousand|percent|%))?\b", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_TOKENIZE = re.compile(r"\w+(?:\.\w+)?")
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "that", "this", "these",
    "those", "it", "its", "he", "she", "they", "them", "we", "you", "i",
})


def tokenize(text: str) -> list[str]:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in text.split() if len(t) > 1 and t not in _STOPWORDS]


def _normalize_number_str(num_str: str) -> float:
    cleaned = num_str.replace(",", "").strip().lower()
    multiplier = 1.0
    if cleaned.endswith("million"):
        multiplier = 1_000_000
        cleaned = cleaned.replace("million", "").strip()
    elif cleaned.endswith("billion"):
        multiplier = 1_000_000_000
        cleaned = cleaned.replace("billion", "").strip()
    elif cleaned.endswith("thousand"):
        multiplier = 1_000
        cleaned = cleaned.replace("thousand", "").strip()
    elif cleaned.endswith("percent") or cleaned.endswith("%"):
        cleaned = cleaned.replace("percent", "").replace("%", "").strip()
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return 0.0


def extract_numeric_values(text: str) -> list[float]:
    matches = _NUMBER_PATTERN.findall(text)
    return [_normalize_number_str(m) for m in matches if _normalize_number_str(m) > 0]


def _value_tolerance(a: float, b: float, unit: str) -> bool:
    if a == b:
        return True
    if unit == "percent" or unit == "%" or "/barrel" in unit:
        return abs(a - b) <= max(1.0, 0.05 * max(a, b))
    if "million" in unit:
        return abs(a - b) <= 0.05 * max(a, b)
    return abs(a - b) <= max(0.01 * max(a, b), 0.5)


def numeric_overlap(claim_value: float | None, claim_unit: str, chunk_text: str) -> float:
    if claim_value is None:
        return 0.0
    chunk_numbers = extract_numeric_values(chunk_text)
    if not chunk_numbers:
        return 0.0
    for cn in chunk_numbers:
        if _value_tolerance(claim_value, cn, claim_unit):
            return 1.0
    return 0.0


def compute_idf(chunks: list[str]) -> dict[str, float]:
    N = len(chunks)
    if N == 0:
        return {}
    df: Counter = Counter()
    for chunk in chunks:
        tokens = set(tokenize(chunk))
        for t in tokens:
            df[t] += 1
    idf: dict[str, float] = {}
    for term, doc_count in df.items():
        idf[term] = math.log(1 + (N - doc_count + 0.5) / (doc_count + 0.5))
    return idf


def bm25_score(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float], avg_dl: float, k1: float = 1.5, b: float = 0.75) -> float:
    if not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    doc_freq = Counter(doc_tokens)
    score = 0.0
    seen = set()
    for term in query_tokens:
        if term in seen:
            continue
        seen.add(term)
        tf = doc_freq.get(term, 0)
        if tf == 0:
            continue
        term_idf = idf.get(term, 0.0)
        score += term_idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_dl))
    return score


def _prepare_chunks(articles: list[dict]) -> list[str]:
    chunks: list[str] = []
    for article in articles:
        for para in article.get("clean_text", []):
            if not para or not para.strip():
                continue
            sentences = _SENTENCE_SPLIT.split(para.strip())
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 20:
                    chunks.append(sent)
    return chunks


def _claim_to_question(claim: str, subject: str, predicate: str, value: float | None, unit: str) -> str:
    if value is not None:
        return f"{subject} {predicate} {value} {unit}"
    return claim


def fact_check(
    claims: list[dict],
    articles: list[dict],
    threshold: float = 0.3,
    alpha: float = 0.6,
    beta: float = 0.4,
) -> list[dict]:
    if not claims or not articles:
        return []

    chunks = _prepare_chunks(articles)
    if not chunks:
        return []

    idf = compute_idf(chunks)
    avg_dl = sum(len(tokenize(c)) for c in chunks) / len(chunks) if chunks else 1.0

    verified: list[dict] = []

    for claim_data in claims:
        claim_text = claim_data.get("claim", "")
        subject = claim_data.get("subject", "")
        predicate = claim_data.get("predicate", "")
        value = claim_data.get("value")
        unit = claim_data.get("unit", "")

        query = _claim_to_question(claim_text, subject, predicate, value, unit)
        query_tokens = tokenize(query)

        if not query_tokens:
            continue

        best_keyword_score = 0.0
        best_numeric_score = 0.0

        for chunk in chunks:
            doc_tokens = tokenize(chunk)
            kw_score = bm25_score(query_tokens, doc_tokens, idf, avg_dl)
            if kw_score > best_keyword_score:
                best_keyword_score = kw_score

            num_score = numeric_overlap(value, unit, chunk)
            if num_score > best_numeric_score:
                best_numeric_score = num_score

        max_possible_kw = bm25_score(query_tokens, query_tokens, idf, avg_dl)
        if max_possible_kw > 0:
            best_keyword_score /= max_possible_kw
        else:
            best_keyword_score = 0.0

        best_keyword_score = min(best_keyword_score, 1.0)

        hybrid = alpha * best_keyword_score + beta * best_numeric_score

        if hybrid >= threshold:
            verified.append(claim_data)

    return verified
