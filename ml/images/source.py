"""Lets the same code read the dataset from a zip, a folder of zips or an extracted folder."""

import zipfile
from pathlib import Path
from typing import Protocol


class Source(Protocol):
    def names(self) -> list[str]: ...
    def read(self, name: str) -> bytes: ...


class ZipSource:
    def __init__(self, path: Path) -> None:
        self._zip = zipfile.ZipFile(path)

    def names(self) -> list[str]:
        return [name for name in self._zip.namelist() if not name.endswith("/")]

    def read(self, name: str) -> bytes:
        return self._zip.read(name)


class DirSource:
    def __init__(self, root: Path) -> None:
        self._root = root

    def names(self) -> list[str]:
        return [path.relative_to(self._root).as_posix() for path in self._root.rglob("*") if path.is_file()]

    def read(self, name: str) -> bytes:
        return (self._root / name).read_bytes()


class ZipFolderSource:
    """A folder holding one zip per country, as in the RDD2022 release (India.zip, Japan.zip, ...).

    Each name is prefixed with its zip's name, so the country is always known, even when the
    zip does not contain a country folder of its own.
    """

    def __init__(self, zip_paths: list[Path]) -> None:
        self._zips = {path.stem: ZipSource(path) for path in zip_paths}

    def names(self) -> list[str]:
        return [f"{stem}/{name}" for stem, source in self._zips.items() for name in source.names()]

    def read(self, name: str) -> bytes:
        stem, inner_name = name.split("/", 1)
        return self._zips[stem].read(inner_name)


def open_source(path: Path) -> Source:
    """A zip file, a folder of country zips, or an extracted folder."""
    if path.is_file():
        return ZipSource(path)
    country_zips = sorted(path.glob("*.zip"))
    return ZipFolderSource(country_zips) if country_zips else DirSource(path)
