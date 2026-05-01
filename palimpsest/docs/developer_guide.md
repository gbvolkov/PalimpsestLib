# Palimpsest Developer Guide

Last reviewed: 2026-05-01

This guide describes the current Palimpsest library behavior as implemented in
the workspace, not an idealized future contract. It covers the public API,
internal methods, configured recognizers and models, supported entities,
anonymization/deanonymization behavior, known limitations, and LangGraph
integration guidance based on `C:\Projects\bot_platform\agents\sd_ass_agent`.

## 1. Purpose And Architecture

Palimpsest is a reversible anonymization layer built on Microsoft Presidio. It
detects sensitive spans, replaces them with realistic fake values, stores a
session-local true/fake mapping, and later restores the original values after
LLM processing.

The core split is:

- `Palimpsest`: heavy, reusable processor. It owns the analyzer runtime,
  recognizers, tokenizer, and Presidio anonymizer engine.
- `PalimpsestSession`: lightweight, conversation/request-scoped state. It owns
  a `FakerContext` and all reversible mappings for that session.
- `FakerContext`: stores true-to-fake and fake-to-true maps and exposes
  generated `fake_*` and `defake*` methods.
- Recognizers: Presidio recognizers plus Palimpsest recognizers for Russian
  people, organizations, addresses, passports, phones, SNILS, INN, bank
  accounts, cards, and ticket numbers.

Create one `Palimpsest` processor per process or service configuration, then
create a separate `PalimpsestSession` per user conversation, request, or
LangGraph thread.

## 2. Public API

Import surface from `palimpsest/__init__.py`:

```python
from palimpsest import (
    Palimpsest,
    PalimpsestSession,
    PalimpsestSessionError,
    SessionRequiredError,
    SessionStateError,
)
```

### `Palimpsest`

Constructor:

```python
Palimpsest(
    verbose: bool = False,
    run_entities: list[str] | None = None,
    locale: str = "ru-RU",
)
```

- `verbose`: when `True`, debug logging emits raw input text, fake values, and
  true/fake mappings. Keep `False` outside local diagnostics.
- `run_entities`: optional entity allow-list. When set, analyzer calls and
  anonymization/deanonymization operators are filtered to these exact entity
  names.
- `locale`: default Faker locale for generated fake data. RU-specific fakers
  still use `ru_RU`; card generation uses `en_US`.

Methods:

| Method | Behavior |
| --- | --- |
| `create_session(session_id=None)` | Creates a new `PalimpsestSession` bound to this processor. If `session_id` is omitted, a UUID is generated. |
| `anonymize(text, *, session)` | Delegates to `session.anonymize(text)`. The `session` argument is required. |
| `anonimize(text, *, session)` | Backward-compatible misspelled alias for `anonymize`. |
| `deanonymize(anonymized_text=None, *, session)` | Delegates to `session.deanonymize(anonymized_text)`. The `session` argument is required. |
| `deanonimize(anonimized_text=None, *, session)` | Backward-compatible misspelled alias for `deanonymize`. |
| `reset_context(*, session)` | Calls `session.reset()`. |

Calling processor-level anonymization without an explicit session raises
`SessionRequiredError`. Passing a session from another processor or a closed
session raises `SessionStateError`.

Preferred usage:

```python
from palimpsest import Palimpsest

processor = Palimpsest(
    verbose=False,
    run_entities=["PERSON", "PHONE_NUMBER", "CREDIT_CARD", "EMAIL_ADDRESS"],
    locale="en-US",
)

session = processor.create_session(session_id="crm-request-1")
anonymized = session.anonymize("Client John Doe, phone +1 (202) 555-0182")

# Send only `anonymized` across the model boundary.
llm_answer = call_llm(anonymized)

restored = session.deanonymize(llm_answer)
```

Processor delegator usage is also valid:

```python
anonymized = processor.anonymize(text, session=session)
restored = processor.deanonymize(anonymized, session=session)
```

### `PalimpsestSession`

Methods and properties:

| Method/property | Behavior |
| --- | --- |
| `session_id` | Caller-provided id or generated UUID string. |
| `closed` | Boolean session lifetime flag. |
| `anonymize(text)` | Analyzes text, replaces supported entities with fake values, and stores mappings in this session. |
| `anonimize(text)` | Backward-compatible misspelled alias for `anonymize`. |
| `deanonymize(anonymized_text=None)` | Restores fake values in the provided text. If text is omitted, restores the last anonymized text. |
| `deanonimize(anonimized_text=None)` | Backward-compatible misspelled alias for `deanonymize`. |
| `reset()` | Clears all mappings and cached analysis for this session while keeping the session open. |
| `close()` | Clears mappings and marks the session closed. Further operations raise `SessionStateError`. |

Session behavior:

- Mappings are isolated per session.
- The same true value in one session returns the same fake value.
- Another session cannot restore a fake value created elsewhere; unmatched fakes
  are returned unchanged.
- `reset()` clears mappings, so old fake values become unrestorable.
- The session uses an internal `RLock` around public operations.

## 3. Internal Runtime Methods

These are not the public consumer API, but developers changing Palimpsest need
to understand them.

### `palimpsest/palimpsest.py`

| Function/class | Purpose |
| --- | --- |
| `_length_factory(tokenizer=None)` | Returns a cached tokenizer length function when a tokenizer is provided; otherwise returns built-in `len`. |
| `_filter_dict(d, valid_keys)` | Keeps only dictionary keys present in `valid_keys`. Used for `run_entities` operator filtering. |
| `_PalimpsestRuntime.__init__(run_entities=None)` | Builds the analyzer, GLiNER tokenizer, supported entity list, Presidio `AnonymizerEngine`, and crypto key reference. |
| `_PalimpsestRuntime._anon_operators(ctx)` | Builds Presidio anonymization operators for each supported entity. |
| `_PalimpsestRuntime._deanon_operators(ctx)` | Builds Presidio operators that restore fake values by calling `ctx.defake*`. |
| `_PalimpsestRuntime.analyze(text, analizer_entities=None)` | Splits text into chunks, runs Presidio analysis, adjusts span offsets, and rebuilds analyzed text with newline separators. |
| `_PalimpsestRuntime.anonymize(ctx, text)` | Runs analysis and Presidio anonymization with fake generators. Returns text, engine items, analyzed text, and analyzer results. |
| `_PalimpsestRuntime.deanonymize(ctx, text, entities)` | Re-analyzes model output and applies deanon operators. Then performs a final legacy decrypt/replacement pass over stored entities. |
| `_runtime_factory(run_entities=None)` | Constructs `_PalimpsestRuntime`. Tests monkeypatch this for lightweight contracts. |
| `_anonimizer_factory(ctx, run_entities=None)` | Legacy factory returning `(anonimizer, deanonimizer, analyze)` closures. |
| `debug_log(...)` | Verbose raw-value diagnostic logger. Unsafe for production data. |

Important spelling detail: internal names still include legacy spellings such as
`_anonimizer_factory`, `anonimize`, `deanonimize`, `anonimized`, and
`analized`. Public corrected aliases exist, but old names remain for backward
compatibility.

### `palimpsest/analyzer_engine_provider.py`

| Function | Purpose |
| --- | --- |
| `create_nlp_engine_with_transformers(model_path)` | Builds a Presidio transformers NLP engine with spaCy `ru_core_news_lg` and a configured label map. |
| `create_nlp_engine_with_flair(model_path)` | Builds a spaCy NLP engine plus Palimpsest `FlairRecognizer`. |
| `create_nlp_engine_with_natasha(model_path)` | Builds a spaCy NLP engine plus `NatashaSlovnetRecognizer`; `model_path` is not used. |
| `create_nlp_engine_with_gliner(model_path, run_entities=None)` | Builds a spaCy NLP engine plus `GlinerRecognizer`; this is the default runtime path. |
| `nlp_engine_and_registry(model_family, model_path, ..., run_entities=None)` | Dispatches to one of the above engine builders based on `model_family`. |
| `analyzer_engine(model_family, model_path, ..., run_entities=None)` | Creates `AnalyzerEngine`, then always adds Natasha and custom regex recognizers. |
| `get_supported_entities(...)` | Convenience wrapper returning analyzer supported entities. |

### `palimpsest/fakers/faker_context.py`

| Method | Purpose |
| --- | --- |
| `__init__(module=None, locale="ru_RU")` | Creates locale-specific Faker instances and dynamically binds all `fake_*` functions from `fakers_funcs`. |
| `reset()` | Clears true/fake maps. |
| `_generate_unique_fake(...)` | Regenerates fake values up to 10 attempts to avoid fake collisions. Raises `ValueError` when exhausted. |
| `_faker_for_function(name)` | Routes faker calls to default, RU, or EN Faker instance. |
| `_call_fake_func(name, func, value)` | Binds the correct Faker instance for the duration of one fake function call. |
| `_wrap(name, func)` | Generic fake wrapper using normalized `calc_hash` mapping. |
| `_wrap_phone(name, func)` | Phone-specific fake wrapper using `normalize_phone` as the map key. |
| `phone_hash(value)` | Returns normalized phone key. |
| `_wrap_address(name, func)` | Address-specific fake wrapper using libpostal unification and fuzzy keys. |
| `address_hash(value)` | Returns `unify_address(value).fuzzy_hash`; rethrows libpostal exceptions with notes. |
| `address_fuzzy_key(value)` | Returns sorted libpostal expanded variants as a string. |
| `defake(fake)` | Normalized direct restore using `calc_hash`. |
| `defake_phone(fake)` | Direct phone restore using normalized phone hash. |
| `defake_address(fake)` | Address restore by direct fuzzy hash, then rapidfuzz partial-ratio fallback. |
| `defake_fuzzy(fake)` | Best-match fuzzy restore over all stored fake values, then generic `defake` fallback. |

### `palimpsest/fakers/fakers_funcs.py`

Fake generation functions:

| Function | Faker provider / output |
| --- | --- |
| `fake_account` | `fake.checking_account()` |
| `fake_ru_bank_account` | `fake.checking_account()` using RU Faker |
| `fake_snils` | `fake.snils()` |
| `fake_inn` | `fake.businesses_inn()` |
| `fake_passport` | `fake.passport_number()` |
| `fake_ru_passport` | `fake.numerify("#### ######")` |
| `fake_name` | First + last name validated by morphology where possible |
| `fake_ru_name` | First + last name using RU Faker |
| `fake_first_name` | First name validated by morphology where possible |
| `fake_middle_name` | Middle name |
| `fake_last_name` | Last name validated by morphology where possible |
| `fake_city` | City |
| `fake_street` | Street name |
| `fake_district` | District |
| `fake_region` | Region code |
| `fake_house` | Street address |
| `fake_ru_address` | Street address using RU Faker |
| `fake_location` | Full address |
| `fake_email` | Safe email |
| `fake_phone` | `basic_phone_number()` when available, otherwise `phone_number()` |
| `fake_card` | Visa 16-digit credit card number |
| `fake_ip` | Public IPv4 address |
| `fake_url` | URL |
| `fake_organization` | Company name |

Only the functions referenced by `_anon_operators()` are used by the default
Palimpsest runtime. Other fakers are available for extension or tests.

### Utility Methods

| Module | Function | Purpose |
| --- | --- | --- |
| `faker_utils.py` | `get_nlp()` | Lazily loads spaCy `ru_core_news_sm` for hashing. |
| `faker_utils.py` | `normalize_phone(raw, default_country="99", default_city="999")` | Converts phone text to a padded digits-only key: 2 country digits + 3 city digits + 7 local digits. |
| `faker_utils.py` | `calc_hash(text)` | Lemmatizes and normalizes text into a stable key for direct mapping. |
| `faker_utils.py` | `validate_name(name)` | Checks that generated Russian name declensions hash consistently. |
| `names_morph.py` | `get_morphs(full_name)` | Produces Russian name forms for singular/plural cases via pytrovich/pymorphy3. |
| `addr_unifier.py` | `unify_address(raw)` | Uses libpostal parse/expand to build canonical address fields, hashes, and fuzzy keys. |
| `sentence_splitter.py` | `split_text(...)` and helpers | Splits long text by lines, Russian sentences, words, and long subwords for analyzer chunking. |

### Complete Module Method Inventory

This inventory names every Palimpsest-owned class/function method in the current
package. Detailed behavior for the central methods is described in the sections
above.

| Module | Class/function/methods |
| --- | --- |
| `palimpsest/__init__.py` | Re-exports `Palimpsest`, `PalimpsestSession`, `PalimpsestSessionError`, `SessionRequiredError`, `SessionStateError`. |
| `palimpsest/config.py` | Loads `gv.env` from the working directory or `~/.env/gv.env`; exposes provider/config constants such as `GIGA_CHAT_*`, `LANGCHAIN_*`, `OPENAI_API_KEY`, `YA_*`, `GEMINI_API_KEY`, `UPD_TIMEOUT`, `CRYPRO_KEY`, and `SECRET_APP_KEY`. |
| `palimpsest/logger_factory.py` | `ProjectFilter.__init__`, `ProjectFilter.filter`, `NotProjectFilter.__init__`, `NotProjectFilter.filter`, `setup_logging`. |
| `palimpsest/palimpsest.py` | `_length_factory`, nested `_len`, `_filter_dict`, `PalimpsestSessionError`, `SessionRequiredError`, `SessionStateError`, `_PalimpsestRuntime.__init__`, `_anon_operators`, `_deanon_operators`, `analyze`, `anonymize`, `deanonymize`, nested `deanonymize_item`, `_runtime_factory`, `_anonimizer_factory`, nested `analyze`, nested `anonimizer`, nested `deanonimizer`, `PalimpsestSession.__init__`, `closed`, `_ensure_open`, `_entries`, `_store_entries`, `anonymize`, `anonimize`, `deanonymize`, `deanonimize`, `reset`, `_reset_unlocked`, `close`, `Palimpsest.__init__`, `create_session`, `_require_session`, `_anonymize_session`, `_deanonymize_session`, `anonymize`, `anonimize`, `deanonymize`, `deanonimize`, `reset_context`, `debug_log`. |
| `palimpsest/analyzer_engine_provider.py` | `create_nlp_engine_with_transformers`, `create_nlp_engine_with_flair`, `create_nlp_engine_with_natasha`, `create_nlp_engine_with_gliner`, `nlp_engine_and_registry`, `analyzer_engine`, `get_supported_entities`. |
| `palimpsest/fakers/faker_context.py` | `FakerContext.__init__`, `reset`, `_generate_unique_fake`, `_faker_for_function`, `_call_fake_func`, `_wrap`, nested generic `wrapper`, `_wrap_phone`, nested phone `wrapper`, `phone_hash`, `_wrap_address`, nested address `wrapper`, `address_hash`, `address_fuzzy_key`, `defake`, `defake_phone`, `defake_address`, `defake_fuzzy`. |
| `palimpsest/fakers/faker_utils.py` | `get_nlp`, `normalize_phone`, `calc_hash`, nested `alnum`, nested `strip_vowels`, nested `normalyze_lemma`, `validate_name`, `validate_name_cusom`. |
| `palimpsest/fakers/fakers_funcs.py` | `fake_factory`, `bind_faker`, `reset_faker`, `current_faker`, `FakerProxy.__getattr__`, all fake generators listed in the fake generation table above. |
| `palimpsest/fakers/names_morph.py` | `get_morphs`. |
| `palimpsest/recognizers/gliner_recogniser.py` | `merge_spans`, `GlinerRecognizer.__init__`, `is_language_supported`, `analyze`, and example-only nested `length_factory`/`_len` under `if __name__ == "__main__"`. |
| `palimpsest/recognizers/natasha_recogniser.py` | `NatashaSlovnetRecognizer.__init__`, `is_language_supported`, `analyze`. |
| `palimpsest/recognizers/slovnet_recogniser.py` | `SlovnetRecognizer.__init__`, `is_language_supported`, `analyze`. |
| `palimpsest/recognizers/flair_recognizer.py` | `FlairRecognizer.__init__`, `load`, `get_supported_entities`, `analyze`, `_convert_to_recognizer_result`, `build_flair_explanation`, private static `__check_label`. |
| `palimpsest/recognizers/regex_recognisers.py` | Module recognizers `ru_internal_passport_recognizer`, `ru_phone_recognizer`, `ticket_number_recogniser`, `SNILSRecognizer.load`, `SNILSRecognizer.__init__`, `SNILSRecognizer.analyze`, `validate_inn`, nested `check_digits`, `INNRecognizer.load`, `INNRecognizer.__init__`, `INNRecognizer.analyze`, `RUBankAccountRecognizer.load`, `RUBankAccountRecognizer.__init__`, `RUBankAccountRecognizer.analyze`, `validate_card`, `RUCreditCardRecognizer.load`, `RUCreditCardRecognizer.__init__`, `RUCreditCardRecognizer.analyze`, `main`. |
| `palimpsest/utils/addr_unifier.py` | `UnifiedAddress` dataclass, `unify_address`. |
| `palimpsest/utils/sentence_splitter.py` | `split_long_word`, `split_long_sentence`, `preprocess_sentences`, `chunk_sentences`, `split_text_by_lines`, nested `flush_current`, `split_text`. |

## 4. Models And NLP Engines

### Default Runtime

The public `Palimpsest` constructor always creates `_PalimpsestRuntime`, which
currently hardcodes:

- Analyzer model family: `"gliner"`.
- GLiNER model id: `"gliner-community/gliner_large-v2.5"`.
- Tokenizer id: `"gliner-community/gliner_large-v2.5"`.
- spaCy NLP model for analyzer engine: `ru_core_news_lg`.
- spaCy NLP model for hashing/faker normalization: `ru_core_news_sm`.
- Device for GLiNER: `cuda` when `torch.cuda.is_available()`, otherwise `cpu`.

The GLiNER model is loaded with `GLiNER.from_pretrained(model_path)`. The
tokenizer is loaded with `AutoTokenizer.from_pretrained(...)`. These calls may
use local Hugging Face cache or network depending on the environment.

If GLiNER `.to(device)` fails, current accepted behavior is warning-only:
construction continues after logging a warning.

### Other Engine Families Available In Code

These are available through `analyzer_engine_provider.py`, but the public
`Palimpsest` runtime does not expose a constructor argument to select them.
Developers can use or wire them explicitly.

| Family selector | Builder | Model behavior |
| --- | --- | --- |
| Contains `"gliner"` | `create_nlp_engine_with_gliner` | Adds `GlinerRecognizer(model_path, run_entities)`, uses spaCy `ru_core_news_lg`. Default GLiNER model is `gliner-community/gliner_large-v2.5`. |
| Contains `"huggingface"` | `create_nlp_engine_with_transformers` | Uses Presidio transformers NLP engine with caller-provided `model_path`, spaCy `ru_core_news_lg`, and a label-to-Presidio map for names, addresses, locations, organizations, dates, phones, IDs, etc. |
| Contains `"flair"` | `create_nlp_engine_with_flair` | Uses `FlairRecognizer(model_path)` and spaCy `en_core_web_sm`. The recognizer class also has default `flair/ner-english-large` when constructed directly without `model_path`. |
| Contains `"natasha"` | `create_nlp_engine_with_natasha` | Uses `NatashaSlovnetRecognizer` with Natasha `NewsEmbedding`, `NewsMorphTagger`, `NewsSyntaxParser`, and `NewsNERTagger`; `model_path` is ignored. |

There is also a standalone `SlovnetRecognizer` in
`palimpsest/recognizers/slovnet_recogniser.py`. It is not registered in the
default analyzer. If used directly, it expects local files:

- `data/navec_news_v1_1B_250K_300d_100q.tar`
- `data/slovnet_ner_news_v1.tar`

### Presidio Built-ins

Each builder starts from Presidio's predefined recognizers. In practice this is
where common entities such as `EMAIL_ADDRESS`, `URL`, `IP_ADDRESS`, and some
standard `PHONE_NUMBER`/`CREDIT_CARD` detections can come from. Palimpsest then
adds custom recognizers on top.

## 5. Recognizers And Detection Specifics

### GLiNER Recognizer

File: `palimpsest/recognizers/gliner_recogniser.py`

Raw labels and mapped entities:

| GLiNER label | Palimpsest entity |
| --- | --- |
| `person` | `PERSON` |
| `person_name` | `PERSON` |
| `address` | `RU_ADDRESS` |
| `house_address` | `RU_ADDRESS` |
| `city` | `RU_CITY` |

Notes:

- `organization` and `organization_name` are commented out, so GLiNER currently
  does not map organizations to `RU_ORGANIZATION`.
- `run_entities` filters the label map at recognizer construction.
- `predict_entities(..., threshold=0.35, flat_ner=True, multi_label=False)` is
  used.
- Adjacent `RU_ADDRESS` spans separated only by whitespace, comma, semicolon,
  colon, or hyphen are merged.
- `is_language_supported()` returns `True`, even though Presidio registration
  uses supported language `"en"`.

### Natasha Recognizer

File: `palimpsest/recognizers/natasha_recogniser.py`

Natasha labels and mapped entities:

| Natasha label | Palimpsest entity |
| --- | --- |
| `PER` | `RU_PERSON` |
| `ORG` | `RU_ORGANIZATION` |
| `LOC` | Not mapped by current code |

Notes:

- Score is fixed at `0.9999`.
- Uses Natasha segmenter, embedding, morphology tagger, syntax parser, and NER
  tagger.
- Registered both when the Natasha engine family is selected and again by
  `analyzer_engine(...)` for all model families.

### Russian Passport

Entity: `RU_PASSPORT`

Recognizer: `ru_internal_passport_recognizer`

Patterns:

| Pattern meaning | Regex shape | Score |
| --- | --- | --- |
| 4 digits + separator + 6 digits | `\b\d{4}[- ]\d{6}\b` | `0.7` |
| 2 digits + separator + 2 digits + separator + 6 digits | `\b\d{2}[- ]\d{2}[- ]\d{6}\b` | `0.7` |
| 10 continuous digits | `\b\d{10}\b` | `0.3` |
| Loose 2+2+6 digits | `\b\d{2}[- ]?\d{2}[- ]?\d{6}\b` | `0.2` |
| Loose 4+6 digits | `\b\d{4}[- ]?\d{6}\b` | `0.2` |

There is no checksum validation.

### Phone Number

Entity: `PHONE_NUMBER`

Recognizer: `ru_phone_recognizer`, plus possible Presidio built-in phone
recognizers.

Patterns:

| Pattern meaning | Score |
| --- | --- |
| Required leading `+`, then 7-16-ish phone characters | `0.4` |
| Optional leading `+`, then 7-16-ish phone characters | `0.2` |

The regex is intentionally broad and can overlap with other numeric entities.
Restoration uses phone-specific normalization; details are in the
deanonymizer section.

### Ticket Number

Entity: `TICKET_NUMBER`

Recognizer: `ticket_number_recogniser`

- Regex: `\bIL\d{2}\-\d{9}\b`
- Score: `0.99`
- Operator: `keep`; ticket numbers are recognized but not anonymized or
  restored.

### SNILS

Entity: `SNILS`

Recognizer: `SNILSRecognizer`

- Regex accepts `123-456-789 00`, `12345678900`, and close variants.
- `petrovna.validate_snils(raw)` is used.
- Valid score: `0.999`.
- Invalid score: `0.0999` because the current accepted behavior is to return
  low-confidence invalid candidates instead of suppressing them.

### INN

Entity: `INN`

Recognizer: `INNRecognizer`

- Regex accepts 10- or 12-digit forms with optional separator after the first
  four digits.
- Uses local checksum validation logic in `validate_inn(...)`.
- Valid score: `0.999`.
- Invalid score: `0.0999`.

### Russian Bank Account

Entity: `RU_BANK_ACC`

Recognizer: `RUBankAccountRecognizer`

- Regex shape: 20 digits, optionally grouped as `5-3-1-4-3-4`.
- Score: `0.7`.
- No active checksum validation. This is an accepted limitation.

### Credit Card

Entity: `CREDIT_CARD`

Recognizer: `RUCreditCardRecognizer`, plus possible Presidio built-in card
recognizer.

- Supports card-like digit strings with optional space, dot, or hyphen
  separators.
- Custom regex covers lengths 12, 13, 14, 15, 16, 18, and 19. Length 17 is not
  covered by this custom regex.
- Uses Luhn validation.
- Valid score: `0.999`.
- Invalid score: `0.0999`.
- Tests cover valid Maestro length 12 and Diners Club length 14.
- Fake cards are generated as Visa 16-digit numbers.

### Flair Recognizer

File: `palimpsest/recognizers/flair_recognizer.py`

Available when explicitly used through the Flair engine family or directly.

| Flair label | Entity |
| --- | --- |
| `PER` | `PERSON` |
| `LOC` | `LOCATION` |
| `ORG` | `ORGANIZATION` |

Default direct model: `flair/ner-english-large`.

### Slovnet Recognizer

File: `palimpsest/recognizers/slovnet_recogniser.py`

Not part of the default runtime. If used directly:

| Slovnet label | Entity |
| --- | --- |
| `PER` | `PERSON` |
| `LOC` | `LOCATION` |
| `ORG` | `ORGANIZATION` |

It loads local Navec and Slovnet model archives from `data/`.

## 6. Entities Palimpsest Can Anonymize And Deanonymize

These are the entities with explicit anonymization/deanonymization operators in
`_PalimpsestRuntime`.

| Entity | Detection source | Anonymizer | Deanonymizer | Notes |
| --- | --- | --- | --- | --- |
| `RU_ORGANIZATION` | Natasha `ORG` | `ctx.fake_organization` | `ctx.defake_fuzzy` | GLiNER org mapping is currently disabled. |
| `RU_PERSON` | Natasha `PER` | `ctx.fake_name` | `ctx.defake_fuzzy` | Handles Russian person spans detected by Natasha. |
| `PERSON` | GLiNER person labels, built-ins, Flair if configured | `ctx.fake_name` | `ctx.defake_fuzzy` | Used for English and generic people. |
| `RU_ADDRESS` | GLiNER address labels | `ctx.fake_house` | `ctx.defake_address` | Requires libpostal for hash/fuzzy matching. |
| `CREDIT_CARD` | Custom card recognizer and built-ins | `ctx.fake_card` | `ctx.defake` | Fake is Visa 16. Restore is normalized direct hash. |
| `PHONE_NUMBER` | Custom phone recognizer and built-ins | `ctx.fake_phone` | `ctx.defake_phone` | Restore is direct phone-normalized lookup. |
| `IP_ADDRESS` | Presidio built-ins | `ctx.fake_ip` | `ctx.defake` | Fake is public IPv4. |
| `URL` | Presidio built-ins | `ctx.fake_url` | `ctx.defake_fuzzy` | Fuzzy restore tolerates small URL rewrites but can mis-select ambiguous values. |
| `EMAIL_ADDRESS` | Presidio built-ins | `ctx.fake_email` | `ctx.defake` | Integration test covers email round trip. |
| `RU_PASSPORT` | Custom regex | `ctx.fake_ru_passport` | `ctx.defake` | Fake format is `#### ######`. |
| `SNILS` | Custom regex + petrovna validation | `ctx.fake_snils` | `ctx.defake` | Invalid candidates may still be low-score detections. |
| `INN` | Custom regex + checksum | `ctx.fake_inn` | `ctx.defake` | Invalid candidates may still be low-score detections. |
| `RU_BANK_ACC` | Custom regex | `ctx.fake_ru_bank_account` | `ctx.defake` | No active checksum validation. |
| `Person` | Case variant | `ctx.fake_name` | `ctx.defake_fuzzy` | Kept for compatibility with alternate entity casing. |

Entities recognized but intentionally kept:

| Entity | Operator | Meaning |
| --- | --- | --- |
| `DEFAULT` | `keep` | Any entity without a more specific operator is left unchanged when this default operator is present. |
| `TICKET_NUMBER` | `keep` | Ticket numbers are detected but not anonymized. |
| `RU_CITY` | `keep` | Cities detected by GLiNER are left unchanged. |

Potentially recognized but not explicitly anonymized:

- `ORGANIZATION`, `LOCATION`, `DATE_TIME`, `AGE`, `ID`, `NRP`, and other
  Presidio or optional model outputs are not in the explicit operator map.
- If `run_entities` includes only unsupported or non-operator entities, they may
  be detected without the intended custom fake/restore behavior.

Use the exact operator entity names above for production `run_entities`.

## 7. Anonymization Flow

1. Consumer creates or retrieves a `PalimpsestSession`.
2. `session.anonymize(text)` delegates to the processor runtime.
3. `_PalimpsestRuntime.analyze(text)`:
   - Gets entity list from `run_entities` or all supported analyzer entities.
   - Splits text using `split_text(..., max_chunk_size=768, _len=tokenizer_len)`.
   - Runs `AnalyzerEngine.analyze(..., language="en")` on each chunk.
   - Offsets chunk-local spans into rebuilt final text.
   - Appends `"\n"` after each chunk in the analyzed text.
4. Presidio `AnonymizerEngine.anonymize(...)` applies `_anon_operators(ctx)`.
5. Each fake operator calls a `FakerContext.fake_*` wrapper.
6. `FakerContext` stores both true-to-fake and fake-to-true mapping entries.
7. `PalimpsestSession` stores Presidio engine items by fake text for later
   deanonymization.

Collision behavior:

- If a generated fake value already exists in the session, Palimpsest retries up
  to 10 times.
- If all attempts collide, `_generate_unique_fake` raises `ValueError`.

Special case:

- If a recognized value is exactly `"PII"`, fake wrappers return it unchanged.

## 8. Deanonymizers

Deanonymization is not a single algorithm. It depends on the entity operator.

### 8.1 Generic Direct Deanonymizer: `defake`

Used for:

- `CREDIT_CARD`
- `IP_ADDRESS`
- `EMAIL_ADDRESS`
- `RU_PASSPORT`
- `SNILS`
- `INN`
- `RU_BANK_ACC`

Algorithm:

1. If candidate fake text is `"PII"`, return `"PII"`.
2. Compute `calc_hash(fake)`.
3. Look up that hash in `ctx._faked`.
4. Return the stored true value when found.
5. Return the input fake value unchanged when not found.

`calc_hash` specifics:

- Loads spaCy `ru_core_news_sm`.
- Tokenizes text and uses token lemmas.
- Normalizes lemmas through `pymorphy3` to nominative, singular, masculine
  where possible.
- Removes punctuation by keeping alphanumeric characters and whitespace.

This is direct in the sense that a normalized hash must match one stored fake
entry. It is not cryptographic encryption, and it is not a fuzzy search.

### 8.2 Phone Deanonymizer: `defake_phone`

Used for:

- `PHONE_NUMBER`

Algorithm:

1. If candidate fake text is `"PII"`, return `"PII"`.
2. Compute `phone_hash(fake)`, which is `normalize_phone(fake)`.
3. Look up the normalized phone key in `ctx._faked`.
4. Return the stored true phone when found; otherwise return the input fake.

`normalize_phone` specifics:

- Extracts digits.
- Country code is normalized to 2 digits.
- City/area code is normalized to 3 digits.
- Local number is normalized to 7 digits.
- Output format is 12 digits: `CCAAALLLLLLL`.
- If no country/city can be inferred, defaults are country `"99"` and city
  `"999"`.
- Parenthesized area code is treated specially.
- The last 7 digits are treated as the local number.

Example behavior covered by tests:

- `+7 (495) 123-45-67` and `7 (495) 123-45-67` map to the same fake because
  they normalize to the same key.

Limitations:

- Different original formats that normalize to the same key collide by design.
- Ambiguous country/city extraction can map unrelated raw strings together.
- No fuzzy matching is used for phones; if an LLM rewrites the fake phone into a
  format that normalizes differently, restoration returns the rewritten fake.

### 8.3 Address Deanonymizer: `defake_address`

Used for:

- `RU_ADDRESS`

Address anonymization stores:

- A direct fake key: `address_hash(fake)`.
- A fuzzy key: `address_fuzzy_key(fake)`.
- The original true address.

`address_hash(value)` specifics:

- Calls `unify_address(value)`.
- Uses libpostal `parse_address`.
- Uses libpostal `expand_address`.
- Returns `UnifiedAddress.fuzzy_hash`, a SHA-256 hash of sorted expanded address
  variants.

`address_fuzzy_key(value)` specifics:

- Calls `unify_address(value)`.
- Returns sorted expanded address variants joined by newline.

Deanonymization algorithm:

1. If candidate fake text is `"PII"`, return `"PII"`.
2. Compute address fuzzy hash for the candidate.
3. If the hash exists in `ctx._faked`, return the stored true address.
4. Otherwise compute the candidate fuzzy key.
5. Compare it to stored fake fuzzy keys using
   `rapidfuzz.process.extractOne(..., scorer=fuzz.partial_ratio, score_cutoff=60)`.
6. Return the matched stored true address if a match exists.
7. Return the candidate fake text unchanged when there is no match.

Limitations:

- libpostal is required for both anonymization and deanonymization.
- Fuzzy fallback is best-match only; ambiguous address candidates do not raise.
- The cutoff is `60`, so moderately similar rewritten addresses may restore,
  but unrelated addresses can become risky if the session contains similar fake
  values.
- Address exception notes currently include the raw address value.

### 8.4 Fuzzy Deanonymizer: `defake_fuzzy`

Used for:

- `RU_ORGANIZATION`
- `RU_PERSON`
- `PERSON`
- `URL`
- `Person`

Algorithm:

1. If candidate fake text is `"PII"`, return `"PII"`.
2. Build a list of all fake values stored in `ctx._faked`, regardless of entity
   type.
3. Use `rapidfuzz.process.extractOne` with:
   - scorer: `fuzz.partial_token_sort_ratio`
   - score cutoff: `60`
4. If a match exists, return the true value at the matched index.
5. If no fuzzy match exists, fall back to `defake(fake)`.

Why this exists:

- LLMs often inflect, reorder, or slightly rewrite generated names,
  organizations, and URLs.
- Fuzzy matching can restore a value even when the model output is not an exact
  string copy of the fake.

Limitations:

- Matching is not scoped by entity type.
- Ambiguous matches choose the first/best match and do not raise.
- If two stored fakes are identical or very similar, restoration may pick the
  wrong original.
- A low cutoff of `60` increases tolerance but also increases collision risk.

### 8.5 Legacy Encrypt/Decrypt Path

`_PalimpsestRuntime.deanonymize(...)` contains `deanonymize_item(item)`, which
decrypts items whose Presidio operator is `"encrypt"` using `CRYPRO_KEY`.

Current anonymization uses custom fake operators, and the default encrypt
operator is commented out. For custom operators, `deanonymize_item(item)` returns
`item.text`, so the final replacement pass is effectively a no-op for custom
fake values. Restoration therefore depends primarily on re-analyzing fake values
in the model output and applying the correct `ctx.defake*` operator.

## 9. Entity-Specific Behavior

### Person And Russian Person

- Detected by GLiNER as `PERSON` and Natasha as `RU_PERSON`.
- Anonymized with `fake_name`.
- Generated fake is first name + last name.
- Name validation tries to ensure morphology-stable Russian declensions.
- If validation fails repeatedly, current accepted behavior returns the last
  generated name and logs `NON_CASHABLE`.
- Restored with `defake_fuzzy`.

Practical implication: person restoration can survive mild case/word-order
changes, but similar fake names in one session can restore incorrectly.

### Organization

- `RU_ORGANIZATION` is detected by Natasha `ORG`.
- GLiNER organization labels are currently commented out.
- Generated fake uses `Faker.company()`.
- Restored with `defake_fuzzy`.

Standard Presidio `ORGANIZATION` is not explicitly mapped to a custom operator
in the current runtime.

### Address

- `RU_ADDRESS` is detected by GLiNER labels `address` and `house_address`.
- Anonymized with `fake_house`, which generates a street address.
- Restore uses libpostal hash and fuzzy expansion, not plain string equality.
- `RU_CITY` is detected but kept; city-only values are not anonymized by the
  current operator table.

### Phone

- Detected by custom broad phone regex and possible built-ins.
- Anonymized with locale phone provider.
- Restore uses normalized 12-digit phone key.
- LLM-visible fake phone must remain parseable enough for the recognizer and
  normalizer.

### Email

- Detected by Presidio built-ins as `EMAIL_ADDRESS`.
- Fake uses `Faker.safe_email()`.
- Restore uses `defake`.
- Integration tests cover round trip.

### URL

- Detected by Presidio built-ins as `URL`.
- Fake uses `Faker.url()`.
- Restore uses `defake_fuzzy`, because LLMs often rewrite punctuation or URL
  token boundaries.
- Fuzzy URL restoration can be ambiguous if several fake URLs are similar.

### IP Address

- Detected by Presidio built-ins as `IP_ADDRESS`.
- Fake uses `Faker.ipv4_public()`.
- Restore uses `defake`.

### Passport, SNILS, INN, Bank Account, Card

- These are structured numeric values.
- Fake values are generated by Faker or simple patterns.
- Restore uses `defake`.
- Invalid SNILS, INN, and cards may still be returned as low-score recognizer
  results and can therefore be acted on depending on Presidio conflict and
  threshold behavior.

## 10. `run_entities` Configuration

Use `run_entities` to narrow detection and operator application:

```python
processor = Palimpsest(
    verbose=False,
    run_entities=[
        "RU_PERSON",
        "PERSON",
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "CREDIT_CARD",
    ],
)
```

Effects:

- GLiNER raw labels are filtered during recognizer construction.
- Analyzer calls receive the allow-list.
- Anonymization and deanonymization operator dictionaries are filtered to the
  same names.

Rules:

- Use exact entity strings from the operator table.
- Include both `RU_PERSON` and `PERSON` when text can contain both Russian and
  generic person detections.
- Include `EMAIL_ADDRESS` explicitly if email must be protected.
- Including `TICKET_NUMBER` or `RU_CITY` recognizes those entities but keeps
  them unchanged.
- `DEFAULT` is not retained when `run_entities` is set unless explicitly
  included, so avoid relying on default operator behavior for unknown entities.

## 11. Installation And Runtime Prerequisites

Current package metadata requires:

- Python `>=3.13`.
- `presidio_analyzer[transformers]`.
- `presidio_anonymizer`.
- `spacy`.
- `gliner`.
- `flair`.
- `natasha`.
- `faker`.
- `rapidfuzz`.
- `pymorphy3`, `pymorphy3-dicts-ru`.
- `petrovna`, `pytrovich`.
- `nltk`.
- `postal`/libpostal:
  - Windows AMD64 CPython 3.13 uses the repository wheel URL.
  - Linux uses `pypostal-multiarch`.
  - Other platforms need libpostal system libraries and compatible Python
    package installation.

Model/data prerequisites:

- spaCy `ru_core_news_lg` for analyzer setup.
- spaCy `ru_core_news_sm` for `calc_hash`.
- GLiNER model/cache for `gliner-community/gliner_large-v2.5`.
- Transformers tokenizer/cache for the same GLiNER model.
- NLTK Russian sentence/word tokenization data may be needed by
  `sentence_splitter`.
- Optional standalone Slovnet recognizer needs local `data/` archives.

Accepted startup behavior:

- If `ru_core_news_lg` is missing, analyzer setup may call
  `spacy.cli.download("ru_core_news_lg")`.
- This can require network access and mutate the local environment.

## 12. Logging And Privacy

Default behavior:

- `Palimpsest(verbose=False)` does not call `debug_log`.
- This is the safe default.

Verbose behavior:

- `Palimpsest(verbose=True)` logs raw input, anonymized output, analyzer spans,
  entity values, and true/fake mappings.
- This behavior is documented as accepted unsafe diagnostics.
- Do not enable it for production, shared logs, LangSmith/Langfuse traces, or
  support bundles containing real user data.

Consumer logging boundary:

- If you log before anonymization, logs contain raw PII.
- If you log after deanonymization, logs contain raw PII.
- Tool outputs can contain PII and must be anonymized before being added to a
  model-visible message or trace.

## 13. Limitations And Accepted Risks

Current limitations developers must account for:

- The public processor API requires explicit sessions; old code that calls
  `processor.anonimize(text)` without `session=` is incompatible with the
  current contract.
- Mappings are in-memory only and are lost on process restart, session reset, or
  close.
- There is no built-in persistence or serialization for `PalimpsestSession`.
- The final deanonymization replacement pass does not restore custom fake values
  if the analyzer misses the fake in model output.
- LLMs must preserve fake values enough for recognizers to detect them again.
- Fuzzy restoration is best-match and does not raise on ambiguous candidates.
- Fuzzy restoration is not entity-scoped.
- Phone restoration is normalization-based only, not fuzzy.
- Address restoration requires libpostal and can be expensive.
- Address fuzzy fallback uses cutoff `60` and can pick a wrong candidate in a
  crowded session.
- `RU_CITY` and `TICKET_NUMBER` are kept by design.
- Standard `ORGANIZATION`, `LOCATION`, and other Presidio entities do not have
  explicit custom fake operators unless mapped to a Palimpsest entity.
- GLiNER organization mapping is disabled.
- The analyzer language argument is hardcoded to `"en"` even for Russian text;
  custom recognizers opt into all languages.
- Chunking appends newline separators and may change whitespace.
- Entities split across chunk boundaries can be missed.
- Invalid SNILS, INN, and card candidates may be returned with low scores.
- Russian bank accounts have no active checksum validation.
- Phone regex is broad and can overlap with other numeric entities.
- Startup can download spaCy models.
- GLiNER device transfer failure logs a warning and continues.
- `verbose=True` logs raw PII by design.
- `CRYPRO_KEY`/encrypt support is present only as a legacy/deactivated path;
  current anonymization is fake-value replacement, not encryption.
- Constructor loads heavy models; creating many processors is expensive.

## 14. LangGraph Integration

The reference implementation is in:

- `C:\Projects\bot_platform\agents\sd_ass_agent\agent.py`
- `C:\Projects\bot_platform\agents\sd_ass_agent\tools\tools.py`

That code shows the intended privacy boundary:

- A `create_agent(..., middleware=middleware)` call wraps model requests.
- Middleware copies each `BaseMessage`.
- Text-like fields inside message content parts are anonymized before the model
  receives them.
- Final AI responses are deanonymized before returning to the user.
- Tool functions can anonymize tool results before those results re-enter the
  model context.

However, the reference code uses the old processor-level API shape:

```python
anonymizer = Palimpsest(verbose=False, run_entities=anon_entities)
anonymizer.anonimize(text)
anonymizer.deanonimize(text)
```

With the current library, adapt this to a session-scoped wrapper.

### Recommended LangGraph Pattern

1. Build one processor at agent startup.
2. Create one Palimpsest session per LangGraph `thread_id`.
3. Use the same session for user messages, tool outputs, sub-agents, validators,
   web-search agents, and final response deanonymization.
4. Reset or close the session when the LangGraph memory thread is reset.
5. Avoid raw before/after anonymization logs.

Example adapter:

```python
from copy import copy
from threading import RLock
from typing import Any

from langchain_core.messages import BaseMessage
from palimpsest import Palimpsest, PalimpsestSession


ANON_ENTITIES = [
    "RU_PERSON",
    "PERSON",
    "RU_ADDRESS",
    "CREDIT_CARD",
    "PHONE_NUMBER",
    "IP_ADDRESS",
    "URL",
    "EMAIL_ADDRESS",
    "RU_PASSPORT",
    "SNILS",
    "INN",
    "RU_BANK_ACC",
]

processor = Palimpsest(
    verbose=False,
    run_entities=ANON_ENTITIES,
    locale="ru-RU",
)

_sessions: dict[str, PalimpsestSession] = {}
_sessions_lock = RLock()


def palimpsest_session_for_thread(thread_id: str) -> PalimpsestSession:
    with _sessions_lock:
        session = _sessions.get(thread_id)
        if session is None or session.closed:
            session = processor.create_session(session_id=thread_id)
            _sessions[thread_id] = session
        return session


def reset_palimpsest_thread(thread_id: str) -> None:
    with _sessions_lock:
        session = _sessions.pop(thread_id, None)
    if session is not None:
        session.close()


class SessionScopedAnonymizer:
    def __init__(self, session: PalimpsestSession):
        self._session = session

    def anonymize(self, text: str) -> str:
        return self._session.anonymize(text)

    def anonimize(self, text: str) -> str:
        return self.anonymize(text)

    def deanonymize(self, text: str | None = None) -> str:
        return self._session.deanonymize(text)

    def deanonimize(self, text: str | None = None) -> str:
        return self.deanonymize(text)
```

Content-part anonymization, adapted from `sd_ass_agent.agent`:

```python
TEXT_PART_KEYS = (
    "text",
    "content",
    "input",
    "title",
    "caption",
    "markdown",
    "explanation",
)


def anonymize_message_content(content: Any, anonymizer: SessionScopedAnonymizer) -> Any:
    if isinstance(content, str):
        return anonymizer.anonymize(content)

    if isinstance(content, list):
        out = []
        for part in content:
            if not isinstance(part, dict):
                out.append(part)
                continue

            copied = dict(part)
            for key in TEXT_PART_KEYS:
                if isinstance(copied.get(key), str):
                    copied[key] = anonymizer.anonymize(copied[key])
            out.append(copied)
        return out

    return content
```

Middleware shape matching the local reference code:

```python
class SDAgentAnonymizationMiddleware:
    def modify_model_request(self, request, state):
        thread_id = state.get("thread_id") or state.get("palimpsest_session_id")
        if not thread_id:
            raise ValueError("Missing thread id for Palimpsest session")

        anonymizer = SessionScopedAnonymizer(
            palimpsest_session_for_thread(str(thread_id))
        )

        anon_messages: list[BaseMessage] = []
        for message in request.messages:
            anon_message = copy(message)
            anon_message.content = anonymize_message_content(
                message.content,
                anonymizer,
            )
            anon_messages.append(anon_message)

        request.messages = anon_messages
        return request
```

If your LangGraph/LangChain middleware API exposes `config`, prefer reading:

```python
thread_id = config["configurable"]["thread_id"]
```

If it does not, put the thread id into graph state before the agent node calls
the model.

Final response deanonymization:

```python
def deanonymize_last_ai_message(state):
    thread_id = state["thread_id"]
    anonymizer = SessionScopedAnonymizer(
        palimpsest_session_for_thread(str(thread_id))
    )

    messages = list(state["messages"])
    last = messages[-1]
    if last.type == "ai" and not getattr(last, "tool_calls", None):
        restored = copy(last)
        if isinstance(restored.content, str):
            restored.content = anonymizer.deanonymize(restored.content)
        messages[-1] = restored

    return {"messages": messages}
```

Reset integration:

```python
def reset_memory(state):
    thread_id = state.get("thread_id")
    if thread_id:
        reset_palimpsest_thread(str(thread_id))

    # Continue with normal LangGraph message removal.
    ...
```

Tool output integration, based on `sd_ass_agent.tools.tools`:

```python
def protect_tool_result(result: str, thread_id: str) -> str:
    anonymizer = SessionScopedAnonymizer(
        palimpsest_session_for_thread(thread_id)
    )
    return anonymizer.anonymize(result)
```

Pass a session-scoped anonymizer to tool factories when tool results can contain
PII. In the reference `tools.py`, the factory accepts `anonymizer` but
`agent.py` currently calls `get_term_and_defition_tools()` without passing one.
For strict privacy, pass the same thread/session wrapper into any tool whose
output is added to model-visible messages.

### LangGraph Privacy Notes

- Middleware protects the model request, but graph state/checkpointers may still
  store raw user messages if anonymization happens only at the model boundary.
  For strongest privacy, anonymize at ingress before adding messages to durable
  graph state.
- Callback handlers such as file tracers, LangSmith, and Langfuse can observe
  raw graph state depending on where they are attached. Confirm they see only
  anonymized payloads or disable raw input/output tracing.
- Multi-agent graphs must share the same Palimpsest session for all model calls
  in one user thread. Separate sessions break restoration.
- Streaming responses should be deanonymized after a complete AI message is
  assembled. Chunk-level deanonymization can fail if fake values are split.
- Do not log `BEFORE ANONIMIZATION` with raw content as the reference agent
  currently does for local debugging.

## 15. Extension Guidance

When adding a new entity:

1. Add or configure a recognizer that emits a stable entity name.
2. Add a fake generator in `fakers_funcs.py` if none exists.
3. Ensure `FakerContext` wrapper type matches the entity:
   - generic normalized direct mapping,
   - phone-normalized mapping,
   - address/libpostal mapping,
   - or a new specialized mapping.
4. Add the entity to `_anon_operators`.
5. Add the entity to `_deanon_operators`.
6. Add deterministic unit tests for:
   - recognizer valid span,
   - invalid or low-score behavior,
   - `run_entities` filtering,
   - anonymize/deanonymize round trip,
   - session isolation,
   - collision handling if fake generation can collide.
7. Update this guide and the accepted findings if the behavior is intentionally
   non-fail-fast or fuzzy.

When adding a new model family:

1. Keep model path, language, threshold, and local/download behavior explicit.
2. Ensure labels map to operator entity names exactly.
3. Add tests that fail on label drift.
4. Avoid carrying user-specific mapping state in shared model objects.

## 16. Quick Reference

Safe default setup:

```python
processor = Palimpsest(
    verbose=False,
    run_entities=[
        "RU_PERSON",
        "PERSON",
        "RU_ADDRESS",
        "RU_ORGANIZATION",
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "CREDIT_CARD",
        "IP_ADDRESS",
        "URL",
        "RU_PASSPORT",
        "SNILS",
        "INN",
        "RU_BANK_ACC",
    ],
)
session = processor.create_session(session_id="thread-or-request-id")
```

Round trip:

```python
protected_text = session.anonymize(raw_text)
model_output = llm.invoke(protected_text)
restored_output = session.deanonymize(model_output)
```

Do not do this with current API:

```python
processor = Palimpsest()
processor.anonimize(raw_text)  # Raises SessionRequiredError.
```

Do this instead:

```python
processor = Palimpsest()
session = processor.create_session()
session.anonimize(raw_text)
```
