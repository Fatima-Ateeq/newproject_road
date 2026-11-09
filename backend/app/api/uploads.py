from fastapi import UploadFile

from app.core.exceptions import InvalidPhotoError


def read_photo(upload: UploadFile | None, max_bytes: int) -> bytes | None:
    """Read an optional upload without ever loading more than max_bytes + 1 bytes."""
    if upload is None or not upload.filename:
        return None
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise InvalidPhotoError(f"Photo is too large (maximum {max_bytes / 1_048_576:g} MB).")
    return data
