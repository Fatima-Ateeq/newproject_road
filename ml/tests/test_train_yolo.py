import json
from pathlib import Path
from types import SimpleNamespace

from ml.images import train_yolo


class FakeBox:
    mp, mr, map50, map = 0.61, 0.52, 0.55, 0.31
    maps = [0.21, 0.32, 0.43, 0.26]


class FakeYOLO:
    """Stands in for Ultralytics so the script's logic can be tested without a graphics card."""

    instances: list = []
    save_dir: Path

    def __init__(self, weights: str) -> None:
        self.weights, self.val_calls, self.train_kwargs = weights, [], None
        FakeYOLO.instances.append(self)

    def train(self, **kwargs):
        self.train_kwargs = kwargs
        (FakeYOLO.save_dir / "weights").mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(save_dir=FakeYOLO.save_dir)

    def val(self, **kwargs):
        self.val_calls.append(kwargs)
        return SimpleNamespace(box=FakeBox())


def run(tmp_path, *extra: str) -> int:
    FakeYOLO.instances = []
    FakeYOLO.save_dir = tmp_path / "runs" / "damage_detector"
    data = tmp_path / "rdd" / "data.yaml"
    data.parent.mkdir(exist_ok=True)
    data.write_text("names: {}")
    return train_yolo.main(["--data", str(data), *extra], yolo_class=FakeYOLO)


def test_training_arguments_are_built_from_the_options(tmp_path):
    assert run(tmp_path, "--epochs", "5", "--batch", "4", "--fraction", "0.1", "--no-amp", "--cache") == 0
    kwargs = FakeYOLO.instances[0].train_kwargs
    assert (kwargs["epochs"], kwargs["batch"], kwargs["fraction"]) == (5, 4, 0.1)
    assert kwargs["amp"] is False and kwargs["cache"] is True
    assert kwargs["device"] == 0 and kwargs["imgsz"] == 640 and kwargs["workers"] == 2
    assert Path(kwargs["data"]).is_absolute()


def test_runs_are_saved_next_to_the_dataset_not_inside_the_repository(tmp_path):
    run(tmp_path)
    assert Path(FakeYOLO.instances[0].train_kwargs["project"]) == (tmp_path / "runs")


def test_the_device_can_be_cpu(tmp_path):
    run(tmp_path, "--device", "cpu")
    assert FakeYOLO.instances[0].train_kwargs["device"] == "cpu"


def test_the_test_split_is_only_scored_when_asked(tmp_path):
    run(tmp_path)
    splits = [call["split"] for call in FakeYOLO.instances[1].val_calls]
    assert splits == ["val"]

    run(tmp_path, "--evaluate-test")
    splits = [call["split"] for call in FakeYOLO.instances[1].val_calls]
    assert splits == ["val", "test"]


def test_the_best_weights_are_the_ones_evaluated(tmp_path):
    run(tmp_path)
    assert FakeYOLO.instances[1].weights.endswith("best.pt")


def test_a_summary_with_the_main_scores_is_saved(tmp_path):
    run(tmp_path, "--evaluate-test")
    summary = json.loads((FakeYOLO.save_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["validation"]["map50"] == 0.55
    assert summary["test"]["recall"] == 0.52
    assert summary["validation"]["map50_95_by_class"]["D40 (pothole)"] == 0.26
    assert summary["classes"] == ["D00", "D10", "D20", "D40"]


def test_a_missing_dataset_file_gives_a_clear_message(tmp_path, capsys):
    assert train_yolo.main(["--data", str(tmp_path / "nope.yaml")], yolo_class=FakeYOLO) == 1
    assert "prepare_rdd2022" in capsys.readouterr().out
