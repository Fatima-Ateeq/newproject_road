"""Converts boxes from pixel corners (VOC) to the normalized centre format YOLO trains on."""

from collections import Counter

from ml.images.classes import CLASS_NAMES
from ml.images.voc import VocAnnotation

INVALID_BOX = "<invalid box>"


def to_yolo_lines(annotation: VocAnnotation) -> tuple[list[str], Counter[str]]:
    """Return one 'class cx cy w h' line per usable box, plus a count of boxes left out.

    Boxes of classes we do not train on, and boxes with no area after clipping to the image,
    are left out and counted so the caller can report them.
    """
    width, height = annotation.width, annotation.height
    lines: list[str] = []
    ignored: Counter[str] = Counter()

    for box in annotation.boxes:
        if box.name not in CLASS_NAMES:
            ignored[box.name or "<no name>"] += 1
            continue
        xmin, xmax = (min(max(value, 0), width) for value in (box.xmin, box.xmax))
        ymin, ymax = (min(max(value, 0), height) for value in (box.ymin, box.ymax))
        if xmax <= xmin or ymax <= ymin:
            ignored[INVALID_BOX] += 1
            continue
        center_x = (xmin + xmax) / 2 / width
        center_y = (ymin + ymax) / 2 / height
        box_width = (xmax - xmin) / width
        box_height = (ymax - ymin) / height
        class_id = CLASS_NAMES.index(box.name)
        lines.append(f"{class_id} {center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}")
    return lines, ignored
