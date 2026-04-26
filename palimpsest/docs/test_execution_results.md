# Test Execution Results

Date: 2026-04-26

Workspace: `C:\Projects\PalimpsestLib`

## Environment

- Requested environment: `C:\Projects\PalimpsestLib\.venv`
- Python executable: `C:\Projects\PalimpsestLib\.venv\Scripts\python.exe`
- Python: `Python 3.13.7`
- Test runner: `pytest 9.0.3`
- Full suite was run outside the command sandbox because native spaCy/blis DLL
  import failed inside the sandbox with `DLL load failed while importing cy:
  Access is denied.`

## Commands Run

```powershell
.\.venv\Scripts\python.exe -m py_compile palimpsest\palimpsest.py palimpsest\__init__.py test.py tests\conftest.py tests\unit\test_public_api_contract.py tests\unit\test_consumer_contract.py tests\integration\test_real_palimpsest_pipeline.py tests\e2e\test_llm_roundtrip.py
.\.venv\Scripts\python.exe -m pytest -q tests\unit\test_public_api_contract.py tests\unit\test_consumer_contract.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Implementation Corrections In This Run

Main library code was modified to implement session-based state isolation:

- Added `PalimpsestSession`, `SessionRequiredError`, and `SessionStateError`.
- Moved reversible mapping state and `FakerContext` from `Palimpsest` into
  explicit session objects.
- Added `Palimpsest.create_session(...)`.
- Added session methods `anonymize`, `deanonymize`, `anonimize`, and
  `deanonimize`.
- Kept processor-level methods as guarded delegators requiring
  `session=...`.
- Made processor-level calls without a session raise `SessionRequiredError`.
- Made closed, foreign, or unmapped sessions raise `SessionStateError`.
- Updated README and local example usage to create and pass explicit sessions.

## Summary

| Command | Result |
| --- | --- |
| `py_compile` over changed library/tests/examples | Passed |
| `pytest -q tests\unit\test_public_api_contract.py tests\unit\test_consumer_contract.py` | `12 passed, 7 warnings` |
| `pytest -q` | `12 failed, 27 passed, 9 warnings` |

## Passing Areas

- Session public API import and exports.
- Processor-level calls fail fast when `session` is omitted.
- Session-level old spellings and corrected aliases round-trip.
- Processor delegators work only with matching sessions.
- Foreign sessions are rejected.
- Deanonimization before a session has mappings raises.
- `session.reset()` clears mappings.
- `session.close()` rejects later calls.
- Long-lived processor plus per-user sessions no longer leaks mappings across
  users.
- One session can retain mappings across multiple turns until reset or close.
- Live e2e OpenAI round trip passed with `OPENAI_API_KEY` from
  `palimpsest/gv.env`.
- Real English and Russian integration round trips passed with explicit
  sessions.

## Remaining Failures

These failures are outside the session-state refactor and correspond to the
previously documented contract gaps.

| Area | Failing Tests | Reason |
| --- | ---: | --- |
| Missing exception notes | 3 | Original dependency exceptions are raised, but Palimpsest context is not attached with `exc.add_note(...)`. |
| Swallowed/fallback behavior | 2 | GLiNER device move failure is swallowed; missing spaCy package triggers runtime download. |
| Faker/context ambiguity | 1 | Ambiguous fuzzy restoration does not raise with candidate diagnostics. |
| Privacy logging | 2 | `debug_log` emits raw PII and mappings; no explicit `unsafe_debug_raw_values=False` gate exists. |
| Natasha label | 1 | Natasha `ORG` still does not map to `RU_ORGANIZATION`. |
| Invalid checksum detections | 3 | Invalid SNILS, INN, and credit-card values are still returned with low score. |

## Current Interpretation

The requested P0 session-isolation fix is covered and passing in deterministic
unit tests plus real integration/e2e flows. The remaining red tests should be
handled as separate production fixes for fail-fast dependency behavior,
privacy-safe diagnostics, recognizer correctness, and deterministic fuzzy
restoration.
