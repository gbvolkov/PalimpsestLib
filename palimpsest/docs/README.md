# Palimpsest Documentation

Start here for future Codex or agent work:

- `agent_guidance.md` contains mandatory engineering rules for changes to the
  Palimpsest library.
- `fail_fast_policy.md` defines the fail-fast contract and the required
  diagnostic information for exceptions.
- `codebase_review_findings.md` records current risks and recommended fixes that
  future changes should preserve or address.

The governing rule for this library is:

**NO WORKAROUNDS. NO FALLBACKS.**

When behavior fails outside an explicitly documented business requirement,
Palimpsest must rethrow the original exception whenever possible, adding
Palimpsest context with exception notes instead of replacing the original
failure data.
