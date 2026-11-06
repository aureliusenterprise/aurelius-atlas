"""Import an Apache Atlas export ZIP into the standalone server: the stack's ``sample-import`` service.

``SAMPLE_ZIP`` names the ZIP in the folder ``SAMPLE_DIR``; without it, or without that file, the script does
nothing. Otherwise it waits for the
server's readiness, signs in as a dev user by the password grant of the webapp's client, and posts the ZIP to
``admin/import`` as Atlas's ``importData`` takes it. Only the standard library: it runs in the server image.
"""

# ruff: noqa: INP001, T201 - a script mounted into a container; its output is its log

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

READY_TIMEOUT_SECONDS = 300
IMPORT_TIMEOUT_SECONDS = 3600


def _context() -> ssl.SSLContext:
    """TLS verified against the dev CA."""
    return ssl.create_default_context(cafile=os.environ["CA_FILE"])


def _wait_ready(url: str, context: ssl.SSLContext) -> None:
    """Return once the server answers its readiness probe; exit when it does not in time."""
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/atlas/admin/readiness", context=context, timeout=5):  # noqa: S310 - https
                return
        except OSError:  # URLError is one
            time.sleep(2)
    sys.exit(f"the server at {url} was not ready within {READY_TIMEOUT_SECONDS} s")


def _token(context: ssl.SSLContext) -> str:
    """A dev user's access token, by the password grant of the webapp's public client ``aurelius``."""
    form = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "aurelius",
            "username": os.environ["ATLAS_USERNAME"],
            "password": os.environ["ATLAS_PASSWORD"],
        }
    ).encode()
    request = urllib.request.Request(os.environ["TOKEN_URL"], data=form, method="POST")  # noqa: S310 - https
    with urllib.request.urlopen(request, context=context, timeout=30) as response:  # noqa: S310 - https
        return json.load(response)["access_token"]


def _multipart(fields: dict[str, tuple[str | None, bytes, str]]) -> tuple[bytes, str]:
    """A ``multipart/form-data`` body of the fields (name to file name, content, type) and its content type."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, (filename, content, content_type) in fields.items():
        disposition = f'form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "")
        head = f"--{boundary}\r\nContent-Disposition: {disposition}\r\nContent-Type: {content_type}\r\n\r\n"
        parts.append(head.encode() + content + b"\r\n")
    return b"".join(parts) + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def main() -> None:
    """Import the ZIP and print Atlas's import result; no ZIP is ignored, a failed import exits non-zero."""
    name = os.environ.get("SAMPLE_ZIP", "").strip()
    if not name:
        print("SAMPLE_ZIP is empty: nothing to import")
        return
    folder = Path(os.environ["SAMPLE_DIR"])
    archive = folder / name
    if Path(name).name != name or not archive.is_file():
        found = ", ".join(sorted(path.name for path in folder.glob("*.zip"))) or "none"
        print(f"no export ZIP {name!r} in the sample folder, which holds: {found}; nothing to import")
        return
    url = os.environ["ATLAS_URL"]
    context = _context()
    _wait_ready(url, context)
    body, content_type = _multipart(
        {
            "request": (None, os.environ.get("IMPORT_REQUEST", "{}").encode(), "application/json"),
            "data": (archive.name, archive.read_bytes(), "application/zip"),
        }
    )
    request = urllib.request.Request(  # noqa: S310 - https
        f"{url}/api/atlas/admin/import",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {_token(context)}", "Content-Type": content_type},
    )
    print(f"importing {archive.name} ({archive.stat().st_size} bytes)", flush=True)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, context=context, timeout=IMPORT_TIMEOUT_SECONDS) as response:  # noqa: S310 - https
            result = json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"the import failed: {error.code} {error.read().decode(errors='replace')}")
    print(f"{result.get('operationStatus')} in {time.monotonic() - started:.1f} s", flush=True)
    print(json.dumps(result.get("metrics", {}), indent=2, sort_keys=True))
    if result.get("operationStatus") not in {"SUCCESS", "PARTIAL_SUCCESS"}:
        sys.exit(1)


if __name__ == "__main__":
    main()
