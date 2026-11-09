"""Compare two labelers and build the final gold test set from their answers."""

from dataclasses import dataclass

from ml.common.categories import CATEGORIES


@dataclass(frozen=True)
class Disagreement:
    id: str
    text: str
    label_a: str
    label_b: str


@dataclass(frozen=True)
class AgreementReport:
    compared: int
    agreed: int
    disagreements: list[Disagreement]
    labeled_by_one_only: list[str]

    @property
    def percent(self) -> float:
        return 100 * self.agreed / self.compared if self.compared else 0.0


def _by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["id"]: row for row in rows}


def compare(rows_a: list[dict[str, str]], rows_b: list[dict[str, str]]) -> AgreementReport:
    a, b = _by_id(rows_a), _by_id(rows_b)
    shared = sorted(set(a) & set(b))
    disagreements = [
        Disagreement(i, a[i]["text"], a[i]["label"], b[i]["label"])
        for i in shared
        if a[i]["label"] != b[i]["label"]
    ]
    return AgreementReport(
        compared=len(shared),
        agreed=len(shared) - len(disagreements),
        disagreements=disagreements,
        labeled_by_one_only=sorted(set(a) ^ set(b)),
    )


def build_gold(
    rows_a: list[dict[str, str]], rows_b: list[dict[str, str]], resolved: dict[str, str]
) -> list[dict[str, str]]:
    """Agreed labels plus the team's decisions on disagreements. Raises if any are unresolved."""
    a, b = _by_id(rows_a), _by_id(rows_b)
    gold: list[dict[str, str]] = []
    unresolved: list[str] = []
    for id_ in sorted(set(a) & set(b)):
        label = a[id_]["label"] if a[id_]["label"] == b[id_]["label"] else resolved.get(id_, "")
        if label not in CATEGORIES:
            unresolved.append(id_)
        else:
            gold.append({"id": id_, "text": a[id_]["text"], "label": label})
    if unresolved:
        raise ValueError(f"{len(unresolved)} disagreements still need a final_label: {unresolved[:10]}")
    return gold
