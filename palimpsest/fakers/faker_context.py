import logging
logger = logging.getLogger(__name__)

import inspect
import functools

from rapidfuzz import fuzz, process

from .faker_utils import calc_hash, normalize_phone
from .fakers_funcs import fake_factory

from ..utils.addr_unifier import unify_address

class FakerContext:
    """
    A context that finds every function named fake_* in the fakers module
    and turns it into a method which records into context-local maps.
    """
    def __init__(self, module=None, locale = "ru_RU"):
        fake_factory(locale=locale)
        # if you don’t pass a module, we introspect the current one
        if module is None:
            from . import fakers_funcs as module
        self._module = module

        # each context gets its own two maps
        self._true: dict[str, dict] = {}
        self._faked: dict[str, dict] = {}

        # wrap & bind every fake_* as an instance method
        phone_func = None
        address_func = None
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name == "fake_phone":
                phone_func = func
                continue
            if name == "fake_house":
                address_func = func
                continue
            if name.startswith("fake_"):
                setattr(self, name, self._wrap(func))
        if phone_func:
            setattr(self, "fake_phone", self._wrap_phone(phone_func))
        if address_func:
            setattr(self, "fake_house", self._wrap_address(address_func))

        # bind defake
        setattr(self, "defake", self.defake)
        setattr(self, "defake_phone", self.defake_phone)
        setattr(self, "defake_address", self.defake_address)
    
    def reset(self):
        self._true: dict[str, dict] = {}
        self._faked: dict[str, dict] = {}



    def _wrap(self, func):
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

            fake_val = func(value)

            # record forward and backward
            self._true[h] = {"true": value, "fake": fake_val}
            self._faked[calc_hash(fake_val)] = {"true": value, "fake": fake_val}

            return fake_val
        return wrapper
    
    def _wrap_phone(self, func):
        """Phone-specific wrapper: direct hash by normalized phone, no fuzzy."""
        @functools.wraps(func)
        def wrapper(value: str) -> str:
            if value == "PII":
                return value

            h = self.phone_hash(value)
            if h in self._true:
                return self._true[h]["fake"]

            fake_val = func(value)

            self._true[h] = {"true": value, "fake": fake_val}
            self._faked[self.phone_hash(fake_val)] = {"true": value, "fake": fake_val}

            return fake_val
        return wrapper
    
    def phone_hash(self, value: str) -> str:
        return normalize_phone(value)

    def _wrap_address(self, func):
        """Address-specific wrapper: store hashes and fuzzy keys for reverse lookup."""
        @functools.wraps(func)
        def wrapper(value: str) -> str:
            if value == "PII":
                return value
            h = self.address_hash(value)
            if h in self._true:
                return self._true[h]["fake"]

            fake_val = func(value)

            self._true[h] = {
                "true": value,
                "fake": fake_val,
                "fuzzy_key": self.address_fuzzy_key(value),
            }
            self._faked[self.address_hash(fake_val)] = {
                "true": value,
                "fake": fake_val,
                "fuzzy_key": self.address_fuzzy_key(fake_val),
            }
            return fake_val
        return wrapper

    def address_hash(self, value: str) -> str:
        unified_addr = unify_address(value)
        return unified_addr.fuzzy_hash

    def address_fuzzy_key(self, value: str) -> str:
        unified_addr = unify_address(value)
        return "\n".join(sorted(unified_addr.fuzzy_keys))
    
    def defake(self, fake):
        if fake == 'PII':
            return fake
        hash = calc_hash(fake)
        if hash in self._faked:
            logger.debug(f"FAKE FOUND: request: {fake}; hash: {hash}; true: {self._faked[hash].get('true')}; fake: {self._faked[hash].get('fake')}")
            return self._faked[hash].get('true')
        else:
            logger.debug(f"FAKE NOT FOUND: request: {fake}; hash: {hash}")
            return fake
    
    def defake_phone(self, fake):
        if fake == 'PII':
            return fake
        h = self.phone_hash(fake)
        if h in self._faked:
            return self._faked[h].get('true')
        return fake

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
        if best:
            return items[best[2]][1].get("true", fake)
        return fake

    def defake_fuzzy(self, fake):
        if fake == 'PII':
            return fake
        items = list(self._faked.items())  
        fakes = [entry["fake"] for _, entry in items]
        best_fake = process.extractOne(fake, fakes, scorer=fuzz.partial_token_sort_ratio, score_cutoff=60)
        if best_fake:
            true_value = [entry["true"] for _, entry in items][best_fake[2]]
            logger.debug(f"Fuzzy search result: request: {fake}; found: {best_fake[0]}; score: {best_fake[1]}; true_value: {true_value}")
            return true_value
            #faked_entries = [v for v in faked_values.values() if v["fake"] == best_fake[0]]
        else:
            return self.defake(fake)

if __name__ == "__main__":
    ctx = FakerContext()
    name = ctx.fake_name()
