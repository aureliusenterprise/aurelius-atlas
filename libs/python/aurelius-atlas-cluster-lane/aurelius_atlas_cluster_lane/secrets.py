"""Secret keys read at run time from the release namespace (CHT-103)."""

import base64
import subprocess


class SecretReader:
    """Read Secret keys from a namespace through ``kubectl``.

    The lane reads credentials (the writer password, the store password) from
    the release's own Secrets instead of mirroring them into the environment:
    one source per credential, and the cluster lane proves the shipped Secret
    wiring as a side effect. Values are returned decoded and never logged.
    """

    def __init__(self, namespace: str) -> None:
        self._namespace = namespace

    def read(self, name: str, key: str) -> str:
        """The decoded string value of one Secret key; AssertionError when unreadable."""
        return self.read_bytes(name, key).decode()

    def read_bytes(self, name: str, key: str) -> bytes:
        """The decoded bytes of one Secret key (a CA certificate, a raw secret)."""
        escaped = key.replace(".", "\\.")
        result = subprocess.run(
            [
                "kubectl",
                "-n",
                self._namespace,
                "get",
                "secret",
                name,
                "-o",
                f"jsonpath={{.data.{escaped}}}",
            ],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"the Secret {name!r} in {self._namespace!r} is unreadable: {result.stderr.decode()}"
        )
        return base64.b64decode(result.stdout)
