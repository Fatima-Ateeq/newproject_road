"""Checks that an upload really is a JPEG or PNG and saves it to the upload folder."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.exceptions import InvalidPhotoError

# (file signature, content type, extension). The signature is checked, not the filename.
_IMAGE_TYPES = (
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
)


@dataclass(frozen=True)
class StoredPhoto:
    file_name: str
    content_type: str


class PhotoStorage:
    def __init__(self, upload_dir: Path) -> None:
        self._upload_dir = upload_dir

    def save(self, data: bytes) -> StoredPhoto:
        content_type, extension = self._detect_type(data)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid4().hex}{extension}"
        (self._upload_dir / file_name).write_bytes(data)
        return StoredPhoto(file_name, content_type)

    def delete(self, file_name: str) -> None:
        self.path_of(file_name).unlink(missing_ok=True)

    def path_of(self, file_name: str) -> Path:
        return self._upload_dir / file_name

    @staticmethod
    def _detect_type(data: bytes) -> tuple[str, str]:
        for signature, content_type, extension in _IMAGE_TYPES:
            if data.startswith(signature):
                return content_type, extension
        raise InvalidPhotoError("Photo must be a JPEG or PNG image.")
