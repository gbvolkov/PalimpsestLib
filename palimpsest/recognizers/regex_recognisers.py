import re
from typing import List, Optional, Tuple, Union
import petrovna

from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerResult,
    EntityRecognizer,
    PatternRecognizer,
    Pattern,
)
import logging
logger = logging.getLogger(__name__)


RU_ENTITIES = ["RU_PASSPORT", "SNILS", "INN", "RU_BANK_ACC"]

# ——— 1) Passport via regex (word-bounded, not anchored) ———
ru_internal_passport_recognizer = PatternRecognizer(
    supported_entity="RU_PASSPORT",
    patterns=[
        Pattern(
            name="any",
            regex=r"\b\d{4}[- ]\d{6}\b",
            score=0.7
        ),
        Pattern(
            name="any",
            regex=r"\b\d{2}[- ]\d{2}[- ]\d{6}\b",
            score=0.7
        ),
        Pattern(
            name="any",
            regex=r"\b\d{10}\b",
            score=0.3
        ),
        Pattern(
            name="any",
            regex=r"\b\d{2}[- ]?\d{2}[- ]?\d{6}\b",
            score=0.2
        ),
        Pattern(
            name="any",
            regex=r"\b\d{4}[- ]?\d{6}\b",
            score=0.2
        ),
    ],
    #supported_language=["ru", "en"],
    name="RUPassportRecognizer",
)

ru_phone_recognizer = PatternRecognizer(
    supported_entity="PHONE_NUMBER",
    patterns=[
        Pattern(
            name="any",
            regex=r"\b[+]{1}(?:[0-9\-\(\)\\.]\s?){6,15}[0-9]{1}\b",
            score=0.4
        ),
        Pattern(
            name="any",
            regex=r"\b([+]{1})?(?:[0-9\-\(\)\\.]\s?){6,15}[0-9]{1}\b",
            score=0.2
        ),
    ],
    name="RUPhoneRecognizer",
)

ticket_number_recogniser = PatternRecognizer(
    supported_entity="TICKET_NUMBER",
    patterns=[
        Pattern(
            name="any",
            regex=r"\bIL\d{2}\d{9}\b",
            score=0.99
        ),
    ],
    name="TicketNumber",
)

# ——— 2) SNILS with checksum via petrovna ———
class SNILSRecognizer(EntityRecognizer):
    def load(self) -> None:
        """No loading is required."""
        pass
    def __init__(self, supported_entities = ["SNILS"]):
        super().__init__(
            supported_entities=supported_entities,
            #supported_language=["ru", "en"],
            name="SNILSRecognizer",
        )
        # match formats like 123-456-789 00 or 12345678900
        self.pattern = re.compile(r"\b\d{3}-?\d{3}-?\d{3}[- ]?\d{2}\b")

    def analyze(self, text: str, entities=None, **kwargs):
        #self.pattern = re.compile(r"\b\d{3}-?\d{3}-?\d{3}[- ]?\d{2}\b")
        results = []
        for m in self.pattern.finditer(text):
            raw = re.sub(r"[- ]", "", m.group())
            score = 0.999
            if not petrovna.validate_snils(raw):
                # invalid — skip
                score = score / 10
            # if caller asked to filter to a specific entity list:
            if entities and "SNILS" not in entities:
                continue
            results.append(
                RecognizerResult(
                    entity_type="SNILS",
                    start=m.start(),
                    end=m.end(),
                    score=score,
                )
            )
        return results

#The patch since in petrovna there is an error in check
def validate_inn(inn: str, errors: bool = False) -> Union[bool, Tuple[bool, Optional[str]]]:
    """
        Проверка ИНН - значение из 10 или 12 цифр с проеркой контрольной суммы
    """
    error = None
    if not inn:
        error = 'ИНН Пуст'
    elif not re.fullmatch(r'[0-9]+', inn):
        error = 'ИНН может состоять только из цифр'
    elif len(inn) not in [10, 12]:
        error = 'ИНН может состоять только из 10 или 12 цифр'
    else:
        def check_digits(_inn: str, coefficients: List[int]):
            n = 0
            for idx, coefficient in enumerate(coefficients):
                n += coefficient * int(_inn[idx])
            return n % 11 % 10

        if len(inn) == 10:
            n10 = check_digits(inn, [2, 4, 10, 3, 5, 9, 4, 6, 8])
            if n10 == int(inn[9]):
                pass
            else: #this else missed in petrovna
                error = 'Неправильно введен ИНН'
        elif len(inn) == 12:
            n11 = check_digits(inn, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
            n12 = check_digits(inn, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
            if n11 == int(inn[10]) and n12 == int(inn[11]):
                pass
            else: #this else missed in petrovna
                error = 'Неправильно введен ИНН'
        else:
            error = 'Неправильно введен ИНН'

    if errors:
        return not bool(error), error
    return not bool(error)

class INNRecognizer(EntityRecognizer):
    def load(self) -> None:
        """No loading is required."""
        pass
    def __init__(self, supported_entities = ["INN"]):
        super().__init__(
            supported_entities=supported_entities,
            #supported_language=["ru", "en"],
            name="INNRecognizer",
        )
        # match formats like 123-456-789 00 or 12345678900
        self.pattern = re.compile(r"\b((\d{4}[- ]?\d{6})|(\d{4}[- ]?\d{8}))\b")

    def analyze(self, text: str, entities=None, **kwargs):
        #self.pattern = re.compile(r"\b\d{3}-?\d{3}-?\d{3}[- ]?\d{2}\b")
        results = []
        for m in self.pattern.finditer(text):
            raw = re.sub(r"[- ]", "", m.group())
            score = 0.999
            if not validate_inn(raw):
                # invalid — skip
                score = score / 10
            # if caller asked to filter to a specific entity list:
            if entities and "INN" not in entities:
                continue
            results.append(
                RecognizerResult(
                    entity_type="INN",
                    start=m.start(),
                    end=m.end(),
                    score=score,
                )
            )
        return results

class RUBankAccountRecognizer(EntityRecognizer):
    def load(self) -> None:
        """No loading is required."""
        pass
    def __init__(self, supported_entities = ["RU_BANK_ACC"]):
        super().__init__(
            supported_entities=supported_entities,
            #supported_language=["ru", "en"],
            name="RUBankAccountRecognizer",
        )
        # match formats like 123-456-789 00 or 12345678900
        self.pattern = re.compile(r"\b\d{5}[- ]?\d{3}[- ]?\d{1}[- ]?\d{4}[- ]?\d{3}[- ]?\d{4}\b")

    def analyze(self, text: str, entities=None, **kwargs):
        #self.pattern = re.compile(r"\b\d{3}-?\d{3}-?\d{3}[- ]?\d{2}\b")
        results = []
        for m in self.pattern.finditer(text):
            raw = re.sub(r"[- ]", "", m.group())
            score = 0.7
            #if not petrovna.validate_rs(raw):
            #    # invalid — skip
            #    score = score / 10
            # if caller asked to filter to a specific entity list:
            if entities and "RU_BANK_ACC" not in entities:
                continue
            results.append(
                RecognizerResult(
                    entity_type="RU_BANK_ACC",
                    start=m.start(),
                    end=m.end(),
                    score=score,
                )
            )
        return results

def validate_card(card_no: str) -> bool:
    # remove spaces or hyphens
    digits = [int(ch) for ch in card_no if ch.isdigit()]
    checksum = 0
    # process from rightmost, i=0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

class RUCreditCardRecognizer(EntityRecognizer):
    def load(self) -> None:
        """No loading is required."""
        pass
    def __init__(self, supported_entities = ["CREDIT_CARD"]):
        super().__init__(
            supported_entities=supported_entities,
            #supported_language=["ru", "en"],
            name="CommonCreditCardRecognizer",
        )
        # match formats like 123-456-789 00 or 12345678900
        self.pattern = re.compile(r"\b(\d(?:[ .-]?\d){12})\b|\b(\d(?:[ .-]?\d){14})\b|\b(\d(?:[ .-]?\d){15})\b|\b(\d(?:[ .-]?\d){17})\b|\b(\d(?:[ .-]?\d){18})\b")

    def analyze(self, text: str, entities=None, **kwargs):
        #self.pattern = re.compile(r"\b\d{3}-?\d{3}-?\d{3}[- ]?\d{2}\b")
        results = []
        for m in self.pattern.finditer(text):
            raw = re.sub(r"[ .-]", "", m.group())
            score = 0.999
            if not validate_card(raw):
                # invalid — skip
                score = score / 10
            # if caller asked to filter to a specific entity list:
            if entities and "CREDIT_CARD" not in entities:
                continue
            results.append(
                RecognizerResult(
                    entity_type="CREDIT_CARD",
                    start=m.start(),
                    end=m.end(),
                    score=score,
                )
            )
        return results

def main():
    engine = AnalyzerEngine()
    # 1) register your custom recognizers
    engine.registry.add_recognizer(ru_internal_passport_recognizer)
    engine.registry.add_recognizer(SNILSRecognizer())
    engine.registry.add_recognizer(INNRecognizer())
    engine.registry.add_recognizer(RUBankAccountRecognizer())

    # 2) define your text
    text = (
        "Паспорт 45 12 345678 выдан в 2005, "
        "СНИЛС 112-233-445 95, ИНН 7707 083893, ИНН 770708389312 "
        "и ещё https://site.ru/user?id=ivanov"
        "счёт 4081781080223500892"
    )

    # 3) explicitly pass the list of entity types you want to detect
    entities_to_find = RU_ENTITIES

    # 4) run the analyzer for Russian
    results = engine.analyze(
        text=text,
        entities=entities_to_find,
        language="en"
    )

    # 5) print out what we found
    print("\n--- Detected Entities ---")
    for r in results:
        snippet = text[r.start:r.end]
        print(f"{r.entity_type:12}  {snippet:20}  score={r.score:.2f}")


if __name__ == "__main__":
    main()
