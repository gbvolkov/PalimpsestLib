# Fail-Fast Policy

This policy applies to Palimpsest runtime behavior, tests, and consumer-facing
documentation.

## Rule

**NO WORKAROUNDS. NO FALLBACKS.**

If Palimpsest cannot complete an operation exactly as configured, it must raise
an exception immediately. By default, it must rethrow the original exception so
the client receives the original type, arguments, traceback, cause/context, and
third-party attributes. Palimpsest context may be added with exception notes, but
it must not replace or summarize away the original failure data.

Explicitly defined business requirements are the only allowed exception. They
must be named, documented, and tested. Without that documentation and test
coverage, continuing after a failure is a bug.

## What Must Raise

- Missing, mismatched, or unloaded models and tokenizers.
- Runtime attempts to download or substitute models.
- Missing optional dependencies when the requested feature needs them.
- Unsupported model families, languages, entity types, or operator keys.
- Recognizer label mismatches and duplicate conflicting recognizer outputs.
- Invalid checksums for structured identifiers when the recognizer is validating
  that identifier type.
- Analyzer, tokenizer, model, or Presidio exceptions.
- Restoration misses, ambiguous fuzzy matches, duplicate fake mappings, or
  mapping/session mismatches.
- Shared-state misuse that could mix mappings across users or conversations.
- Unsafe logging configuration in production paths.

## Diagnostic Minimum

Every raised error should expose as much of this context as is available:

- Operation: initialization, analyze, anonymize, restore, logging, or consumer
  integration boundary.
- Library component: class, function, recognizer, operator, model loader, or
  dependency.
- Configuration: model family, model path, local-only flag, language, device,
  entity allow-list, thresholds, locale, and feature flags.
- Third-party context: package/library name, original exception type and message,
  model/provider response, and dependency version when known.
- Text context without raw PII: input length, span start/end, span length, entity
  type, recognizer score, request/session id, and redacted hashes.

Prefer rethrowing the original exception with an added note:

```python
except SomeThirdPartyError as exc:
    exc.add_note(
        "Palimpsest context: operation='tokenizer_init', "
        f"dependency='transformers', model_path={model_path!r}"
    )
    raise
```

Do not convert a rich third-party exception into a generic Palimpsest message:

```python
except SomeThirdPartyError as exc:
    raise RuntimeError("Tokenizer initialization failed") from exc
```

Wrapping is allowed only when Palimpsest itself created the error or a documented
public API contract explicitly requires a Palimpsest exception type. In that
case, preserve the original exception with `raise ... from exc` and include all
available original exception fields and third-party context.

## Disallowed Behaviors

- Returning the unmodified input because anonymization failed.
- Returning a partially anonymized or partially restored string without raising.
- Swallowing an exception after logging it.
- Replacing a failed model, recognizer, dependency, language, device, or provider
  with another option.
- Lowering confidence scores to hide invalid recognizer results.
- Treating fuzzy restoration as success when more than one candidate is possible.
- Writing raw PII diagnostics to logs as a substitute for structured errors.
- Adding retries that change behavior or hide the final failure context.

## Allowed Business Exceptions

The following patterns can be valid only when explicitly configured and covered
by tests:

- `keep` for a specific entity type that the consumer intentionally does not want
  anonymized.
- Opt-in integration tests skipped because a local model, GPU, network, or
  external service is unavailable.
- Lazy import of optional dependencies before the optional feature is used.
- Backward-compatible method aliases that preserve exactly the same behavior as
  the primary API.

These exceptions must not mask failures inside a requested operation.
