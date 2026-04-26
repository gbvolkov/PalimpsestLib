from __future__ import annotations

import inspect
import logging

import pytest

from tests.conftest import SAMPLE_CARD, SAMPLE_PERSON, SAMPLE_PHONE, StubEngineItem


pytestmark = [pytest.mark.unit, pytest.mark.privacy]


def test_verbose_logging_does_not_emit_raw_pii_or_mapping_values(caplog):
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
    assert SAMPLE_PERSON not in log_text
    assert SAMPLE_PHONE not in log_text
    assert SAMPLE_CARD not in log_text
    assert "Fake Person" not in log_text


def test_raw_value_debug_mode_is_explicit_and_disabled_by_default():
    from palimpsest import Palimpsest

    signature = inspect.signature(Palimpsest)

    assert "unsafe_debug_raw_values" in signature.parameters
    assert signature.parameters["unsafe_debug_raw_values"].default is False
