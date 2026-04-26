# Palimpsest Codebase Review Findings

Review date: 2026-04-26

Scope:
- `C:\Projects\PalimpsestLib`
- Usage example in `C:\Projects\bot_platform\agents\sd_ass_agent`

## Findings

### 1. [P0] Shared anonymizer state can leak across users

Location: `palimpsest/palimpsest.py:163`

`Palimpsest` stores mappings and last anonymization results on one mutable instance, while `sd_ass_agent` creates a single `Palimpsest` and reuses it in middleware. In a long-running bot this can mix contexts across threads/users and deanonimize with another user's mapping.

Why change it:
- The library is intended to protect PII, but shared mutable mapping state can expose one user's original values in another user's response.
- The consumer code uses the library as middleware in a long-lived agent, so this is a production-facing design risk.

Recommended change:
- Make anonymization return a per-request/session mapping object and pass that explicitly to `deanonimize`, or create one isolated `Palimpsest` per conversation.
- Separate heavyweight analyzer/model cache from per-session anonymization state.

### 2. [P0] Sensitive data is written to plaintext logs

Location: `palimpsest/palimpsest.py:196`

`debug_log` records raw input, anonymized output, entity values, and true/fake mapping pairs. `sd_ass_agent` also writes before/after anonymization and deanonimization content to `./logs`.

Why change it:
- Logging original PII defeats the purpose of a privacy/anonymization library.
- Log files are durable, often copied to support systems, and may have broader access than application memory.

Recommended change:
- Replace raw PII logs with redacted structured diagnostics.
- Require an explicit unsafe debug flag for any raw-value logging.
- In the consumer, remove `BEFORE ANONIMIZATION` and `AFTER DEANONIMIZATION` raw content logs or gate them behind a local-only development mode.

### 3. [P1] Entity allow-list does not actually constrain analysis

Location: `palimpsest/palimpsest.py:44`

`run_entities` filters the operator dictionaries, but `analyze` still defaults to `analyzer.get_supported_entities() + RU_ENTITIES`, and `analyzer_engine` adds recognizers unconditionally. A detected entity outside `run_entities` can be processed by Presidio defaults or become non-restorable.

Why change it:
- Callers expect `run_entities` to define the behavioral surface.
- Partial filtering makes output harder to reason about and can corrupt data when a detected entity lacks a matching reversible operator.

Recommended change:
- Use the allow-list consistently for recognizer registration, `analyze(..., entities=...)`, and operator selection.
- Keep `DEFAULT` behavior explicit when filtering operators.
- Add tests proving excluded entities remain untouched.

### 4. [P1] Runtime startup depends on heavyweight downloads and local caches

Location: `palimpsest/palimpsest.py:41`

`Palimpsest` construction hardcodes GLiNER and tokenizer loading. GLiNER is loaded with `local_files_only=True`, while the tokenizer is not. spaCy models are downloaded at runtime, and the code checks `ru_core_news_sm` but configures `ru_core_news_lg`.

Why change it:
- Startup can be slow and brittle in offline, CI, or server environments.
- Runtime downloads are hard to secure, cache, and reproduce.
- The current model-name mismatch makes deployment requirements unclear.

Recommended change:
- Inject model configuration.
- Validate required local models at startup with clear errors.
- Remove runtime `spacy.cli.download` from library code.
- Cache analyzer engines separately from request/conversation state.

### 5. [P1] Organization recognizer label typo prevents configured handling

Location: `palimpsest/recognizers/natasha_recogniser.py:50`

Natasha maps `ORG` to `RU ORGANIZATION` with a space, but the supported entity and operators use `RU_ORGANIZATION`. Organization detections therefore will not match the anonymization/deanonimization operators as intended.

Why change it:
- Organization anonymization is configured but can silently fail for Natasha results.
- Silent entity-label mismatches are difficult to diagnose from output alone.

Recommended change:
- Change the label to `RU_ORGANIZATION`.
- Add a recognizer unit test for Natasha organization mapping.

### 6. [P1] Invalid IDs and cards are still returned as detections

Location: `palimpsest/recognizers/regex_recognisers.py:103`

SNILS, INN, and credit-card recognizers only reduce score when checksum validation fails, then still return the result. Combined with broad phone/passport numeric regexes, this can anonymize unrelated numbers and corrupt text.

Why change it:
- False positives are destructive in an anonymizer because replacement changes user content.
- Low confidence does not guarantee a result will be ignored by the analyzer pipeline.

Recommended change:
- Skip invalid checksum matches by default.
- If low-score invalid matches are intentionally retained, add tests proving they cannot pass configured analyzer thresholds.
- Tighten broad numeric patterns or add context requirements.

### 7. [P1] Deanonimization uses global string replacement

Location: `palimpsest/palimpsest.py:143`

`deanonimizer` re-analyzes the model output, then replaces every occurrence of each fake string with the original. This is order-sensitive and can replace unrelated text if the fake token appears elsewhere, especially with fuzzy matching.

Why change it:
- Global replacement is not span-aware and can mutate non-PII text.
- Re-analysis of LLM output makes restoration depend on recognition quality after the text has already changed.

Recommended change:
- Prefer placeholder tokens with stable IDs, or span-aware replacement against the exact mapping generated by anonymization.
- Keep restoration deterministic and tied to explicit anonymization entries.

### 8. [P2] Tests do not currently protect the library

Location: `tests/test_palimpsest.py:67`

Several tests call real LLM code, `test_complex_text_processing` reads ignored `./data` files, and assertions such as `assert deanon != _TEXT` and the OR-heavy fakers assertion do not verify the intended behavior.

Why change it:
- The suite is not deterministic enough for CI.
- Some assertions can pass while the intended behavior is broken.
- Integration tests that require LLMs, local models, and ignored data hide regressions.

Recommended change:
- Split unit tests from integration tests.
- Mock analyzers and LLM calls in unit tests.
- Seed Faker where deterministic output matters.
- Add deterministic tests for round-trip restoration, false positives, allow-list behavior, and recognizer label mappings.

## Additional Improvement Areas

### Packaging and repository hygiene

Issues:
- `pyproject.toml` and `setup.cfg` duplicate dependency metadata.
- `Palimpsest.egg-info` is tracked.
- The stray tracked file `et --soft 8f29b9a` appears to be accidental command output.
- The Windows `postal` wheel is tracked in the repository.
- The direct dependency URL points to `raw.githubusercontent.com/.../main/...whl`, which is mutable and fragile.

Why change it:
- Duplicate metadata drifts over time.
- Generated artifacts and accidental files make releases noisy and less trustworthy.
- Mutable dependency URLs reduce reproducibility.

Recommended change:
- Keep package metadata in `pyproject.toml` only.
- Remove generated artifacts from source control.
- Publish platform wheels through a package index or release artifact with pinned hashes.

### Optional address dependency

Issue:
- Importing `FakerContext` imports `postal` immediately through `addr_unifier`, so even non-address use requires libpostal.

Why change it:
- libpostal is the hardest dependency to install and should not block non-address anonymization.

Recommended change:
- Make address support an optional extra and lazy-load `postal` only when address anonymization is enabled or used.

### Public API naming

Issue:
- Public methods use `anonimize` and `deanonimize`.

Why change it:
- Misspelled public APIs become harder to change after adoption.

Recommended change:
- Add correctly spelled aliases, for example `anonymize` and `deanonymize`, while keeping the old names as backward-compatible wrappers.

### Configuration side effects

Issue:
- Library import loads broad application secrets from `gv.env` or a home-directory env file via `config.py`.

Why change it:
- Library imports should not load unrelated provider credentials or mutate configuration implicitly.

Recommended change:
- Keep library configuration narrow and explicit.
- Move app-specific provider secrets to sample or consumer code.

### Consumer integration gap

Issue:
- `sd_ass_agent` calls `get_term_and_defition_tools()` without passing the anonymizer, so tool outputs can be stored or traced raw before middleware prepares model requests.

Why change it:
- Tool results may contain sensitive data and should follow the same privacy policy as user messages.

Recommended change:
- Pass the anonymizer into tool factories where tool outputs may contain sensitive content, or enforce anonymization at a single boundary before tracing/model calls.

## Verification Notes

Verification was limited by the local environment:

- `python -m compileall palimpsest tests test.py` completed syntax compilation.
- `uv run` hit an access-denied uv cache path.
- `pytest --collect-only` through `uv run` imported an unrelated installed `palimpsest` package.
- The root `.venv` could not read `presidio_analyzer`.
- The nested `palimpsest\.venv` could import this checkout but did not have `pytest` installed.

Why change it:
- Reproducibility gaps make it difficult to trust future fixes.

Recommended change:
- Add a clean, documented test environment setup.
- Ensure the local checkout wins import resolution in tests.
- Add CI that runs deterministic unit tests without external LLM calls or runtime model downloads.
