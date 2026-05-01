from __future__ import annotations

import pytest

from tests.conftest import SAMPLE_RU_TEXT, SAMPLE_TEXT, assert_note_contains


pytestmark = pytest.mark.integration


def test_real_palimpsest_constructs_with_configured_dependencies():
    from palimpsest import Palimpsest

    processor = Palimpsest(
        verbose=False,
        run_entities=[
            "PERSON",
            "RU_PERSON",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "RU_PASSPORT",
            "SNILS",
            "INN",
            "RU_BANK_ACC",
        ],
    )

    assert processor is not None


def test_real_pipeline_anonymizes_and_restores_email_address():
    from palimpsest import Palimpsest

    processor = Palimpsest(
        verbose=False,
        run_entities=["EMAIL_ADDRESS"],
        locale="en-US",
    )
    session = processor.create_session(session_id="integration-email")
    text = "Contact john.doe@example.com for details."

    anonymized = session.anonymize(text)
    restored = session.deanonymize(anonymized)

    assert "john.doe@example.com" not in anonymized
    assert "john.doe@example.com" in restored


def test_real_pipeline_anonymizes_and_restores_representative_english_text():
    from palimpsest import Palimpsest

    processor = Palimpsest(
        verbose=False,
        run_entities=["PERSON", "PHONE_NUMBER", "CREDIT_CARD"],
        locale="en-US",
    )
    session = processor.create_session(session_id="integration-english")

    anonymized = session.anonimize(SAMPLE_TEXT)
    restored = session.deanonimize(anonymized)

    assert "John Doe" not in anonymized
    assert "4111111111111111" not in anonymized
    assert "John Doe" in restored
    assert "4111111111111111" in restored


def test_real_pipeline_anonymizes_and_restores_representative_russian_text():
    from palimpsest import Palimpsest

    processor = Palimpsest(
        verbose=False,
        run_entities=["RU_PERSON", "PERSON", "PHONE_NUMBER"],
        locale="ru-RU",
    )
    session = processor.create_session(session_id="integration-russian")

    anonymized = session.anonimize(SAMPLE_RU_TEXT)
    restored = session.deanonimize(anonymized)

    assert "Иван Иванов" not in anonymized
    assert "Иван Иванов" in restored


def test_missing_gliner_model_rethrows_original_dependency_exception():
    import palimpsest.recognizers.gliner_recogniser as gliner_module

    with pytest.raises(Exception) as exc_info:
        gliner_module.GlinerRecognizer(model_path="__missing_gliner_model__")

    assert type(exc_info.value) is not RuntimeError
    assert_note_contains(
        exc_info.value,
        "__missing_gliner_model__",
        "gliner_model_load",
    )


def test_libpostal_address_unification_is_available_for_address_features():
    from palimpsest.utils.addr_unifier import unify_address

    address = unify_address("221B Baker Street, London NW1")

    assert address.raw
    assert address.fuzzy_hash
    assert address.fuzzy_keys
