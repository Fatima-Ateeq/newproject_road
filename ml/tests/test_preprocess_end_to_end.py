import sys

from ml.text import preprocess
from ml.text.csv_io import read_rows, write_rows


def test_preprocess_writes_clean_splits_without_leakage(tmp_path, monkeypatch, capsys):
    train_file, gold_file, out_dir = tmp_path / "train.csv", tmp_path / "gold.csv", tmp_path / "out"
    write_rows(
        train_file,
        [{"text": f"road problem {i}", "label": "Road Damage", "language": "en"} for i in range(10)]
        + [{"text": "shared complaint", "label": "Other", "language": "en"}],
        ["text", "label", "language"],
    )
    write_rows(gold_file, [{"text": "Shared  complaint", "label": "Other"}], ["text", "label"])
    monkeypatch.setattr(
        sys, "argv",
        ["preprocess", "--train-input", str(train_file), "--test", str(gold_file), "--out-dir", str(out_dir)],
    )

    assert preprocess.main() == 0

    train, val, test = (read_rows(out_dir / f"{name}.csv") for name in ("train", "val", "test"))
    assert len(train) + len(val) == 10
    assert all(row["text"] != "shared complaint" for row in train + val)
    assert [row["text"] for row in test] == ["Shared complaint"]
    assert {row["script"] for row in train} == {"latin"}


def test_preprocess_rejects_unknown_labels(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.csv"
    write_rows(bad, [{"text": "something here", "label": "Nonsense"}], ["text", "label"])
    monkeypatch.setattr(sys, "argv", ["preprocess", "--train-input", str(bad), "--test", str(tmp_path / "none.csv"),
                                      "--out-dir", str(tmp_path / "out")])
    assert preprocess.main() == 1
    assert "Unknown labels" in capsys.readouterr().out
