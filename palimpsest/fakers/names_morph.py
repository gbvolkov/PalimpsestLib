from functools import lru_cache
from pytrovich.enums import NamePart, Gender, Case
from pytrovich.maker import PetrovichDeclinationMaker
from pytrovich.detector import PetrovichGenderDetector

import pymorphy3


_detector = PetrovichGenderDetector()
_maker    = PetrovichDeclinationMaker()
_morph    = pymorphy3.MorphAnalyzer()

@lru_cache(maxsize=2048)
def get_morphs(full_name: str) -> dict[str, dict[str, str]]:
    """
    Decline a Russian full name into all six cases, both singular and plural.

    Returns a dict:
      {
        "singular": {case_name: declined_full, …},
        "plural":   {case_name: declined_full_plural, …}
      }
    """
    # — split input
    parts = full_name.split()
    if len(parts) == 3:
        first, middle, last = parts
    elif len(parts) == 2:
        first, middle, last = parts[0], "", parts[1]
    elif len(parts) == 1:
        first, middle, last = parts[0], "", ""
    else:
        raise ValueError("Use either ‘First Last’ or ‘First Middle Last’")

    # — detect gender via pytrovich
    try:
        gender = _detector.detect(firstname=first, middlename=middle)
    except:
        #first = last
        #last = first
        gender = _detector.detect(firstname=last, middlename=middle)
    
    # — prepare the declension maker
    cases = {
        "nominative":    "NOM",
        "genitive":      Case.GENITIVE,
        "dative":        Case.DATIVE,
        "accusative":    Case.ACCUSATIVE,
        "instrumental":  Case.INSTRUMENTAL,
        "prepositional": Case.PREPOSITIONAL,
    }

    # — 1) singular forms via pytrovich
    singular: dict[str, str] = {}
    for cname, cenum in cases.items():
        if cname == "nominative":
            fn = first
            mn = middle if middle else ""
            ln = last
        else:
            fn = _maker.make(NamePart.FIRSTNAME,  gender, cenum, first)
            mn = _maker.make(NamePart.MIDDLENAME, gender, cenum, middle) if middle else ""
            ln = _maker.make(NamePart.LASTNAME,   gender, cenum, last)
        singular[cname] = " ".join(p for p in (fn, mn, ln) if p)

    # — 2) plural forms via pymorphy2
    pym_feats = {
        "nominative":    set(),
        "genitive":      {"gent"},
        "dative":        {"datv"},
        "accusative":    {"accs"},
        "instrumental":  {"ablt"},
        "prepositional": {"loct"},
    }

    plural: dict[str, str] = {}
    for cname, feats in pym_feats.items():
        feats = feats | {"plur"}  # add plural
        declined = []
        for tok in (first, middle, last) if middle else (first, last):
            p = _morph.parse(tok)[0]
            inf = p.inflect(feats)
            declined.append(inf.word if inf else tok)
        plural[cname] = " ".join(declined)

    return {"singular": singular, "plural": plural}


if __name__ == "__main__":
    from faker import Faker
    from palimpsest.fakers.fakers_funcs import calc_hash
    
    fake = Faker(locale="ru-RU")
    for i in range(0,1023):
        try:
            name = fake.first_name() + " " + fake.last_name() 
            forms = get_morphs(name)
            hash_nom = calc_hash(name)
            for case, val in forms["singular"].items():
                hash_var = calc_hash(val)
                if hash_var != hash_nom:
                    print(f"{name} ({hash_nom}): {case}: {val} ({hash_var})")
                    break
            if hash_var != hash_nom:
                continue
            for case, val in forms["plural"].items():
                hash_var = calc_hash(val)
                if hash_var != hash_nom:
                    print(f"{name} ({hash_nom}): plural_{case}: {val} ({hash_var})")
                    break
        except:
            hash_non = calc_hash(name)
            print(f"{name} ({hash_nom}); EXCEPTION")
            print()
