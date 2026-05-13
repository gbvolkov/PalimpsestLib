import logging
logger = logging.getLogger(__name__)

import inspect
import functools
from typing import Callable

from rapidfuzz import fuzz, process

from .faker_utils import calc_hash, normalize_phone
from .fakers_funcs import fake_factory

from ..utils.addr_unifier import unify_address

MAX_FAKE_GENERATION_ATTEMPTS = 10

_TYPED_PLACEHOLDER_PREFIXES = {
    "PERSON": "PERSON",
    "Person": "PERSON",
    "RU_PERSON": "PERSON",
    "PHONE_NUMBER": "PHONE",
    "EMAIL_ADDRESS": "EMAIL",
    "CREDIT_CARD": "CREDIT_CARD",
    "IP_ADDRESS": "IP",
    "URL": "URL",
    "RU_ADDRESS": "ADDRESS",
    "RU_ORGANIZATION": "ORGANIZATION",
    "RU_CITY": "CITY",
    "RU_PASSPORT": "PASSPORT",
    "SNILS": "SNILS",
    "INN": "INN",
    "RU_BANK_ACC": "BANK_ACC",
    "TICKET_NUMBER": "TICKET",
}

class FakerContext:
    """
    A context that finds every function named fake_* in the fakers module
    and turns it into a method which records into context-local maps.
    """
    def __init__(self, module=None, locale = "ru_RU"):
        # if you do not pass a module, we introspect the current one
        if module is None:
            from . import fakers_funcs as module
        self._module = module
        self._faker_by_locale = {
            "default": fake_factory(locale=locale),
            "ru": fake_factory(locale="ru_RU"),
            "en": fake_factory(locale="en_US"),
        }
        self._fake_func_locale = {
            "fake_ru_bank_account": "ru",
            "fake_ru_passport": "ru",
            "fake_ru_name": "ru",
            "fake_ru_address": "ru",
            "fake_card": "en",
        }

        # each context gets its own two maps
        self._true: dict[str, dict] = {}
        self._faked: dict[str, dict] = {}
        self._exact_faked: dict[str, dict] = {}
        self._placeholder_counters: dict[str, int] = {}

        # wrap & bind every fake_* as an instance method
        phone_func = None
        address_funcs = {}
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name == "fake_factory":
                continue
            if name == "fake_phone":
                phone_func = func
                continue
            if name in {"fake_house", "fake_ru_address"}:
                address_funcs[name] = func
                continue
            if name.startswith("fake_"):
                setattr(self, name, self._wrap(name, func))
        if phone_func:
            setattr(self, "fake_phone", self._wrap_phone("fake_phone", phone_func))
        for name, func in address_funcs.items():
            setattr(self, name, self._wrap_address(name, func))

        # bind defake
        setattr(self, "defake", self.defake)
        setattr(self, "defake_phone", self.defake_phone)
        setattr(self, "defake_address", self.defake_address)
    
    def reset(self):
        self._true: dict[str, dict] = {}
        self._faked: dict[str, dict] = {}
        self._exact_faked: dict[str, dict] = {}
        self._placeholder_counters: dict[str, int] = {}



    def _generate_unique_fake(
        self,
        value: str,
        func: Callable[[str], str],
        fake_hash_func: Callable[[str], str],
        build_entry: Callable[[str], dict],
    ) -> tuple[str, str, dict]:
        for _ in range(MAX_FAKE_GENERATION_ATTEMPTS):
            fake_val = func(value)
            fake_hash = fake_hash_func(fake_val)
            if fake_hash not in self._faked:
                return fake_val, fake_hash, build_entry(fake_val)

        raise ValueError(
            "Could not generate unique fake value: "
            f"func={func.__name__!r}, "
            f"true={value!r}, "
            f"attempts={MAX_FAKE_GENERATION_ATTEMPTS}"
        )

    def _store_mapping(self, true_hash: str, fake_hash: str, entry: dict) -> None:
        self._true[true_hash] = entry
        self._faked[fake_hash] = entry
        self._exact_faked[entry["fake"]] = entry

    def _faker_for_function(self, name: str):
        locale_key = self._fake_func_locale.get(name, "default")
        return self._faker_by_locale[locale_key]

    def _call_fake_func(self, name: str, func: Callable[[str], str], value: str) -> str:
        bind_faker = getattr(self._module, "bind_faker", None)
        reset_faker = getattr(self._module, "reset_faker", None)
        if bind_faker is None or reset_faker is None:
            return func(value)

        token = bind_faker(self._faker_for_function(name))
        try:
            return func(value)
        finally:
            reset_faker(token)

    def _wrap(self, name, func):
        """Return a wrapper around func(value: str)->str that records into our maps."""
        @functools.wraps(func)
        def wrapper(value: str) -> str:
            # bypass non-PII
            if value == "PII":
                return value

            h = calc_hash(value)
            if h in self._true:
                # already faked this exact true value
                return self._true[h]["fake"]

            fake_val, fake_hash, entry = self._generate_unique_fake(
                value,
                lambda source: self._call_fake_func(name, func, source),
                calc_hash,
                lambda fake: {"true": value, "fake": fake},
            )

            # record forward and backward
            self._store_mapping(h, fake_hash, entry)

            return fake_val
        return wrapper
    
    def _wrap_phone(self, name, func):
        """Phone-specific wrapper: direct hash by normalized phone, no fuzzy."""
        @functools.wraps(func)
        def wrapper(value: str) -> str:
            if value == "PII":
                return value

            h = self.phone_hash(value)
            if h in self._true:
                return self._true[h]["fake"]

            fake_val, fake_hash, entry = self._generate_unique_fake(
                value,
                lambda source: self._call_fake_func(name, func, source),
                self.phone_hash,
                lambda fake: {"true": value, "fake": fake},
            )

            self._store_mapping(h, fake_hash, entry)

            return fake_val
        return wrapper
    
    def phone_hash(self, value: str) -> str:
        return normalize_phone(value)

    def _wrap_address(self, name, func):
        """Address-specific wrapper: store hashes and fuzzy keys for reverse lookup."""
        @functools.wraps(func)
        def wrapper(value: str) -> str:
            if value == "PII":
                return value
            h = self.address_hash(value)
            if h in self._true:
                return self._true[h]["fake"]

            source_fuzzy_key = self.address_fuzzy_key(value)
            fake_val, fake_hash, entry = self._generate_unique_fake(
                value,
                lambda source: self._call_fake_func(name, func, source),
                self.address_hash,
                lambda fake: {
                    "true": value,
                    "fake": fake,
                    "fuzzy_key": self.address_fuzzy_key(fake),
                },
            )

            self._true[h] = {**entry, "fuzzy_key": source_fuzzy_key}
            self._faked[fake_hash] = entry
            self._exact_faked[entry["fake"]] = entry
            return fake_val
        return wrapper

    def address_hash(self, value: str) -> str:
        try:
            unified_addr = unify_address(value)
        except Exception as exc:
            exc.add_note(
                "Palimpsest "
                "operation=address_hash "
                "component=FakerContext "
                "dependency=libpostal "
                f"value={value!r}"
            )
            raise
        return unified_addr.fuzzy_hash

    def address_fuzzy_key(self, value: str) -> str:
        try:
            unified_addr = unify_address(value)
        except Exception as exc:
            exc.add_note(
                "Palimpsest "
                "operation=address_fuzzy_key "
                "component=FakerContext "
                "dependency=libpostal "
                f"value={value!r}"
            )
            raise
        return "\n".join(sorted(unified_addr.fuzzy_keys))

    def typed_placeholder_prefix(self, entity_type: str) -> str:
        prefix = _TYPED_PLACEHOLDER_PREFIXES.get(entity_type)
        if prefix:
            return prefix
        return "".join(
            char if char.isalnum() else "_"
            for char in entity_type.upper()
        ).strip("_") or "ENTITY"

    def _next_typed_placeholder(self, prefix: str) -> str:
        while True:
            next_index = self._placeholder_counters.get(prefix, 0) + 1
            self._placeholder_counters[prefix] = next_index
            placeholder = f"{prefix}_{next_index:03d}"
            if placeholder not in self._exact_faked:
                return placeholder

    def typed_placeholder(
        self,
        entity_type: str,
        value: str,
        true_hash_func: Callable[[str], str] | None = None,
    ) -> str:
        if value == "PII":
            return value

        hash_func = true_hash_func or calc_hash
        prefix = self.typed_placeholder_prefix(entity_type)
        true_hash = f"typed-placeholder:{prefix}:{hash_func(value)}"
        if true_hash in self._true:
            return self._true[true_hash]["fake"]

        placeholder = self._next_typed_placeholder(prefix)
        entry = {
            "true": value,
            "fake": placeholder,
            "entity_type": entity_type,
            "replacement_strategy": "typed_placeholder",
            "exact": True,
        }
        self._store_mapping(
            true_hash,
            f"typed-placeholder-fake:{placeholder}",
            entry,
        )
        return placeholder
    
    def defake_exact(self, fake):
        if fake == 'PII':
            return fake
        entry = self._exact_faked.get(fake)
        return entry.get("true") if entry else fake

    def deanonymize_exact_text(self, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be str")
        restored = text
        for fake in sorted(self._exact_faked, key=len, reverse=True):
            if fake != "PII":
                restored = restored.replace(fake, self._exact_faked[fake]["true"])
        return restored

    def defake(self, fake):
        if fake == 'PII':
            return fake
        fake_hash = calc_hash(fake)
        return self._faked[fake_hash].get('true') if fake_hash in self._faked else fake
    
    def defake_phone(self, fake):
        if fake == 'PII':
            return fake
        h = self.phone_hash(fake)
        return self._faked[h].get('true') if h in self._faked else fake

    def defake_address(self, fake):
        if fake == 'PII':
            return fake
        h = self.address_hash(fake)
        if h in self._faked:
            return self._faked[h].get('true')
        # fallback: fuzzy match on concatenated expanded variants
        items = list(self._faked.items())
        if not items:
            return fake
        fuzzy_key = self.address_fuzzy_key(fake)
        stored_keys = [entry.get("fuzzy_key", "") for _, entry in items]
        best = process.extractOne(fuzzy_key, stored_keys, scorer=fuzz.partial_ratio, score_cutoff=60)
        return items[best[2]][1].get("true", fake) if best else fake

    def defake_fuzzy(self, fake):
        if fake == 'PII':
            return fake
        items = list(self._faked.items())
        fakes = [entry["fake"] for _, entry in items]
        best_fake = process.extractOne(fake, fakes, scorer=fuzz.partial_token_sort_ratio, score_cutoff=60)
        if best_fake:
            return [entry["true"] for _, entry in items][best_fake[2]]
                #faked_entries = [v for v in faked_values.values() if v["fake"] == best_fake[0]]
        else:
            return self.defake(fake)

if __name__ == "__main__":
    ctx = FakerContext()
    name = ctx.fake_name()
