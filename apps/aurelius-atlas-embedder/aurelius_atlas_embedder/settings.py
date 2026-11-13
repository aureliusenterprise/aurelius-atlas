"""The app's settings, read once at start-up from the environment (EMB-09)."""

from pathlib import Path
from typing import Literal, Self

from pydantic import DirectoryPath, Field, FilePath, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_EMBEDDER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21004
"""The app's port: above the auxiliary APIs' 21001 to 21003."""

MODEL_ID = "intfloat/multilingual-e5-small"
"""The model the image ships (DD-429)."""

MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
"""The model's pinned revision on Hugging Face, as the image fetches it (EMB-10, DD-431)."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels uvicorn accepts."""

TLS_PAIR_ERROR = (
    f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE must both be set, or both be unset, to configure TLS"
)


class EmbedderSettings(BaseSettings):
    """How the app runs and which model it serves from where."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore", protected_namespaces=())

    host: str = "localhost"
    """The interface to listen on; the container image sets ``0.0.0.0``."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    """The port to listen on."""

    log_level: LogLevel = "info"
    """The lowest level of log record the app and uvicorn emit."""

    environment: Literal["production", "development"] = "production"
    """What the app runs in: the image ships production; ``serve`` sets development,
    which turns on the dev-only OpenAPI surface (AUX-07, DD-557)."""

    tls_cert_file: FilePath | None = None
    """PEM certificate to serve HTTPS with; requires ``tls_key_file``."""

    tls_key_file: FilePath | None = None
    """PEM private key of ``tls_cert_file``."""

    model_dir: DirectoryPath
    """The directory holding ``model.onnx`` and ``tokenizer.json``; the app never fetches them (EMB-08)."""

    model_id: str = MODEL_ID
    """The served model's id, as ``/v1/models`` names it and a request's ``model`` must match (EMB-05, EMB-06)."""

    model_revision: str = MODEL_REVISION
    """The served model's revision, as ``/v1/models`` reports it (EMB-06)."""

    max_tokens: int = Field(default=512, ge=1)
    """Tokens a text is cut at, the model's window (EMB-03)."""

    threads: int = Field(default=0, ge=0)
    """ONNX Runtime's threads per inference; 0 lets it choose."""

    @model_validator(mode="after")
    def _tls_pair(self) -> Self:
        """TLS is configured by a pair, never by one half of it."""
        if (self.tls_cert_file is None) != (self.tls_key_file is None):
            raise ValueError(TLS_PAIR_ERROR)
        return self

    @property
    def tls(self) -> tuple[Path, Path] | None:
        """The certificate and key to serve HTTPS with, or None for plain HTTP."""
        if self.tls_cert_file is None or self.tls_key_file is None:
            return None
        return Path(self.tls_cert_file), Path(self.tls_key_file)

    @property
    def is_development(self) -> bool:
        """Whether ``environment`` is set to development: the dev OpenAPI surface answers, production's does not."""
        return self.environment == "development"
