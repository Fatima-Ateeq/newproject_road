"""A simple word-overlap similarity between two complaint texts."""

import re

_WORD = re.compile(r"\w+")


def _words(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.casefold()) if len(word) > 2}


def jaccard(first: str, second: str) -> float:
    """Shared words divided by all words, from 0 (nothing shared) to 1 (same words)."""
    a, b = _words(first), _words(second)
    union = a | b
    return len(a & b) / len(union) if union else 0.0
