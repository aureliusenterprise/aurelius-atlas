"""The upload of a form, read within the server's size limit (SRV-12, DD-708).

Atlas's Java answers an oversized body in its servlet container, before any Atlas code runs; nothing here
mirrors that layer. Ours refuses the upload itself, so the answer is Atlas's error body rather than the edge's
or the server framework's.
"""

from fastapi import Request
from starlette.datastructures import UploadFile

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode

CHUNK_SIZE = 64 * 1024
"""Bytes of an upload read at a time."""


async def read_upload(request: Request, field: str, what: str) -> bytes:
    """The form's file of ``field``, read to the end; no file or a non-file part is empty (DV-119, DV-104).

    The file is read in chunks and refused once it passes ``upload_max_bytes``, so the server never holds more
    than the limit plus one chunk of an upload (SRV-12).

    Args:
        request: The request whose form holds the file.
        field: The form field that names the file.
        what: What the file is, for the refusal's message: ``"data"``, ``"file"`.

    Raises:
        AtlasError: ``PAYLOAD_TOO_LARGE`` when the file passes the limit.
    """
    upload = (await request.form()).get(field)
    if not isinstance(upload, UploadFile):
        return b""
    limit = request.app.state.settings.upload_max_bytes
    chunks: list[bytes] = []
    size = 0
    while chunk := await upload.read(CHUNK_SIZE):
        size += len(chunk)
        if size > limit:
            raise AtlasError(AtlasErrorCode.PAYLOAD_TOO_LARGE, what, limit)
        chunks.append(chunk)
    return b"".join(chunks)
