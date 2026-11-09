"""Compare two labelers' files and list what they disagree on.

    python -m ml.text.check_agreement ml/data/text/labels/ali.csv ml/data/text/labels/sara.csv
"""

import argparse
from pathlib import Path

from ml.common.paths import LABELS_DIR
from ml.text.agreement import compare
from ml.text.csv_io import read_rows, write_rows

DISAGREEMENT_FIELDS = ["id", "text", "label_a", "label_b", "final_label"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure agreement between two labelers.")
    parser.add_argument("file_a", type=Path)
    parser.add_argument("file_b", type=Path)
    parser.add_argument("--out", type=Path, default=LABELS_DIR / "disagreements.csv")
    args = parser.parse_args()

    report = compare(read_rows(args.file_a), read_rows(args.file_b))
    print(f"Agreement: {report.percent:.1f}% ({report.agreed} of {report.compared} complaints)")
    if report.labeled_by_one_only:
        print(f"Warning: {len(report.labeled_by_one_only)} complaints were labeled by only one person.")

    rows = [
        {"id": d.id, "text": d.text, "label_a": d.label_a, "label_b": d.label_b, "final_label": ""}
        for d in report.disagreements
    ]
    write_rows(args.out, rows, DISAGREEMENT_FIELDS)
    print(f"{len(rows)} disagreements written to {args.out}. Fill in the final_label column together.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
