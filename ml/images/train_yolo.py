"""Fine-tune a pretrained YOLO model on our RDD2022 road-damage dataset.

Quick check that everything works (a few minutes at most):

    python -m ml.images.train_yolo --data E:\\work_folder\\datasets\\rdd2022_yolo\\data.yaml --epochs 1 --fraction 0.1

The real run:

    python -m ml.images.train_yolo --data E:\\work_folder\\datasets\\rdd2022_yolo\\data.yaml --epochs 40

Run it from the training environment (ml\\.venv: PyTorch with CUDA and ultralytics), not the backend environment.
Close games, launchers and browsers first: the graphics card is shared with Windows and everything else you run.

Model selection uses the validation split. The test split is used once, at the end, only with --evaluate-test.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from ml.images.classes import CLASS_DESCRIPTIONS, CLASS_NAMES


def parse_device(value: str) -> int | str:
    """'0' means the first graphics card. Anything else (for example 'cpu') is passed through."""
    return int(value) if value.isdigit() else value


def build_train_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """Everything passed to the trainer, in one place so it can be read and tested."""
    return {
        "data": str(args.data.resolve()),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "device": parse_device(args.device),
        "seed": args.seed,
        "patience": args.patience,
        "project": str(args.project),
        "name": args.name,
        "cache": args.cache,
        "amp": not args.no_amp,
        "fraction": args.fraction,
        "plots": True,
    }


def summarize(metrics: Any) -> dict[str, Any]:
    """Pick the numbers we report out of an Ultralytics validation result."""
    box = metrics.box
    by_class = {}
    per_class_map = list(getattr(box, "maps", []))
    for index, name in enumerate(CLASS_NAMES):
        if index < len(per_class_map):
            by_class[f"{name} ({CLASS_DESCRIPTIONS[name]})"] = round(float(per_class_map[index]), 4)
    return {
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
        "map50": round(float(box.map50), 4),
        "map50_95": round(float(box.map), 4),
        "map50_95_by_class": by_class,
    }


def _load_yolo():
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise SystemExit(
            "ultralytics is not installed in this environment. Activate ml\\.venv "
            "(see docs/setup.md, section GPU training environment)."
        ) from error
    return YOLO


def main(argv: list[str] | None = None, yolo_class: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Fine-tune YOLO on the RDD2022 YOLO dataset.")
    parser.add_argument("--data", type=Path, required=True, help="Path to data.yaml made by prepare_rdd2022")
    parser.add_argument("--model", default="yolo11n.pt", help="Pretrained starting weights (nano is the smallest)")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8, help="Lower it if you run out of graphics memory")
    parser.add_argument("--workers", type=int, default=2, help="Use 0 if training hangs on Windows")
    parser.add_argument("--device", default="0", help="0 for the first graphics card, or cpu")
    parser.add_argument("--patience", type=int, default=10, help="Stop early after this many epochs without improvement")
    parser.add_argument("--fraction", type=float, default=1.0, help="Train on this share of the images (for quick checks)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cache", action="store_true", help="Keep the images in memory (faster, uses RAM)")
    parser.add_argument("--no-amp", action="store_true", help="Turn off mixed precision if the loss turns to NaN")
    parser.add_argument("--evaluate-test", action="store_true", help="Also score the held-out test split (do this once, at the end)")
    parser.add_argument("--project", type=Path, default=None, help="Where runs are saved (default: a 'runs' folder next to the dataset)")
    parser.add_argument("--name", default="damage_detector")
    args = parser.parse_args(argv)

    if not args.data.exists():
        print(f"{args.data} not found. Create it with python -m ml.images.prepare_rdd2022 first.")
        return 1
    if args.project is None:
        args.project = args.data.resolve().parent.parent / "runs"  # outside the Git repository

    yolo = yolo_class or _load_yolo()
    model = yolo(args.model)
    results = model.train(**build_train_arguments(args))
    save_dir = Path(getattr(results, "save_dir", None) or model.trainer.save_dir)
    best_weights = save_dir / "weights" / "best.pt"

    best = yolo(str(best_weights))
    shared = {"data": str(args.data.resolve()), "imgsz": args.imgsz, "batch": args.batch,
              "workers": args.workers, "device": parse_device(args.device)}
    summary: dict[str, Any] = {
        "starting_model": args.model,
        "epochs_requested": args.epochs,
        "classes": list(CLASS_NAMES),
        "validation": summarize(best.val(split="val", **shared)),
        "test": summarize(best.val(split="test", **shared)) if args.evaluate_test else None,
        "note": "Validation scores guide choices. The test split is for one final measurement.",
    }
    (save_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nBest weights: {best_weights}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
