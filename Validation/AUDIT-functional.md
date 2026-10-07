# Functional test audit (pinned source, not a runtime PASS)

## Scope and evidence

Reviewed every declaration in `ABAP code/Unit test.txt:1-786` and every complete method beginning in `787-3589`: **108 methods**. All line references to Unit test below are to base **c2bf1b3cc171dfe043648d7294d58e9bee78cd45**, not later concurrent edits in the shared checkout. Production files were read from this checkout and are unchanged relative to that base. No Unit test or production source was edited. No SAP/ABAP/HANA/Gateway execution was available or performed; JSON inspection is not ABAP execution. Neither `Validation/REPORT.md` nor an earlier PASS was used as evidence.

Verdicts describe the existing code. **correct** means the stated, narrow assertion follows from the inspected implementation; it does not mean executed. **corrected** means a concrete proposed correction is supplied below, not that it was applied. **limited coverage** means a valid predicate/oracle cannot distinguish an important wrong implementation. **runtime-dependent** means the test additionally needs live SAP data/configuration/framework behavior. A correct integration oracle can still be runtime-dependent; each row spells out that distinction.

### Production dependency key (all paths under `ABAP code/`)

* **P-request** — `zif_fi_das_dashboard.txt:10-60`: modes `1/2/3`, material/service/all `0/9/*`, explicitly separate `top` and `top_requested`; there is **no select-list or skip-calculation request field**. `ZCL_ZFI_DAS_DPC_EXT.txt:57-68,70-97,99-175,177-221` routes requests and copies parameters/filter/sort/paging, creates a new dashboard for each request, and leaves projection to Gateway.
* **P-execute** — `zcl_fi_das_dashboard.txt:992-1085`: validate, adjust, obtain keys, construct results, generic-filter then count then restore paging and sort. `3745-3777`: only a noninitial order or generic predicate requests full processing. No `$select` optimization is active. The comments/constants at `87-94` are stale, not executable evidence.
* **P-page** — dashboard `975-979` accepts a standard table; `1359-1435` accepts valid unique requested fields, appends missing default ties only when a valid requested sort exists, sorts before skip/top, distinguishes requested zero from omitted zero, empties high-skip pages, and clips the tail. `3823-3828` default is PSTYPE descending, PO ascending, item ascending. `3752-3767` removes **any exact prefix** of that default, irrespective of mode; it does not remove ascending PSTYPE.
* **P-keys** — dashboard `610-631,2680-3098,3316-3346`: owner requestor **OR preparer** match at `2740-2744`, effective Japan/Brazil service reclassification at `2719-2730,2747-2800`, owner bypass of role scopes at `2811-2822`, nonowner scope at `2826-2926`. Threshold sums the scoped net values per PO/effective type/currency (`2940-2960`), including JPY/VND x100; conversion `2962-2977`; Over **>**, Under **<=** (`2989-2998`); exclusions `3002-3037`; item predicate after classification `3047-3049`; count before paging `3051-3057`; complete default key order and row-number window `3059-3096`.
* **P-scope** — dashboard `559-590,2127-2144,2279-2300,2330-2355,3100-3124,3482-3493`. Company normalizes uppercase; cost center uses ALPHA input, special NULL marker; management unit retains case and has NULL marker. Sorted unique scope types are `298-324`. Utility `split_list`, `zcl_fi_das_utility.txt:474-484`, condenses spaces and discards empty pieces **without deduplicating before the single-value wildcard test**.
* **P-data** — dashboard `2302-2328,2406-2461,2146-2265,2489-2503,2505-2544,2547-2651,3189-3225,3622-3743`: source details, accounts, history, status, notifications and users are real reads. `ZI_FI_DAS_PO_BASE.txt:8-90` uses global header/item company configuration and replicated source eligibility. `get_row:3495-3608` always applies detail/user/account/history/status/calculation/currency/closure/notification; `get_results:3348-3375` preserves key iteration order and chooses request-user format.
* **P-calc** — dashboard `1120-1174,1437-1533,1559-1754,1769-1930,1933-1983,1985-2015`: status supplies persisted accrual method, service availability controls WTD fallback, persisted STL chooses STL, material has zero work calculation, accrued amount floors at zero. **Closure sets flags, not unconditional zero amounts** (`1158-1174`). History and STL/review calculations depend on current date (`2636-2651,3126-3186,3378-3480`).
* **P-format** — utility signatures `97-107`, implementation `196-356`: magnitude via WRITE/no grouping, normalized decimal point, explicit separator selection, grouping preserving spaces, leading minus and optional sub-ten padding. Dashboard serialization `3228-3293` chooses CHAR displays; requesting user's decimal format is `2366-2404`; row-owner user fields are a separate lookup at `3667-3743`.
* **P-filter** — DPC `99-140`, dashboard `2017-2125,1276-1303`: full predicate takes precedence over range projections; HANA applies generic predicate to constructed OData rows and restores original order. Range-only PO/item/supplier predicates can prefilter; generic range-only properties build a complete predicate. These paths are relevant to membership and value-help tests, not proof of a select optimization.

### Helper chain actually followed

* **H-reset/group** — Unit `5379-5411`: uppercases dynamic method names, catches `cx_root`, records failures with `quit=no`, restores group state; reset constructs a fresh `mo_cut` and clears differences/unused flag. Reset does **not** alter DB data, freeze the clock, seed roles, install MIME fixtures, or change the Gateway dashboard instance. Every leaf in this range resets explicitly; group state intentionally survives leaf reset.
* **H-parity** — `run_scope_case:5413-5426` chooses Over/service/nonowner fixture and email. `run_paged_case:5428-5573` reads MIME, builds expected index, fetches bounded pages, compares every returned key/property, compares each total with expected cardinality, records extra/duplicate/missing keys, bounds runaway paging, and frees page memory. `fetch_gateway_page:5575-5589`, `get_gateway_response:5591-5614`, `build_resource_path:5616-5714`, `append_filter:5716-5774`, `odata_quote:5776-5785`, `execute_gateway_get/raw:5787-5851` are the actual route. A nonempty fixture forces count and bounded top=1000. Comparison is keyed, **not ordered**.
* **H-JSON** — `read_mime_fixture:6344-6391`, `build_expected_index:6393-6523`, `find_results_array_bounds:6525-6581`, `read_json_row_key:6583-6731`, first-key reader `6733-6774`, property readers `6776-6813`, object-bound reader `6271-6342`, property reader `6930-7024`, string/value/bracket readers `7739-7977`, whitespace/trim `7978-8088`, decoder `8090-8205`. Index duplicate detection calls `add_difference`, not an immediate assert. Property reader omits `__metadata`; first-property helper returns an already-decoded value. These are targeted OData readers, not a general JSON validator.
* **H-compare** — `compare_actual_page:6815-6857` rejects repeated expected keys across pages; `compare_raw_object:6859-6928` rejects missing/extra properties except absent `ID`; `compare_raw_property:7026-7186` uses field-specific one-way NULL exceptions (`7188-7453`), time canonicalization (`7455-7594`), absent-ID rule (`7596-7601`) and unordered aggregate multisets (`7603-7737`, preserving duplicate and empty slots); remaining strings are decoded, all other tokens strict. `add_difference/assert_no_differences:8207-8280` counts all mismatches but caps retained diagnostics.
* **H-count/filter/sort** — `read_inline_count:5853-5898` returns zero when count is absent; `get_result_count:5900-5946`; absent-count assert `5948-5955`; filter assert `5957-6026` uppercases both sides and uses ABAP CS for contains; sort assert `6028-6178` numeric PSTYPE/amount, character supplier/reviewer, no tie/key validation; duplicate/page-key helpers `6180-6269`. The filter assertion does not prove case-sensitive contains.
* **H-select** — `check_select:8304-8375` fetches selected first row, reads PO/item, obtains full row with key filter, asserts each requested property exists and equals that full row, checks nonempty/non-NULL STATUS, and checks count absent. It does not assert nonselected fields are absent, calculate an independent status/amount oracle, or inspect a nonexistent calculation-skip flag. Its auxiliary callees are H-JSON and the same Gateway chain.
* **Additional transitive helpers** — `extract_range:8282-8295`, `filter_rows:8297-8302`, `matches_complex_fixture:8377-8430` were read; the latter is only used by optional complex-filter parity paths, never by the standard/owner/scope/format cases audited here. Group methods also dispatch leaves outside the assigned body range; this document verifies those target names/declarations but does not substitute a grouped verdict for their separate functional review.

## Confirmed test/oracle corrections and precise strengthening snippets

These are proposals only. Do not change production expectations to make a failing parity test pass.

### F1 — `sort_adds_default_ties:2902-2926` does not discriminate the default ties

Both existing `Same` rows have different PSTYPE **and** naturally ascending PO numbers in the same expected order. Ignoring PSTYPE still passes; there is no same-PO/different-item witness. Replace Arrange/Act/assertions in this method with the following to force every tie level and the page boundary. Add a second unpaged call if retaining the method's unpaged role is desired.

```abap
DATA(lt_input) = VALUE zcl_fi_das_dashboard=>tt_odata_result(
  ( ponumber = '8000000001' itemno = '00001' pstype = '0' suppliername = 'Same' )
  ( ponumber = '8000000004' itemno = '00001' pstype = '9' suppliername = 'Same' )
  ( ponumber = '8000000002' itemno = '00002' pstype = '9' suppliername = 'Same' )
  ( ponumber = '8000000002' itemno = '00001' pstype = '9' suppliername = 'Same' )
  ( ponumber = '8000000005' itemno = '00001' pstype = '0' suppliername = 'Other' ) ).
DATA(lt_expected) = VALUE zcl_fi_das_dashboard=>tt_odata_result(
  ( ponumber = '8000000005' itemno = '00001' pstype = '0' suppliername = 'Other' )
  ( ponumber = '8000000002' itemno = '00001' pstype = '9' suppliername = 'Same' )
  ( ponumber = '8000000002' itemno = '00002' pstype = '9' suppliername = 'Same' )
  ( ponumber = '8000000004' itemno = '00001' pstype = '9' suppliername = 'Same' )
  ( ponumber = '8000000001' itemno = '00001' pstype = '0' suppliername = 'Same' ) ).
DATA(lt_result) = lt_input.
mo_cut->apply_sort_and_paging(
  EXPORTING is_request = VALUE #(
    orderby = VALUE #( ( property = `SUPPLIERNAME` ) ) )
  CHANGING ct_result = lt_result ).
cl_abap_unit_assert=>assert_equals(
  quit = mv_assert_quit act = lt_result exp = lt_expected ).
DATA lt_joined TYPE zcl_fi_das_dashboard=>tt_odata_result.
DO 3 TIMES.
  DATA(lv_skip) = ( sy-index - 1 ) * 2.
  lt_result = lt_input.
  mo_cut->apply_sort_and_paging(
    EXPORTING is_request = VALUE #(
      orderby = VALUE #( ( property = `SUPPLIERNAME` ) )
      paging = VALUE #( skip = lv_skip top = 2 top_requested = abap_true ) )
    CHANGING ct_result = lt_result ).
  APPEND LINES OF lt_result TO lt_joined.
ENDDO.
cl_abap_unit_assert=>assert_equals(
  quit = mv_assert_quit act = lt_joined exp = lt_expected ).
```

Production evidence: P-page `1390-1410,1414-1432`. Whole-table equality proves cardinality, full membership and order, rather than only an endpoint.

### F2 — Two-page checks are not complete paging membership oracles

Affected leaves: `test_inlinecount_with_top_one:1849-1922`, `test_filter_sort_and_paging:2076-2126`, `test_under_paging:2128-2190`, `test_excl_paging:2192-2254`, `test_excl_pstype_pages:2355-2453`; `default_exclude_key_order:3059-3129` samples four positions. Existing row counts/count stability/nonoverlap do not prove every key is returned or that pages equal the correct windows. The independent fixture membership checks in the standard cases help, but do not validate **these alternate sorts**.

* For `test_excl_pstype_pages`, capture `e_inline_count` for all four requests, assert equal totals and exact cardinalities `min(100,total)` / `min(100,max(0,total-100))`, and only dereference a boundary when both pages are nonempty. Require a positive second-page witness when testing that boundary. Add duplicate checking in both directions. Do not silently skip an intended boundary fixture.
* At each integration leaf using `assert_no_duplica_across_pages`, add `assert_no_differences( )` after the last helper call (base insertion sites before `1922`, `2126`, `2190`, `2254`; also before `2453` after adding the duplicate checks). Its `build_expected_index` calls can record **within-page** duplicates without asserting; the two-page helper only asserts an intersection. Thus a page with 100 physical rows and 99 distinct keys currently need not fail.
* For complete membership, use `run_paged_case` with the matching fixture and predicate/orderby, followed by `assert_no_differences`; that proves all keys once, count and raw values but still needs an ordered window oracle. Example addition in `test_filter_sort_and_paging`:

```abap
" Independently retain only JPY rows from the complete fixture index
" (read properties at stored offsets); compare all returned sorted pages.
" Extend run_paged_case with an optional expected-property predicate rather
" than passing the unfiltered 20131-row fixture to a filtered request.
```

The comment above is a design instruction, not executable ABAP. An immediately applicable **complete ordered** check already fits the existing `default_exclude_key_order` oracle: replace its four-position list at `3090-3091` with:

```abap
DATA lt_positions TYPE STANDARD TABLE OF i WITH EMPTY KEY.
DO lines( lt_order ) TIMES.
  APPEND sy-index TO lt_positions.
ENDDO.
```

This retains the existing count/type/PO/item assertions at each position and tests every item once in default order. It is bounded-memory but performs 3254 requests on the recorded fixture; a production-sized implementation should instead read bounded pages and compare every page row to the corresponding `lt_order` entry. The same ordered approach applies to ascending PSTYPE, supplier and amount sorts, with typed numeric amount comparison. P-keys `3059-3096`, P-page `1390-1432` are the exact ordering contracts.

### F3 — Explicit zero versus omitted top: strengthen, do not reverse expectations

`test_top_zero:2021-2074` preserves `top_specified=true` when copying the case; its URI really contains `$top=0`. Correct. However, both baseline and zero response could be empty/count zero and pass. Add after the first request:

```abap
cl_abap_unit_assert=>assert_equals(
  quit = mv_assert_quit act = get_result_count( lv_json_full ) exp = 1 ).
cl_abap_unit_assert=>assert_true(
  quit = mv_assert_quit act = xsdbool( lv_count_full > 0 ) ).
```

The four direct zero/omitted tests (`2673-2700,2979-3005`) correctly separate requested from omitted zero, but omitted variants only assert the row count. Preserve a copy before Act and assert whole-table equality afterward. To cover the untested Gateway omission, start from `ls_case_full`, clear `top_specified`, set `top=0`, and **leave fixture initial**: H-URI `5669-5675` then omits `$top`. Compare returned key membership/count against an independently complete fixture, not against a different first-page request. Omitting a top while leaving `fixture` set is not an omission test: fixtures force bounded top=1000.

DPC `153-165` infers requestedness from `get_top()`'s inferred return type. This repository does not contain the installed `/iwbep/if_mgw_req_entityset` signature. If it returns string/character `'0'`, `IS NOT INITIAL` is true; if numeric zero, requestedness is lost. **Do not report a confirmed production defect merely from this expression.** The live SAP signature and actual zero/omitted requests are needed. Dashboard/AMDP zero semantics themselves are confirmed by P-page `1417-1420` and P-keys `3074-3096`.

### F4 — Selection coverage after removal of optimization

`skip_true_for_*:3409-3425` calls are **not stale true assertions**: all delegate to H-select and assert selected/full field equivalence. Retain their behavior; rename misleading methods and group string targets together if names are changed. Do not introduce a skip flag: P-request contains none; P-data `3495-3608` always calculates.

At `check_select:8352-8373`, checking only requested fields allows Gateway to ignore `$select` and return every column. For the five select lists used here, `POVALUE` is never selected and is not a key. Add after that loop:

```abap
cl_abap_unit_assert=>assert_false(
  quit = mv_assert_quit
  act = xsdbool( line_exists( lt_selected[ name = 'POVALUE' ] ) )
  msg = 'Gateway must omit a nonselected nonkey property' ).
```

`skip_false_without_select:3427-3451` only requires noninitial decoded AMOUNTACCRUED; a textual `'null'` also satisfies that test. Add an exact non-NULL token check using `read_object_properties`, as H-select already does for STATUS at `8368-8371`; do **not** require amount >0, because legitimate zero is valid. For independent calculated-field coverage use known nonzero fixture row/status and compare to the XSA oracle, not merely the same full production path.

`test_all_pstype_request:3339-3407` verifies sum of counts and allowed type values, not exact set identity. A wrong subset of the same size passes. Immediately after fetching each single and filtered combined page (`3384-3385`), add:

```abap
cl_abap_unit_assert=>assert_equals(
  quit = mv_assert_quit
  act = get_result_count( lv_combined )
  exp = get_result_count( lv_single ) ).
DO get_result_count( lv_single ) TIMES.
  DATA(lv_index) = sy-index.
  assert_row_keys_match(
    i_json_left = lv_single i_left_index = lv_index
    i_json_right = lv_combined i_right_index = lv_index ).
ENDDO.
```

This discriminates the first 1000-row windows, not the complete >1000 sets. Iterate all remaining bounded pages with stable total/count and unique seen keys for complete coverage; use independent standard fixture sets for each type as the membership oracle.

### F5 — Predicate assertions must follow actual predicate semantics

`assert_all_rows_match_filter:5957-6026` makes `substringof('Fuji',...)` and `substringof('Lee Hecht',...)` case-insensitive by uppercasing and CS. The request predicate is case-sensitive; equal/contains behavior must not be conflated. For contains only, replace `lv_actual CS lv_expected` at `6009` with the following, retaining case-normalization in the EQ branch where intended:

```abap
act = xsdbool( find(
  val = unquote_json( <ls_property>-token )
  sub = i_value
  case = abap_true ) >= 0 )
```

Affected assigned leaves: `test_po_value_help`, `test_item_value_help`, `test_supplier_value_help`, `test_under_po_help`, `test_excl_po_help`, `test_under_supplier_help`. PO/item digits are insensitive to this distinction but supplier names are not. The corrected positive-witness checks still do not independently prove complete filtered membership or projection.

### F6 — Numeric-sort and reviewer-sort vacuity

`test_sort_amountaccrued:2503-2537` and `test_sort_reviewed_by:2539-2573` only require `count >= rows`; `assert_rows_sorted` accepts zero or one row. Add `rows >= 2` plus at least two **distinct sort values** as an Arrange/witness assertion, or replace with a known synthetic two-value helper case while keeping the Gateway smoke test. Merely asserting rows>0 still cannot distinguish a no-op sorter when all values tie. Test reviewer property `REVIWED_BY` is correctly spelled for the actual migrated contract (`get_odata_row:3233`).

### F7 — Shared JSON/sort helper defects must not be papered over in leaves

`assert_rows_sorted:6058-6066` calls `read_result_property` (already decoded at `6809-6811`) and then `unquote_json` again. Replace that second decode with `lv_current = lv_token`. Otherwise a legitimate string containing literal surrounding quotes is changed before the oracle comparison.

`unquote_json:8153-8203` does multiple global replacements. A JSON encoded literal backslash followed by `n` (`"\\n"`) must decode to backslash+n, but replacing `\n` before `\\` corrupts it into backslash+newline. It needs a **single-pass JSON escape decoder** that consumes escapes atomically; simply reversing replacement order corrupts other sequences. Include escape-witness cases for `"\\n"`, `"\\u0026"`, `"\""`, and `"\u0026"` before treating parity/sorting as general escaped-string coverage. Other JSON audit work owns the full decoder patch; this functional matrix does not claim that this defect is exercised by every recorded fixture.

### F8 — Requested count absence must not masquerade as count zero

`read_inline_count:5866-5868` returns initial zero when `__count` is absent. H-Gateway calls this parser only when count was requested or a fixture forced it (`5605-5610`). Thus empty scope fixtures can pass despite a missing required count. Replace that RETURN branch with:

```abap
IF sy-subrc <> 0.
  RAISE EXCEPTION TYPE zcx_fi_das_error
    EXPORTING i_reason = 'Requested inline count is absent from Gateway response'.
ENDIF.
```

The existing signature already raises this exception. `test_no_inlinecount` is unaffected: its request does not call this parser. Preserve explicit `"0"` as valid. This fixes count-presence discrimination, not the missing-role false confidence in empty scope tests.

Before `run_paged_case` in `run_scope_case:5422`, add a read-only role precondition after the case email is assigned:

```abap
SELECT COUNT( * ) FROM zfi_das_roles
  WHERE user_emailid = @ls_case-email
  INTO @DATA(lv_role_rows).
cl_abap_unit_assert=>assert_equals(
  quit = mv_assert_quit act = lv_role_rows exp = 1
  msg = |Scope fixture requires exactly one configured role for { ls_case-email }| ).
IF lv_role_rows <> 1.
  RETURN.
ENDIF.
```

This respects the one-role-per-user invariant, performs no DB mutation, and prevents missing-role empty results from passing as scope semantics. The exact intended role triple must still be checked against the fixture setup specification; it cannot be invented from an empty output.

## Per-method matrix

All source ranges below refer to Unit test at the pinned base. `R` means H-reset plus the appropriate production/helper references above; integration limits include real registered Gateway metadata, MIME upload and aligned source/clock/configuration. A matrix entry is not a grouped PASS.

| Method / source range | Verdict | Arrange + predicate + Act + expected/assert discrimination evidence | Helper / production dependencies | Limits |
|---|---|---|---|---|
| all_tests 787-952 | correct | Dispatches all 164 declared leaf names, each uppercase dynamic target exists; collects failures while continuing. | H-reset/group; all leaf helpers | Other leaves' bodies are outside this assigned matrix; duplicated native/group execution is intentional. |
| standard 954-960 | correct | Dispatches exactly five nonowner flow/type parity leaves; no wrong owner target. | H-reset/group; H-parity | Aggregate wrapper, not independent data coverage. |
| owner 962-968 | correct | Dispatches all five owner parity leaves. | H-reset/group; P-keys owner OR | Aggregate wrapper; each leaf's runtime data remains required. |
| filter 970-1044 | correct | Dispatches filter/request/HANA/select/paging/scope leaves named in declarations, including cross-OR and company parity. | H-reset/group; P-filter | Broad wrapper is valid, not evidence its unassigned targets are correct. |
| scope 1046-1079 | correct | All scope01..30 plus wildcard and normalization dispatched exactly. | H-reset/group; H-parity; P-scope | No role seeding in wrapper. |
| sort_paging 1081-1118 | correct | All 36 declared paging/sort leaves dispatched; both zero/omitted pairs included. | H-reset/group; P-page | No independent paging oracle. |
| selection 1120-1136 | correct | All 15 selection leaves dispatched; string targets match declared names. | H-reset/group; H-select | Misleading skip names do not implement a skip flag. |
| format 1138-1143 | correct | Three owner fixtures and pure numeric-format matrix dispatched. | H-reset/group; P-format | Does not configure user defaults. |
| request_processing 1145-1178 | correct | Declared range/threshold/review/predicate targets all resolve. | H-reset/group; P-filter | Leaf-body review outside 3589 is separately required. |
| hana_filter 1180-1206 | correct | Declared HANA filter and hybrid parity targets all resolve. | H-reset/group; P-filter | HANA execution unavailable. |
| utility 1208-1211 | correct | Dispatches the two declared utility leaves, catches errors/continues. | H-reset/group | Does not itself assert utility arithmetic. |
| test_over_material 1216-1238 | runtime-dependent | Adam/nonowner/Over/0 with over-material fixture, 2019 unique keys; complete keyed property parity plus counts/missing/extra/duplicates. | R; H-parity/H-compare; P-keys/P-data | Correct fixture/request; no deterministic threshold-equality or ordered oracle; aligned DB/date required. |
| test_over_service 1240-1262 | runtime-dependent | Adam/nonowner/Over/9, over-service fixture, 20131 unique keys; all bounded pages compared. | R; H-parity/H-compare; P-keys/P-calc | Correct oracle; snapshot arithmetic/notifications can drift; no explicit equality tie witness. |
| test_under_material 1264-1286 | runtime-dependent | Adam/nonowner/Under/0, under-material fixture 78861 keys; strict full membership/values/count. | R; H-parity; P-keys <= / P-calc | Correct fixture, no injected threshold tie; not an assertion that every Under amount is zero. |
| test_under_service 1288-1310 | runtime-dependent | Adam/nonowner/Under/9, under-service fixture 40030 keys; all actual rows/raw fields matched once. | R; H-parity; P-calc persisted method | Correct oracle; do not force STL or closure zero; clock/source drift must be distinguished. |
| test_exclude 1312-1334 | runtime-dependent | Adam/nonowner/exclude/all, exclude fixture 3254 keys; complete key/value parity and count. | R; H-parity; P-keys exclusion; P-data | Both effective types present; keyed comparison ignores ordering. |
| test_over_material_owner 1339-1363 | runtime-dependent | Anita/owner X/Over/0, matching owner fixture 36 keys; full parity. | R; H-parity; P-keys 2740-2744 | Correct fixture; owner means requestor OR preparer, not exclusive POOWNER_EMAIL. |
| test_over_service_owner 1365-1389 | runtime-dependent | Elisa/owner X/Over/9, matching 61-row fixture; parity accepts mixed requestors retained via preparer. | R; H-parity; P-keys owner OR | Correct choice; asserting every row's owner email equals Elisa would be wrong. |
| test_under_material_owner 1391-1415 | runtime-dependent | Katarina/owner X/Under/0, matching 129-row fixture; full parity. | R; H-parity; P-keys/P-data | Correct choice; current thresholds/source must match snapshot. |
| test_under_service_owner 1417-1441 | runtime-dependent | Teresa **scoggin**/owner X/Under/9, matching 100-row fixture and download URI; complete parity. | R; H-parity; P-keys/P-calc | Email is correct, not a typo; recorded 100 rows alone does not prove live total remains 100. |
| test_exclude_owner 1443-1467 | runtime-dependent | Alta/owner X/exclude/all, matching 74-row fixture, mixed requestors allowed; full parity. | R; H-parity; P-keys owner OR/exclusion | Correct choice; preparer relationship needed in source data. |
| test_scope_01 1472-1475 | limited coverage | Reset; scope01 email/fixture; expects no keys/count0. | H-parity/H-scope; P-scope | Empty fixture also passes for missing role or wholly broken/empty source. |
| test_scope_02 1477-1480 | runtime-dependent | scope02, Over/9/nonowner; complete parity of 280 fixture keys. | H-scope/H-parity; P-scope/P-keys | Positive discrimination, but role values are not arranged or asserted. |
| test_scope_03 1482-1485 | limited coverage | scope03 fixture expects empty/count0. | H-scope/H-parity; P-scope | Cannot distinguish intended NULL behavior from missing role/source. |
| test_scope_04 1487-1490 | limited coverage | scope04 fixture expects empty/count0. | H-scope/H-parity; P-scope | No independent config or positive companion witness in leaf. |
| test_scope_05 1492-1495 | limited coverage | scope05 fixture expects empty/count0. | H-scope/H-parity; P-scope | Missing role also produces empty scopes. |
| test_scope_06 1497-1500 | runtime-dependent | scope06 fixture has 4 keys; exact keyed/raw parity. | H-scope/H-parity; P-scope | Correct matching case; actual role literals not checked. |
| test_scope_07 1502-1505 | runtime-dependent | scope07 fixture has 317 keys; all compared and count317. | H-scope/H-parity; P-scope | Correct oracle conditional on aligned role/source. |
| test_scope_08 1507-1510 | runtime-dependent | scope08 fixture has 280 keys; exact parity. | H-scope/H-parity; P-scope | Same cardinality as02 is not proof of same role semantics. |
| test_scope_09 1512-1515 | runtime-dependent | scope09 fixture has 4 keys; exact parity. | H-scope/H-parity; P-scope | Positive keys distinguish global empty response; role arrangement external. |
| test_scope_10 1517-1520 | limited coverage | scope10 fixture empty; rejects extras but permits empty/count0. | H-scope/H-parity; P-scope | No proof email has its intended role. |
| test_scope_11 1522-1525 | runtime-dependent | scope11 fixture 8 keys; complete comparison. | H-scope/H-parity; P-scope | Positive oracle, current account/CSKS validity required. |
| test_scope_12 1527-1530 | runtime-dependent | scope12 fixture 8 keys; complete comparison. | H-scope/H-parity; P-scope | Correct matched number; no direct asserted role contents. |
| test_scope_13 1532-1535 | limited coverage | scope13 empty/count0 parity. | H-scope/H-parity; P-scope | Missing role yields same observable result. |
| test_scope_14 1537-1540 | runtime-dependent | scope14 fixture 8 keys; exact count and raw values. | H-scope/H-parity; P-scope | Correct oracle; role literals not recoverable from output alone. |
| test_scope_15 1542-1545 | limited coverage | scope15 empty/count0 parity. | H-scope/H-parity; P-scope | Empty-source/missing-role false confidence possible. |
| test_scope_16 1547-1550 | runtime-dependent | scope16 fixture 20131 keys; complete positive set comparison. | H-scope/H-parity; P-scope | Correct oracle; full set does not independently establish wildcard role setup. |
| test_scope_17 1552-1555 | limited coverage | scope17 empty/count0 parity. | H-scope/H-parity; P-scope | Role/source absent indistinguishable from intended exclusion. |
| test_scope_18 1557-1562 | runtime-dependent | scope18 fixture 4 keys; exact parity. | H-scope/H-parity; P-scope | Correct number/email coupling; external role setup. |
| test_scope_19 1564-1569 | limited coverage | scope19 empty/count0 parity. | H-scope/H-parity; P-scope | No role assertion. |
| test_scope_20 1571-1576 | limited coverage | scope20 empty/count0 parity. | H-scope/H-parity; P-scope | No independent positive control. |
| test_scope_21 1578-1583 | runtime-dependent | scope21 fixture 4 keys; complete parity. | H-scope/H-parity; P-scope | Positive oracle; cannot infer intended role CSV from these keys. |
| test_scope_22 1585-1590 | limited coverage | scope22 empty/count0 parity. | H-scope/H-parity; P-scope | Missing role also empty. |
| test_scope_23 1592-1597 | runtime-dependent | scope23 fixture 20131 keys; complete positive parity. | H-scope/H-parity; P-scope | Correct oracle; role and current source externally supplied. |
| test_scope_24 1599-1604 | runtime-dependent | scope24 fixture 4 keys; complete comparison. | H-scope/H-parity; P-scope | Correct matching fixture/email; no config precondition. |
| test_scope_25 1606-1611 | runtime-dependent | scope25 fixture 42 keys; exact parity. | H-scope/H-parity; P-scope | Role setup required; distinct count is not a config oracle. |
| test_scope_26 1613-1618 | limited coverage | scope26 empty/count0 parity. | H-scope/H-parity; P-scope | Empty system can pass. |
| test_scope_27 1620-1625 | runtime-dependent | scope27 fixture 4 keys; complete positive parity. | H-scope/H-parity; P-scope | Correct request; role assertion missing. |
| test_scope_28 1627-1632 | limited coverage | scope28 empty/count0 parity. | H-scope/H-parity; P-scope | No guard against missing role. |
| test_scope_29 1634-1639 | limited coverage | scope29 empty/count0 parity. | H-scope/H-parity; P-scope | No guard against missing role/source. |
| test_scope_30 1641-1646 | limited coverage | scope30 empty/count0 parity. | H-scope/H-parity; P-scope | No guard against missing role; correctness needs configured intended role. |
| single_star_wildcard 1648-1664 | correct | Pure `*` gives wildcard; mixed `*,ab01` gives no wildcard and literal `*` member. | R; P-scope company; utility split_list | Narrow wildcard distinction correct; no all-field or duplicate-star witness here. |
| scope_field_normalization 1666-1844 | correct | Uppercase/ALPHA/case-preserving MU, empty CSV, duplicates, NULL markers, mixed literal star and sole effective star checked with exact counts/members. | R; P-scope; utility474-484 | Does not test SQL NULL joins, role access, or duplicate `*,*` semantics; those are not implied. |
| test_inlinecount_with_top_one 1849-1922 | limited coverage | Over9 top1/count at skip0/1; one row each, total>1 stable, keys distinct. | R; H-count/H-page-keys; P-keys | Valid count assertion; not complete membership/order and helper differences not finalized (F2). |
| test_no_inlinecount 1924-1966 | runtime-dependent | Over9 top1 without count; asserts no __count, parsed count0, one row. | R; H-count; P-request/P-keys/P-execute | Correct omission oracle; one positive live row required. |
| test_skip_beyond_result_set 1968-2019 | limited coverage | Over9 top1/count; skip999999 response empty and count equals first request. | R; H-count; P-page/P-keys | Both empty/count0 can pass; assumes total<999999 rather than deriving skip from total. |
| test_top_zero 2021-2074 | corrected | Copied case keeps top_requested; requested0 must empty while count equals top1 baseline. | R; H-URI/H-count; P-page/P-keys | Correct zero semantics; baseline can be empty (F3); Gateway signature remains runtime-dependent. |
| test_filter_sort_and_paging 2076-2126 | limited coverage | JPY Over9 supplier asc, top100 skip0/100; positive first page, counts stable, predicates/sort/boundary/nonoverlap. | R; H-filter/H-sort/H-page-keys; P-filter/P-page | Exact window sizes/full set/ties not proved; JPY fixture has661 positive witnesses; F2/F5/F7. |
| test_under_paging 2128-2190 | limited coverage | Under9 top100 skip0/100; both100, same count, no overlap, boundary keys differ. | R; H-count/H-page-keys; P-keys | Needs >=200 live keys; valid narrow oracle but lost/replaced windows pass; F2. |
| test_excl_paging 2192-2254 | limited coverage | Exclude/all top100 skip0/100; both100, stable count, no overlap, boundary unequal. | R; H-count/H-page-keys; P-keys | Needs >=200 keys; does not prove complete membership/default ties; F2. |
| test_exclusion_pstype_desc 2256-2304 | runtime-dependent | Exclude/all top100 order PSTYPE desc; page sorted and first type9. | R; H-sort/H-count; P-page/P-keys | Correct service-first expectation; first page alone does not test material group or ties; F7. |
| test_exclusion_pstype_asc 2306-2353 | runtime-dependent | Exclude/all top100 PSTYPE asc; sorted and first type0. | R; H-sort; P-page generic sort | Correct material-first expectation; needs material witness, not full ordering; F7. |
| test_excl_pstype_pages 2355-2453 | corrected | Four top100 pages, PSTYPE asc/desc, per-page sort plus boundary inequality. | R; H-sort/H-properties; P-page/P-keys | F2: discarded counts, no sizes/nonoverlap/full membership; repeated identical pages can pass; empty boundary throws. |
| test_orderby_invalid 2455-2501 | runtime-dependent | Raw request NOT_A_COLUMN; HTTP400, error text, no “SHORT DUMP”, nonempty status text. | R; H-URI/H-Gateway; P-request; Gateway metadata | Dashboard ignores invalid component, but Gateway rejects invalid metadata property before it; no contradiction. Status and serialized error contract need SAP verification. |
| test_sort_amountaccrued 2503-2537 | corrected | Over9 amount desc top100; count>=rows; numeric adjacent sorted comparison. | R; H-sort; P-page amount field | F6: empty/single/all-equal passes; numeric comparison correct, no tie or exact windows; F7. |
| test_sort_reviewed_by 2539-2573 | corrected | Over9 REVIWED_BY desc top100; count>=rows; character adjacent sorted comparison. | R; H-sort; P-data3233/P-page | Property spelling correct; F6: empty/all-blank page passes; F7 double decoding. |
| test_skip_high_sorted 2575-2610 | runtime-dependent | Over9 supplier asc skip999999 top100; rows0, total>0. | R; H-count; P-execute/P-page | Positive total guard correct; assumes total<999999, not a complete sort/count oracle. |
| sort_ascending_with_paging 2612-2634 | correct | C,A,B with unique keys; supplier asc skip1/top1 produces exactly Bravo. | R; P-page | Discriminates sort-before-page; no tie witness. |
| sort_descending 2636-2650 | limited coverage | A,B supplier desc must first Bravo. | R; P-page | Valid ordering assertion, but dropped Alpha or extra rows not rejected. |
| sort_unknown_property_no_dump 2652-2671 | correct | PO2,PO1 and invalid component; count2 and firstPO2 prove ignored/no sort. | R; P-page1372-1383 | Direct helper contract, not Gateway metadata behavior; second-row contents not compared. |
| top_zero_requested_empty 2673-2685 | correct | Two rows and requested top0; table must empty. | R; P-page1417-1420 | Direct helper path only; no inline count/Gateway requestedness. |
| top_zero_not_requested_all 2687-2700 | limited coverage | Two rows, top0 default false; count remains2. | R; P-page | Correct omitted semantics; wrong two-row contents would pass; F3 whole-table equality. |
| paging_window_boundaries 2702-2730 | correct | Ten numbered keys; PO asc skip8/top5 clips to exactly PO09,PO10. | R; P-page | Positive tail boundary and values discriminated; no ties or skip exactlyN. |
| no_orderby_leaves_table_asis 2732-2749 | correct | PO2,PO1 empty request; count2 and firstPO2 prove no implicit default sort. | R; P-page1391/P-keys default order separate | Direct helper preserves caller input; does not contradict default AMDP ordering. |
| pstype_sort_noop_for_over 2751-2767 | runtime-dependent | Over/PSTYPE desc removed; full processing false; then selected/detail equivalence via check_select. | R; P-page/P-execute; H-select | First two asserts deterministic and correct default-prefix behavior; last is live select, not optimization evidence. |
| pstype_sort_kept_for_exclude 2769-2791 | limited coverage | Mixed0/9/0 rows; direct desc sorter first9, secondPO1. | R; P-page | Correct helper outcome; **never calls remove_default_sorting**, so name “kept” does not prove exclusion order survives adjustment. |
| pstype_sort_desc_mixed_rows 2793-2815 | correct | 0,9,9; PSTYPE desc then skip2/top1 yields single material0. | R; P-page | Discriminates sort before paging; does not test tie order within service. |
| skip_high_sorted 2817-2831 | correct | Two supplier rows; sorted skip999999/top100 => empty. | R; P-page1422-1424 | Known in-memory cardinality makes high skip valid; no count assert needed. |
| default_order_unique_keys 2833-2868 | correct | get_default_orderby returns exactly three fields, exact names/directions9desc/POasc/itemasc. | R; P-page3823-3828 | Tests metadata, not actual SQL key ordering or uniqueness enforcement. |
| default_prefix_removed 2870-2879 | correct | Default first component PSTYPE desc, initial mode; removal clears order. | R; P-page3752-3767 | Mode-independent prefix contract correct; no test of all prefixes/mismatch later. |
| non_default_order_preserved 2881-2900 | correct | PO desc mismatches default first component; retains exact single field/direction. | R; P-page3752-3767 | No mixed default-prefix plus nondefault suffix witness. |
| sort_adds_default_ties 2902-2926 | corrected | Other then two Same rows; expected all three PO endpoints. | R; P-page1390-1410 | F1: PSTYPE and PO correlated, item untied; exact multi-level page oracle proposed. |
| invalid_duplicate_sorts 2928-2954 | correct | Unknown component then supplier asc then duplicate supplier desc; count2 exact A,B. | R; P-page1372-1388 | Discriminates first-valid-duplicate direction wins; no default tie witness. |
| paging_follows_sort 2956-2977 | correct | PO3,PO1,PO2; POasc skip1/top1 returns onlyPO2. | R; P-page | Discriminates sorting after paging mutation; no filtering/DB path. |
| requested_top_zero_is_empty 2979-2990 | correct | Single row explicit requested0 -> empty. | R; P-page | Duplicate coverage with2673, not a defective expectation. |
| omitted_top_keeps_all_rows 2992-3005 | limited coverage | Two rows explicit omitted0 -> count2. | R; P-page | F3 compare complete copied input; no Gateway omission exercised. |
| empty_order_preserves_input 3007-3024 | correct | PO2,PO1 empty request; first and second PO retained exactly. | R; P-page | Does not explicitly assert cardinality, but both accesses catch dropping; appended row undetected. |
| key_table_preserves_order 3026-3057 | correct | tt_key standard table literalPO3/PO1/PO2; count3 and each position plus firsttype9. | R; P-keys type288 | Type invariant only; does not invoke actual key retrieval. |
| default_exclude_key_order 3059-3129 | limited coverage | Sort real 3254 fixture keys by9desc/PO/item; sample first/lastservice/firstmaterial/last; top1 count/keys exact. | R; H-JSON/H-Gateway; P-keys | Strong boundary witness both types; middle reordering/lost/replaced keys not covered. F2 complete-position proposal. |
| test_selection 3134-3147 | runtime-dependent | Over9 PO8000401022/item00002/containsFuji; one-row selection fixture matches full keyed raw parity. | R; H-parity/H-URI; P-filter/P-keys | Correct conjunction and fixture (supplier Fujifilm); method is filter selection, not a `$select` test. |
| test_select_calc_status 3149-3153 | limited coverage | Select PO,item,STATUS; selected first key's fields equal full lookup; STATUS present/nonempty/non-NULL. | R; H-select; P-data/P-calc | Valid projected value equivalence; shared wrong status can pass; F4 no independent arithmetic/projection omission oracle. |
| test_po_value_help 3155-3178 | limited coverage | Over9 substring40102 PO, selects PO/desc top50; positive rows, count>=rows, all match. | R; H-Gateway/H-filter; P-filter/P-keys | No exact full membership, upper bound or projection absence oracle; F4/F5. |
| test_item_value_help 3180-3203 | limited coverage | Over0 substring00002 item, selectITEMNO top50; positive rows/count/predicate. | R; H-Gateway/H-filter; P-filter/P-keys | Correct zero-preserving digit predicate; no selection-absence or full key oracle. |
| test_supplier_value_help 3205-3228 | corrected | Over9 substringFuji, select supplierID/name top50; positive/count/matching rows. | R; H-filter; P-filter/P-data | F5 case-sensitive assertion mismatch; missing projection/membership assertions. |
| test_under_po_help 3230-3270 | limited coverage | Under9 substring89065 PO; selectsPO/desc top50, positive/count/predicate. | R; H-filter/H-Gateway; P-filter/P-keys | Correct predicate; live matching rows required, no complete membership/projection. |
| test_excl_po_help 3272-3312 | limited coverage | Exclude/all substring98339 PO; selectPO/desc top50, positive/count/predicate. | R; H-filter/H-Gateway; P-filter/P-keys | Correct predicate; no full membership/projection/size ceiling. |
| test_under_supplier_help 3314-3337 | corrected | Under9 substringLee Hecht, select supplier fields top50, positive/count/predicate. | R; H-filter; P-filter/P-data | F5 contains case mismatch; no complete set/projection checks. |
| test_all_pstype_request 3339-3407 | corrected | Over* page0 top1000 allowed0/9, both single-type positive counts, combined filtered subsets same totals, sum equalsall. | R; H-Gateway/H-filter; P-keys effective types | F4 cardinalities cannot establish subset identity or complete union; no old filter leaks (cleared3399). |
| skip_true_for_po_value_help 3409-3413 | limited coverage | SelectPO,item,desc through check_select, same-key full-field equivalence. | R; H-select; P-request/P-data | Correct present behavior; name stale, no skip flag/assertion; F4 omitted-field check. |
| skip_true_for_item_value_help 3415-3419 | limited coverage | SelectPO,item through check_select; projected keys match full row. | R; H-select; P-request/P-data | Name stale only; does not prove calculation optimization, which was removed. |
| skip_true_for_supplier_help 3421-3425 | limited coverage | SelectPO,item,supplierID/name; same-key full values checked. | R; H-select; P-request/P-data | Correct field equivalence; no select-absence oracle; F4. |
| skip_false_without_select 3427-3451 | corrected | Unselected Over9 top1; one row, noninitial STATUS/amount. | R; H-properties/H-Gateway; P-data/P-calc | F4 textual null satisfies noninitial; legitimate0 must remain valid; no independent calculated oracle. |
| skip_false_for_mixed_select 3453-3457 | limited coverage | SelectPO,item,STATUS through check_select; same-key STATUS nonempty/non-NULL. | R; H-select; P-data/P-calc | Valid equivalence, not proof a removed optimization is false; F4. |
| skip_false_with_orderby 3459-3470 | runtime-dependent | SelectPO,item with supplierorder, full-row key lookup; direct nondefault order=>full processingtrue. | R; H-select; P-execute3745-3749 | Direct predicate correct; live select equality limited, no skip flag. |
| test_y_format 3475-3499 | runtime-dependent | Agnieszka/owner X/Under0, matching y-format fixture6 keys, full raw parity. | R; H-parity/H-compare; P-format/P-data | Correct fixture; request-user format must beY and source snapshot aligned, not seeded by reset. |
| test_x_format 3501-3525 | runtime-dependent | Anchalee/owner X/Over9, matching x-format fixture5 keys, full raw parity. | R; H-parity/H-compare; P-format/P-calc | Correct fixture; user defaults/date affect expected amount strings. |
| test_empty_format 3527-3551 | runtime-dependent | Ana/owner X/Under0, matching empty-format fixture381 keys, mixed requestors via preparer allowed. | R; H-parity/H-compare; P-format/P-keys | Correct owner request; empty configured format differs from missing-user fallbackX. |
| amount_format_x_y_default 3553-3585 | correct | Ten exact cases: X/Y/space separators, multigroupY, no groupingY, all negative formats, negative nongroupedY, zeroY; equality of complete strings. | R; P-format utility196-356 | Correct deterministic format oracle; no rounding boundary, decimal count0/6/8 or optional sub-ten padding witness. |

## Boundary and runtime conclusions

1. **Threshold ties:** Over must be strictly greater; Under includes equality. This is exact in P-keys `2992-2997`, and pinned XSA `getOpenPOQueryWithEmail.hdbfunction:313-333,343-363` uses `>` / `<=` over scoped PO net sums. None of these assigned tests arranges a PO exactly at the converted threshold. Whole-fixture parity does not prove the equality boundary exists in fixtures. A deterministic HANA fixture must include below/equal/above scoped PO totals with multiple items, and verify all keys in each class; do not use displayed gross POVALUE as the threshold sum. Do not mutate productive DB data from this HARMLESS test class.
2. **Scopes:** the documented thirty fixture emails do not declare the thirty actual role triples in this assigned source. `download-xsa-json.ps1:99-110` expressly requires identical externally installed roles. Empty scope tests need a role-exists precondition and intended literal triple check, plus a positive baseline fixture/system check. Keep **one role per email**, global header/item company configuration, and do not widen wildcard semantics to “any star anywhere.” P-scope sole-effective-star behavior differs from mixed lists by design.
3. **USD and company invariants:** P-keys threshold join `2975-2977` joins source currency without target restriction; conversion lookup `2473-2487` requires the source/**USD** pair. Preserve the stated USD-target dataset invariant, unique role/user setup and global company configuration. Do not invent arbitrary other targets/duplicate roles/users to call valid tests wrong; conversely a snapshot cannot verify these prerequisites are installed.
4. **Under stored accrual method/closure:** pinned XSA source was fetched directly, not inferred from report prose. [TF_getOpenAllThresholdPO:76-89](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenAllThresholdPO.hdbfunction#L76-L89) routes Under to detail mode2. [TF_getPODetail:172-190](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/TF_getPODetail.hdbfunction#L172-L190) passes stored `accrualMethod`. [SF_accrualMethod:88-137](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/SF_accrualMethod.hdbfunction#L88-L137) chooses available-service WTD/fallback STL or persisted STL. P-calc `1523-1524,1640-1726` follows that branch structure. No unconditional closure-zero assertion is valid.
5. **Possible production status divergence, not a test fix:** pinned [TF_getPODetail:333-376](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/TF_getPODetail.hdbfunction#L333-L376) checks closure=true before visible status and returns Reviewed. Dashboard `1936-1941` returns Pending first for a Pending/initial stored status, even if `apply_status:1515-1517` set closure=true; this is a confirmed source-level branch divergence for that input, **not proof the recorded fixtures contain that stored-status input**. Do not weaken Under fixture parity to accept it. A deterministic source-status+closure witness is required to demonstrate live impact.
6. **No SAP runtime claim:** Gateway generated metadata/framework interfaces and actual DB/MIME/role contents are not present. HTTP400, explicit-zero requestedness, DDIC length details, SAP activation and date-dependent fixture parity require real SAP verification. Static declaration/target consistency and JSON witness inspections establish no runtime PASS.
