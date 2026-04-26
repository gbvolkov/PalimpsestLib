from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests.conftest import assert_note_contains


pytestmark = [pytest.mark.unit, pytest.mark.state]


@dataclass
class FakeUnifiedAddress:
    fuzzy_hash: str
    fuzzy_keys: set[str]


def test_repeated_true_value_returns_same_fake(deterministic_faker_context):
    from palimpsest.fakers.faker_context import FakerContext

    ctx = FakerContext(module=deterministic_faker_context.module)

    first = ctx.fake_account("account-1")
    second = ctx.fake_account("account-1")

    assert first == second


def test_fake_value_restores_only_within_same_context(deterministic_faker_context):
    from palimpsest.fakers.faker_context import FakerContext

    ctx1 = FakerContext(module=deterministic_faker_context.module)
    ctx2 = FakerContext(module=deterministic_faker_context.module)

    fake = ctx1.fake_account("account-1")

    assert ctx1.defake(fake) == "account-1"
    assert ctx2.defake(fake) == fake


def test_ambiguous_fuzzy_restoration_raises_with_diagnostics(
    deterministic_faker_context,
):
    from palimpsest.fakers.faker_context import FakerContext

    ctx = FakerContext(module=deterministic_faker_context.module)
    ctx._faked = {
        "first": {"true": "original-one", "fake": "same fake"},
        "second": {"true": "original-two", "fake": "same fake"},
    }

    with pytest.raises(Exception) as exc_info:
        ctx.defake_fuzzy("same fake")

    assert "same fake" in str(exc_info.value)


def test_phone_normalization_makes_repeated_formats_deterministic(
    deterministic_faker_context,
):
    from palimpsest.fakers.faker_context import FakerContext

    ctx = FakerContext(module=deterministic_faker_context.module)

    first = ctx.fake_phone("+7 (495) 123-45-67")
    second = ctx.fake_phone("7 (495) 123-45-67")

    assert first == second


def test_address_mapping_uses_unified_hash_and_restores(
    deterministic_faker_context,
    monkeypatch,
):
    from palimpsest.fakers.faker_context import FakerContext

    monkeypatch.setattr(
        deterministic_faker_context.context_module,
        "unify_address",
        lambda value: FakeUnifiedAddress(
            fuzzy_hash="same-address",
            fuzzy_keys={"same-address-key"},
        ),
    )
    ctx = FakerContext(module=deterministic_faker_context.module)

    fake = ctx.fake_house("Original Street 1")

    assert ctx.fake_house("Original Street 1") == fake
    assert ctx.defake_address(fake) == "Original Street 1"


def test_address_dependency_failure_rethrows_original_with_context_note(
    deterministic_faker_context,
    monkeypatch,
):
    from palimpsest.fakers.faker_context import FakerContext

    class LibpostalFailure(RuntimeError):
        pass

    def fail_unify_address(value):
        raise LibpostalFailure("libpostal parser payload")

    monkeypatch.setattr(
        deterministic_faker_context.context_module,
        "unify_address",
        fail_unify_address,
    )
    ctx = FakerContext(module=deterministic_faker_context.module)

    with pytest.raises(LibpostalFailure) as exc_info:
        ctx.address_hash("Broken address")

    assert_note_contains(exc_info.value, "address", "libpostal")
