from collections import OrderedDict
from functools import lru_cache
from threading import RLock
from typing import Any, List
from uuid import uuid4

from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine, EngineResult
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

class PalimpsestSessionError(RuntimeError):
    """Base class for Palimpsest session-state errors."""


class SessionRequiredError(PalimpsestSessionError):
    """Raised when a processor-level call requires an explicit session."""


class SessionStateError(PalimpsestSessionError):
    """Raised when a session is closed, foreign, or has no usable mapping."""


class _PalimpsestRuntime:
    def __init__(self, run_entities: List[str] = None):
        from .analyzer_engine_provider import analyzer_engine
        from .recognizers.regex_recognisers import RU_ENTITIES

        self._run_entities = list(run_entities) if run_entities else None
        self._analyzer = analyzer_engine(
            "gliner",
            "gliner-community/gliner_large-v2.5",
            run_entities=run_entities,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(
            "gliner-community/gliner_large-v2.5"#,
            #local_files_only=True,
        )
        self._calc_len = _length_factory(self._tokenizer)
        supported = self._analyzer.get_supported_entities() + RU_ENTITIES
        if "IN_PAN" in supported:
            supported.remove("IN_PAN")
        self._supported = supported
        self._analyzer_entities = self._run_entities or supported
        self._engine = AnonymizerEngine()
        self._cr_key = CRYPRO_KEY

    def _anon_operators(self, ctx: FakerContext) -> dict:
        operators = {
            #"DEFAULT": OperatorConfig("encrypt", {"key": self._cr_key}),
            "DEFAULT": OperatorConfig("keep"),
            "TICKET_NUMBER": OperatorConfig("keep"),
            "RU_ORGANIZATION": OperatorConfig("custom", {"lambda": ctx.fake_organization}),
            "RU_CITY": OperatorConfig("keep"),
            "RU_PERSON": OperatorConfig("custom", {"lambda": ctx.fake_name}),
            "PERSON": OperatorConfig("custom", {"lambda": ctx.fake_name}),
            "RU_ADDRESS": OperatorConfig("custom", {"lambda": ctx.fake_house}),
            "CREDIT_CARD": OperatorConfig("custom", {"lambda": ctx.fake_card}),
            "PHONE_NUMBER": OperatorConfig("custom", {"lambda": ctx.fake_phone}),
            "IP_ADDRESS": OperatorConfig("custom", {"lambda": ctx.fake_ip}),
            "URL": OperatorConfig("custom", {"lambda": ctx.fake_url}),
            "EMAIL_ADDRESS": OperatorConfig("custom", {"lambda": ctx.fake_email}),
            "RU_PASSPORT": OperatorConfig("custom", {"lambda": ctx.fake_ru_passport}),
            "SNILS": OperatorConfig("custom", {"lambda": ctx.fake_snils}),
            "INN": OperatorConfig("custom", {"lambda": ctx.fake_inn}),
            "RU_BANK_ACC": OperatorConfig("custom", {"lambda": ctx.fake_ru_bank_account}),
            "Person": OperatorConfig("custom", {"lambda": ctx.fake_name}),
        }
        if self._run_entities:
            return _filter_dict(operators, self._run_entities)
        return operators

    def _deanon_operators(self, ctx: FakerContext) -> dict:
        operators = {
            "DEFAULT": OperatorConfig("keep"),
            "TICKET_NUMBER": OperatorConfig("keep"),
            "RU_ORGANIZATION": OperatorConfig("custom", {"lambda": ctx.defake_fuzzy}),
            "RU_CITY": OperatorConfig("keep"),
            "RU_PERSON": OperatorConfig("custom", {"lambda": ctx.defake_fuzzy}),
            "PERSON": OperatorConfig("custom", {"lambda": ctx.defake_fuzzy}),
            "RU_ADDRESS": OperatorConfig("custom", {"lambda": ctx.defake_address}),
            "CREDIT_CARD": OperatorConfig("custom", {"lambda": ctx.defake}),
            "PHONE_NUMBER": OperatorConfig("custom", {"lambda": ctx.defake_phone}),
            "IP_ADDRESS": OperatorConfig("custom", {"lambda": ctx.defake}),
            "URL": OperatorConfig("custom", {"lambda": ctx.defake_fuzzy}),
            "RU_PASSPORT": OperatorConfig("custom", {"lambda": ctx.defake}),
            "SNILS": OperatorConfig("custom", {"lambda": ctx.defake}),
            "INN": OperatorConfig("custom", {"lambda": ctx.defake}),
            "RU_BANK_ACC": OperatorConfig("custom", {"lambda": ctx.defake}),
        }
        if self._run_entities:
            return _filter_dict(operators, self._run_entities)
        return operators

    def analyze(self, text, analizer_entities=None):
        from .utils.sentence_splitter import split_text

        entities = list(analizer_entities or self._analyzer_entities)
        chunks = split_text(text, max_chunk_size=768, _len=self._calc_len)
        analyzer_results = []
        shift = 0
        final_text = ""
        for chunk in chunks:
            analized = self._analyzer.analyze(
                text=chunk,
                entities=entities,
                language="en",
                return_decision_process=False,
            )
            analized = [
                RecognizerResult(
                    r.entity_type,
                    r.start + shift,
                    r.end + shift,
                    r.score,
                    r.analysis_explanation,
                    r.recognition_metadata,
                )
                for r in analized
            ]
            analyzer_results.extend(analized)
            final_text = final_text + chunk + "\n"
            shift = len(final_text)
        return final_text, analyzer_results

    def anonymize(self, ctx: FakerContext, text: str):
        final_text, analyzer_results = self.analyze(text)
        result = self._engine.anonymize(
            text=final_text,
            analyzer_results=analyzer_results,
            operators=self._anon_operators(ctx),
        )
        return result.text, result.items, final_text, analyzer_results

    def deanonymize(self, ctx: FakerContext, text: str, entities):
        def deanonymize_item(item):
            if item.operator == "encrypt":
                return Decrypt().operate(text=item.text, params={"key": self._cr_key})
            return item.text

        analized_anon_text, analized_anon_results = self.analyze(text)
        result = self._engine.anonymize(
            text=analized_anon_text,
            analyzer_results=analized_anon_results,
            operators=self._deanon_operators(ctx),
        )

        deanonimized_text = result.text
        deanonimized_entities = [
            {**item.to_dict(), "restored": deanonymize_item(item)}
            for item in entities
        ]
        for item in deanonimized_entities:
            deanonimized_text = deanonimized_text.replace(item["text"], item["restored"])

        return deanonimized_text, result.items, analized_anon_text, analized_anon_results


def _runtime_factory(run_entities: List[str] = None):
    return _PalimpsestRuntime(run_entities)


def _anonimizer_factory(ctx: FakerContext, run_entities: List[str] = None):
    #from nltk.tokenize import sent_tokenize

    runtime = _runtime_factory(run_entities)

    def analyze(text, analizer_entities=None):
        return runtime.analyze(text, analizer_entities)

    def anonimizer(text):
        return runtime.anonymize(ctx, text)

    def deanonimizer(text, entities):
        return runtime.deanonymize(ctx, text, entities)

    return anonimizer, deanonimizer, analyze

class PalimpsestSession:
    def __init__(self, processor: "Palimpsest", session_id: str = None):
        self.session_id = session_id or str(uuid4())
        self._processor = processor
        self._ctx = FakerContext(locale=processor._locale)
        self._anon_entries_by_text = OrderedDict()
        self._anon_analysis = None
        self._anon_analized_text = None
        self._anonimized_text = ""
        self._deanon_analysis = None
        self._deanon_analized_text = None
        self._deanonimized_text = ""
        self._closed = False
        self._lock = RLock()

    @property
    def closed(self) -> bool:
        return self._closed

    def _ensure_open(self):
        if self._closed:
            raise SessionStateError(f"Palimpsest session is closed: {self.session_id!r}")

    def _entries(self):
        return list(self._anon_entries_by_text.values())

    def _store_entries(self, entries):
        for entry in entries:
            fake_text = getattr(entry, "text", None)
            if fake_text:
                self._anon_entries_by_text[fake_text] = entry

    def anonymize(self, text: str) -> str:
        with self._lock:
            self._ensure_open()
            return self._processor._anonymize_session(self, text)

    def anonimize(self, text: str) -> str:
        return self.anonymize(text)

    def deanonymize(self, anonymized_text: str = None) -> str:
        with self._lock:
            self._ensure_open()
            if anonymized_text is None:
                anonymized_text = self._anonimized_text
            return self._processor._deanonymize_session(self, anonymized_text)

    def deanonimize(self, anonimized_text: str = None) -> str:
        return self.deanonymize(anonimized_text)

    def reset(self):
        with self._lock:
            self._ensure_open()
            self._reset_unlocked()

    def _reset_unlocked(self):
        self._ctx.reset()
        self._anon_entries_by_text.clear()
        self._anon_analysis = None
        self._anon_analized_text = None
        self._anonimized_text = ""
        self._deanon_analysis = None
        self._deanon_analized_text = None
        self._deanonimized_text = ""

    def close(self):
        with self._lock:
            if not self._closed:
                self._reset_unlocked()
                self._closed = True


class Palimpsest():
    def __init__(self, verbose=False, run_entities: List[str] = None, locale: str = "ru-RU"):
        self._verbose = verbose
        self._locale=locale
        self._run_entities = run_entities
        self._runtime = _runtime_factory(run_entities)

    def create_session(self, session_id: str = None) -> PalimpsestSession:
        return PalimpsestSession(self, session_id=session_id)

    def _require_session(self, session: PalimpsestSession = None) -> PalimpsestSession:
        if session is None:
            raise SessionRequiredError(
                "Palimpsest processor calls require an explicit session. "
                "Use processor.create_session(...) and pass session=session, "
                "or call session.anonymize/session.deanonymize directly."
            )
        if not isinstance(session, PalimpsestSession):
            raise SessionStateError("session must be a PalimpsestSession")
        if session._processor is not self:
            raise SessionStateError(
                f"Palimpsest session belongs to another processor: {session.session_id!r}"
            )
        session._ensure_open()
        return session

    def _anonymize_session(self, session: PalimpsestSession, text: str) -> str:
        session._anonimized_text, entries, session._anon_analized_text, session._anon_analysis = self._runtime.anonymize(session._ctx, text)
        session._store_entries(entries)
        if self._verbose:
            debug_log("ANONIMIZATION", text, session._anonimized_text, entries, session._ctx, session._anon_analized_text, session._anon_analysis)
        return session._anonimized_text

    def _deanonymize_session(self, session: PalimpsestSession, anonymized_text: str) -> str:
        session._deanonimized_text, deanon_entries, session._deanon_analized_text, session._deanon_analysis = self._runtime.deanonymize(
            session._ctx,
            anonymized_text,
            session._entries(),
        )
        if self._verbose:
            debug_log("DEANONIMIZATION", anonymized_text, session._deanonimized_text, deanon_entries, session._ctx, session._deanon_analized_text, session._deanon_analysis)
        return session._deanonimized_text

    def anonymize(self, text: str, *, session: PalimpsestSession = None) -> str:
        return self._require_session(session).anonymize(text)

    def anonimize(self, text: str, *, session: PalimpsestSession = None) -> str:
        return self.anonymize(text, session=session)

    def deanonymize(self, anonymized_text: str = None, *, session: PalimpsestSession = None) -> str:
        return self._require_session(session).deanonymize(anonymized_text)

    def deanonimize(self, anonimized_text: str = None, *, session: PalimpsestSession = None) -> str:
        return self.deanonymize(anonimized_text, session=session)

    def reset_context(self, *, session: PalimpsestSession = None):
        self._require_session(session).reset()


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
