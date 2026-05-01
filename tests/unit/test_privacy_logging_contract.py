from __future__ import annotations

import logging

import pytest

from tests.conftest import SAMPLE_CARD, SAMPLE_PERSON, SAMPLE_PHONE, StubEngineItem


pytestmark = [pytest.mark.unit, pytest.mark.privacy]


def test_verbose_debug_log_emits_raw_values_by_design(caplog):
    from palimpsest.palimpsest import debug_log

    pii_text = f"{SAMPLE_PERSON} {SAMPLE_PHONE} {SAMPLE_CARD}"
    fake_text = "Fake Person +7 (999) 000-00-00 4000000000000002"
    fake_item = StubEngineItem(
        entity_type="PERSON",
        text="Fake Person",
        operator="custom",
        restored=SAMPLE_PERSON,
    )

    class FakeContext:
        _faked = {
            "fake-hash": {
                "true": SAMPLE_PERSON,
                "fake": "Fake Person",
            }
        }
        _true = {
            "true-hash": {
                "true": SAMPLE_PERSON,
                "fake": "Fake Person",
            }
        }

    caplog.set_level(logging.DEBUG, logger="palimpsest.palimpsest")

    debug_log(
        "ANONIMIZATION",
        input_text=pii_text,
        output_text=fake_text,
        action_entries=[fake_item],
        ctx=FakeContext(),
        analised_text=pii_text,
        action_analysis=[],
    )

    log_text = caplog.text
    assert SAMPLE_PERSON in log_text
    assert SAMPLE_PHONE in log_text
    assert SAMPLE_CARD in log_text
    assert "Fake Person" in log_text


def test_processor_default_verbose_false_does_not_call_debug_log(
    lightweight_palimpsest_factory,
    caplog,
):
    from palimpsest import Palimpsest

    caplog.set_level(logging.DEBUG, logger="palimpsest.palimpsest")

    processor = Palimpsest()
    session = processor.create_session(session_id="privacy-default")
    session.anonymize(f"{SAMPLE_PERSON} {SAMPLE_PHONE} {SAMPLE_CARD}")

    assert caplog.text == ""
