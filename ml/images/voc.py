"""Reads the Pascal VOC XML annotation files that RDD2022 ships with (one XML per image).

The files come from the official dataset release, which we trust. The standard library XML
parser is not designed for untrusted input, so do not point this at files from elsewhere.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    name: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float


@dataclass(frozen=True)
class VocAnnotation:
    width: int
    height: int
    boxes: list[Box]


def _number(parent: ET.Element | None, tag: str) -> float:
    text = parent.findtext(tag) if parent is not None else None
    if text is None:
        raise ValueError(f"missing <{tag}>")
    return float(text)


def parse_voc(xml_bytes: bytes) -> VocAnnotation:
    """Parse one annotation. Raises ValueError if the XML is malformed or incomplete."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise ValueError(f"invalid XML: {error}") from error

    size = root.find("size")
    boxes = []
    for obj in root.findall("object"):
        bndbox = obj.find("bndbox")
        boxes.append(
            Box(
                name=(obj.findtext("name") or "").strip(),
                xmin=_number(bndbox, "xmin"),
                ymin=_number(bndbox, "ymin"),
                xmax=_number(bndbox, "xmax"),
                ymax=_number(bndbox, "ymax"),
            )
        )
    return VocAnnotation(int(_number(size, "width")), int(_number(size, "height")), boxes)
