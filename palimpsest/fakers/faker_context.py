import logging
logger = logging.getLogger(__name__)

import inspect
import functools

from rapidfuzz import fuzz, process

from .faker_utils import calc_hash

class FakerContext:
    """
    A context that finds every function named fake_* in the fakers module
    and turns it into a method which records into context-local maps.
    """
    def __init__(self, module=None):
        # if you don’t pass a module, we introspect the current one
        if module is None:
            from . import fakers_funcs as module
        self._module = module

        # each context gets its own two maps
        self._true: dict[str, dict] = {}
        self._faked: dict[str, dict] = {}

        # wrap & bind every fake_* as an instance method
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("fake_"):
                setattr(self, name, self._wrap(func))

        # bind defake
        setattr(self, "defake", self.defake)


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