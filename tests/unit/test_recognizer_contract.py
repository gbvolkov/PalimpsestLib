from __future__ import annotations

from types import SimpleNamespace

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.recognizer]


class FakeFakerContext:
    def __getattr__(self, name):
        if name.startswith("fake_") or name.startswith("defake"):
            return lambda value: value
        raise AttributeError(name)


def test_natasha_org_maps_to_ru_organization(monkeypatch):
    import palimpsest.recognizers.natasha_recogniser as natasha_module

    class FakeDoc:
        def __init__(self, text):
            self.spans = [SimpleNamespace(type="ORG", start=0, stop=len(text))]

        def segment(self, segmenter):
            pass

        def tag_morph(self, morph_tagger):
            pass

        def parse_syntax(self, syntax_parser):
            pass

        def tag_ner(self, ner_tagger):
            pass

    recognizer = natasha_module.NatashaSlovnetRecognizer.__new__(
        natasha_module.NatashaSlovnetRecognizer
    )
    recognizer.segmenter = object()
    recognizer.morph_tagger = object()
    recognizer.syntax_parser = object()
    recognizer.ner_tagger = object()
    monkeypatch.setattr(natasha_module, "Doc", FakeDoc)

    results = recognizer.analyze("Acme", entities=["RU_ORGANIZATION"])

    assert len(results) == 1
    assert results[0].entity_type == "RU_ORGANIZATION"
    assert results[0].start == 0
    assert results[0].end == 4


@pytest.mark.parametrize(
    ("recognizer_cls", "entity", "text"),
    [
        ("SNILSRecognizer", "SNILS", "112-233-445 96"),
        ("INNRecognizer", "INN", "7707083895"),
        ("RUCreditCardRecognizer", "CREDIT_CARD", "4000000000000003"),
    ],
)
def test_invalid_structured_identifiers_are_not_returned(
    recognizer_cls,
    entity,
    text,
):
    import palimpsest.recognizers.regex_recognisers as regex_module

    recognizer = getattr(regex_module, recognizer_cls)()

    assert recognizer.analyze(text, entities=[entity]) == []


@pytest.mark.parametrize(
    ("recognizer_cls", "entity", "text", "expected"),
    [
        (
            "SNILSRecognizer",
            "SNILS",
            "Передайте номер 112-233-445 95 бухгалтеру.",
            "112-233-445 95",
        ),
        (
            "INNRecognizer",
            "INN",
            "Реквизиты организации 7707083893 подтверждены.",
            "7707083893",
        ),
        (
            "RUCreditCardRecognizer",
            "CREDIT_CARD",
            "Оплата пройдет по номеру 4000000000000002 завтра.",
            "4000000000000002",
        ),
    ],
)
def test_valid_structured_identifiers_return_type_score_and_span(
    recognizer_cls,
    entity,
    text,
    expected,
):
    import palimpsest.recognizers.regex_recognisers as regex_module

    recognizer = getattr(regex_module, recognizer_cls)()
    results = recognizer.analyze(text, entities=[entity])

    assert len(results) == 1
    result = results[0]
    assert result.entity_type == entity
    assert result.score >= 0.99
    assert text[result.start : result.end] == expected


def test_recognizer_entity_allow_list_excludes_unrequested_entities():
    from palimpsest.recognizers.regex_recognisers import SNILSRecognizer

    recognizer = SNILSRecognizer()

    assert recognizer.analyze("Номер 112-233-445 95 указан в тексте", entities=["INN"]) == []


def test_analyzer_allow_list_is_passed_to_analysis(monkeypatch):
    import palimpsest.analyzer_engine_provider as provider_module
    import palimpsest.palimpsest as palimpsest_module
    import palimpsest.utils.sentence_splitter as splitter_module

    seen_entities = []

    class FakeAnalyzer:
        def get_supported_entities(self):
            return ["PERSON", "EMAIL_ADDRESS"]

        def analyze(self, text, entities, language, return_decision_process):
            seen_entities.append(list(entities))
            return []

    class FakeTokenizer:
        def encode(self, text):
            return list(text)

    monkeypatch.setattr(
        provider_module,
        "analyzer_engine",
        lambda *args, **kwargs: FakeAnalyzer(),
    )
    monkeypatch.setattr(
        palimpsest_module.AutoTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: FakeTokenizer(),
    )
    monkeypatch.setattr(splitter_module, "split_text", lambda text, **kwargs: [text])

    _, _, analyze = palimpsest_module._anonimizer_factory(
        FakeFakerContext(),
        run_entities=["PERSON"],
    )
    analyze("John john@example.com")

    assert seen_entities == [["PERSON"]]


def test_chunk_offset_correction_preserves_original_spans(monkeypatch):
    from presidio_analyzer import RecognizerResult

    import palimpsest.analyzer_engine_provider as provider_module
    import palimpsest.palimpsest as palimpsest_module
    import palimpsest.utils.sentence_splitter as splitter_module

    class FakeAnalyzer:
        def get_supported_entities(self):
            return ["PERSON"]

        def analyze(self, text, entities, language, return_decision_process):
            if text == "Alice":
                return [RecognizerResult("PERSON", 0, 5, 0.99)]
            if text == "Bob":
                return [RecognizerResult("PERSON", 0, 3, 0.99)]
            return []

    class FakeTokenizer:
        def encode(self, text):
            return list(text)

    monkeypatch.setattr(
        provider_module,
        "analyzer_engine",
        lambda *args, **kwargs: FakeAnalyzer(),
    )
    monkeypatch.setattr(
        palimpsest_module.AutoTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: FakeTokenizer(),
    )
    monkeypatch.setattr(
        splitter_module,
        "split_text",
        lambda text, **kwargs: ["Alice", "Bob"],
    )

    _, _, analyze = palimpsest_module._anonimizer_factory(
        FakeFakerContext(),
        run_entities=["PERSON"],
    )

    final_text, results = analyze("ignored")

    assert final_text == "Alice\nBob\n"
    assert [final_text[result.start : result.end] for result in results] == [
        "Alice",
        "Bob",
    ]
