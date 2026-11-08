"""Bounded lexical reranking of already eligible pgvector candidates.

BM25 statistics are local to the candidate pool, not the entire corpus. Scores are
ranking signals, never probabilities or diagnostic confidence. No source is added,
edited or promoted past repository permission/scope/similarity gates here.
"""

import math
import re
import unicodedata
from collections import Counter

# Remove question scaffolding and repeated manual branding; retain technical terms,
# component tags, numbers and negations. This is a small EN/ES/FR tokenizer, not a
# full language stemmer. Reference titles are deliberately not part of the score.
STOP_WORDS = frozenset(
    "a an the and or of to in on for is are be what does do how which this that it with "
    "about from as say says reference references workshop technical documentation "
    "described describe describes discusses discussed related vehicle car golf volkswagen "
    "manual training que de la el los las del un una y en le les des du au une avec dans "
    "pour sur est sont ces ce qui quelle quel quoi comment information".split()
)


def terms(text: str) -> list[str]:
    # Discretionary PDF line wraps are not word boundaries (e.g. per‐\nformed).
    text = re.sub(r"(?<=\w)[\u00ad\u2010-]\s*\n(?=\w)", "", text)
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )
    output = []
    for word in re.findall(r"[a-z0-9]+", text):
        if word in STOP_WORDS or (len(word) < 3 and word not in {"no", "ne", "ni"}):
            continue
        # Keep mixed technical identifiers intact; do not stem a part/component tag.
        if word.isalpha():
            if word.endswith("ing") and len(word) > 6:
                word = word[:-3]
            elif word.endswith("s") and len(word) > 4:
                word = word[:-1]
        output.append(word)
    return output


def lexical_scores(documents, queries):
    """Best normalized BM25 match across original and translated questions."""
    if not documents:
        return []
    counts = [Counter(terms(document.relevant_text)) for document in documents]
    lengths = [sum(counter.values()) for counter in counts]
    average = sum(lengths) / len(counts) or 1.0
    frequency = Counter(term for counter in counts for term in counter)
    count = len(counts)
    best = [0.0] * count
    for query in queries[:3]:
        query_terms = set(terms(query))
        scores = []
        for counter, length in zip(counts, lengths, strict=True):
            score = 0.0
            for term in sorted(query_terms):
                occurrence = counter[term]
                if occurrence:
                    idf = math.log1p((count - frequency[term] + 0.5) / (frequency[term] + 0.5))
                    score += (
                        idf
                        * occurrence
                        * 2.2
                        / (occurrence + 1.2 * (0.25 + 0.75 * length / average))
                    )
            scores.append(score)
        maximum = max(scores) or 1.0
        best = [max(old, score / maximum) for old, score in zip(best, scores, strict=True)]
    return best


def rerank(documents, queries, limit, *, weight=0.15):
    """A bounded lexical bonus supplements, rather than replaces, semantic relevance.

    Caller bypasses this for explicit component-code requests: the repository's
    exact code-coverage ordering is more informative for those questions.
    """
    if not documents or not queries or weight == 0:
        return documents[:limit]
    try:
        semantic = [float(doc.relevance_metadata["cosine_similarity"]) for doc in documents]
    except (KeyError, ValueError, TypeError):
        return documents[:limit]
    if not all(math.isfinite(score) for score in semantic):
        return documents[:limit]
    scores = lexical_scores(documents, queries)
    wants_contents = any(
        {"content", "index", "indice", "sommaire"}.intersection(terms(query))
        for query in queries[:3]
    )
    penalties = [
        weight if not wants_contents and re.search(r"(?:\.\s*){8,}", doc.relevant_text) else 0.0
        for doc in documents
    ]
    combined = [
        similarity + weight * lexical - penalty
        for similarity, lexical, penalty in zip(semantic, scores, penalties, strict=True)
    ]
    order = sorted(range(len(documents)), key=lambda index: (-combined[index], index))
    selected = []
    for index in order[:limit]:
        document = documents[index]
        selected.append(
            document.model_copy(
                update={
                    "relevance_metadata": {
                        **document.relevance_metadata,
                        "ranking_strategy": "semantic_bm25",
                        "lexical_score": scores[index],
                        "contents_penalty": penalties[index],
                        "ranking_score": combined[index],
                    }
                }
            )
        )
    return selected
