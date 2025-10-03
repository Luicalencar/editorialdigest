import re
from typing import Dict, Any, List

HEDGE_WORDS = [
    "may", "might", "could", "suggests", "appears", "reportedly", "allegedly", "possible"
]
OVERCLAIM_WORDS = [
    "proves", "undeniably", "certainly", "always", "never", "guarantees"
]
QUOTE_VERBS = ["said", "told", "according to", "stated", "wrote"]


def simple_sentence_split(text: str) -> List[str]:
    return re.split(r"(?<=[.!?])\s+", text.strip()) if text else []


def compute_features(text: str) -> Dict[str, Any]:
    sentences = simple_sentence_split(text)
    words = re.findall(r"\w+", text)
    quotes = re.findall(r"“[^”]+”|\"[^\"]+\"", text)
    hedge_hits = [w for w in HEDGE_WORDS if re.search(rf"\b{re.escape(w)}\b", text, re.I)]
    overclaim_hits = [w for w in OVERCLAIM_WORDS if re.search(rf"\b{re.escape(w)}\b", text, re.I)]

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_len_first5": _avg_sentence_len(sentences[:5]),
        "quotes_detected": len(quotes),
        "hedge_hits": hedge_hits,
        "overclaim_hits": overclaim_hits,
        "paragraphs": text.split("\n\n") if text else [],
    }


def _avg_sentence_len(sentences: List[str]) -> float:
    if not sentences:
        return 0.0
    counts = [len(re.findall(r"\w+", s)) for s in sentences]
    return sum(counts) / len(counts)



