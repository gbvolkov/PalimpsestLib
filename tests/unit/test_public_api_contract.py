from __future__ import annotations

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
