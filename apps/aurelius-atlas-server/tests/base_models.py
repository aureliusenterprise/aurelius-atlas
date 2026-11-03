"""Atlas's base model and its replication patch alone, for the modules that export or import (MDL-16)."""

# ruff: noqa: INP001

import shutil
from pathlib import Path

from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR

MODELS = (
    Path("0000-Area0/0010-base_model.json"),
    Path("0000-Area0/patches/001-base_model_replication_attributes.json"),
)
"""The files that hold the ``AtlasServer`` and ``__ExportImportAuditEntry`` types and ``replicatedTo``."""


def base_models(tmp_path: Path) -> Path:
    """A models directory of :data:`MODELS` under ``tmp_path``."""
    directory = tmp_path / "base-models"
    for model in MODELS:
        (directory / model.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(BUILTIN_MODELS_DIR / model, directory / model)
    return directory
