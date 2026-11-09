from ml.text.csv_io import append_row, read_rows, write_rows


def test_round_trip_keeps_urdu_and_commas(tmp_path):
    rows = [{"text": "سڑک پر گڑھا ہے, بہت بڑا", "label": "Road Damage"}]
    write_rows(tmp_path / "a.csv", rows, ["text", "label"])
    assert read_rows(tmp_path / "a.csv") == rows


def test_append_row_writes_the_header_once(tmp_path):
    path = tmp_path / "a.csv"
    append_row(path, {"id": "1"}, ["id"])
    append_row(path, {"id": "2"}, ["id"])
    assert [row["id"] for row in read_rows(path)] == ["1", "2"]
