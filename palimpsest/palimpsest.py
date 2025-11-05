from functools import lru_cache
from typing import List, Dict, Tuple, Any

from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine, EngineResult
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.operators import Decrypt

from transformers import AutoTokenizer

from .fakers.faker_context import FakerContext

from .config import *

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


def _filter_dict(d: dict, valid_keys)-> dict:
    valid = set(valid_keys)
    return {k: v for k, v in d.items() if k in valid}

def _anonimizer_factory(ctx: FakerContext, run_entities: List[str] = None):
    from .utils.sentence_splitter import split_text
    #from nltk.tokenize import sent_tokenize

    from .analyzer_engine_provider import analyzer_engine
    from .recognizers.regex_recognisers import RU_ENTITIES

    analyzer = analyzer_engine("gliner", "gliner-community/gliner_large-v2.5")
    tokenizer =  AutoTokenizer.from_pretrained("gliner-community/gliner_large-v2.5")
    calc_len = _length_factory(tokenizer)
    supported = analyzer.get_supported_entities() + RU_ENTITIES
    if "IN_PAN" in supported: supported.remove("IN_PAN")
    engine = AnonymizerEngine()
    cr_key = CRYPRO_KEY
    _ctx = ctx
    
    anon_operators = {
        #"DEFAULT": OperatorConfig("encrypt", {"key": cr_key}),
        "DEFAULT": OperatorConfig("keep"),
        "TICKET_NUMBER": OperatorConfig("keep"),
        "RU_ORGANIZATION": OperatorConfig("custom", {"lambda": _ctx.fake_organization}),
        "RU_CITY": OperatorConfig("keep"),
        "RU_PERSON": OperatorConfig("custom", {"lambda": _ctx.fake_name}),
        "RU_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.fake_house}),
        "CREDIT_CARD": OperatorConfig("custom", {"lambda": _ctx.fake_card}),
        "PHONE_NUMBER": OperatorConfig("custom", {"lambda": _ctx.fake_phone}),
        "IP_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.fake_ip}),
        "URL": OperatorConfig("custom", {"lambda": _ctx.fake_url}),
        "EMAIL_ADDRESS": OperatorConfig("custom", {"lambda": _ctx.fake_email}),
        "RU_PASSPORT": OperatorConfig("custom", {"lambda": _ctx.fake_passport}),
        "SNILS": OperatorConfig("custom", {"lambda": _ctx.fake_snils}),
        "INN": OperatorConfig("custom", {"lambda": _ctx.fake_inn}),
        "RU_BANK_ACC": OperatorConfig("custom", {"lambda": _ctx.fake_account}),
    }
    if run_entities: 
        anon_operators = _filter_dict(anon_operators, run_entities)

    deanon_operators = {
        "DEFAULT": OperatorConfig("keep"),
        "TICKET_NUMBER": OperatorConfig("keep"),
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
    }
    if run_entities: 
        deanon_operators = _filter_dict(deanon_operators, run_entities)

    def analyze(text, analizer_entities=supported):
        #sentences = sent_tokenize(text, language='russian')
        #texts = chunk_sentences(sentences, max_chunk_size=768, overlap_size=0, _len=calc_len)    
        chunks = split_text(text, max_chunk_size=768, _len=calc_len)
        analyzer_results = []
        shift = 0
        final_text = ""
        for chunk in chunks:
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
            operators=anon_operators)

        return result.text, result.items, final_text, analyzer_results
    
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
            operators=deanon_operators)

        deanonimized_text = result.text
        deanonimized_entities = [
            {**item.to_dict(), 'restored': deanonimize(item)}
            for item in entities]
        for item in deanonimized_entities:
            deanonimized_text  = deanonimized_text.replace(item["text"], item["restored"])


        return deanonimized_text, result.items, analized_anon_text, analized_anon_results

    return anonimizer, deanonimizer, analyze

class Palimpsest():
    def __init__(self, verbose=False, run_entities: List[str] = None):
        self._ctx = FakerContext()
        self._anonimizer, self._deanonimizer, _ = _anonimizer_factory(self._ctx, run_entities)
        self._anon_entries = None
        self._anon_analysis = None
        self._anon_analized_text = None
        self._anonimized_text = ""
        self._deanon_analysis = None
        self._deanon_analized_text = None
        self._deanonimized_text = ""
        self._verbose = verbose
    def anonimize(self, text: str) -> str:
        self._anonimized_text, self._anon_entries, self._anon_analized_text, self._anon_analysis = self._anonimizer(text)
        if self._verbose:
            debug_log("ANONIMIZATION", text, self._anonimized_text, self._anon_entries, self._ctx, self._anon_analized_text, self._anon_analysis)
        return self._anonimized_text
    
    def deanonimize(self, anonimized_text: str = None) -> str:
        if anonimized_text == None:
            anonimized_text = self._anonimized_text
        if self._anon_entries:
            self._deanonimized_text, deanon_entries, self._deanon_analized_text, self._deanon_analysis = self._deanonimizer(anonimized_text, self._anon_entries)
            if self._verbose:
                debug_log("DEANONIMIZATION", anonimized_text, self._deanonimized_text, deanon_entries, self._ctx, self._deanon_analized_text, self._deanon_analysis)
            return self._deanonimized_text
        else:
            return anonimized_text
    
    def reset_context(self):
        self._ctx.reset()


def debug_log(action: str, input_text: str = None, output_text: str = None, action_entries: EngineResult = None, ctx: FakerContext = None, analised_text: str = None, action_analysis: list[RecognizerResult] = None):
    debug = logger.debug
    debug(f"\n+======================================{action}=====================================+")
    if input_text: debug(f"\n>====================={action} INPUT:\n{input_text}")
    if output_text: debug(f"\n>====================={action} OUTPUT:\n{output_text}")
    if action_analysis:
        debug(f"\n>============================{action} ANALYSIS================================")
        for r in action_analysis:
            debug(f"{r.entity_type}: `{analised_text[r.start:r.end] if analised_text else "ND"}` (score={r.score:.2f})) , Recognizer:{r.recognition_metadata['recognizer_name']}")
    if action_entries:
        debug(f"\n>============================{action} ENTRIES================================")
        for r in action_entries:
            debug(f"\ttype: {r.entity_type};  value: {r.text};  operator: {r.operator}")
    if ctx: 
        debug(f"\n>============================{action} CONTEXT================================")
        debug(  f"\n/============================{action} FAKED_VALUES:")
        for hash in ctx._faked:
            debug(f"\thash: {hash};  true: {ctx._faked[hash]['true']};  fake: {ctx._faked[hash]['fake']}")
        debug(  f"\n/============================{action} TRUE_VALUES:")
        for hash in ctx._true:
            debug(f"\thash: {hash};  true: {ctx._true[hash]['true']};  fake: {ctx._true[hash]['fake']}")
        return
