# Test Report

Date: 2026-05-01

Workspace: `C:\Projects\PalimpsestLib`

Policy context: `palimpsest/docs/accepted_findings.md` is authoritative for
accepted behaviors. Tests were reviewed and updated to match accepted findings
before execution.

## Commands Executed

| Command | Scope | Result | Notes |
| --- | --- | --- | --- |
| `uv run pytest -q tests\unit` | Deterministic unit tests | PASS: 44 passed | 2 warnings from SWIG-generated dependency types. |
| `uv run pytest -q tests\integration` | Real Palimpsest dependency pipeline | PASS: 6 passed | 6 warnings, including Hugging Face `resume_download` deprecation. |
| `uv run pytest -q -m "not e2e"` | All local/non-live tests | PASS: 50 passed, 1 deselected | Deselects live OpenAI e2e test. |
| `uv run pytest -q tests\e2e` | Live OpenAI e2e | NOT EXECUTED | Blocked because it would use local credentials and send data to an external third-party service without explicit approval. |

## Unit Test Details

| Test | Incoming data | Expected result | Actual result | Failure reason |
| --- | --- | --- | --- | --- |
| `test_import_exposes_palimpsest_class` | Import `Palimpsest`, `PalimpsestSession`. | Exported class names are `Palimpsest` and `PalimpsestSession`. | Matched expected names. | None. |
| `test_processor_methods_require_explicit_session` | Processor calls `anonimize("secret")`, `deanonimize("secret")` without session. | Both raise `SessionRequiredError`. | Both raised `SessionRequiredError`. | None. |
| `test_session_misspelled_methods_remain_backward_compatible` | Session `anonimize("secret")`. | Anonymized `FAKE_VALUE_1`; deanonimized `secret`. | Returned `FAKE_VALUE_1`; restored `secret`. | None. |
| `test_session_corrected_aliases_round_trip` | Session `anonymize("secret")`. | Anonymized `FAKE_VALUE_1`; deanonymized `secret`. | Returned `FAKE_VALUE_1`; restored `secret`. | None. |
| `test_processor_delegators_require_matching_session` | Processor/session call with `"secret"`, then foreign processor with same session. | Matching session restores `secret`; foreign processor raises `SessionStateError`. | Matching session restored `secret`; foreign processor raised. | None. |
| `test_unsupported_input_raises_instead_of_returning_original` | `session.anonimize(None)`. | Raise `TypeError`. | Raised `TypeError`. | None. |
| `test_deanonimize_without_session_mapping_returns_input_unchanged` | New session `deanonimize("FAKE_VALUE_1")`. | Return `FAKE_VALUE_1`. | Returned `FAKE_VALUE_1`. | None. |
| `test_session_reset_and_close_enforce_lifetime` | Anonymize `"secret"`, reset, close, then anonymize again. | Reset makes old fake unrestorable; closed session raises `SessionStateError`. | Old fake returned unchanged; closed session raised. | None. |
| `test_consumer_middleware_anonymizes_all_text_parts_before_model_boundary` | Message content with `"user John Doe"`, `"tool John Doe"`, `"title John Doe"`. | Result contains no `John Doe`; calls are exactly the three input strings. | `John Doe` absent; calls matched expected list. | None. |
| `test_consumer_contract_requires_tool_outputs_to_use_same_anonymizer` | Tool output `"Tool result contains John Doe"`. | Protected output `ANON::1`. | Returned `ANON::1`. | None. |
| `test_long_lived_shared_palimpsest_returns_unmatched_foreign_mapping_unchanged` | User one fake for `"user-one secret"` used in user two session. | User two leaves fake unchanged; user one restores original. | User two returned fake unchanged; user one restored `user-one secret`. | None. |
| `test_one_session_can_keep_mappings_across_multiple_turns` | Same session anonymizes `"first secret"` and `"second secret"`. | Both mappings remain restorable. | Restored `first secret` and `second secret`. | None. |
| `test_verbose_debug_log_emits_raw_values_by_design` | `debug_log()` with `John Doe`, `+1 (202) 555-0182`, `4111111111111111`, fake `Fake Person`. | Logs include raw and fake values, per accepted verbose diagnostics behavior. | Captured log included all expected raw/fake values. | None. |
| `test_processor_default_verbose_false_does_not_call_debug_log` | Default processor anonymizes `John Doe +1 (202) 555-0182 4111111111111111`. | No `palimpsest.palimpsest` debug output. | Captured log was empty. | None. |
| `test_tokenizer_load_failure_rethrows_original_with_context_note` | Fake tokenizer raises `TokenizerLoadError("transformers tokenizer payload")`. | Original exception type rethrown with operation/model note. | `TokenizerLoadError` raised; notes included tokenizer and GLiNER model id. | None. |
| `test_gliner_model_load_failure_rethrows_original_with_context_note` | Fake GLiNER loader raises `GlinerModelLoadError("gliner model payload")`. | Original exception type rethrown with `gliner_model_load` note. | `GlinerModelLoadError` raised; notes matched. | None. |
| `test_gliner_device_move_failure_is_warning_only` | Fake model `.to(device)` raises `DeviceMoveError`. | Recognizer construction continues and warning is logged. | Recognizer returned; warning contained `Could not move GLiNER model to device`. | None. |
| `test_spacy_runtime_download_is_attempted_when_model_missing` | Missing spaCy model simulated; download function records model and raises. | Runtime attempts download of `ru_core_news_lg`. | Download attempted with `ru_core_news_lg`; assertion error raised by test hook. | None. |
| `test_repeated_true_value_returns_same_fake` | `fake_account("account-1")` twice. | Same fake returned both times. | Both returned same fake. | None. |
| `test_fake_value_restores_only_within_same_context` | Two `FakerContext` instances; fake created in first context. | First restores `account-1`; second returns fake unchanged. | Matched expected context isolation. | None. |
| `test_fake_value_collision_regenerates_without_overwriting` | Fake generator yields `same-fake`, `same-fake`, `unique-fake`. | First true maps to `same-fake`; second true maps to `unique-fake`; both restore correctly. | Matched expected values and restoration. | None. |
| `test_fake_value_collision_exhaustion_raises` | Generator always returns `same-fake`. | Second true value raises `ValueError`. | Raised `ValueError` with expected message. | None. |
| `test_ambiguous_fuzzy_restoration_uses_best_match` | `_faked` has two entries with fake `"same fake"`. | Accepted behavior: return best match `original-one`. | Returned `original-one`. | None. |
| `test_phone_normalization_makes_repeated_formats_deterministic` | `+7 (495) 123-45-67` and `7 (495) 123-45-67`. | Same fake phone for both formats. | Same fake returned. | None. |
| `test_phone_fake_collision_regenerates_without_overwriting` | Generator yields `same-phone`, `same-phone`, `unique-phone`. | First true maps to `same-phone`; second true maps to `unique-phone`; both restore correctly. | Matched expected values and restoration. | None. |
| `test_address_mapping_uses_unified_hash_and_restores` | Address `"Original Street 1"` with fake unified hash `same-address`. | Repeated true address returns same fake; fake restores to original. | Matched expected address behavior. | None. |
| `test_address_fake_collision_regenerates_without_overwriting` | Fake address generator yields `same-address`, `same-address`, `unique-address`. | Collision regenerates; both fake addresses restore to their original true values. | Matched expected values and restoration. | None. |
| `test_ru_specific_fakers_use_ru_locale_with_en_default` | Locale `en-US`; RU passport/bank/name/address fakers. | RU-specific fakers use RU data; values restore to original tokens. | Passport and bank formats matched; RU name/address had Cyrillic; restored all tokens. | None. |
| `test_ru_specific_fakers_do_not_break_default_card_faker` | Locale `en-US`; RU and EN fake factories. | Default card faker remains EN/default; RU passport uses RU faker; direct unbound fake call raises. | Matched expected factory routing and raised unbound runtime error. | None. |
| `test_address_dependency_failure_rethrows_original_with_context_note` | `address_hash("Broken address")` with failing `unify_address`. | Original `LibpostalFailure` rethrown; notes include `address`, `libpostal`, and `Broken address`. | Raised original exception; notes contained expected data. | None. |
| `test_natasha_org_maps_to_ru_organization` | Fake Natasha `ORG` span over `"Acme"`. | One result: entity `RU_ORGANIZATION`, span `0..4`. | Returned one `RU_ORGANIZATION`, span `0..4`. | None. |
| `test_invalid_structured_identifiers_are_returned_with_low_score` | Invalid `SNILS=112-233-445 96`, `INN=7707083895`, card `4000000000000003`. | Each recognizer returns one result with matching entity and score `< 0.2`. | All three returned one low-score result over full input. | None. |
| `test_email_address_has_deanonymization_operator` | Runtime `_deanon_operators()` with no run entity filter. | Operators include `EMAIL_ADDRESS`. | `EMAIL_ADDRESS` present. | None. |
| `test_email_address_survives_run_entity_filtering` | Runtime `_run_entities=["EMAIL_ADDRESS"]`. | Filtered operators exactly `{"EMAIL_ADDRESS"}`. | Returned exactly `{"EMAIL_ADDRESS"}`. | None. |
| `test_valid_structured_identifiers_return_type_score_and_span` | Valid SNILS `112-233-445 95`, INN `7707083893`, card `4000000000000002`. | Each recognizer returns one result, score `>= 0.99`, span equals expected value. | All valid values returned with high score and expected spans. | None. |
| `test_credit_card_recognizer_supports_maestro_and_diners_lengths` | Maestro `675944116713`; Diners `30569309025904`. | Each is recognized as `CREDIT_CARD` with score `>= 0.99`. | Both recognized with expected spans. | None. |
| `test_recognizer_entity_allow_list_excludes_unrequested_entities` | Text contains valid SNILS but requested entities `["INN"]`. | Return `[]`. | Returned `[]`. | None. |
| `test_analyzer_allow_list_is_passed_to_analysis` | Run entities `["PERSON"]`; text `"John john@example.com"`. | Analyzer receives exactly `["PERSON"]`. | Recorded entities were `[['PERSON']]`. | None. |
| `test_chunk_offset_correction_preserves_original_spans` | Split chunks `["Alice", "Bob"]`, each with local recognizer span. | Final text `Alice\nBob\n`; spans map to `Alice`, `Bob`. | Final text and span extraction matched expected data. | None. |

## Integration Test Details

| Test | Incoming data | Expected result | Actual result | Failure reason |
| --- | --- | --- | --- | --- |
| `test_real_palimpsest_constructs_with_configured_dependencies` | Real `Palimpsest(verbose=False, run_entities=[PERSON, RU_PERSON, PHONE_NUMBER, CREDIT_CARD, RU_PASSPORT, SNILS, INN, RU_BANK_ACC])`. | Processor constructs successfully. | Processor constructed successfully. | None. |
| `test_real_pipeline_anonymizes_and_restores_email_address` | Text `Contact john.doe@example.com for details.` with `run_entities=["EMAIL_ADDRESS"]`. | Anonymized text does not contain `john.doe@example.com`; restored text contains it. | Assertions passed: original email removed from anonymized output and present in restored output. | None. |
| `test_real_pipeline_anonymizes_and_restores_representative_english_text` | `Client John Doe will use 4111111111111111. Call +1 (202) 555-0182.` | Anonymized text excludes `John Doe` and `4111111111111111`; restored text includes both. | Assertions passed. | None. |
| `test_real_pipeline_anonymizes_and_restores_representative_russian_text` | Russian sample with `Иван Иванов` and `+7 (495) 123-45-67`. | Anonymized text excludes `Иван Иванов`; restored text includes `Иван Иванов`. | Assertions passed. | None. |
| `test_missing_gliner_model_rethrows_original_dependency_exception` | `GlinerRecognizer(model_path="__missing_gliner_model__")`. | Raises original dependency exception, not generic `RuntimeError`; notes contain `__missing_gliner_model__` and `gliner_model_load`. | Assertions passed. | None. |
| `test_libpostal_address_unification_is_available_for_address_features` | Address `221B Baker Street, London NW1`. | Unified address has non-empty `raw`, `fuzzy_hash`, and `fuzzy_keys`. | Assertions passed. | None. |

## E2E Test Not Executed

| Test | Incoming data | Expected result | Actual result | Failure reason |
| --- | --- | --- | --- | --- |
| `test_live_llm_roundtrip_keeps_raw_pii_out_of_model_request` | Synthetic PII: `Client John Doe can be reached at +1 (202) 555-0182. Payment value: 4111111111111111.` Fake values patched to `Jane Smith`, `+1 (303) 555-0199`, `4000000000000002`; model `gpt-4.1-nano`; API key from `palimpsest/gv.env`. | Serialized OpenAI request excludes raw PII; live LLM echoes anonymized text; restored response contains `John Doe`, `+1 (202) 555-0182`, and `4111111111111111`. | Not executed. | The run would send data to OpenAI using local credentials. Execution was blocked as a higher-risk external data transfer without explicit approval. |

## Warnings

- Unit run: 2 warnings from SWIG-generated dependency types lacking
  `__module__`.
- Integration and non-e2e aggregate runs: Hugging Face Hub emitted
  `resume_download` deprecation warnings while loading model assets.
- No test failures occurred in executed tests.
