import sys

from ml.text import merge_collected
from ml.text.collection import merge
from ml.text.csv_io import read_rows, read_rows_any_delimiter, write_rows


def row(text, language="en", scenario="Damaged road", writer=""):
    return {"text": text, "language": language, "scenario": scenario, "writer": writer}


def test_merge_assigns_sequential_ids_in_file_name_order():
    result = merge({"b_sara": [row("second file complaint")], "a_ali": [row("first file complaint"), row("another one")]})
    assert [(r["id"], r["text"]) for r in result.rows] == [
        ("T001", "first file complaint"), ("T002", "another one"), ("T003", "second file complaint")
    ]


def test_writer_defaults_to_the_file_name():
    result = merge({"a_ali": [row("some complaint text")], "b": [row("other complaint", writer="Sara")]})
    assert [r["writer"] for r in result.rows] == ["a_ali", "Sara"]


def test_blank_rows_are_ignored_and_duplicates_removed_across_files():
    result = merge({"a": [row("Big  pothole here"), row("   ")], "b": [row("big pothole HERE")]})
    assert len(result.rows) == 1
    assert result.duplicates == 1


def test_unknown_language_is_reported_with_its_line_number():
    result = merge({"a": [row("fine complaint"), row("bad language row", language="french")]})
    assert len(result.rows) == 1
    assert "a line 3" in result.problems[0]


def test_headers_with_capitals_and_spaces_are_accepted():
    result = merge({"a": [{" Text ": "A real complaint", "LANGUAGE": "UR", "Scenario": "x"}]})
    assert result.rows[0]["language"] == "ur"


def test_semicolon_separated_files_from_excel_can_be_read(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("text;language;scenario\nbig pothole near school;en;Damaged road\n", encoding="utf-8-sig")
    assert read_rows_any_delimiter(path)[0]["language"] == "en"


def test_script_writes_the_pool_from_a_folder(tmp_path, monkeypatch, capsys):
    folder, out = tmp_path / "collected", tmp_path / "pool.csv"
    write_rows(folder / "ali.csv", [row("complaint one about a road"), row("سڑک پر گڑھا ہے", "ur")],
               ["text", "language", "scenario", "writer"])
    monkeypatch.setattr(sys, "argv", ["merge", "--input-dir", str(folder), "--out", str(out)])
    assert merge_collected.main() == 0
    assert [r["id"] for r in read_rows(out)] == ["T001", "T002"]
    assert "By language" in capsys.readouterr().out


def test_script_fails_clearly_when_the_folder_is_empty(tmp_path, monkeypatch, capsys):
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(sys, "argv", ["merge", "--input-dir", str(tmp_path / "empty"), "--out", str(tmp_path / "o.csv")])
    assert merge_collected.main() == 1
    assert "No CSV files" in capsys.readouterr().out
