import pytest

from ml.common.categories import CATEGORIES
from ml.text.agreement import build_gold, compare

ROAD, TRAFFIC = CATEGORIES[0], CATEGORIES[1]


def rows(*pairs):
    return [{"id": i, "text": f"text {i}", "label": label} for i, label in pairs]


def test_agreement_percentage_and_disagreements():
    report = compare(rows(("1", ROAD), ("2", ROAD), ("3", TRAFFIC), ("4", TRAFFIC)),
                     rows(("1", ROAD), ("2", TRAFFIC), ("3", TRAFFIC), ("4", TRAFFIC)))
    assert report.percent == 75.0
    assert [d.id for d in report.disagreements] == ["2"]


def test_ids_labeled_by_only_one_person_are_reported():
    report = compare(rows(("1", ROAD), ("2", ROAD)), rows(("1", ROAD)))
    assert report.compared == 1
    assert report.labeled_by_one_only == ["2"]


def test_gold_uses_agreed_labels_and_resolved_ones():
    a = rows(("1", ROAD), ("2", ROAD))
    b = rows(("1", ROAD), ("2", TRAFFIC))
    gold = build_gold(a, b, resolved={"2": TRAFFIC})
    assert [(g["id"], g["label"]) for g in gold] == [("1", ROAD), ("2", TRAFFIC)]


def test_gold_refuses_unresolved_or_invalid_decisions():
    a, b = rows(("1", ROAD)), rows(("1", TRAFFIC))
    with pytest.raises(ValueError):
        build_gold(a, b, resolved={})
    with pytest.raises(ValueError):
        build_gold(a, b, resolved={"1": "Not a category"})
