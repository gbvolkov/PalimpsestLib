# Palimpsest Agent Guidance

This document is mandatory guidance for Codex and other agents working on the
Palimpsest library.

## Non-Negotiable Policy

**NO WORKAROUNDS. NO FALLBACKS.**

Palimpsest protects and restores sensitive data. Silent recovery, best-effort
behavior, compatibility shims, hidden downloads, fuzzy guesses, and "keep going"
branches can leak PII or corrupt consumer text. When anything unexpected happens,
the library must fail fast by raising an exception with all available diagnostic
information.

The only exceptions to this rule are explicitly defined business requirements
documented in code, tests, and public guidance. An example of a business rule is
an allow-listed entity configured as `keep`. A missing model, bad recognizer
configuration, dependency failure, checksum mismatch, unsupported entity,
unrestorable fake value, or consumer misuse is not a workaround opportunity.

## Required Error Handling

- Re-raise the original exception whenever possible. The client must receive the
  original exception type, arguments, traceback, cause/context, and any
  third-party attributes Python preserves.
- Do not replace a rich third-party exception with a Palimpsest-only
  notification such as `RuntimeError("Failed to ...")`.
- If Palimpsest context is needed, attach it to the original exception with
  `exc.add_note(...)` and then use bare `raise`.
- Raise new typed exceptions only for errors created by Palimpsest itself, or
  when a documented public API contract explicitly requires a Palimpsest error
  type. If wrapping is unavoidable, preserve the original exception object with
  `raise ... from exc` and include all available original exception details.
- Do not return the original text, an empty list, `None`, a low-confidence
  result, or a partially restored response unless that exact behavior is an
  explicit business requirement.
- Include actionable diagnostic context: operation name, entity type, recognizer
  name, model family, model path, dependency name and version when available,
  language, configured threshold, input span indexes, and relevant third-party
  exception details.
- Do not catch broad `Exception` only to log and continue. Catch broad
  exceptions only at a boundary where you immediately annotate and re-raise the
  original exception.
- Do not hide third-party failures behind Palimpsest-only text. The caller needs
  both Palimpsest context and the original library context.
- Do not degrade from one recognizer, model, tokenizer, device, dependency, or
  algorithm to another without an explicit documented business rule and tests.

Preferred pattern:

```python
try:
    model = GLiNER.from_pretrained(model_path, local_files_only=True)
except Exception as exc:
    exc.add_note(
        "Palimpsest context: "
        f"operation='recognizer_init', model_path={model_path!r}, "
        "local_files_only=True"
    )
    raise
```

Disallowed pattern:

```python
try:
    model = GLiNER.from_pretrained(model_path, local_files_only=True)
except Exception as exc:
    raise RuntimeError(
        "Failed to load GLiNER model "
        f"model_path={model_path!r}, local_files_only=True, "
        f"operation='recognizer_init'"
    ) from exc
```

Also disallowed:

```python
try:
    model.to(device)
except Exception:
    logger.warning("Could not move model to device")
```

## Dependency And Model Loading

- Library code must not download models, wheels, dictionaries, NLP assets, or
  other dependencies at runtime. Installation and model provisioning belong to
  packaging, deployment, or explicit consumer setup.
- Validate all required local assets during initialization and fail before any
  text processing starts.
- Keep model names consistent across validation and engine configuration. Do not
  check one spaCy package and configure a different package.
- Make model paths, local-only behavior, language, device, thresholds, and entity
  lists explicit configuration. Avoid hardcoded production dependencies inside
  request/session state.
- Separate heavy model/analyzer caches from per-request or per-conversation
  anonymization state. Shared model objects are acceptable only when they do not
  contain user-specific mappings or sensitive text.
- Optional dependencies must be imported lazily only at the feature boundary, but
  a requested optional feature must fail fast if its dependency is unavailable.
  Do not silently disable address support, morphology, tokenizer behavior, or a
  recognizer.

## Recognizer Behavior

- Entity allow-lists must be enforced consistently in recognizer registration,
  analyzer calls, and anonymization/deanonymization operators.
- Recognizer labels must exactly match supported entities and operator keys.
  Typos, casing drift, or alternate spellings must raise or be covered by an
  explicit mapping with tests.
- Invalid structured identifiers, including cards, INN, SNILS, passports, bank
  accounts, and phones, must not be returned as detections unless retaining them
  is an explicit business requirement with threshold tests.
- A checksum failure is diagnostic information, not a reason to return a lower
  score and hope downstream filtering removes it.
- Result spans must be deterministic and traceable to the original text. When
  chunking text, tests must verify offset correction and boundary behavior.
- Do not use fuzzy matching for restoration unless the ambiguity model is
  documented and tested. If restoration cannot find exactly one safe original
  value, raise with the fake value, entity type, candidate count, scores, and
  request/session context identifier.

## Anonymization And Restoration State

- Treat anonymization mappings as per-request or per-conversation secrets.
  Long-lived shared `Palimpsest` instances must not carry mappings across users.
- Prefer explicit mapping/session objects passed to restoration over implicit
  mutable instance state.
- Restoration must be deterministic and tied to the anonymization entries that
  were produced for the same session. Avoid global string replacement and
  re-analysis as the source of truth for restoration.
- Resetting state is not a substitute for isolation. Design APIs so consumers
  cannot accidentally mix mappings across users.

## Logging And Privacy

- Logs must not contain raw user text, raw detected PII, fake-to-true mappings,
  full prompts, full model responses, or reversible identifiers by default.
- Diagnostics should use redacted structured fields: operation, entity type,
  recognizer name, score, span length, hash or stable opaque request id, model
  identifier, dependency name, and exception class.
- Any unsafe raw-value debug mode must be explicit, local-development-only,
  disabled by default, and named so consumers cannot enable it casually.
- Never log secrets loaded from configuration, model provider credentials, or
  environment files.
- Tests should assert that normal logs do not contain sample PII or mapping
  values.

## Tests Required For Agent Changes

- Add deterministic unit tests for every behavior change. Mock heavy analyzers,
  model calls, and LLM calls unless the test is explicitly marked integration.
- Tests for errors must assert fail-fast behavior and original exception chaining.
- Tests for recognizers must cover valid matches, invalid non-matches, label
  mapping, entity allow-lists, thresholds, and span indexes.
- Tests for anonymization must cover round-trip restoration, context isolation,
  repeated values, chunk boundaries, and unsupported entities.
- Tests for privacy must cover logging redaction and absence of raw PII in normal
  logs.
- Integration tests that require local models, libpostal, spaCy assets, network,
  GPUs, or LLMs must be opt-in and skipped with a clear reason when prerequisites
  are missing.

## Consumer Integration

- Consumers must choose a privacy boundary and anonymize before data crosses it:
  model calls, tracing, durable logs, queue messages, tool calls, analytics, and
  storage.
- Do not require consumers to infer missing setup from runtime behavior. Validate
  dependencies and configuration at startup and fail with deployment instructions.
- Keep per-user mapping state isolated. Middleware in long-running services must
  create or receive a session-scoped context instead of sharing one mutable
  anonymizer across users.
- Tool outputs and downstream model responses can contain sensitive data and must
  follow the same anonymization and logging policy as user messages.
- Public API changes must preserve privacy and determinism first. Backward
  compatibility wrappers are acceptable only when they delegate exactly and do
  not add hidden recovery behavior.

## Working Rules For Future Agents

- Read `palimpsest/docs/codebase_review_findings.md` before changing behavior.
- Keep changes scoped. Do not refactor unrelated modules or rewrite generated
  metadata while fixing a targeted issue.
- Preserve user and collaborator edits. Inspect `git status` before and after
  changes, and do not revert files you did not touch.
- When a current implementation conflicts with this guidance, prefer a small,
  tested fail-fast change over a compatibility workaround.
- Document every intentional business exception to "NO WORKAROUNDS, NO
  FALLBACKS" in the code path and in tests.
