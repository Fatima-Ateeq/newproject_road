from ml.common.categories import CATEGORIES
from ml.text.cleaning import dedupe, detect_script, normalize_text, remove_leakage, split_stratified


def row(text, label=CATEGORIES[0]):
    return {"text": text, "label": label}


def test_normalize_collapses_whitespace_and_strips_control_characters():
    assert normalize_text("  big \t pothole\n\n here\x00 ") == "big pothole here"


def test_normalize_keeps_urdu_zero_width_joiner():
    assert "\u200c" in normalize_text("ہوں\u200cگے")


def test_detect_script():
    assert detect_script("سڑک پر گڑھا ہے") == "arabic"
    assert detect_script("Sarak par gaddha hai") == "latin"
    assert detect_script("pothole سڑک گڑھا") == "mixed"
    assert detect_script("123 !!!") == "other"


def test_dedupe_ignores_case_and_spacing_and_reports_conflicts():
    rows = [row("Big pothole"), row("  big   POTHOLE "), row("Big pothole", CATEGORIES[1])]
    unique, conflicts = dedupe(rows)
    assert len(unique) == 1
    assert conflicts == ["Big pothole"]


def test_leakage_removes_training_rows_found_in_the_test_set():
    kept, removed = remove_leakage([row("a b"), row("c d")], [row("A  B")])
    assert [r["text"] for r in kept] == ["c d"]
    assert removed == 1


def test_split_is_stratified_deterministic_and_disjoint():
    rows = [row(f"road {i}", CATEGORIES[0]) for i in range(20)] + [row(f"jam {i}", CATEGORIES[1]) for i in range(10)]
    train, val = split_stratified(rows, 0.2, seed=1)
    assert split_stratified(rows, 0.2, seed=1) == (train, val)
    assert sum(r["label"] == CATEGORIES[0] for r in val) == 4
    assert sum(r["label"] == CATEGORIES[1] for r in val) == 2
    assert {r["text"] for r in train}.isdisjoint({r["text"] for r in val})
    assert len(train) + len(val) == len(rows)
