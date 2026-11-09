"""Merge the filled-in collection sheets into the test pool.

    python -m ml.text.merge_collected

Reads every CSV in ml/data/text/collected/ and writes ml/data/text/test_pool.csv with ids T001, T002, ...
"""

import argparse
from collections import Counter
from pathlib import Path

from ml.common.paths import COLLECTED_DIR, TEST_POOL
from ml.text.collection import POOL_FIELDS, merge
from ml.text.csv_io import read_rows_any_delimiter, write_rows

MIN_PER_SCENARIO = 15


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge collected complaint sheets into the test pool.")
    parser.add_argument("--input-dir", type=Path, default=COLLECTED_DIR)
    parser.add_argument("--out", type=Path, default=TEST_POOL)
    args = parser.parse_args()

    files = {path.stem: read_rows_any_delimiter(path) for path in sorted(args.input_dir.glob("*.csv"))}
    if not files:
        print(f"No CSV files found in {args.input_dir}")
        return 1

    result = merge(files)
    for problem in result.problems[:10]:
        print("Problem:", problem)
    if len(result.problems) > 10:
        print(f"... and {len(result.problems) - 10} more problems")
    if not result.rows:
        print("No usable complaints found.")
        return 1

    write_rows(args.out, result.rows, POOL_FIELDS)
    print(f"{len(result.rows)} complaints from {len(files)} files written to {args.out}")
    print(f"Duplicates removed: {result.duplicates}. Rows with problems skipped: {len(result.problems)}")
    print("By language:", dict(Counter(row["language"] for row in result.rows)))
    scenarios = Counter(row["scenario"] or "(none)" for row in result.rows)
    print("By scenario:", dict(scenarios))
    low = [name for name, count in scenarios.items() if count < MIN_PER_SCENARIO]
    if low:
        print(f"Warning: fewer than {MIN_PER_SCENARIO} complaints for: {low}. Ask for a few more.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
