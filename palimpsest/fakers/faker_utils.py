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

        _nlp = spacy.load("ru_core_news_sm")
    return _nlp

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