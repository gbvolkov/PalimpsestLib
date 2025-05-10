from typing import Optional, List, Tuple, Set

from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerResult

from gliner import GLiNER
import re

import logging
logger = logging.getLogger(__name__)


def merge_spans(results, entity_type, text, delim_pattern=r'^[\s,;:\-]+$'):
    spans = [r for r in results if r.entity_type == entity_type]
    others = [r for r in results if r.entity_type != entity_type]
    spans.sort(key=lambda r: r.start)
    merged = []
    cur = None
    delim_re = re.compile(delim_pattern)
    for r in spans:
        if cur is None:
            cur = r
        else:
            between = text[cur.end:r.start]
            if delim_re.match(between):
                cur = RecognizerResult(entity_type, cur.start, r.end,
                                    score=max(cur.score, r.score))
            else:
                merged.append(cur)
                cur = r
    if cur:
        merged.append(cur)
    return others + merged

class GlinerRecognizer(EntityRecognizer):
    def __init__(
        self,
        supported_language: str = "ru",
        supported_entities: Optional[List[str]] = None,
        check_label_groups: Optional[Tuple[Set, Set]] = None,
        model_path: Optional[str] = "gliner-community/gliner_large-v2.5",
        
    ):
        # map them to the Presidio-standard types:
        self.label_map = {
            "person":             "RU_PERSON",
            "person_name":        "RU_PERSON",
            "organization":       "RU_ORGANIZATION",
            "organization_name":  "RU_ORGANIZATION",
            "address":            "RU_ADDRESS",
            "house_address":      "RU_ADDRESS",
            "city":               "RU_CITY",
        }

        supported_entities = list(set(self.label_map.values()))
        self.raw_labels = list(self.label_map.keys())
        super().__init__(
            supported_entities=supported_entities,
            supported_language="en",
            name="GlinerRecognizer",
        )
        self._model = GLiNER.from_pretrained(model_path, local_files_only=True)

    def is_language_supported(self, language: str) -> bool:
        # Принудительно говорим Presidio: "вызывайте меня всегда"
        return True

    def analyze(self, text: str, entities=None, **kwargs):
        # запускаем Natasha NER
        spans = self._model.predict_entities(text=text, labels = self.raw_labels, flat_ner=True, threshold=0.35, multi_label=False)

        results = []
        for span in spans:
            # Переводим PER/LOC/ORG → Presidio-тизеры
            raw_label = span.get("label")  # "PER", "LOC", "ORG"
            presidio_label = self.label_map.get(raw_label, raw_label)
            # фильтруем, если у нас есть entities-фильтр
            if entities and presidio_label not in entities:
                continue
            results.append(
                RecognizerResult(
                    entity_type=presidio_label,
                    start=span.get("start"),
                    end=span.get("end"),
                    score=span.get("score"),
                )
            )

        # split ADDRESS vs everything else
        results = merge_spans(results, "RU_ADDRESS", text)
        results.sort(key=lambda r: r.score)

        return results


if __name__ == "__main__":
    #from ..sentence_splitter import chunk_sentences
    #from nltk.tokenize import sent_tokenize
    from functools import lru_cache
    from typing import Any
    from transformers import AutoTokenizer

    def length_factory(tokenizer: Any = None):
        @lru_cache(maxsize=5000, typed=True)
        def _len(text: str) -> int:
            return len(tokenizer.encode(text))
        if tokenizer:
            return _len
        else:
            return len
    tokenizer =  AutoTokenizer.from_pretrained("gliner-community/gliner_large-v2.5")
    calc_len = length_factory(tokenizer)

    # Собираем движок с дефолтными Pattern/Spacy-распознавателями
    engine = AnalyzerEngine()
    # Впихиваем наш Natasha-распознаватель
    #engine.registry.add_recognizer(GlinerRecognizer(model_path="urchade/gliner_multi-v2.1"))
    engine.registry.add_recognizer(GlinerRecognizer(model_path="gliner-community/gliner_large-v2.5"))
    engine.registry.remove_recognizer("SpacyRecognizer")

    # Тест на реальном русском
    text_ru = "Пётр Иванов из Санкт-Петербурга поехал в офис Яндекса."
    text = """Клиент Степан Степанов (паспорт 4519345678) по поручению Ивана Иванова обратился в "НашаКомпания" с предложением купить трактор. 
    Для оплаты используется его карта 4694791869619038. 
    Позвоните ему 9867777777 или 9857777237.
    Или можно по адресу г. Санкт-Петербург, Сенная Площадь, д1/2кв17
    Посмотреть его данные можно https://infoaboutclient.ru/name=stapanov:3000 или зайти на 182.34.35.12/
    """        
    #with open("logs/test.txt", encoding="utf-8") as f:
    #    text_ru = f.read()
    #sentences = sent_tokenize(text_ru, language='russian')
    #texts = chunk_sentences(sentences, max_chunk_size=768, overlap_size=0, _len=calc_len)    
    print(f"\n=== Analysis for ===\n{text_ru}")
    result = engine.analyze(text=text_ru, language="en", return_decision_process=True)
    for r in result:
        print(f"{r.entity_type}: `{text_ru[r.start:r.end]}` (score={r.score:.2f})) , Recognizer:{r.recognition_metadata['recognizer_name']}")
