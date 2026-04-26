# Palimpsest Test Report

Date: 2026-04-26

Workspace: `C:\Projects\PalimpsestLib`

Report type: contract test execution report after session-based state
isolation implementation.

## Executive Summary

The Palimpsest contract suite was executed with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

- Total tests collected: 39
- Passed: 27
- Failed: 12
- Skipped: 0
- Collection errors: 0
- Duration: 63.25 seconds

The session-isolation refactor is covered and passing. The remaining failures
are unrelated contract gaps: fail-fast exception notes/rethrows, runtime
download fallback, fuzzy-restoration ambiguity, privacy logging, Natasha label
mapping, and invalid checksum detections.

## Scope

The suite is an executable specification for the desired Palimpsest behavior:

- No workarounds.
- No silent fallbacks.
- Third-party failures raise immediately and preserve original exception data.
- Palimpsest context is added with `exc.add_note(...)` where useful.
- Normal logs do not contain raw PII, fake values, prompts, model responses, or
  true/fake mappings.
- Reversible anonymization state is isolated per explicit session.
- Recognizers produce correct labels, spans, scores, checksums, and allow-list
  behavior.
- Consumer behavior modeled after `bot_platform/agents/sd_ass_agent` keeps text
  protected at model/tool boundaries.

## Environment

| Item | Value |
| --- | --- |
| OS/platform | Windows / `win32` |
| Workspace | `C:\Projects\PalimpsestLib` |
| Python executable | `C:\Projects\PalimpsestLib\.venv\Scripts\python.exe` |
| Python version | `3.13.7` |
| pytest version | `9.0.3` |
| pytest config | `pytest.ini` |
| pytest rootdir | `C:\Projects\PalimpsestLib` |
| E2E API key source | `palimpsest/gv.env`, key `OPENAI_API_KEY` |
| E2E OpenAI model | `gpt-4.1-nano` |

The first sandboxed pytest run failed while importing a native dependency:
`ImportError: DLL load failed while importing cy: Access is denied.` The same
tests were rerun outside the sandbox using the requested `.venv` environment.

## Commands Executed

```powershell
.\.venv\Scripts\python.exe -m py_compile palimpsest\palimpsest.py palimpsest\__init__.py test.py tests\conftest.py tests\unit\test_public_api_contract.py tests\unit\test_consumer_contract.py tests\integration\test_real_palimpsest_pipeline.py tests\e2e\test_llm_roundtrip.py
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q tests\unit\test_public_api_contract.py tests\unit\test_consumer_contract.py
.\.venv\Scripts\python.exe -m pytest -q
```

| Command | Result |
| --- | --- |
| `py_compile` over changed files | Passed |
| `pytest --collect-only -q` | 39 tests collected |
| Focused public API + consumer contract tests | 12 passed, 7 warnings |
| Full suite | 12 failed, 27 passed, 9 warnings |

## Test Data

| Name | Value | Purpose |
| --- | --- | --- |
| `SAMPLE_PERSON` | `John Doe` | Synthetic person PII for API, privacy, integration, and e2e scenarios. |
| `SAMPLE_PHONE` | `+1 (202) 555-0182` | Synthetic phone PII. |
| `SAMPLE_CARD` | `4111111111111111` | Synthetic valid Luhn card for privacy/e2e flow. |
| `SAMPLE_TEXT` | `Client John Doe will use 4111111111111111. Call +1 (202) 555-0182.` | English integration text with no exact entity-name prefix before card. |
| `SAMPLE_RU_TEXT` | Russian natural sentence containing `Ivan Ivanov` and `+7 (495) 123-45-67`. | Russian integration text. |
| Address fixture | `221B Baker Street, London NW1` | libpostal address unification. |
| Invalid SNILS | `112-233-445 96` | Checksum-negative recognizer case. |
| Valid SNILS | Natural Russian sentence containing `112-233-445 95`. | Checksum-positive recognizer case without exact entity-name prefix. |
| Invalid INN | `7707083895` | Checksum-negative recognizer case. |
| Valid INN | Natural Russian sentence containing `7707083893`. | Checksum-positive recognizer case without exact entity-name prefix. |
| Invalid card | `4000000000000003` | Luhn-negative recognizer case. |
| Valid card | Natural Russian sentence containing `4000000000000002`. | Luhn-positive recognizer case without exact entity-name prefix. |
| E2E fake name | `Jane Smith` | Deterministic fake value for live LLM test. |
| E2E fake phone | `+1 (303) 555-0199` | Deterministic fake value for live LLM test. |
| E2E fake card | `4000000000000002` | Deterministic fake value for live LLM test. |

## Result By Layer

| Layer | Tests | Passed | Failed | Result |
| --- | ---: | ---: | ---: | --- |
| E2E | 1 | 1 | 0 | Passed |
| Integration | 5 | 4 | 1 | Failed |
| Unit: consumer contract | 4 | 4 | 0 | Passed |
| Unit: fail-fast | 3 | 0 | 3 | Failed |
| Unit: faker/context | 6 | 4 | 2 | Failed |
| Unit: privacy/logging | 2 | 0 | 2 | Failed |
| Unit: public API/session | 8 | 8 | 0 | Passed |
| Unit: recognizers | 10 | 6 | 4 | Failed |

## Scenario Matrix

### E2E

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| E2E-001 | Live anonymize -> OpenAI -> deanonymize round trip. Confirms raw PII is not sent to the model and mapped values are restored. | `Client John Doe can be reached at +1 (202) 555-0182. Payment value: 4111111111111111.` Session id `e2e-openai-roundtrip`. Model `gpt-4.1-nano`. | Serialized model request excludes `John Doe`, `+1 (202) 555-0182`, and `4111111111111111`. Restored response contains all three originals. | Test passed. Raw synthetic PII was absent from the request and restored response contained original values. | PASS |

### Integration

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| INT-001 | Construct real processor without runtime downloads. | `Palimpsest(run_entities=[PERSON, RU_PERSON, PHONE_NUMBER, CREDIT_CARD, RU_PASSPORT, SNILS, INN, RU_BANK_ACC])`; `spacy.cli.download` monkeypatched to fail if called. | Constructor completes and no download is attempted. | Constructor returned a processor. | PASS |
| INT-002 | Real English session round trip. | Explicit session `integration-english`; `SAMPLE_TEXT`. | Anonymized text removes person/card; deanonymized text restores them. | Assertions passed. | PASS |
| INT-003 | Real Russian session round trip. | Explicit session `integration-russian`; Russian sample with `Ivan Ivanov` and phone. | Anonymized text removes Russian person; deanonymized text restores it. | Assertions passed. | PASS |
| INT-004 | Missing GLiNER model must rethrow original dependency exception with Palimpsest context notes. | `GlinerRecognizer(model_path="__missing_gliner_model__")`. | Original exception type, not `RuntimeError`; notes include model path and `recognizer_init`. | Original dependency exception was raised, but `__notes__` was empty. | FAIL |
| INT-005 | libpostal address support is available. | `221B Baker Street, London NW1`. | Unified address contains raw value, fuzzy hash, and fuzzy keys. | Assertions passed. | PASS |

### Unit: Public API And Session State

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| API-001 | Package import exports processor and session types. | `from palimpsest import Palimpsest, PalimpsestSession`. | Both names import. | Assertions passed. | PASS |
| API-002 | Processor methods require explicit session. | `processor.anonimize("secret")`, `processor.deanonimize("secret")`. | `SessionRequiredError`. | Assertions passed. | PASS |
| API-003 | Session misspelled compatibility methods round-trip. | `session.anonimize("secret")`, then `session.deanonimize(fake)`. | Returns fake then restores `secret`. | Assertions passed. | PASS |
| API-004 | Correct session aliases round-trip. | `session.anonymize("secret")`, then `session.deanonymize(fake)`. | Returns fake then restores `secret`. | Assertions passed. | PASS |
| API-005 | Processor delegators require matching session. | `processor.anonymize("secret", session=session)` and same session for restore; foreign processor with same session. | Matching session works; foreign processor raises `SessionStateError`. | Assertions passed. | PASS |
| API-006 | Unsupported input raises. | `session.anonimize(None)`. | `TypeError`. | Assertions passed. | PASS |
| API-007 | Deanonymize before mapping raises. | New session, `session.deanonimize("FAKE_VALUE_1")`. | `SessionStateError`. | Assertions passed. | PASS |
| API-008 | Reset and close enforce lifetime. | Anonymize, `session.reset()`, restore old fake; then `session.close()` and anonymize again. | Reset clears mapping; close rejects further calls. | Assertions passed. | PASS |

### Unit: Consumer Contract

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| CON-001 | sd-ass-agent-like middleware anonymizes text fields before model boundary. | Multi-part message with `user John Doe`, `tool John Doe`, and `title John Doe`. | All text parts replaced; `John Doe` absent. | Calls recorded all three source strings; output contains anonymized values. | PASS |
| CON-002 | Tool output uses same anonymization boundary. | `Tool result contains John Doe`. | Protected output equals `ANON::1`. | Assertion passed. | PASS |
| CON-003 | Two sessions from one processor cannot restore each other's fake values. | User one session anonymizes `user-one secret`; user two session anonymizes `user-two secret`; user two attempts restore of user one fake. | User two restore raises; user one restore succeeds. | Assertions passed. | PASS |
| CON-004 | One session keeps mappings across multiple turns. | Same session anonymizes `first secret` and `second secret`. | Both fakes restore in that session. | Assertions passed. | PASS |

### Unit: Fail-Fast Behavior

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| FF-001 | Tokenizer load failure preserves original exception and context notes. | Monkeypatched `AutoTokenizer.from_pretrained` raises `TokenizerLoadError("transformers tokenizer payload")`. | `TokenizerLoadError`; notes include operation, tokenizer, and model id. | Original type raised, but notes were empty. | FAIL |
| FF-002 | GLiNER device move failure is not swallowed. | Fake model `.to("cpu")` raises `DeviceMoveError("device unavailable: cpu")`. | `DeviceMoveError` raised with context notes. | No exception raised; warning logged: `Could not move GLiNER model to device cpu`. | FAIL |
| FF-003 | Missing spaCy package does not trigger runtime download fallback. | `spacy.util.is_package` returns `False`; download function records calls. | Dependency failure raises without calling download. | Download attempted for `ru_core_news_sm`. | FAIL |

### Unit: Faker Context

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| FK-001 | Repeated true value returns same fake. | `ctx.fake_account("account-1")` twice. | Same fake both times. | Assertions passed. | PASS |
| FK-002 | Fake value restores only within same context. | `ctx1.fake_account("account-1")`, then restore in `ctx1` and `ctx2`. | `ctx1` restores; `ctx2` does not. | Assertions passed. | PASS |
| FK-003 | Ambiguous fuzzy restoration raises with diagnostics. | Two `_faked` entries share fake value `same fake`. | Exception containing candidate diagnostics. | No exception raised. | FAIL |
| FK-004 | Phone normalization is deterministic. | `+7 (495) 123-45-67` and `7 (495) 123-45-67`. | Same fake phone. | Assertions passed. | PASS |
| FK-005 | Address mapping uses unified hash and restores. | `Original Street 1`. | Repeated fake is stable and defake restores original. | Assertions passed. | PASS |
| FK-006 | Address dependency failure preserves original exception with notes. | Monkeypatched `unify_address` raises `LibpostalFailure("libpostal parser payload")`. | `LibpostalFailure`; notes include address/libpostal context. | Original type raised, but notes were empty. | FAIL |

### Unit: Privacy And Logging

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| PRIV-001 | Normal verbose/debug logs do not leak raw PII or mappings. | Input contains `John Doe`, `+1 (202) 555-0182`, `4111111111111111`; fake output and true/fake mapping are supplied to `debug_log`. | Captured logs contain none of the raw or fake values. | Captured logs included raw input, fake output, entry values, and mapping true/fake values. | FAIL |
| PRIV-002 | Unsafe raw debug mode is explicit and off by default. | `inspect.signature(Palimpsest)`. | Signature has `unsafe_debug_raw_values=False`. | Signature has only `verbose`, `run_entities`, and `locale`. | FAIL |

### Unit: Recognizers

| ID | Scenario | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- | --- |
| REC-001 | Natasha `ORG` maps to `RU_ORGANIZATION`. | Fake Natasha `ORG` span over `Acme`, requested entities `["RU_ORGANIZATION"]`. | One result with entity `RU_ORGANIZATION`, span `0..4`. | No result returned. | FAIL |
| REC-002 | Invalid SNILS checksum is rejected. | `112-233-445 96`. | Empty detection list. | Returned `SNILS` result, score `0.0999`. | FAIL |
| REC-003 | Invalid INN checksum is rejected. | `7707083895`. | Empty detection list. | Returned `INN` result, score `0.0999`. | FAIL |
| REC-004 | Invalid credit-card checksum is rejected. | `4000000000000003`. | Empty detection list. | Returned `CREDIT_CARD` result, score `0.0999`. | FAIL |
| REC-005 | Valid SNILS in natural text is detected with span and score. | Natural Russian sentence containing `112-233-445 95`. | One `SNILS` result, score at least `0.99`, exact span text. | Assertions passed. | PASS |
| REC-006 | Valid INN in natural text is detected with span and score. | Natural Russian sentence containing `7707083893`. | One `INN` result, score at least `0.99`, exact span text. | Assertions passed. | PASS |
| REC-007 | Valid card in natural text is detected with span and score. | Natural Russian sentence containing `4000000000000002`. | One `CREDIT_CARD` result, score at least `0.99`, exact span text. | Assertions passed. | PASS |
| REC-008 | Recognizer allow-list excludes unrequested entities. | SNILS recognizer over valid SNILS text with entities `["INN"]`. | Empty result list. | Assertion passed. | PASS |
| REC-009 | Top-level analyzer allow-list is passed to analysis. | `run_entities=["PERSON"]`; fake analyzer supports `PERSON` and `EMAIL_ADDRESS`. | Analyzer receives only `["PERSON"]`. | Assertion passed after session refactor runtime change. | PASS |
| REC-010 | Chunk offset correction preserves original spans. | Split chunks `Alice` and `Bob`; fake recognizer returns local spans. | Final text `Alice\nBob\n`; extracted spans `Alice` and `Bob`. | Assertion passed. | PASS |

## Failure Analysis

### F1: Missing exception notes on original dependency failures

Affected tests: INT-004, FF-001, FK-006.

The original exception type is preserved, but the exception has no
`__notes__`. This means clients receive the third-party payload but do not
receive operation-specific Palimpsest context such as model id, path, tokenizer,
address/libpostal operation, or recognizer initialization.

### F2: Swallowed exceptions and runtime fallback

Affected tests: FF-002, FF-003.

GLiNER device move failure is logged and execution continues. Missing spaCy
package triggers a runtime download attempt. Both violate the explicit
no-workaround/no-fallback policy.

### F3: Privacy logging leaks data

Affected tests: PRIV-001, PRIV-002.

`debug_log` writes raw input, anonymized output, fake entity values, and
true/fake mappings. There is no explicit unsafe opt-in parameter protecting raw
diagnostics.

### F4: Recognizer correctness gaps

Affected tests: REC-001 through REC-004.

Natasha organization labels do not match configured operator keys, and invalid
structured identifiers are still emitted as detections with low confidence. For
privacy tooling, low-confidence invalid IDs can still corrupt unrelated
numbers, so invalid checksum matches should be dropped or blocked by a proven
threshold contract.

### F5: Ambiguous fuzzy restoration is not fail-fast

Affected test: FK-003.

When multiple true values map to the same fuzzy fake, restoration does not
raise. The desired behavior is to raise with candidate diagnostics so the caller
does not receive an arbitrary restoration.

## Conclusion

The requested session-based state isolation has been implemented and verified:
public API/session tests, consumer-contract tests, real integration round trips,
and the live e2e flow all pass under explicit sessions.

The full suite remains red by design because it also captures the next set of
required production changes: fail-fast dependency errors with notes,
privacy-safe logging, recognizer label/checksum correctness, and ambiguous
fuzzy restoration diagnostics.
