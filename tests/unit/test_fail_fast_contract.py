from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.conftest import assert_note_contains


pytestmark = [pytest.mark.unit, pytest.mark.fail_fast]


class TokenizerLoadError(RuntimeError):
    pass


class DeviceMoveError(RuntimeError):
    pass


class GlinerModelLoadError(RuntimeError):
    pass


def test_tokenizer_load_failure_rethrows_original_with_context_note(monkeypatch):
    import palimpsest.analyzer_engine_provider as provider_module
    import palimpsest.palimpsest as palimpsest_module

    class FakeAnalyzer:
        def get_supported_entities(self):
            return []

    def fake_analyzer_engine(*args, **kwargs):
        return FakeAnalyzer()

    def fail_from_pretrained(*args, **kwargs):
        raise TokenizerLoadError("transformers tokenizer payload")

    monkeypatch.setattr(provider_module, "analyzer_engine", fake_analyzer_engine)
    monkeypatch.setattr(
        palimpsest_module.AutoTokenizer,
        "from_pretrained",
        fail_from_pretrained,
    )

    with pytest.raises(TokenizerLoadError) as exc_info:
        palimpsest_module._anonimizer_factory(SimpleNamespace())

    assert_note_contains(
        exc_info.value,
        "operation",
        "tokenizer",
        "gliner-community/gliner_large-v2.5",
    )


def test_gliner_model_load_failure_rethrows_original_with_context_note(monkeypatch):
    import palimpsest.recognizers.gliner_recogniser as gliner_module

    def fail_from_pretrained(*args, **kwargs):
        raise GlinerModelLoadError("gliner model payload")

    monkeypatch.setattr(gliner_module.GLiNER, "from_pretrained", fail_from_pretrained)

    with pytest.raises(GlinerModelLoadError) as exc_info:
        gliner_module.GlinerRecognizer(model_path="missing-gliner-model")

    assert_note_contains(
        exc_info.value,
        "operation",
        "gliner_model_load",
        "missing-gliner-model",
    )


def test_gliner_device_move_failure_is_not_logged_and_swallowed(monkeypatch):
    import palimpsest.recognizers.gliner_recogniser as gliner_module

    class FakeModel:
        def to(self, device):
            raise DeviceMoveError(f"device unavailable: {device}")

    class FakeGLiNER:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            return FakeModel()

    monkeypatch.setattr(gliner_module, "GLiNER", FakeGLiNER)

    with pytest.raises(DeviceMoveError) as exc_info:
        gliner_module.GlinerRecognizer()

    assert_note_contains(exc_info.value, "operation", "recognizer_init")


def test_spacy_runtime_download_is_forbidden(monkeypatch):
    import palimpsest.analyzer_engine_provider as provider_module
    import palimpsest.recognizers.gliner_recogniser as gliner_module

    download_calls = []

    class StubGlinerRecognizer:
        def __init__(self, *args, **kwargs):
            pass

    def forbidden_download(model_name):
        download_calls.append(model_name)
        raise AssertionError(f"runtime download attempted: {model_name}")

    monkeypatch.setattr(gliner_module, "GlinerRecognizer", StubGlinerRecognizer)
    monkeypatch.setattr(provider_module.spacy.util, "is_package", lambda name: False)
    monkeypatch.setattr(provider_module.spacy.cli, "download", forbidden_download)

    with pytest.raises(Exception):
        provider_module.create_nlp_engine_with_gliner("model-path")

    assert download_calls == []
