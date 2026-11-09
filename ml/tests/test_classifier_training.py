import json
import sys

from ml.common.categories import CATEGORIES
from ml.common.paths import GENERATED_TRAINING_FILES
from ml.text import train_classifier
from ml.text.classifier_training import (
    baseline_metrics, build_pipeline, cross_validated_metrics, fit_final_model, score,
)
from ml.text.csv_io import read_rows, write_rows

ROWS = [row for path in GENERATED_TRAINING_FILES for row in read_rows(path)]


def test_score_reports_accuracy_macro_f1_and_per_category_f1():
    metrics = score([CATEGORIES[0], CATEGORIES[0], CATEGORIES[1]], [CATEGORIES[0], CATEGORIES[1], CATEGORIES[1]])
    assert metrics.accuracy == 2 / 3
    assert set(metrics.f1_per_category) == set(CATEGORIES)
    assert metrics.f1_per_category[CATEGORIES[2]] == 0.0


def test_pipeline_learns_to_tell_two_obvious_categories_apart():
    rows = [{"text": "big pothole crack", "label": CATEGORIES[0]}] * 5 + [{"text": "traffic jam queue", "label": CATEGORIES[1]}] * 5
    model = fit_final_model(rows)
    assert model.predict(["a pothole"])[0] == CATEGORIES[0]
    assert model.predict(["a long jam"])[0] == CATEGORIES[1]


def test_trained_model_beats_the_keyword_baseline_on_the_generated_data():
    """A regression guard. These are generated examples, so the numbers are not the final result."""
    trained = cross_validated_metrics(ROWS)
    assert trained.macro_f1 >= 0.80
    assert trained.macro_f1 > baseline_metrics(ROWS).macro_f1


def test_training_script_saves_the_model_and_its_card(tmp_path, monkeypatch, capsys):
    train, val, out = tmp_path / "train.csv", tmp_path / "val.csv", tmp_path / "out"
    write_rows(train, ROWS[:200], ["text", "label"])
    write_rows(val, ROWS[200:], ["text", "label"])
    monkeypatch.setattr(sys, "argv", ["train", "--train", str(train), "--val", str(val), "--out-dir", str(out)])
    assert train_classifier.main() == 0
    assert (out / "text_classifier.joblib").exists()
    card = json.loads((out / "text_classifier_card.json").read_text(encoding="utf-8"))
    assert card["examples"] == len(ROWS)
    assert "not on the human-written test set" in card["note"]


def test_training_script_explains_what_to_run_first_when_data_is_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["train", "--train", str(tmp_path / "a.csv"), "--val", str(tmp_path / "b.csv")])
    assert train_classifier.main() == 1
    assert "preprocess" in capsys.readouterr().out
