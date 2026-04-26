# Current Codebase Review Findings

Date: 2026-04-27

Scope: Current `PalimpsestLib` workspace review.

Evidence standard:

- Findings are based on current failing tests, deterministic probes, or direct
  deterministic code-path analysis.
- Nondeterministic observations are not treated as findings.
- Current full-suite result used for this review:

```text
12 failed, 27 passed, 9 warnings
```

## Finding 1: [P0] Raw PII is logged

Location: `palimpsest/palimpsest.py:337-357`

`debug_log` logs raw input, anonymized output, fake values, and true/fake
mappings. Current failing tests prove logs contain `John Doe`,
`+1 (202) 555-0182`, `4111111111111111`, and `Fake Person`.

This is a direct privacy leak whenever verbose logging is enabled.

## Finding 2: [P1] Stored custom mappings are not used if analyzer misses

Location: `palimpsest/palimpsest.py:158-177`

Deterministic probe: a stored custom entry `FAKE_CARD -> TRUE_CARD` with analyzer
returning no results restores `pay FAKE_CARD now` as `pay FAKE_CARD now`.

The final mapping pass calls `deanonymize_item()`, but for custom operators that
function returns `item.text`, making `replace(fake, fake)` a no-op. This means
restoration depends on re-detecting the fake value.

## Finding 3: [P1] Faker can generate cards recognizer cannot detect

Location: `palimpsest/recognizers/regex_recognisers.py:239-250`

Deterministic probe with `Faker.seed(42)` generated valid Luhn card
`36483503056414` length 14.
`RUCreditCardRecognizer().analyze(..., entities=["CREDIT_CARD"])` returned `[]`.

The fake-card generator and recognizer therefore do not share a closed contract.

## Finding 4: [P1] Missing dependency context notes

Location: `palimpsest/palimpsest.py:59-61`

Current tests prove original dependency exceptions are rethrown without required
`__notes__`: missing GLiNER model, tokenizer load failure, and libpostal address
failure all preserve exception type but lose operation/model/address context.

## Finding 5: [P1] GLiNER device failure is swallowed

Location: `palimpsest/recognizers/gliner_recogniser.py:71-74`

Current failing test injects a model whose `.to(device)` raises
`DeviceMoveError`; `GlinerRecognizer()` does not raise and only logs a warning.

This violates fail-fast behavior for model initialization.

## Finding 6: [P1] Startup attempts runtime download

Location: `palimpsest/analyzer_engine_provider.py:192-194`

Current failing test proves `create_nlp_engine_with_gliner` calls
`spacy.cli.download("ru_core_news_sm")` when the package is missing.

Library construction is therefore network-dependent instead of validating local
prerequisites and failing.

## Finding 7: [P1] Invalid identifiers are still returned

Location: `palimpsest/recognizers/regex_recognisers.py:100-114`

Current recognizer tests prove invalid SNILS `112-233-445 96`, invalid INN
`7707083895`, and invalid credit card `4000000000000003` are returned as
detections with score `0.0999`.

The code lowers score after checksum failure but still appends
`RecognizerResult`, despite comments saying invalid values should be skipped.

## Finding 8: [P1] Natasha ORG label mismatch

Location: `palimpsest/recognizers/natasha_recogniser.py:47-53`

Current test proves an `ORG` span requested as `RU_ORGANIZATION` returns no
result.

The code maps `ORG` to `RU ORGANIZATION` with a space, while supported entities
and operators use `RU_ORGANIZATION`.

## Finding 9: [P1] Ambiguous fuzzy restore does not raise

Location: `palimpsest/fakers/faker_context.py:171-180`

Current test creates two fake entries with the same fake value `same fake`;
`defake_fuzzy("same fake")` does not raise.

The code uses `extractOne` and returns one candidate without detecting
duplicates, ties, or close competing candidates.

## Finding 10: [P1] Faker locale is global

Location: `palimpsest/fakers/fakers_funcs.py:8-14`

Deterministic probe shows `fake_factory("en-US")` followed by
`fake_factory("ru-RU")` returns the same Faker object; both report `["en_US"]`.

The first locale wins globally, so session/processor locale isolation is broken.

## Finding 11: [P2] Generated metadata is tracked

Location: `Palimpsest.egg-info/SOURCES.txt:29-31`

`git ls-files` shows `Palimpsest.egg-info/*` is tracked, and `SOURCES.txt`
references deleted old tests.

This is stale generated packaging state in source control.

## Finding 12: [P2] Accidental git-log file is tracked

Location: `et --soft 8f29b9a:1`

`git ls-files` includes root file `et --soft 8f29b9a`; its contents are colored
`git log` output.

It is not source, tests, docs, or package config.

## Explicit Non-Findings

The following items were checked and are not treated as current findings:

- Person-only `run_entities` behavior is currently correct.
- The English card integration test currently passes in isolation.
- Escaped Unicode literals were replaced with UTF-8 text; current search found no
  remaining `\u....` literals.
