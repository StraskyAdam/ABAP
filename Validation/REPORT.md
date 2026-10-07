# ABAP dashboard parity and validation report

## Compared revisions

| Repository | Reference | Revision |
|---|---|---|
| ABAP | `Complete-refactoring` (base of this change) | `2b8877649b7dbae31d8e554e2b79bbba752ad84f` |
| XSA | default branch `main` | `e5fd6d0a36957baa795608f85abdc9d4e810e834` |
| UI | default branch `main` | `461761582d2bae0008a7b05d203ec1c15c65e28c` |

The ABAP worktree is based on `Complete-refactoring`, not `main` or `New-logic-for-filtering`. XSA and UI were read-only comparison sources. File paths below are relative to `/home/runner/work/ABAP/ABAP/`.

Files used for the comparison:

| Repository path | Revision / file SHA |
|---|---|
| `ABAP code/zcl_fi_das_dashboard.txt`, `ABAP code/ZCL_ZFI_DAS_DPC_EXT.txt`, `ABAP code/zif_fi_das_dashboard.txt`, `ABAP code/zcl_fi_das_utility.txt`, `ABAP code/zcx_fi_das_error.txt`, `ABAP code/Metadata for SEGW.txt` | ABAP base `2b8877649b7dbae31d8e554e2b79bbba752ad84f` |
| `ABAP code/Test cases.txt`, `ABAP code/Unit test.txt`, `Table definition/ZI_FI_DAS_PO_BASE.txt`, `Table definition/ZI_FI_DAS_THRESH.txt`, `Source system constraints/Constraints of replication.txt`, `Workflow/DAS_XSA_ABAP_Field_Mapping.html`, `Workflow/Dataflow in XSA.html` | ABAP base `2b8877649b7dbae31d8e554e2b79bbba752ad84f` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenPO.hdbfunction` | XSA `d59c76f9c79d67235bbf68c4832a7f53386511f9` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenThresholdPO.hdbfunction` | XSA `dd472a0b3b4aa95b450b76394e1d840a9bfde0ea` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_getExclusionPOFinal.hdbfunction` | XSA `f11bea3b505125dedeeaa6b5a07805d430d70703` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_filterPOByThreshold.hdbfunction` | XSA `78f0fa922254a3e2cec198b402f0dbacb9429dc5` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenPOQuery.hdbfunction` | XSA `5d71c11190481aa3f06893c79073e21cbc4eeb6d` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_UserConfigCompanyCodes.hdbfunction` | XSA `767e1987cc9840dfe60bca197807534927da6eb5` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_UserConfigCostCenter.hdbfunction` | XSA `c735eae370b6e0e4ea0b843f713dc6a95c388003` |
| `ARIBA_ACCRUALS_DB/src/Functions/TF_UserConfigManagementUnit.hdbfunction` | XSA `ff3adb724f75373fae6dd2c0589dbcfc3450add2` |
| `Accrual_UI5/webapp/model/poValueHelp.js` | UI `a2c08d8ea277cb9a76a8d319b5e3aa019efb59a5` |
| `Accrual_UI5/webapp/model/lineItemValueHelp.js` | UI `cd5030ee47b57067e5e56131180837f667021550` |
| `Accrual_UI5/webapp/controller/Business.controller.js` | UI `87d89dfc0223a622c8a18a8efd446aa955c96194` |

## Logic trace and findings

The ABAP request flow is `build_request` / `get_filter` in `ABAP code/ZCL_ZFI_DAS_DPC_EXT.txt`, then `execute_request` → `adjust_request` → `get_required_keys` → `get_context` / `get_results` → optional generic filter → sort and page in `ABAP code/zcl_fi_das_dashboard.txt`. `get_required_keys` returns the pre-page count from AMDP; when generic processing is needed, `execute_request` counts after filtering and restores the original page before the ABAP sort/page step.

### Filter extraction and key prefilter safety

`get_filter` obtains both Gateway select-options and the filter string. The previous flow rejected an empty filter string even if select-options were present, and `extract_filters` could apply those select-options as key filters while also applying the generic string. That combination cannot safely be assumed equivalent for cross-property OR expressions.

The change now:

* allows an empty generic string to proceed when Gateway supplied select-options; recognized complete ranges are converted for AMDP optimization;
* rejects select-options that cannot be safely optimized when there is no generic predicate available, rather than silently dropping them;
* when a generic predicate is present, retains it and does not use select-options as prefilters. This preserves cross-property OR results; generic filtering runs against the full candidate set.
* retains the AMDP exception as `zcx_fi_das_error-previous` when range conversion fails.

This is a correctness-first path: requests with a generic predicate may process more candidates. Actual Gateway expression-tree conversion and HANA `APPLY_FILTER` behavior still require SAP/HANA execution; the ABAP tests below do not claim to validate Gateway translation.

The remaining filter risks are Gateway-specific: `$top=0` versus omitted `$top` depends on the deployed Gateway API's `get_top()` behavior; and the required complex OData expression must be exercised through the real request context to validate its converted predicate, escaped literals, dates, and cross-property OR semantics.

### Business logic and contract comparison

* **OData/UI contract:** `poValueHelp.js` and `lineItemValueHelp.js` send `IP_PSTYPE`, `IP_EMAIL`, and `IP_POOWNER` for Over/Under, omit `IP_PSTYPE` for Exclude, use contains filters for PO/item lookup, and request selected properties. UI table rebinding applies a default `PSTYPE` descending sorter only when there is no user sorter. The ABAP DPC parameter mapping and entity metadata expose these request properties.
* **Historical property spelling:** UI, OData metadata, XSA, and the field-mapping document expose `REVIWED_BY`. ABAP's internal status field is `REVIEWED_BY`, mapped to the historical external name. This is an intentional compatibility mapping, not a typo to “correct” in the public entity.
* **PSType and owner selection:** `TF_getOpenPOQuery.hdbfunction` and XSA open/exclusion table functions supply the reference set; ABAP implements candidate selection in SQLScript `get_keys`. Exclusion requests intentionally have no `IP_PSTYPE` and ABAP's `get_pstype` selects `*` for that mode. Owner and authorization behavior depends on role/scope configuration and replicated tables; it was statically traced but not verified against a live system.
* **Threshold/exclusion:** XSA `TF_getOpenPO`, `TF_getOpenThresholdPO`, and exclusion functions exclude already-excluded rows from Over/Under and select those rows for Exclude. The ABAP AMDP applies exclusion and uses `>` for Over and `<=` for Under after its PO/currency aggregate and threshold conversion. Static inspection is not enough to prove the threshold unit/aggregation matches all XSA runtime data; multi-line, currency, and exact-boundary cases remain integration checks.
* **Amount/currency:** XSA's `TF_getOpenPO.hdbfunction` applies the historical JPY/VND normalization around USD conversion; ABAP has corresponding currency-factor/conversion logic in `apply_currency`, `convert_to_usd`, and calculation methods. Decimal-scale, SQL NULL versus zero, and rounding parity require SAP/HANA fixture execution.
* **Status, dates, nulls, and exclusions:** field mappings and dataflow references were compared with the result mapping and status/calculation methods in `zcl_fi_das_dashboard.txt`. Existing XSA JSONs contain the comparison datasets, but no live ABAP response was available. Do not treat this static comparison as end-to-end parity.
* **Ordering:** the ABAP AMDP key query orders by `PSTYPE DESC, PONUMBER ASC, ITEMNO ASC`, matching `get_default_orderby`. Requested fields are sorted first and missing defaults are tie-breakers; unknown and duplicate fields are ignored. The key pair `(PONUMBER, ITEMNO)` is unique in the ABAP key table. The UI's default `PSTYPE` sorter is conditional on there being no user sorter.
* **Scope conversion:** ABAP's individual company-code, cost-center, and management-unit builders were retained. They keep the sole-`*` wildcard rule, cost-center/management-unit null handling, uppercase conversion for company code/cost center, management-unit case preservation, and KOSTL ALPHA conversion to the target field length. XSA scope functions and `Validation/xsa-scope-01.json` through `xsa-scope-30.json` are the references; the fixture matrix still needs execution in ABAP.

No other production-code change was made because the remaining business-path concerns need system evidence before a safe correction can be confirmed.

## Test coverage matrix

Each ABAP Unit method creates its own dashboard instance in `setup`; utility tests use only static utility methods.

| Class / methods | Logic covered | Reference inputs / limits |
|---|---|---|
| `ltc_request_processing_verified`: `default_order_has_unique_keys`, `compatible_default_prefix_is_removed`, `non_default_order_is_preserved`, `requested_sort_adds_default_ties`, `invalid_and_duplicate_sorts_are_ignored`, `paging_follows_sort`, `requested_top_zero_is_empty`, `omitted_top_keeps_all_rows`, `empty_orderby_preserves_input_order` | Default/requested ordering, tie-breakers, invalid/duplicate sort fields, paging order and top-zero semantics | Synthetic in-memory rows; pure ABAP |
| `ltc_request_processing_verified`: `known_ranges_are_optimized`, `mixed_filter_keeps_generic_predicate`, `cross_property_or_disables_prefilter`, `unoptimizable_filter_without_predicate_fails`, `empty_generic_filter_is_a_noop` | Optimized-only ranges, generic-only or mixed requests, safe cross-property OR handling, malformed/unavailable predicate rejection, early exit | Synthetic request structures; verifies ABAP request preparation, not SAP Gateway parsing |
| `ltc_request_processing_verified`: `only_single_star_is_a_wildcard`, `scope_normalization_is_field_specific` | Wildcard distinction, normalization and target-length KOSTL conversion | Synthetic scope strings; scope fixture matrix not run |
| `ltc_hana_filter_integration`: `nested_and_or_filters_synthetic_rows`, `escaped_apostrophe_matches_synthetic_row`, `date_boundary_is_exclusive`, `no_match_returns_no_rows` | Nested AND/OR, escaped apostrophe, date boundary, and empty result | Calls the actual AMDP `filter_result` / HANA `APPLY_FILTER` with synthetic rows; SAP/HANA required, not mocked |
| `ltc_utility_contracts`: `amount_format_x_y_and_default`, `percentage_parsing_and_error`, `decimal_truncation_is_toward_zero` | X/Y/default amount formatting, invalid percentage handling, truncation of negative values | Synthetic values; pure ABAP |
| `ltc_fi_das_gateway_parity`: `test_over_material`, `test_over_service`, `test_under_material`, `test_under_service`, `test_exclude` | Standard material/service Over and Under; Exclude | `xsa-over-material.json`, `xsa-over-service.json`, `xsa-under-material.json`, `xsa-under-service.json`, `xsa-exclude.json`; live SEGW endpoint and SAP MIME fixtures required |
| `ltc_fi_das_gateway_parity`: `test_over_material_owner`, `test_over_service_owner`, `test_under_material_owner`, `test_under_service_owner`, `test_exclude_owner` | Owner variants | Corresponding `*-owner.json` fixtures; SAP integration required |
| `ltc_fi_das_gateway_parity`: `test_scope_01` through `test_scope_30` | Company-code/cost-center/management-unit authorization scope cases | `xsa-scope-01.json` through `xsa-scope-30.json`; SAP role/configuration required |
| `ltc_fi_das_gateway_parity`: `test_inlinecount_with_top_one`, `test_no_inlinecount`, `test_skip_beyond_result_set`, `test_top_zero`, `test_po_value_help`, `test_item_value_help`, `test_supplier_value_help`, `test_filter`, `test_selection`, `test_filter_sort_and_paging`, `test_under_paging`, `test_excl_paging`, `test_exclusion_pstype_desc`, `test_exclusion_pstype_asc`, `test_excl_pstype_pages`, `test_orderby_invalid`, `test_nonexistent_supplier`, `test_filter_companycode`, `test_filter_polinedesc`, `test_filter_curr_company`, `test_filter_supplierid`, `test_filter_po_or_supplier`, `test_skip_high_sorted`, `test_empty_contains_po`, `test_under_po_help`, `test_excl_po_help`, `test_under_supplier_help` | Filter, selection, value help, count, sorting, paging, Exclude ordering, and no-match cases | Existing ABAP Unit integration methods and the GET requests in `ABAP code/Test cases.txt`; SAP endpoint required |
| `ltc_fi_das_gateway_parity`: `test_x_format`, `test_y_format`, `test_empty_format`, `test_select_calc_status`, `test_sort_amountaccrued`, `test_sort_reviewed_by` | Formatting, selection/calculation fields, status and reviewer mapping | X/Y/empty-format and selection fixtures; SAP endpoint required |

`ltc_request_processing` in the inherited test source still contains legacy empty method bodies and commented-out assertions. Those placeholders are **not counted** as passing tests. The live-fixture tests and the new focused classes above are independently named, but this legacy class still needs SAP activation review and cleanup/restoration against the current APIs. The old commented `test_all_pstype_request` is likewise not counted.

## Executed checks and results

| Check | Result |
|---|---|
| Confirm branch base and PR target | Verified: PR #27 targets `Complete-refactoring` at `2b8877649b7dbae31d8e554e2b79bbba752ad84f` |
| XSA/UI reference access | GitHub source access succeeded; default-branch SHAs recorded above |
| LFS inspection | All five `.gitattributes` LFS files are hydrated JSON, not pointer text. `git lfs ls-files -l` lists the five payload OIDs. The `Validation/` directory is 948,538,232 bytes. |
| Test declaration/implementation and source whitespace checks | One-off structural check found 16 + 4 + 3 declared methods implemented in the three new classes; CRLF-aware `git diff --check` passed. This cannot establish ABAP activation or execution. |
| Representative fixture parsing | `jq -e '(.d.results \| type) == "array"'` passed on `xsa-filter.json`, `xsa-selection.json`, `xsa-x_format.json`, `xsa-y_format.json`, and `xsa-scope-01.json`. |
| Automated PR validation | No actionable review comments were returned. The validation tool reported its code-review model unavailable and CodeQL found no analyzable source languages in the `.txt` ABAP export; treat both automated review and CodeQL as **NOT EXECUTED**, not as a clean code review/security result. |
| ABAP Unit / activation / ATC | **NOT EXECUTED** — no SAP ABAP system, SAP Gateway runtime, or ATC endpoint is available in this environment. |
| HANA `APPLY_FILTER` | **NOT EXECUTED** — the new class calls the real AMDP and requires HANA; it is not a mock. |
| OData end-to-end / XSA fixture parity | **NOT EXECUTED** — requires the SAP service, configured MIME fixture repository, and system data/configuration. |
| Local build/lint/test command | **NOT AVAILABLE** — no ABAP lint/build/test configuration or ABAP CLI was found in the repository/environment. |
| Download script | **NOT EXECUTED** — `Validation/download-xsa-json.ps1` depends on the external XSA environment and credentials. |
| GitHub Actions investigation | `actions_list` showed the current Copilot run still in progress on the initial-plan commit. A prior failure on `copilot/generic-filter-sort` (run `36745459100`) ended with a Copilot monthly-quota error, not a code/test failure. Its logs were retrieved. |

## Required SAP follow-up (not evidence of current success)

1. Activate changed DPC/dashboard classes and local ABAP Unit classes on the `Complete-refactoring` base; resolve syntax/type errors before running tests.
2. Run ATC for the changed classes and the applicable package.
3. Run ABAP Unit per method in `ltc_request_processing_verified` and `ltc_utility_contracts`; record individual outcomes.
4. Run `ltc_hana_filter_integration` per method on the target HANA release, verifying `APPLY_FILTER`, date typing, escaped quote semantics, and row order.
5. Run `ltc_fi_das_gateway_parity` per method, including `test_scope_01`–`test_scope_30`, all standard/owner methods, formats, selection, counts, paging, and filters. Use the SAP Gateway client for the filter cases in `ABAP code/Test cases.txt`, especially cross-property OR, negation, nested expressions, escaped apostrophes, dates, and no matches.
6. Explicitly compare `$top=0` against omitted `$top`, inline count before paging, page-one plus page-two concatenation versus the combined result, and optimized versus generic-only requests. Re-run the complex filter from the issue using safe synthetic data before asserting parity.

No runtime compatibility, full parity, or “all tests passed” claim is made by this report.
