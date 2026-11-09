from ml.common.categories import CATEGORIES
from ml.text.label_tool import run_session
from ml.text.labeling import Item, LabelStore, parse_choice

ITEMS = [Item("T1", "first complaint", "en"), Item("T2", "second complaint", "en"), Item("T3", "third", "en")]


def scripted(answers):
    iterator = iter(answers)
    return lambda _prompt: next(iterator)


def make_store(tmp_path):
    return LabelStore(tmp_path / "ali.csv", "ali")


def test_parse_choice_maps_numbers_to_categories():
    assert parse_choice("1") == CATEGORIES[0]
    assert parse_choice(" 5 ") == CATEGORIES[4]
    assert parse_choice("6") is None
    assert parse_choice("x") is None


def test_labels_are_saved_with_the_labeler_name(tmp_path):
    store = make_store(tmp_path)
    run_session(ITEMS, store, ask=scripted(["1", "2", "q"]), show=lambda _: None)
    rows = store.rows()
    assert [(r["id"], r["label"], r["labeler"]) for r in rows] == [
        ("T1", CATEGORIES[0], "ali"),
        ("T2", CATEGORIES[1], "ali"),
    ]


def test_session_resumes_where_it_stopped(tmp_path):
    store = make_store(tmp_path)
    run_session(ITEMS, store, ask=scripted(["1", "q"]), show=lambda _: None)
    run_session(ITEMS, store, ask=scripted(["2", "3"]), show=lambda _: None)
    assert [r["id"] for r in store.rows()] == ["T1", "T2", "T3"]


def test_undo_removes_the_last_label_and_asks_again(tmp_path):
    store = make_store(tmp_path)
    run_session(ITEMS[:2], store, ask=scripted(["1", "u", "3", "2"]), show=lambda _: None)
    assert [(r["id"], r["label"]) for r in store.rows()] == [("T1", CATEGORIES[2]), ("T2", CATEGORIES[1])]


def test_skipped_items_come_back_later_in_the_session(tmp_path):
    store = make_store(tmp_path)
    run_session(ITEMS[:2], store, ask=scripted(["s", "1", "2"]), show=lambda _: None)
    assert [r["id"] for r in store.rows()] == ["T2", "T1"]


def test_invalid_input_asks_again_without_saving(tmp_path):
    store = make_store(tmp_path)
    run_session(ITEMS[:1], store, ask=scripted(["9", "hello", "4"]), show=lambda _: None)
    assert [r["label"] for r in store.rows()] == [CATEGORIES[3]]
