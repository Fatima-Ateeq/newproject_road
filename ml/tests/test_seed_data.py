from collections import Counter

from ml.common.categories import CATEGORIES
from ml.common.paths import GENERATED_TRAINING_FILES
from ml.text.cleaning import dedupe, normalize_text
from ml.text.csv_io import read_rows

ROWS = [row for path in GENERATED_TRAINING_FILES for row in read_rows(path)]


def test_generated_files_exist():
    assert len(GENERATED_TRAINING_FILES) >= 2


def test_every_label_is_a_valid_category():
    assert {row["label"] for row in ROWS} <= set(CATEGORIES)


def test_categories_are_balanced_with_30_examples_per_file():
    expected = 30 * len(GENERATED_TRAINING_FILES)
    assert Counter(row["label"] for row in ROWS) == {name: expected for name in CATEGORIES}


def test_languages_are_known_codes():
    assert {row["language"] for row in ROWS} == {"en", "roman_ur", "ur"}


def test_no_duplicate_or_empty_texts_across_all_files():
    assert all(normalize_text(row["text"]) for row in ROWS)
    unique, conflicts = dedupe(ROWS)
    assert len(unique) == len(ROWS)
    assert conflicts == []
