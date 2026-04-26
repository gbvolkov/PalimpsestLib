from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_PERSON = "John Doe"
SAMPLE_PHONE = "+1 (202) 555-0182"
SAMPLE_CARD = "4111111111111111"
SAMPLE_TEXT = (
    f"Client {SAMPLE_PERSON} will use {SAMPLE_CARD}. "
    f"Call {SAMPLE_PHONE}."
)
SAMPLE_RU_TEXT = (
    "Клиент Иван "
    "Иванов, телефон "
    "+7 (495) 123-45-67."
)


@dataclass
class StubEngineItem:
    entity_type: str
    text: str
    operator: str
    restored: str
    start: int = 0
    end: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "text": self.text,
            "operator": self.operator,
            "start": self.start,
            "end": self.end,
        }


def exception_notes(exc: BaseException) -> str:
    return "\n".join(getattr(exc, "__notes__", ()))


def assert_note_contains(exc: BaseException, *parts: str) -> None:
    notes = exception_notes(exc)
    for part in parts:
        assert part in notes


@pytest.fixture
def lightweight_palimpsest_factory(monkeypatch):
    """Replace heavyweight model setup with a deterministic runtime."""
    import palimpsest.palimpsest as palimpsest_module

    calls: dict[str, object] = {
        "anon": [],
        "deanon": [],
        "run_entities": None,
    }

    class FakeRuntime:
        def __init__(self, run_entities=None):
            calls["run_entities"] = run_entities

        def anonymize(self, ctx, text):
            if not isinstance(text, str):
                raise TypeError("text must be str")
            anon_calls = calls["anon"]
            assert isinstance(anon_calls, list)
            anon_calls.append(text)
            fake = f"FAKE_VALUE_{len(anon_calls)}"
            item = StubEngineItem(
                entity_type="PERSON",
                text=fake,
                operator="custom",
                restored=text,
                start=0,
                end=len(fake),
            )
            return fake, [item], text, []

        def deanonymize(self, ctx, text, entries):
            if not isinstance(text, str):
                raise TypeError("text must be str")
            deanon_calls = calls["deanon"]
            assert isinstance(deanon_calls, list)
            deanon_calls.append((text, tuple(entries)))
            matches = [entry for entry in entries if entry.text in text]
            if not matches:
                return text, [], text, []
            if len(matches) != 1:
                raise LookupError("mapping/session mismatch")
            return text.replace(matches[0].text, matches[0].restored), [], text, []

        def analyze(self, text):
            return text, []

    monkeypatch.setattr(palimpsest_module, "_runtime_factory", FakeRuntime)
    return calls


@pytest.fixture
def deterministic_faker_context(monkeypatch):
    import palimpsest.fakers.faker_context as context_module

    monkeypatch.setattr(context_module, "fake_factory", lambda locale=None: None)
    monkeypatch.setattr(context_module, "calc_hash", lambda value: f"h:{value}".lower())

    class FakeModule:
        counter = 0

        @staticmethod
        def fake_account(value):
            FakeModule.counter += 1
            return f"fake-account-{FakeModule.counter}"

        @staticmethod
        def fake_phone(value):
            FakeModule.counter += 1
            return "+7 (495) 123-45-67"

        @staticmethod
        def fake_house(value):
            FakeModule.counter += 1
            return "Fake Street 10"

    return SimpleNamespace(context_module=context_module, module=FakeModule)
