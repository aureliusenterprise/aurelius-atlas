"""Unit tests for the model: pooling, prefixes, batches and loading (EMB-03, EMB-04, EMB-08)."""

from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from aurelius_atlas_embedder import model as model_module
from aurelius_atlas_embedder.model import InputType, Model, ModelLoadError, check_model_dir, load_model
from aurelius_atlas_embedder.settings import EmbedderSettings
from fakes import FakeSession, FakeTokenizer, fake_model


@pytest.mark.covers("aurelius_atlas_embedder.model.Model.embed", rules=["EMB-03"])
def test__an_embedding_is_the_mean_over_the_text_s_tokens_scaled_to_length_1(model: Model) -> None:
    """The fake hidden state of ``passage: a`` averaged over its tokens, then scaled to length 1."""
    embeddings = model.embed(["a"])

    text = "passage: a"
    ids = [ord(character) % 50 + 1 for character in text]
    mean = np.mean([[float(i), float(i % 3), 1.0, 0.0] for i in ids], axis=0)
    assert embeddings.vectors[0] == pytest.approx((mean / np.linalg.norm(mean)).tolist(), abs=1e-6)
    assert np.linalg.norm(embeddings.vectors[0]) == pytest.approx(1.0, abs=1e-6)
    assert model.dimensions == 4


@pytest.mark.covers("aurelius_atlas_embedder.model.Model.embed", rules=["EMB-03"])
def test__each_text_carries_its_input_type_s_prefix(model: Model) -> None:
    """Passages and queries are prefixed as the model was trained."""
    tokenizer = model._tokenizer  # noqa: SLF001 - the fake records its input
    assert isinstance(tokenizer, FakeTokenizer)

    model.embed(["customer address"], InputType.QUERY)
    model.embed(["client location"])

    assert tokenizer.seen == [["query: customer address"], ["passage: client location"]]


@pytest.mark.covers("aurelius_atlas_embedder.model.Model.embed", rules=["EMB-04"])
def test__a_text_s_embedding_does_not_depend_on_the_other_texts_in_its_batch(model: Model) -> None:
    """The padding a longer neighbour forces is kept out of the mean."""
    alone = model.embed(["ab"]).vectors[0]
    beside_a_longer_text = model.embed(["ab", "a longer text"]).vectors[0]

    assert beside_a_longer_text == pytest.approx(alone, abs=1e-6)


@pytest.mark.covers("aurelius_atlas_embedder.model.Model.embed", rules=["EMB-02", "EMB-03"])
def test__the_token_count_is_what_the_model_read_after_truncation(model: Model) -> None:
    """Each text is cut at the tokenizer's window; the count adds up the tokens left."""
    embeddings = model.embed(["a", "a text much longer than the fake tokenizer's 32 tokens"])

    assert embeddings.tokens == len("passage: a") + 32


@pytest.mark.covers("aurelius_atlas_embedder.model.Model.__init__", rules=["EMB-03"])
@pytest.mark.parametrize("token_types", [True, False])
def test__token_type_ids_are_fed_only_to_a_model_that_takes_them(token_types: bool) -> None:  # noqa: FBT001
    """The e5 export takes ``token_type_ids`` (all zero); a model without that input gets none."""
    model = fake_model(token_types=token_types)

    model.embed(["a"])

    session = model._session  # noqa: SLF001 - the fake records its feeds
    assert isinstance(session, FakeSession)
    feed = session.feeds[0]
    assert ("token_type_ids" in feed) is token_types
    if token_types:
        assert not feed["token_type_ids"].any()


@pytest.mark.covers("aurelius_atlas_embedder.model.check_model_dir", rules=["EMB-08"])
@pytest.mark.parametrize("present", [[], ["model.onnx"], ["tokenizer.json"]])
def test__a_directory_without_the_model_or_the_tokenizer_is_refused(tmp_path: Path, present: list[str]) -> None:
    """Each missing file is named; the embedder never fetches its model."""
    for name in present:
        (tmp_path / name).write_text("x")

    with pytest.raises(ModelLoadError, match="never fetches") as refused:
        check_model_dir(tmp_path)

    for name in {"model.onnx", "tokenizer.json"} - set(present):
        assert name in str(refused.value)


@pytest.mark.covers("aurelius_atlas_embedder.model.check_model_dir", rules=["EMB-08"])
def test__a_directory_with_both_files_is_accepted(tmp_path: Path) -> None:
    """The check passes when both files are there."""
    (tmp_path / "model.onnx").write_text("x")
    (tmp_path / "tokenizer.json").write_text("x")

    check_model_dir(tmp_path)


@pytest.mark.covers("aurelius_atlas_embedder.model.load_model", rules=["EMB-08"])
def test__load_model_refuses_a_directory_without_the_model(tmp_path: Path) -> None:
    """Loading checks the directory before anything else."""
    with pytest.raises(ModelLoadError, match=r"model\.onnx"):
        load_model(EmbedderSettings(model_dir=tmp_path))


@pytest.mark.covers("aurelius_atlas_embedder.model.load_model", rules=["EMB-08"])
def test__load_model_names_a_missing_onnx_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On a Python without ONNX Runtime the load fails with the reason, not an import error (DD-433)."""
    (tmp_path / "model.onnx").write_text("x")
    (tmp_path / "tokenizer.json").write_text("x")
    real_import = model_module.importlib.import_module

    def without_onnxruntime(name: str, package: str | None = None) -> ModuleType:
        if name == "onnxruntime":
            raise ImportError(name)
        return real_import(name, package)

    monkeypatch.setattr(model_module.importlib, "import_module", without_onnxruntime)

    with pytest.raises(ModelLoadError, match="ONNX Runtime is not installed"):
        load_model(EmbedderSettings(model_dir=tmp_path))


def test__the_module_imports_without_onnx_runtime() -> None:
    """Importing the model module needs no ONNX Runtime: only ``load_model`` imports it (DD-433)."""
    assert "onnxruntime" not in vars(model_module)
