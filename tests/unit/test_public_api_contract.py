from __future__ import annotations

from collections import OrderedDict

import pytest


pytestmark = pytest.mark.unit


def test_import_exposes_palimpsest_class():
    from palimpsest import Palimpsest, PalimpsestSession

    assert Palimpsest.__name__ == "Palimpsest"
    assert PalimpsestSession.__name__ == "PalimpsestSession"


def test_processor_methods_require_explicit_session(lightweight_palimpsest_factory):
    from palimpsest import Palimpsest, SessionRequiredError

    processor = Palimpsest()

    with pytest.raises(SessionRequiredError):
        processor.anonimize("secret")
    with pytest.raises(SessionRequiredError):
        processor.deanonimize("secret")


def test_session_misspelled_methods_remain_backward_compatible(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest()
    session = processor.create_session(session_id="legacy")

    anon = session.anonimize("secret")
    assert anon == "FAKE_VALUE_1"
    assert session.deanonimize(anon) == "secret"


def test_session_corrected_aliases_round_trip(lightweight_palimpsest_factory):
    from palimpsest import Palimpsest

    processor = Palimpsest()
    session = processor.create_session(session_id="corrected")

    anonymized = session.anonymize("secret")

    assert anonymized == "FAKE_VALUE_1"
    assert session.deanonymize(anonymized) == "secret"


def test_processor_delegators_require_matching_session(lightweight_palimpsest_factory):
    from palimpsest import Palimpsest, SessionStateError

    processor = Palimpsest()
    session = processor.create_session(session_id="delegator")

    anonymized = processor.anonymize("secret", session=session)

    assert anonymized == "FAKE_VALUE_1"
    assert processor.deanonymize(anonymized, session=session) == "secret"

    other_processor = Palimpsest()
    with pytest.raises(SessionStateError):
        other_processor.anonymize("secret", session=session)


def test_unsupported_input_raises_instead_of_returning_original(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest()
    session = processor.create_session(session_id="type-check")

    with pytest.raises(TypeError):
        session.anonimize(None)


def test_deanonimize_without_session_mapping_returns_input_unchanged(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest()
    session = processor.create_session(session_id="empty")

    assert session.deanonimize("FAKE_VALUE_1") == "FAKE_VALUE_1"


def test_session_reset_and_close_enforce_lifetime(lightweight_palimpsest_factory):
    from palimpsest import Palimpsest, SessionStateError

    processor = Palimpsest()
    session = processor.create_session(session_id="lifetime")
    anonymized = session.anonymize("secret")

    session.reset()
    assert session.deanonymize(anonymized) == anonymized

    session.close()
    with pytest.raises(SessionStateError):
        session.anonymize("new secret")


def test_session_typed_placeholders_use_exact_deanonymization(monkeypatch):
    import palimpsest.palimpsest as palimpsest_module
    from palimpsest import EntityReplacement, Palimpsest

    calls = {"deanon": 0}

    class PlaceholderRuntime:
        def __init__(self, run_entities=None):
            pass

        def anonymize(self, ctx, text, entity_replacements=None):
            assert entity_replacements == OrderedDict(
                [
                    ("PERSON", "typed_placeholder"),
                    ("PHONE_NUMBER", "typed_placeholder"),
                ]
            )
            anonymized = text.replace(
                "John Williams",
                ctx.typed_placeholder("PERSON", "John Williams", lambda value: value),
            )
            anonymized = anonymized.replace(
                "445856786",
                ctx.typed_placeholder(
                    "PHONE_NUMBER",
                    "445856786",
                    lambda value: value,
                ),
            )
            return anonymized, [], text, []

        def deanonymize(self, ctx, text, entries, entity_replacements=None, exact=False):
            calls["deanon"] += 1
            return "runtime fuzzy path", [], text, []

    monkeypatch.setattr(palimpsest_module, "_runtime_factory", PlaceholderRuntime)

    processor = Palimpsest()
    session = processor.create_session(
        session_id="typed-placeholders",
        entity_replacements=[
            EntityReplacement("PERSON", "typed_placeholder"),
            {"entity_type": "PHONE_NUMBER", "strategy": "placeholder"},
        ],
    )

    anonymized = session.anonymize("John Williams can be reached at 445856786")

    assert anonymized == "PERSON_001 can be reached at PHONE_001"
    assert session.entity_replacements == OrderedDict(
        [
            ("PERSON", "typed_placeholder"),
            ("PHONE_NUMBER", "typed_placeholder"),
        ]
    )
    assert session.deanonymize("Contact PERSON_001 via PHONE_001") == (
        "Contact John Williams via 445856786"
    )
    assert calls["deanon"] == 0


def test_session_entity_replacements_validate_strategy(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest()

    with pytest.raises(ValueError, match="Unsupported replacement strategy"):
        processor.create_session(entity_replacements={"PERSON": "redact"})


def test_session_entity_replacements_must_fit_processor_run_entities(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest(run_entities=["PERSON"])

    with pytest.raises(ValueError, match="subset of processor run_entities"):
        processor.create_session(
            entity_replacements={"PHONE_NUMBER": "typed_placeholder"},
        )
