# Accepted Findings

As of 2026-05-01, the items below are known review findings that remain in the
codebase by explicit acceptance. They are not active defects for the current
scope, but they do define operational constraints and expected behavior.

## 1. Raw PII is logged when verbose diagnostics are enabled

- Status: Accepted
- Location: `palimpsest/palimpsest.py`, `debug_log()`
- Current behavior:
  `Palimpsest(verbose=True)` logs raw input/output text, recognized entity
  values, and true/fake mappings.
- Acceptance basis:
  This is intentional unsafe diagnostic behavior gated by `verbose=True`. The
  default path remains `verbose=False`.
- Operational implication:
  Do not enable `verbose=True` in production or in privacy-sensitive runs.

## 2. spaCy model download during startup

- Status: Accepted
- Location: `palimpsest/analyzer_engine_provider.py`
- Current behavior:
  If the configured spaCy model is not installed locally, startup may call
  `spacy.cli.download(...)`.
- Acceptance basis:
  Automatic model acquisition during startup is expected behavior.
- Operational implication:
  Startup may require network access and may mutate the local Python/spaCy
  environment on first run.

## 3. GLiNER device move failure is warning-only

- Status: Accepted risk
- Location: `palimpsest/recognizers/gliner_recogniser.py`
- Current behavior:
  If `self._model.to(device)` fails, the recognizer logs a warning and
  continues instead of raising.
- Acceptance basis:
  Current behavior is intentionally left as-is.
- Operational implication:
  Runtime may continue on a different device state than originally intended,
  and startup is not fail-fast for this path.

## 4. Name validation falls back to the last generated name

- Status: Accepted
- Location: `palimpsest/fakers/faker_utils.py`,
  `palimpsest/fakers/fakers_funcs.py`
- Current behavior:
  If name validation fails repeatedly, `fake_name()` logs `NON_CASHABLE` and
  returns the last generated name instead of raising.
- Acceptance basis:
  This is by design.
- Operational implication:
  If morphology or validation dependencies malfunction, anonymization may
  continue with an unvalidated fake name.

## 5. RU bank account recognizer has no active checksum validation

- Status: Accepted
- Location: `palimpsest/recognizers/regex_recognisers.py`
- Current behavior:
  `RUBankAccountRecognizer` matches bank-account-shaped values and returns them
  without an active validation step.
- Acceptance basis:
  This is by design.
- Operational implication:
  Account-like 20-digit strings may be detected even when no checksum-style
  validation is applied.

## 6. Invalid structured identifiers may still be emitted with low score

- Status: Accepted for current iteration
- Location: `palimpsest/recognizers/regex_recognisers.py`
- Current behavior:
  Invalid `SNILS`, `INN`, and `CREDIT_CARD` candidates are not dropped; their
  score is reduced instead.
- Acceptance basis:
  Returning low-confidence candidates instead of suppressing them is currently
  accepted behavior.
- Operational implication:
  Downstream thresholds and operator handling must be chosen carefully to avoid
  acting on weak numeric matches.

## 7. Analysis may add newline separators to caller text

- Status: Accepted
- Location: `palimpsest/palimpsest.py`, `_PalimpsestRuntime.analyze()`
- Current behavior:
  Analyzed text is rebuilt from chunks and appends `"\n"` after each chunk. This
  can add trailing or additional newlines to anonymized and deanonymized output.
- Acceptance basis:
  This formatting behavior is currently intentional and not considered a
  defect.
- Operational implication:
  Callers that require exact whitespace preservation should normalize or compare
  output accordingly.

## 8. Fuzzy restoration does not raise on ambiguous matches

- Status: Accepted
- Location: `palimpsest/fakers/faker_context.py`, `defake_fuzzy()`
- Current behavior:
  Fuzzy restoration uses the best match returned by `rapidfuzz.process.extractOne`
  and does not raise when multiple stored fake values could plausibly match.
- Acceptance basis:
  Best-match fuzzy restoration is accepted behavior for the current
  implementation.
- Operational implication:
  Callers that require deterministic restoration should prefer exact-match
  entity types or avoid workflows that can create ambiguous fake values.

## 9. Address exception notes include the raw input value

- Status: Accepted
- Location: `palimpsest/fakers/faker_context.py`, `address_hash()` and
  `address_fuzzy_key()`
- Current behavior:
  When libpostal address processing raises, Palimpsest rethrows the original
  exception with a diagnostic note that includes `value={value!r}`.
- Acceptance basis:
  The caller already supplied the address value, and logging or exposing
  exception details is the caller's operational decision.
- Operational implication:
  Callers should avoid logging exception notes in privacy-sensitive environments
  if those notes may contain address PII.
