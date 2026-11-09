"""A regression guard for the keyword baseline that backs the agent's fallback.

This is NOT an evaluation: the seed texts were written by the same hand that chose the keywords,
so the number is optimistic. The real measurement uses the human-written, labeled test set.
"""

from app.ai.classifier import KeywordTextClassifier  # importable because ml.common.categories adds backend to the path
from ml.common.paths import GENERATED_TRAINING_FILES
from ml.text.csv_io import read_rows

ROWS = [row for path in GENERATED_TRAINING_FILES for row in read_rows(path)]


def test_baseline_gets_most_of_the_generated_seed_right():
    classifier = KeywordTextClassifier()
    correct = sum(classifier.predict(row["text"]).category.value == row["label"] for row in ROWS)
    assert correct / len(ROWS) >= 0.70


def test_texts_with_no_keywords_become_other_with_low_confidence():
    prediction = KeywordTextClassifier().predict("Something unusual happened today")
    assert prediction.category.value == "Other"
    assert prediction.confidence < 0.5
