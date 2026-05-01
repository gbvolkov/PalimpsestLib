import logging
logger = logging.getLogger(__name__)

import pymorphy3
from .names_morph import get_morphs

_nlp = None  # spaCy model, loaded once
_morph = pymorphy3.MorphAnalyzer(lang='ru')

def get_nlp():
    """Lazily load and return the shared spaCy Russian pipeline."""
    global _nlp
    if _nlp is None:
        import spacy
        if not spacy.util.is_package("ru_core_news_sm"):
            spacy.cli.download("ru_core_news_sm")

        _nlp = spacy.load("ru_core_news_sm")
    return _nlp

def normalize_phone(raw: str, default_country: str = "99", default_city: str = "999") -> str:
    """
    Normalize phone to digits-only form.
    - Strip leading zeroes from every part (country, city, local) before padding.
    - Country: 2 digits; city: 3 digits; local: 7 digits.
    """
    digits_all = "".join(ch for ch in raw if ch.isdigit())
    if not digits_all:
        country_core = default_country.lstrip("0") or "0"
        city_core = default_city.lstrip("0") or "0"
        local_core = ""
    else:
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
