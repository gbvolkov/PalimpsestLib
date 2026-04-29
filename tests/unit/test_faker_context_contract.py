from __future__ import annotations

import re
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


def test_fake_value_collision_regenerates_without_overwriting(monkeypatch):
    import palimpsest.fakers.faker_context as context_module
    from palimpsest.fakers.faker_context import FakerContext

    monkeypatch.setattr(context_module, "fake_factory", lambda locale=None: None)
    monkeypatch.setattr(context_module, "calc_hash", lambda value: value)

    class FakeModule:
        generated = iter(["same-fake", "same-fake", "unique-fake"])

        @staticmethod
        def fake_account(value):
            return next(FakeModule.generated)

    ctx = FakerContext(module=FakeModule)

    first = ctx.fake_account("true-one")
    second = ctx.fake_account("true-two")

    assert first == "same-fake"
    assert second == "unique-fake"
    assert ctx.defake("same-fake") == "true-one"
    assert ctx.defake("unique-fake") == "true-two"


def test_fake_value_collision_exhaustion_raises(monkeypatch):
    import palimpsest.fakers.faker_context as context_module
    from palimpsest.fakers.faker_context import FakerContext

    monkeypatch.setattr(context_module, "fake_factory", lambda locale=None: None)
    monkeypatch.setattr(context_module, "calc_hash", lambda value: value)

    class FakeModule:
        @staticmethod
        def fake_account(value):
            return "same-fake"

    ctx = FakerContext(module=FakeModule)

    assert ctx.fake_account("true-one") == "same-fake"
    with pytest.raises(ValueError, match="Could not generate unique fake value"):
        ctx.fake_account("true-two")


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


def test_phone_fake_collision_regenerates_without_overwriting(monkeypatch):
    import palimpsest.fakers.faker_context as context_module
    from palimpsest.fakers.faker_context import FakerContext

    monkeypatch.setattr(context_module, "fake_factory", lambda locale=None: None)
    monkeypatch.setattr(context_module, "normalize_phone", lambda value: value)

    class FakeModule:
        generated = iter(["same-phone", "same-phone", "unique-phone"])

        @staticmethod
        def fake_phone(value):
            return next(FakeModule.generated)

    ctx = FakerContext(module=FakeModule)

    first = ctx.fake_phone("true-phone-one")
    second = ctx.fake_phone("true-phone-two")

    assert first == "same-phone"
    assert second == "unique-phone"
    assert ctx.defake_phone("same-phone") == "true-phone-one"
    assert ctx.defake_phone("unique-phone") == "true-phone-two"


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


def test_address_fake_collision_regenerates_without_overwriting(
    deterministic_faker_context,
    monkeypatch,
):
    from palimpsest.fakers.faker_context import FakerContext

    def fake_unify_address(value):
        return FakeUnifiedAddress(
            fuzzy_hash=value,
            fuzzy_keys={f"{value}-key"},
        )

    monkeypatch.setattr(
        deterministic_faker_context.context_module,
        "unify_address",
        fake_unify_address,
    )

    class FakeModule:
        generated = iter(["same-address", "same-address", "unique-address"])

        @staticmethod
        def fake_house(value):
            return next(FakeModule.generated)

    ctx = FakerContext(module=FakeModule)

    first = ctx.fake_house("true-address-one")
    second = ctx.fake_house("true-address-two")

    assert first == "same-address"
    assert second == "unique-address"
    assert ctx.defake_address("same-address") == "true-address-one"
    assert ctx.defake_address("unique-address") == "true-address-two"


def test_ru_specific_fakers_use_ru_locale_with_en_default(monkeypatch):
    import palimpsest.fakers.faker_context as context_module
    from palimpsest.fakers.faker_context import FakerContext

    monkeypatch.setattr(context_module, "calc_hash", lambda value: value)
    monkeypatch.setattr(FakerContext, "address_hash", lambda self, value: value)
    monkeypatch.setattr(FakerContext, "address_fuzzy_key", lambda self, value: value)

    class DefaultFake:
        def first_name(self):
            return "John"

        def last_name(self):
            return "Doe"

    class RuFake:
        def numerify(self, pattern):
            return "1234 567890"

        def checking_account(self):
            return "40702810900000000001"

        def first_name(self):
            return "Иван"

        def last_name(self):
            return "Иванов"

        def street_address(self):
            return "ул. Ленина, д. 1"

    default_fake = DefaultFake()
    ru_fake = RuFake()

    def fake_factory(locale="ru_RU"):
        return ru_fake if locale.replace("-", "_") == "ru_RU" else default_fake

    monkeypatch.setattr(context_module, "fake_factory", fake_factory)

    def has_cyrillic(value: str) -> bool:
        return any("А" <= char <= "я" or char in "Ёё" for char in value)

    ctx = FakerContext(locale="en-US")

    passport = ctx.fake_ru_passport("passport")
    bank_account = ctx.fake_ru_bank_account("bank-account")
    name = ctx.fake_ru_name("person")
    address = ctx.fake_ru_address("address")

    assert re.fullmatch(r"(\d{4} \d{6})|(\d{2} \d{2} \d{6})", passport)
    assert re.fullmatch(r"\d{20}", bank_account)
    assert has_cyrillic(name)
    assert has_cyrillic(address)
    assert ctx.defake(passport) == "passport"
    assert ctx.defake(bank_account) == "bank-account"
    assert ctx.defake_address(address) == "address"


def test_ru_specific_fakers_do_not_break_default_card_faker():
    from palimpsest.fakers import fakers_funcs
    from palimpsest.fakers.faker_context import FakerContext

    fakers_funcs._fake_by_locale = {}

    ctx = FakerContext(locale="en-US")
    default_fake = fakers_funcs.fake_factory("en_US")
    ru_fake = fakers_funcs.fake_factory("ru_RU")

    assert ctx._faker_for_function("fake_name") is default_fake
    assert ctx._faker_for_function("fake_card") is default_fake
    assert ctx._faker_for_function("fake_ru_passport") is ru_fake

    passport = ctx.fake_ru_passport("passport")
    card = ctx.fake_card("card")

    assert re.fullmatch(r"(\d{4} \d{6})|(\d{2} \d{2} \d{6})", passport)
    assert re.fullmatch(r"\d{16}", card)

    with pytest.raises(RuntimeError, match="No Faker is bound"):
        fakers_funcs.fake_card("card")


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
