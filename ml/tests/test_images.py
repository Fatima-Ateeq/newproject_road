import json
import sys
import zipfile
from pathlib import Path

import pytest

from collections import Counter

from ml.images import prepare_rdd2022
from ml.images.rdd2022 import Sample
from ml.images.rdd2022 import index_samples
from ml.images.splitting import assign_splits
from ml.images.voc import parse_voc
from ml.images.yolo_format import to_yolo_lines


def xml(width=100, height=50, boxes=(("D00", 10, 5, 60, 25),)):
    objects = "".join(
        f"<object><name>{n}</name><bndbox><xmin>{a}</xmin><ymin>{b}</ymin><xmax>{c}</xmax><ymax>{d}</ymax></bndbox></object>"
        for n, a, b, c, d in boxes
    )
    return f"<annotation><size><width>{width}</width><height>{height}</height></size>{objects}</annotation>".encode()


# ---------- parsing and conversion ----------

def test_voc_box_becomes_normalized_yolo_line():
    lines, ignored = to_yolo_lines(parse_voc(xml()))
    assert lines == ["0 0.350000 0.300000 0.500000 0.400000"]
    assert not ignored


def test_class_ids_follow_the_class_order():
    lines, _ = to_yolo_lines(parse_voc(xml(boxes=[("D10", 0, 0, 10, 10), ("D40", 0, 0, 10, 10)])))
    assert [line.split()[0] for line in lines] == ["1", "3"]


def test_boxes_are_clipped_to_the_image():
    lines, _ = to_yolo_lines(parse_voc(xml(boxes=[("D00", -20, -20, 200, 100)])))
    assert lines == ["0 0.500000 0.500000 1.000000 1.000000"]


def test_unknown_classes_and_empty_boxes_are_counted_not_converted():
    lines, ignored = to_yolo_lines(parse_voc(xml(boxes=[("D99", 0, 0, 10, 10), ("D00", 30, 30, 30, 40)])))
    assert lines == []
    assert ignored["D99"] == 1
    assert ignored["<invalid box>"] == 1


def test_malformed_xml_raises_value_error():
    with pytest.raises(ValueError):
        parse_voc(b"<annotation><size>")
    with pytest.raises(ValueError):
        parse_voc(b"<annotation><object><name>D00</name><bndbox/></object></annotation>")


# ---------- splitting ----------

def test_split_keeps_groups_together_and_is_repeatable():
    labels = assign_splits(200, 0.1, 0.1, seed=7, group_size=20)
    assert labels == assign_splits(200, 0.1, 0.1, seed=7, group_size=20)
    for start in range(0, 200, 20):
        assert len(set(labels[start:start + 20])) == 1
    assert set(labels) == {"train", "val", "test"}
    assert labels.count("val") == 20 and labels.count("test") == 20


def test_split_of_few_items_still_covers_every_position():
    assert len(assign_splits(5, 0.1, 0.1, seed=1, group_size=20)) == 5


# ---------- indexing ----------

def test_index_pairs_images_with_annotations_and_ignores_test_images():
    names = [
        "RDD2022/India/train/images/India_1.jpg",
        "RDD2022/India/train/annotations/xmls/India_1.xml",
        "RDD2022/India/train/images/India_2.jpg",          # no annotation
        "RDD2022/India/test/images/India_9.jpg",           # unlabeled official test image
    ]
    by_country, unpaired = index_samples(names)
    assert [s.stem for s in by_country["India"]] == ["India_1"]
    assert unpaired == 1


# ---------- the whole script ----------

def build_dataset(files: dict[str, bytes], countries: dict[str, int]) -> None:
    for country, count in countries.items():
        for i in range(count):
            stem = f"{country}_{i:06d}"
            files[f"RDD2022/{country}/train/images/{stem}.jpg"] = b"\xff\xd8\xff" + stem.encode()
            boxes = [("D00", 1, 1, 50, 20)] if i % 3 else []          # every third image is background
            files[f"RDD2022/{country}/train/annotations/xmls/{stem}.xml"] = xml(boxes=boxes)
        files[f"RDD2022/{country}/test/images/{country}_t0.jpg"] = b"\xff\xd8\xff"
    bad = "India_bad"
    files[f"RDD2022/India/train/images/{bad}.jpg"] = b"\xff\xd8\xff"
    files[f"RDD2022/India/train/annotations/xmls/{bad}.xml"] = xml(width=0, height=0)


@pytest.fixture
def raw_dir(tmp_path) -> Path:
    files: dict[str, bytes] = {}
    build_dataset(files, {"India": 100, "Japan": 60})
    root = tmp_path / "raw"
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


@pytest.fixture
def raw_zip(raw_dir, tmp_path) -> Path:
    path = tmp_path / "rdd.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for file in raw_dir.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(raw_dir).as_posix())
    return path


def run(monkeypatch, source: Path, out_dir: Path, *extra: str) -> int:
    argv = ["prepare", "--source", str(source), "--out-dir", str(out_dir), *extra]
    monkeypatch.setattr(sys, "argv", argv)
    return prepare_rdd2022.main()


@pytest.mark.parametrize("kind", ["zip", "folder"])
def test_script_builds_a_yolo_dataset_from_zip_or_folder(kind, raw_zip, raw_dir, tmp_path, monkeypatch):
    out = tmp_path / "yolo"
    source = raw_zip if kind == "zip" else raw_dir
    assert run(monkeypatch, source, out, "--countries", "India", "Japan", "--group-size", "10") == 0

    images = {split: sorted(p.name for p in (out / "images" / split).glob("*.jpg")) for split in ("train", "val", "test")}
    labels = {split: sorted(p.stem for p in (out / "labels" / split).glob("*.txt")) for split in ("train", "val", "test")}
    for split in images:
        assert [Path(n).stem for n in images[split]] == labels[split]
        assert images[split]
    all_images = sum(images.values(), [])
    assert len(all_images) == len(set(all_images)) == 160            # 100 + 60 labeled, bad one skipped, test images ignored

    summary = json.loads((out / "summary.json").read_text())
    assert summary["skipped_images"] == {"missing image size": 1}
    assert sum(summary["images"].values()) == 160
    assert sum(summary["background_images"].values()) > 0
    assert "0: D00" in (out / "data.yaml").read_text() and "3: D40" in (out / "data.yaml").read_text()


def test_max_images_limits_each_country(raw_zip, tmp_path, monkeypatch):
    out = tmp_path / "yolo"
    assert run(monkeypatch, raw_zip, out, "--countries", "India", "Japan", "--max-images-per-country", "40",
               "--group-size", "5") == 0
    total = sum(json.loads((out / "summary.json").read_text())["images"].values())
    assert 70 <= total <= 82                                         # about 40 per country


def test_unknown_country_and_non_empty_output_are_rejected(raw_zip, tmp_path, monkeypatch, capsys):
    assert run(monkeypatch, raw_zip, tmp_path / "a", "--countries", "Narnia") == 1
    assert "Not found" in capsys.readouterr().out

    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "file.txt").write_text("x")
    assert run(monkeypatch, raw_zip, busy, "--countries", "India") == 1
    assert "not empty" in capsys.readouterr().out


def make_country_zips(raw_dir: Path, folder: Path, keep_country_folder: bool) -> None:
    """Build India.zip and Japan.zip like the real release: one zip per country."""
    folder.mkdir()
    for country in ("India", "Japan"):
        with zipfile.ZipFile(folder / f"{country}.zip", "w") as archive:
            for file in (raw_dir / "RDD2022" / country).rglob("*"):
                if file.is_file():
                    inner = file.relative_to(raw_dir / "RDD2022")
                    if not keep_country_folder:
                        inner = inner.relative_to(country)
                    archive.write(file, inner.as_posix())


@pytest.mark.parametrize("keep_country_folder", [True, False])
def test_script_reads_a_folder_of_country_zips(keep_country_folder, raw_dir, tmp_path, monkeypatch):
    folder = tmp_path / "countries"
    make_country_zips(raw_dir, folder, keep_country_folder)
    out = tmp_path / "yolo"
    assert run(monkeypatch, folder, out, "--countries", "India", "Japan", "--group-size", "10") == 0
    assert sum(json.loads((out / "summary.json").read_text())["images"].values()) == 160


def test_script_shows_file_names_when_nothing_matches(tmp_path, monkeypatch, capsys):
    folder = tmp_path / "odd"
    folder.mkdir()
    (folder / "something.txt").write_text("x")
    assert run(monkeypatch, folder, tmp_path / "out", "--countries", "India") == 1
    output = capsys.readouterr().out
    assert "No labeled images found" in output and "something.txt" in output


# ---------- background images ----------

def converted(stem: str, with_damage: bool, other_class: bool = False):
    lines = ["0 0.5 0.5 0.2 0.2"] if with_damage else []
    ignored = Counter({"D44": 1}) if other_class else Counter()
    sample = Sample("India", stem, f"{stem}.xml", f"{stem}.jpg")
    return prepare_rdd2022.Converted(sample, lines, ignored)


def test_limit_background_keeps_all_damage_images_and_caps_the_rest():
    items = [converted(f"d{i}", True) for i in range(18)] + [converted(f"b{i}", False) for i in range(12)]
    kept = prepare_rdd2022.limit_background(items, max_ratio=0.1, seed=1)
    assert sum(1 for item in kept if item.lines) == 18
    assert sum(1 for item in kept if not item.lines) == 2          # 0.1 / 0.9 * 18
    assert kept == [item for item in items if item in kept]          # original order is preserved


def test_limit_background_changes_nothing_when_already_under_the_limit():
    items = [converted(f"d{i}", True) for i in range(18)] + [converted("b0", False)]
    assert prepare_rdd2022.limit_background(items, max_ratio=0.1, seed=1) == items


def test_images_with_only_other_class_boxes_are_counted_as_background_with_other_classes():
    assert converted("x", False, other_class=True).has_other_class_boxes
    assert not converted("x", False).has_other_class_boxes


def test_script_limits_background_in_train_only(raw_zip, tmp_path, monkeypatch):
    out = tmp_path / "yolo"
    assert run(monkeypatch, raw_zip, out, "--countries", "India", "Japan", "--group-size", "10",
               "--max-background-ratio", "0.1") == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["background_dropped_by_ratio_limit"] > 0
    train_images = len(list((out / "images" / "train").glob("*.jpg")))
    train_background = summary["background_images"]["train"]
    assert train_background / train_images <= 0.12
    assert summary["background_images"]["val"] + summary["background_images"]["test"] > 0


def test_script_rejects_a_ratio_outside_zero_and_one(raw_zip, tmp_path, monkeypatch, capsys):
    assert run(monkeypatch, raw_zip, tmp_path / "o", "--countries", "India", "--max-background-ratio", "1.5") == 1
    assert "between 0 and 1" in capsys.readouterr().out
