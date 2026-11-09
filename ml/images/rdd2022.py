"""Finds the labeled RDD2022 images and decides which of them go into which split."""

import random
import re
from collections import defaultdict
from dataclasses import dataclass

from ml.images.splitting import assign_splits

# Only the 'train' folders have annotations. The official 'test' folders contain images only.
_ANNOTATION = re.compile(r"(?:^|.*/)([^/]+)/train/annotations/xmls/([^/]+)\.xml$")
_IMAGE = re.compile(r"(?:^|.*/)([^/]+)/train/images/([^/]+)\.(?:jpe?g|png)$", re.IGNORECASE)


@dataclass(frozen=True)
class Sample:
    country: str
    stem: str
    xml_name: str
    image_name: str


def index_samples(names: list[str]) -> tuple[dict[str, list[Sample]], int]:
    """Pair every annotation with its image. Returns samples per country and the unpaired count."""
    annotations: dict[tuple[str, str], str] = {}
    images: dict[tuple[str, str], str] = {}
    for name in names:
        if match := _ANNOTATION.match(name):
            annotations[(match.group(1), match.group(2))] = name
        elif match := _IMAGE.match(name):
            images[(match.group(1), match.group(2))] = name

    paired = sorted(annotations.keys() & images.keys())
    by_country: dict[str, list[Sample]] = defaultdict(list)
    for country, stem in paired:
        by_country[country].append(Sample(country, stem, annotations[(country, stem)], images[(country, stem)]))
    unpaired = len(annotations) + len(images) - 2 * len(paired)
    return dict(by_country), unpaired


def plan_split(
    samples: list[Sample],
    max_images: int | None,
    val_fraction: float,
    test_fraction: float,
    seed: int,
    group_size: int,
) -> dict[str, list[Sample]]:
    """Split one country's samples, then keep at most `max_images` of them in total."""
    ordered = sorted(samples, key=lambda sample: sample.stem)
    labels = assign_splits(len(ordered), val_fraction, test_fraction, seed, group_size)
    plan: dict[str, list[Sample]] = {"train": [], "val": [], "test": []}
    for sample, split in zip(ordered, labels):
        plan[split].append(sample)

    if max_images is not None and len(ordered) > max_images:
        keep = max_images / len(ordered)
        rng = random.Random(seed)
        for split, members in plan.items():
            target = round(len(members) * keep)
            plan[split] = sorted(rng.sample(members, target), key=lambda sample: sample.stem)
    return plan
