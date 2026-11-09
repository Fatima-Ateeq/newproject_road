"""Clean the text datasets and split them into train, validation and test files.

    python -m ml.text.preprocess

Inputs : every generated_*.csv training file (or the files you pass), and gold_test.csv if it exists
Outputs: ml/data/text/processed/train.csv, val.csv, test.csv
"""

import argparse
from collections import Counter
from pathlib import Path

from ml.common.categories import CATEGORIES
from ml.common.paths import GENERATED_TRAINING_FILES, GOLD_TEST_SET, PROCESSED_DIR
from ml.text.cleaning import dedupe, detect_script, normalize_text, remove_leakage, split_stratified
from ml.text.csv_io import read_rows, write_rows

OUTPUT_FIELDS = ["text", "label", "language", "script", "source"]


def prepare(rows: list[dict[str, str]], default_source: str) -> list[dict[str, str]]:
    """Normalize text, add the script column, and drop empty rows."""
    prepared = []
    for row in rows:
        text = normalize_text(row["text"])
        if text:
            prepared.append(
                {
                    "text": text,
                    "label": row["label"].strip(),
                    "language": row.get("language", "").strip() or "unknown",
                    "script": detect_script(text),
                    "source": row.get("source", "").strip() or default_source,
                }
            )
    return prepared


def invalid_labels(rows: list[dict[str, str]]) -> list[str]:
    return sorted({row["label"] for row in rows if row["label"] not in CATEGORIES})


def print_summary(splits: dict[str, list[dict[str, str]]]) -> None:
    print(f"{'split':<8}" + "".join(f"{name[:12]:>14}" for name in CATEGORIES) + f"{'total':>8}")
    for split_name, rows in splits.items():
        counts = Counter(row["label"] for row in rows)
        print(f"{split_name:<8}" + "".join(f"{counts[name]:>14}" for name in CATEGORIES) + f"{len(rows):>8}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean and split the text datasets.")
    parser.add_argument("--train-input", type=Path, nargs="+", default=GENERATED_TRAINING_FILES)
    parser.add_argument("--test", type=Path, default=GOLD_TEST_SET)
    parser.add_argument("--out-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train_rows = [r for path in args.train_input for r in prepare(read_rows(path), path.stem)]
    test_rows = prepare(read_rows(args.test), "gold") if args.test.exists() else []

    bad = invalid_labels(train_rows + test_rows)
    if bad:
        print(f"Unknown labels found: {bad}. Allowed: {CATEGORIES}")
        return 1

    train_rows, conflicts = dedupe(train_rows)
    if conflicts:
        print(f"{len(conflicts)} texts appear with different labels. Fix them first, e.g.: {conflicts[:3]}")
        return 1

    train_rows, leaked = remove_leakage(train_rows, test_rows)
    train, val = split_stratified(train_rows, args.val_fraction, args.seed)

    splits = {"train": train, "val": val, "test": test_rows}
    for name, rows in splits.items():
        write_rows(args.out_dir / f"{name}.csv", rows, OUTPUT_FIELDS)

    print_summary(splits)
    print(f"\nRemoved {leaked} training rows that also appear in the test set.")
    if not test_rows:
        print(f"Note: {args.test} does not exist yet, so test.csv is empty.")
    print(f"Files written to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
