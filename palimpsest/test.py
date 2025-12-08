import logging
logger = logging.getLogger(__name__)

import pymorphy3
from fakers.names_morph import get_morphs
from fakers.fakers_funcs import fake_phone as _base_fake_phone, fake_factory as _fake_factory
from rapidfuzz import fuzz, process

_nlp = None  # spaCy model, loaded once
_morph = pymorphy3.MorphAnalyzer(lang='ru')
_true: dict[str, dict] = {}
_faked: dict[str, dict] = {}
_phone_cache: dict[str, str] = {}

def get_nlp():
    """Lazily load and return the shared spaCy Russian pipeline."""
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("ru_core_news_sm")
    return _nlp

def normalize_phone(raw: str, default_country: str = "99", default_city: str = "999") -> str:
    """
    Normalize phone to digits-only form.
    - Strip leading zeroes from every part (country, city, local) before padding.
    - Country code is always 2 digits (left-padded with zero if needed after stripping).
    - City code is always 3 digits (left-padded with zero if needed after stripping).
    - Local part kept at 7 digits (rightmost digits, left-padded with zero if too short).
    """
    digits_all = "".join(ch for ch in raw if ch.isdigit())
    if not digits_all:
        country_core = default_country.lstrip("0") or "0"
        city_core = default_city.lstrip("0") or "0"
        local_core = ""
    else:
        # Extract parts from formatted input if possible
        before_paren = raw.split("(", 1)[0]
        country_part = "".join(ch for ch in before_paren if ch.isdigit())

        city_raw = ""
        if "(" in raw and ")" in raw.split("(", 1)[1]:
            inside = raw.split("(", 1)[1].split(")", 1)[0]
            city_raw = "".join(ch for ch in inside if ch.isdigit())
            tail = raw.split(")", 1)[1]
        else:
            tail = raw

        tail_digits = "".join(ch for ch in tail if ch.isdigit())
        local_raw = (tail_digits or digits_all)[-7:]

        # Fallback city from remaining prefix if not taken from parentheses
        if not city_raw:
            prefix_full = digits_all[:-7]
            if country_part and prefix_full.startswith(country_part):
                remainder = prefix_full[len(country_part):]
            else:
                remainder = prefix_full
            city_raw = remainder[:3]

        country_raw = country_part.lstrip("0")
        country_core = (country_raw or default_country.lstrip("0") or "0")[-2:]
        city_core = city_raw.lstrip("0") or default_city.lstrip("0") or "0"
        local_core = local_raw.lstrip("0")

    country = country_core.zfill(2)
    city = city_core.zfill(3)
    local = local_core.zfill(7)

    return f"{country}{city}{local}"

def fake_phone(value: str) -> str:
    """
    Phone-specific anonymizer: direct lookup by phone_hash (normalized), no fuzzy.
    """
    if value == "PII":
        return value

    _fake_factory()  # ensure faker is initialized
    h = phone_hash(value)
    if h in _true:
        return _true[h]["fake"]

    fake_val = _base_fake_phone(value)
    _true[h] = {"true": value, "fake": fake_val}
    _faked[phone_hash(fake_val)] = {"true": value, "fake": fake_val}

    return fake_val

def defake_phone(value: str) -> str:
    """
    Phone-specific exact defake: direct lookup by phone_hash (no fuzzy).
    """
    if value == "PII":
        return value
    h = phone_hash(value)
    if h in _faked:
        return _faked[h].get("true")
    return value

def defake_phone_fuzzy(value: str):
    """
    Phone-specific fuzzy defake: now delegates to exact lookup.
    """
    return defake_phone(value)

def phone_hash(value: str) -> str:
    """
    Phone hash: normalized phone string (digits-only with padding rules).
    """
    return normalize_phone(value)

def calc_hash(text):
    VOWELS = set("АЕЁИОУЫЭЮЯаеёиоуыэюя")
    def alnum(s: str) -> str:
        def strip_vowels(word: str) -> str:
            while word and word[-1] in VOWELS:
                word = word[:-1]
            return word
        alfanum = ''.join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)   

        words = alfanum.split()
        #stripped = [strip_vowels(w) for w in words]
        stripped = [w for w in words]
        return " ".join(stripped)
    
    def normalyze_lemma(lemma):
        parse = _morph.parse(lemma)[0]
        form = parse.inflect({"nomn", "sing", "masc"})
        return form.word if form else lemma

    nlp = get_nlp()
    tockens = nlp(text)
    hash = alnum("".join([normalyze_lemma(token.lemma_) for token in tockens]))
    return hash

def validate_name(name):
    try:
        forms = get_morphs(name)
        hash_nom = calc_hash(name)
        for case, val in forms["singular"].items():
            hash_var = calc_hash(val)
            if hash_var != hash_nom:
                #print(f"{name} ({hash_nom}): {case}: {val} ({hash_var})")
                return False
        for case, val in forms["plural"].items():
            hash_var = calc_hash(val)
            if hash_var != hash_nom:
                #print(f"{name} ({hash_nom}): plural_{case}: {val} ({hash_var})")
                return False
        return True
    except:
        return False

def validate_name_cusom(name):
    return True



if __name__ == "__main__":
    src = "99923420392020900087-64-05"
    norm = fake_phone(src)
    print("normalized:", norm)
    print("restored  :", defake_phone(norm))
