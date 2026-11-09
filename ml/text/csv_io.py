"""CSV reading and writing. UTF-8 with a BOM, so Excel shows Urdu text correctly."""

import csv
from pathlib import Path

ENCODING = "utf-8-sig"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding=ENCODING) as file:
        return list(csv.DictReader(file))


def read_rows_any_delimiter(path: Path) -> list[dict[str, str]]:
    """Like read_rows, but also accepts files saved with ';' or tab separators by Excel."""
    with path.open(newline="", encoding=ENCODING) as file:
        sample = file.read(4096)
        file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(file, dialect=dialect))


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding=ENCODING) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_row(path: Path, row: dict[str, str], fieldnames: list[str]) -> None:
    is_new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding=ENCODING) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow(row)
