"""Where the text datasets live. Change a folder here and every script follows."""

from pathlib import Path

TEXT_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "text"
LABELS_DIR = TEXT_DATA_DIR / "labels"
PROCESSED_DIR = TEXT_DATA_DIR / "processed"
COLLECTED_DIR = TEXT_DATA_DIR / "collected"
TEST_POOL = TEXT_DATA_DIR / "test_pool.csv"
GOLD_TEST_SET = TEXT_DATA_DIR / "gold_test.csv"

# Every generated_*.csv file is training data written by Claude. Add a batch by adding a file.
GENERATED_TRAINING_FILES = sorted(TEXT_DATA_DIR.glob("generated_*.csv"))

# The trained text classifier is saved inside the backend, because the backend loads it at runtime.
CLASSIFIER_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "backend" / "app" / "ai" / "artifacts"
