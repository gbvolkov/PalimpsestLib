from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerResult
from navec import Navec
from slovnet import NER

import logging
logger = logging.getLogger(__name__)

class SlovnetRecognizer(EntityRecognizer):
    def __init__(self):
        # мы отдаем только три базовых типа из Natasha: PER, LOC, ORG
        supported_entities = ["PERSON", "LOCATION", "ORGANIZATION"]
        super().__init__(
            supported_entities=supported_entities,
            name="NatashaSlovnetRecognizer",
        )
        self._navec = Navec.load('data/navec_news_v1_1B_250K_300d_100q.tar')
        self._ner = NER.load('data/slovnet_ner_news_v1.tar')
        self._ner.navec(self._navec)
        # инициализируем Natasha-пайплайн

    def is_language_supported(self, language: str) -> bool:
        # Принудительно говорим Presidio: "вызывайте меня всегда"
        return True

    def analyze(self, text: str, entities=None, **kwargs):
        # запускаем Natasha NER
        doc = self._ner(text)

        results = []
        for span in doc.spans:
            # Переводим PER/LOC/ORG → Presidio-тизеры
            label = span.type  # "PER", "LOC", "ORG"
            presidio_label = {
                "PER": "PERSON",
                "LOC": "LOCATION",
                "ORG": "ORGANIZATION",
            }.get(label, label)
            # фильтруем, если у нас есть entities-фильтр
            if entities and presidio_label not in entities:
                continue
            results.append(
                RecognizerResult(
                    entity_type=presidio_label,
                    start=span.start,
                    end=span.stop,
                    # Natasha не всегда дает score, поэтому по умолчанию 1.0
                    score=0.9999,
                )
            )
        return results


if __name__ == "__main__":
    # Собираем движок с дефолтными Pattern/Spacy-распознавателями
    engine = AnalyzerEngine()
    # Впихиваем наш Natasha-распознаватель
    engine.registry.add_recognizer(SlovnetRecognizer())

    # Тест на реальном русском
    text_ru = "Пётр Иванов из Санкт-Петербурга поехал в офис Яндекса."
    text = """Клиент Степан Степанов (паспорт 4519345678) по поручению Ивана Иванова обратился в "НашаКомпания" с предложением купить трактор. 
    Для оплаты используется его карта 4694791869619038. 
    Позвоните ему 9867777777 или 9857777237.
    Или можно по адресу г. Санкт-Петербург, Сенная Площадь, д1/2кв17
    Посмотреть его данные можно https://infoaboutclient.ru/name=stapanov:3000 или зайти на 182.34.35.12/
    """        

    print("\n=== Russian call ===")
    result = engine.analyze(text=text_ru, language="en", return_decision_process=True)
    for r in result:
        print(f"{r.entity_type}: `{text_ru[r.start:r.end]}` (score={r.score:.2f})) , Recognizer:{r.recognition_metadata['recognizer_name']}")
