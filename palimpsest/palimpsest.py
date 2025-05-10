from functools import lru_cache
from typing import List, Dict, Tuple, Any

from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.operators import Decrypt

from transformers import AutoTokenizer

from fakers.faker_context import FakerContext

import config

import logging

logger = logging.getLogger(__name__)

def _length_factory(tokenizer: Any = None):
    @lru_cache(maxsize=5000, typed=True)
    def _len(text: str) -> int:
        return len(tokenizer.encode(text))
    if tokenizer:
        return _len
    else:
        return len

def _anonimizer_factory(ctx: FakerContext):
    from utils.sentence_splitter import chunk_sentences
    from nltk.tokenize import sent_tokenize

    from analyzer_engine_provider import analyzer_engine
    from recognizers.regex_recognisers import RU_ENTITIES

    analyzer = analyzer_engine("gliner", "gliner-community/gliner_large-v2.5")
    tokenizer =  AutoTokenizer.from_pretrained("gliner-community/gliner_large-v2.5")
    calc_len = _length_factory(tokenizer)
    supported = analyzer.get_supported_entities() + RU_ENTITIES
    supported.remove("IN_PAN")
    engine = AnonymizerEngine()
    cr_key = config.CRYPRO_KEY
    _ctx = ctx
    
    def analyze(text, analizer_entities=supported):
        sentences = sent_tokenize(text, language='russian')
        texts = chunk_sentences(sentences, max_chunk_size=768, overlap_size=0, _len=calc_len)    
        analyzer_results = []
        shift = 0
        final_text = ""
        for chunk in texts:
            analized = analyzer.analyze(text=chunk, entities=analizer_entities, language='en', return_decision_process=False)
            analized = [
                RecognizerResult(r.entity_type, r.start + shift, r.end + shift, r.score, r.analysis_explanation, r.recognition_metadata)
                for r in analized
            ]
            analyzer_results.extend(analized)
            final_text = final_text + chunk + "\n"
            shift = len(final_text)#shift + len(chunk) + 2
        return final_text, analyzer_results
    def anonimizer(text):
        final_text, analyzer_results = analyze(text)

        result = engine.anonymize(
            text=final_text,
            analyzer_results=analyzer_results,
            operators={"DEFAULT": OperatorConfig("encrypt", {"key": cr_key}),
                    "RU_ORGANIZATION": OperatorConfig("custom", {"lambda": _ctx.fake_organization}),
                    "RU_CITY": OperatorConfig("keep"),
                    "RU_PERSON": OperatorConfig("custom", {"lambda": _ctx.fake_name}),
                    "RU_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.fake_house}),
                    "CREDIT_CARD": OperatorConfig("custom", {"lambda": _ctx.fake_card}),
                    "PHONE_NUMBER": OperatorConfig("custom", {"lambda": _ctx.fake_phone}),
                    "IP_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.fake_ip}),
                    "URL": OperatorConfig("custom", {"lambda": _ctx.fake_url}),
                    "RU_PASSPORT": OperatorConfig("custom", {"lambda": _ctx.fake_passport}),
                    "SNILS": OperatorConfig("custom", {"lambda": _ctx.fake_snils}),
                    "INN": OperatorConfig("custom", {"lambda": _ctx.fake_inn}),
                    "RU_BANK_ACC": OperatorConfig("custom", {"lambda": _ctx.fake_account}),
                    })

        return result.text, result.items
    
    def deanonimizer_simple(text, entities):
        def deanonimize(item):
            if item.operator=="encrypt":
                return Decrypt().operate(text=item.text, params={"key": cr_key})
            elif item.operator=="custom":
                return _ctx.defake(item.text)
            else:
                return item.text
        deanonimized_entities = [
            {**item.to_dict(), 'restored': deanonimize(item)}
            for item in entities]
        for item in deanonimized_entities:
            text  = text.replace(item["text"], item["restored"])
        
        return text
    
    def deanonimizer(text, entities):
        def deanonimize(item): 
            if item.operator=="encrypt":
                return Decrypt().operate(text=item.text, params={"key": cr_key})
            else:
                return item.text


        analized_anon_text, analized_anon_results = analyze(text)#, ["person", "house_address"])
        
        result = engine.anonymize(
            text=analized_anon_text,
            analyzer_results=analized_anon_results,

            operators={"DEFAULT": OperatorConfig("keep"),
                    "RU_ORGANIZATION": OperatorConfig("custom", {"lambda": _ctx.defake_fuzzy}),
                    "RU_CITY": OperatorConfig("keep"),
                    "RU_PERSON": OperatorConfig("custom", {"lambda": _ctx.defake_fuzzy}),
                    "RU_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.defake_fuzzy}),
                    "CREDIT_CARD": OperatorConfig("custom", {"lambda": _ctx.defake}),
                    "PHONE_NUMBER": OperatorConfig("custom", {"lambda": _ctx.defake_fuzzy}),
                    "IP_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.defake}),
                    "URL": OperatorConfig("custom", {"lambda": _ctx.defake_fuzzy}),
                    "RU_PASSPORT": OperatorConfig("custom", {"lambda": _ctx.defake}),
                    "SNILS": OperatorConfig("custom", {"lambda": _ctx.defake}),
                    "INN": OperatorConfig("custom", {"lambda": _ctx.defake}),
                    "RU_BANK_ACC": OperatorConfig("custom", {"lambda": _ctx.defake}),
                    })

        deanonimized_text = result.text
        deanonimized_entities = [
            {**item.to_dict(), 'restored': deanonimize(item)}
            for item in entities]
        for item in deanonimized_entities:
            deanonimized_text  = deanonimized_text.replace(item["text"], item["restored"])


        return deanonimized_text, result.items

    return anonimizer, deanonimizer, analyze

class Palimpsest():
    def __init__(self, verbose=False):
        self._ctx = FakerContext()
        self._anonimizer, self._deanonimizer, _ = _anonimizer_factory(self._ctx)
        self._entities = None
        self._anonimized_text = ""
        self._verbose = verbose
    def anonimize(self, text: str) -> str:
        self._anonimized_text, self._entities = self._anonimizer(text)
        return self._anonimized_text
    
    def deanonimize(self, anonimized_text: str) -> str:
        if self._entities:
            deanonimized_text, deanon_entities = self._deanonimizer(anonimized_text, self._entities)
            return deanonimized_text
        else:
            return ""
