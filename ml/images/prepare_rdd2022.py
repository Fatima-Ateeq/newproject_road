"""Turn RDD2022 into a YOLO training dataset with our own train, validation and test split.

    python -m ml.images.prepare_rdd2022 --source RDD2022 --out-dir yolo_dataset --countries India Japan --max-images-per-country 2000

--source can be a folder of country zips (India.zip, Japan.zip, ...), one zip file, or an extracted RDD2022
folder. Nothing is written inside the Git repository.
"""

import argparse
import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ml.images.classes import CLASS_DESCRIPTIONS, CLASS_NAMES
from ml.images.rdd2022 import Sample, index_samples, plan_split
from ml.images.source import Source, open_source
from ml.images.voc import parse_voc
from ml.images.yolo_format import to_yolo_lines

SPLITS = ("train", "val", "test")


@dataclass
class Report:
    images: Counter = field(default_factory=Counter)  # per split
    background: Counter = field(default_factory=Counter)  # images with no usable box, per split
    ignored_only: Counter = field(default_factory=Counter)  # background images that had boxes of other classes
    boxes: dict = field(default_factory=lambda: {split: Counter() for split in SPLITS})
    ignored_boxes: Counter = field(default_factory=Counter)
    skipped: Counter = field(default_factory=Counter)  # reason -> count
    dropped_background: int = 0
    unpaired_files: int = 0

    def as_dict(self) -> dict:
        return {
            "images": dict(self.images),
            "background_images": dict(self.background),
            "background_with_only_other_classes": dict(self.ignored_only),
            "background_dropped_by_ratio_limit": self.dropped_background,
            "boxes_per_class": {split: dict(counts) for split, counts in self.boxes.items()},
            "ignored_boxes": dict(self.ignored_boxes),
            "skipped_images": dict(self.skipped),
            "unpaired_files": self.unpaired_files,
        }


@dataclass(frozen=True)
class Converted:
    """One sample whose annotation has been read and converted, not yet written to disk."""

    sample: Sample
    lines: list[str]
    ignored: Counter

    @property
    def has_other_class_boxes(self) -> bool:
        """True if the image had boxes of classes we do not train on (not just invalid boxes)."""
        return any(not name.startswith("<") for name in self.ignored)


def convert_sample(source: Source, sample: Sample, report: Report) -> Converted | None:
    """Read and convert one annotation. Bad samples are counted and skipped (None)."""
    try:
        annotation = parse_voc(source.read(sample.xml_name))
    except ValueError:
        report.skipped["bad annotation"] += 1
        return None
    if annotation.width <= 0 or annotation.height <= 0:
        report.skipped["missing image size"] += 1
        return None
    lines, ignored = to_yolo_lines(annotation)
    return Converted(sample, lines, ignored)


def limit_background(items: list[Converted], max_ratio: float, seed: int) -> list[Converted]:
    """Keep every image with damage, and only as many background images as `max_ratio` allows."""
    positives = sum(1 for item in items if item.lines)
    background = [item for item in items if not item.lines]
    allowed = int(max_ratio / (1 - max_ratio) * positives)
    if len(background) <= allowed:
        return items
    kept = {id(item) for item in random.Random(seed).sample(background, allowed)}
    return [item for item in items if item.lines or id(item) in kept]


def write_sample(source: Source, item: Converted, split: str, out_dir: Path, report: Report) -> None:
    sample = item.sample
    image_file = out_dir / "images" / split / Path(sample.image_name).name
    label_file = out_dir / "labels" / split / f"{sample.stem}.txt"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    label_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_bytes(source.read(sample.image_name))
    label_file.write_text("\n".join(item.lines) + ("\n" if item.lines else ""), encoding="utf-8")

    report.images[split] += 1
    report.ignored_boxes.update(item.ignored)
    if not item.lines:
        report.background[split] += 1
        if item.has_other_class_boxes:
            report.ignored_only[split] += 1
    for line in item.lines:
        report.boxes[split][CLASS_NAMES[int(line.split()[0])]] += 1


def write_data_yaml(out_dir: Path) -> None:
    names = "\n".join(f"  {index}: {name}" for index, name in enumerate(CLASS_NAMES))
    (out_dir / "data.yaml").write_text(
        f"train: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n", encoding="utf-8"
    )


def print_report(report: Report) -> None:
    print(f"\n{'split':<8}{'images':>8}{'no-box':>8}" + "".join(f"{name:>8}" for name in CLASS_NAMES))
    for split in SPLITS:
        counts = report.boxes[split]
        print(
            f"{split:<8}{report.images[split]:>8}{report.background[split]:>8}"
            + "".join(f"{counts[name]:>8}" for name in CLASS_NAMES)
        )
    print("\nClasses: " + ", ".join(f"{name} = {text}" for name, text in CLASS_DESCRIPTIONS.items()))
    print(f"no-box images that only had boxes of other classes: {dict(report.ignored_only)}")
    if report.dropped_background:
        print(f"Background images dropped from train by the ratio limit: {report.dropped_background}")
    if report.ignored_boxes:
        print(f"Boxes left out (other classes or invalid): {dict(report.ignored_boxes)}")
    if report.skipped:
        print(f"Images skipped: {dict(report.skipped)}")
    if report.unpaired_files:
        print(f"Files without a matching image or annotation: {report.unpaired_files}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert RDD2022 into a YOLO dataset.")
    parser.add_argument("--source", type=Path, required=True, help="Folder of country zips, a zip, or a folder")
    parser.add_argument("--out-dir", type=Path, required=True, help="Where to write the YOLO dataset")
    parser.add_argument("--countries", nargs="+", required=True, help="For example: India Japan")
    parser.add_argument("--max-images-per-country", type=int, default=None)
    parser.add_argument("--max-background-ratio", type=float, default=None,
                        help="Largest share of train images without damage, e.g. 0.1. Default: keep all")
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--test-fraction", type=float, default=0.1)
    parser.add_argument("--group-size", type=int, default=20, help="Consecutive images kept together")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    ratio = args.max_background_ratio
    if ratio is not None and not 0 < ratio < 1:
        print("--max-background-ratio must be between 0 and 1, for example 0.1")
        return 1
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        print(f"{args.out_dir} is not empty. Delete it or choose another folder, so runs are never mixed.")
        return 1

    source = open_source(args.source)
    names = source.names()
    by_country, unpaired = index_samples(names)
    if not by_country:
        print("No labeled images found. The first file names in the source were:")
        print(*names[:10], sep="\n")
        print("Expected names like <Country>/train/annotations/xmls/<name>.xml and <Country>/train/images/<name>.jpg")
        return 1
    unknown = [country for country in args.countries if country not in by_country]
    if unknown:
        print(f"Not found: {unknown}. Available: {sorted(by_country)}")
        return 1

    report = Report(unpaired_files=unpaired)
    for country in args.countries:
        plan = plan_split(
            by_country[country], args.max_images_per_country,
            args.val_fraction, args.test_fraction, args.seed, args.group_size,
        )
        for split, samples in plan.items():
            converted = [c for sample in samples if (c := convert_sample(source, sample, report))]
            if split == "train" and ratio is not None:
                limited = limit_background(converted, ratio, args.seed)
                report.dropped_background += len(converted) - len(limited)
                converted = limited
            for item in converted:
                write_sample(source, item, split, args.out_dir, report)
        print(f"{country}: done")

    write_data_yaml(args.out_dir)
    (args.out_dir / "summary.json").write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    print_report(report)
    print(f"\nDataset written to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
