"""Build the final gold test set from two labelers' files and the resolved disagreements.

    python -m ml.text.build_gold_set ml/data/text/labels/ali.csv ml/data/text/labels/sara.csv
"""

import argparse
from pathlib import Path

from ml.common.paths import GOLD_TEST_SET, LABELS_DIR
from ml.text.agreement import build_gold
from ml.text.csv_io import read_rows, write_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the gold test set.")
    parser.add_argument("file_a", type=Path)
    parser.add_argument("file_b", type=Path)
    parser.add_argument("--resolved", type=Path, default=LABELS_DIR / "disagreements.csv")
    parser.add_argument("--out", type=Path, default=GOLD_TEST_SET)
    args = parser.parse_args()

    resolved_rows = read_rows(args.resolved) if args.resolved.exists() else []
    resolved = {row["id"]: row["final_label"].strip() for row in resolved_rows}
    try:
        gold = build_gold(read_rows(args.file_a), read_rows(args.file_b), resolved)
    except ValueError as error:
        print(error)
        return 1

    write_rows(args.out, gold, ["id", "text", "label"])
    print(f"Gold test set with {len(gold)} complaints written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
