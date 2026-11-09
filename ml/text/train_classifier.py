"""Train the text classifier, measure it, and save it where the backend loads it.

    python -m ml.text.preprocess          (first, to create the train and validation files)
    python -m ml.text.train_classifier

The scores printed here come from generated examples. They show that the model learns, but they are
NOT the final result. The final result is measured on the human-written gold test set.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn

from ml.common.categories import CATEGORIES
from ml.common.paths import CLASSIFIER_ARTIFACT_DIR, PROCESSED_DIR
from ml.text.classifier_training import (
    Metrics,
    baseline_metrics,
    cross_validated_metrics,
    fit_final_model,
    validation_metrics,
)
from ml.text.csv_io import read_rows

MODEL_FILE = "text_classifier.joblib"
CARD_FILE = "text_classifier_card.json"


def print_metrics(title: str, metrics: Metrics) -> None:
    per_category = "  ".join(f"{name[:9]}={value:.2f}" for name, value in metrics.f1_per_category.items())
    print(f"{title:<28} n={metrics.examples:<4} accuracy={metrics.accuracy:.3f}  macro-F1={metrics.macro_f1:.3f}")
    print(f"{'':<28} F1 by category: {per_category}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and save the complaint text classifier.")
    parser.add_argument("--train", type=Path, default=PROCESSED_DIR / "train.csv")
    parser.add_argument("--val", type=Path, default=PROCESSED_DIR / "val.csv")
    parser.add_argument("--out-dir", type=Path, default=CLASSIFIER_ARTIFACT_DIR)
    args = parser.parse_args()

    for path in (args.train, args.val):
        if not path.exists():
            print(f"{path} not found. Run python -m ml.text.preprocess first.")
            return 1
    train_rows, val_rows = read_rows(args.train), read_rows(args.val)
    everything = train_rows + val_rows

    cross_validated = cross_validated_metrics(everything)
    validation = validation_metrics(train_rows, val_rows)
    baseline = baseline_metrics(everything)
    print_metrics("Trained model, 5-fold CV", cross_validated)
    print_metrics("Trained model, validation", validation)
    print_metrics("Keyword baseline, all", baseline)

    model = fit_final_model(everything)  # the saved model learns from every example
    args.out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.out_dir / MODEL_FILE)
    card = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "examples": len(everything),
        "categories": CATEGORIES,
        "cross_validated": cross_validated.__dict__,
        "validation": validation.__dict__,
        "keyword_baseline": baseline.__dict__,
        "scikit_learn_version": sklearn.__version__,
        "note": "Measured on generated examples, not on the human-written test set.",
    }
    (args.out_dir / CARD_FILE).write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {args.out_dir / MODEL_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
