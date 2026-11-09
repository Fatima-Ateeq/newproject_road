"""Text cleaning and dataset splitting. Pure functions, easy to test."""

import random
import re
import unicodedata
from collections import defaultdict

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Unicode-normalize, drop control characters and collapse whitespace.

    Format characters such as the zero-width non-joiner are kept, because Urdu needs them.
    """
    text = unicodedata.normalize("NFC", text)
    text = "".join(ch for ch in text if ch in " \t\n" or unicodedata.category(ch) != "Cc")
    return _WHITESPACE.sub(" ", text).strip()


def detect_script(text: str) -> str:
    """Return 'arabic' (Urdu script), 'latin' (English or Roman Urdu), 'mixed' or 'other'."""
    arabic = latin = 0
    for ch in text:
        if not ch.isalpha():
            continue
        name = unicodedata.name(ch, "")
        if name.startswith("ARABIC"):
            arabic += 1
        elif name.startswith("LATIN"):
            latin += 1
    total = arabic + latin
    if total == 0:
        return "other"
    if arabic / total >= 0.8:
        return "arabic"
    if latin / total >= 0.8:
        return "latin"
    return "mixed"


def dedupe_key(text: str) -> str:
    return normalize_text(text).casefold()


def dedupe(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    """Keep the first copy of each text. Also return texts that appear with different labels."""
    first: dict[str, dict[str, str]] = {}
    conflicts: list[str] = []
    for row in rows:
        key = dedupe_key(row["text"])
        if key not in first:
            first[key] = row
        elif first[key]["label"] != row["label"] and row["text"] not in conflicts:
            conflicts.append(row["text"])
    return list(first.values()), conflicts


def remove_leakage(
    train_rows: list[dict[str, str]], test_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], int]:
    """Drop training rows whose text also appears in the test set. Returns (kept, removed_count)."""
    test_keys = {dedupe_key(row["text"]) for row in test_rows}
    kept = [row for row in train_rows if dedupe_key(row["text"]) not in test_keys]
    return kept, len(train_rows) - len(kept)


def split_stratified(
    rows: list[dict[str, str]], val_fraction: float, seed: int
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split so every label appears in both parts in the same proportion. Same seed, same split."""
    by_label: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)

    rng = random.Random(seed)
    train: list[dict[str, str]] = []
    val: list[dict[str, str]] = []
    for label in sorted(by_label):
        group = by_label[label][:]
        rng.shuffle(group)
        n_val = round(len(group) * val_fraction)
        if val_fraction > 0 and len(group) >= 2:
            n_val = max(n_val, 1)
        val.extend(group[:n_val])
        train.extend(group[n_val:])
    return train, val
