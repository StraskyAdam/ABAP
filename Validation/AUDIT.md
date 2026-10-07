# Exhaustive logical audit — PR #30

## Provenance and meaning of verdicts

At session start, `git ls-remote origin refs/heads/copilot/abap-correct-incomplete-test-work`
resolved the explicitly requested base to **`c2bf1b3cc171dfe043648d7294d58e9bee78cd45`**.
The working branch initially had `aa635edee81d22ed04109858d42cbd7bcb2d4ed4`
(`Initial plan`) on that base; `git diff c2bf1b3 --stat` was empty.
PR [#30](https://github.com/StraskyAdam/ABAP/pull/30) targets
`copilot/abap-correct-incomplete-test-work`, not main/Complete-refactoring.
All local production references in this audit mean that base revision.

The entire 8,431-line base `ABAP code/Unit test.txt`, including every method body,
was divided into contiguous review ranges. The detailed matrices are:

* [Functional tests and groups](AUDIT-functional.md): method starts 787–3589.
* [Filters, status boundary and utilities](AUDIT-filters.md): starts 3590–5378.
* [Gateway, fixtures and comparison helpers](AUDIT-oracles.md): starts 5379–7187.
* [JSON/normalization helpers and static auditor](AUDIT-json-static.md): starts 7188–8431.

Matrix source coordinates are **base-revision** coordinates, so corrections do
not make the evidence ambiguous. Added methods and final correction coordinates
are recorded separately below. “Correct” is a reasoned review verdict, **not a
passing execution**. “Limited coverage/runtime-dependent” records precisely
what an assertion or an unavailable runtime cannot establish. A production
finding is not permission to weaken an oracle. The historical `REPORT.md` is
prior-PR documentation, not evidence for this audit.

## Actual XSA source consulted

XSA HEAD was resolved independently using the GitHub commits API:
**`e5fd6d0a36957baa795608f85abdc9d4e810e834`**. Source was fetched at that SHA,
not inferred from mapping HTML. Paths below are under
`ARIBA_ACCRUALS_DB/src/` in `StraskyAdam/XSA`.

| Source | Blob SHA | Evidence |
|---|---|---|
| `Functions/TF_getOpenThresholdPO.hdbfunction` | `dd472a0b3b4aa95b450b76394e1d840a9bfde0ea` | Calls `TF_getOpenAllThresholdPO`, then excludes/aggregates; preserves translated stored accrual method. |
| `Functions/TF_getOpenAllThresholdPO.hdbfunction` | `734260ed0af1371a583d5dbf20df14bff71e5e50` | Calls `TF_getOpenPOQueryWithEmail('2', …)` and `TF_getPODetail(…, '2')`. |
| `Functions/TF_getPODetail.hdbfunction` | `976127a927d796d178e3685fbc4d1d67249f5dec` | Lines 149, 172–269 pass `accrualMethod` into `SF_accrualMethod`, without an Under-only STL replacement. |
| `Functions/TF_getPODetailQuery.hdbfunction` | `a5927bb9cec4971a407f2b023ecba2e797678f18` | Projects `edgePO.accrualMethod`; closure changes visible status, not an unconditional accrual zero. |
| `Functions/TF_getOpenAllPO.hdbfunction` | `10b9594374a96331218c0672463826453af305e5` | Separate path: lines 149–154 contain the threshold=`2` service STL override. It must not be imported into the preceding Under path. |
| `Models/CV_getThresholdPO.hdbcalculationview` | `d3dc8c849dcdcfd08528b8e37055c6fb1cfff1fa` | Lines 798–824: accrual is nonnegative work/GR minus invoice; USD conversion rounds. No closure operand in the accrual formula. |
| `Functions/getOpenPOQueryWithEmail.hdbfunction` | `ba1d9d162e3817f1f7ccfbfaab84800f2b5a175d` | Actual definition is `TF_getOpenPOQueryWithEmail`; USD threshold, scoped PO sums, inverse rates, `>` for Over and `<=` for Under. |
| `Functions/TF_UserConfigCompanyCodes.hdbfunction` | `767e1987cc9840dfe60bca197807534927da6eb5` | Wildcard branches and the single flat role value are read directly. |
| `Functions/TF_filterPOByThreshold.hdbfunction` | `78f0fa922254a3e2cec198b402f0dbacb9429dc5` | Separate per-line threshold helper; not substituted for the actual grouped-PO path. |
| `Functions/TF_getOpenThresholdPOFinal.hdbfunction` | `7acdb07d02965f726822989e34b703a39c43e9df` | Reads `CV_getThresholdPO`, formats output; no unconditional closure zero. |

Global company-code `*` threshold configuration, USD-only target rates, one flat
role record per user, wildcard parity and external `REVIWED_BY` spelling remain
unchanged. No production business logic is changed.

## Added observation regressions

| Method | Verdict | Independent oracle and Act | Limits |
|---|---|---|---|
| `observed_po_item_or` | Correct; runtime-dependent | Supplies exactly `(PONUMBER = '8000401022') OR (ITEMNO = '00001')` with **empty** options. Extraction must preserve SQL and leave optimized filters empty. Four rows represent both/PO-only/item-only/neither. Full-table equality requires exactly the first three in original order. | Supplied observed translation input; calls production extraction and HANA filtering, **not** real Gateway translation. Not executed on HANA. |
| `observed_po_item_and` | Correct; runtime-dependent | Supplies the AND expression with both populated EQ options. Extraction consumes options but preserves authoritative SQL. The same four witnesses must produce exactly the both row. Also independently feeds the complete representable ranges through select-only extraction and sequential generated filters; requires the same exact result. | Hybrid and optimized SQL paths, not a mocked or executed Gateway translator. Not executed on HANA. |

`cross_or_disables_prefilter` is now explicitly labelled a deliberately partial
range **robustness** input. It is not the observed empty-option Gateway case.
The original expression determines logical structure; neither property identity
nor a partial projection can replace that expression.

## Final inventory and verdict reconciliation

The base has **225 methods: 164 leaves, 11 groups, 50 helpers**.
The final code has **233 methods: 170 leaves, 11 groups, 52 helpers**;
**181 methods are FOR TESTING**. Declaration and implementation sets coincide.
The four base matrices contain exactly **225 distinct method rows**, with no
missing or repeated method. This was checked against the entire pinned source,
not against previous reports or a truncated retrieval.

Those matrices are forensic **base-revision** reviews. Their defect/proposal
wording is retained to explain the evidence, not to suggest unapplied fixes.
The following final overrides supersede it. Unchanged methods inherit their
individual base verdict and stated limits; corrected shared helpers also repair
their callers' identified false-pass paths. No verdict means runtime PASS.
All final source ranges below refer to `ABAP code/Unit test.txt` in this PR.

### Changed tests and group wiring

| Method / final lines | Final verdict | Defect, correction and discriminating evidence |
|---|---|---|
| `all_tests` 807–978 | Corrected wiring | Exactly 170 leaves, each once; six new leaves also have category dispatch. This is inventory evidence, not semantic evidence. |
| `filter` 996–1072 | Corrected wiring | Adds observed PO/item OR and AND; does not mislabel partial ranges as observed Gateway output. |
| `request_processing` 1173–1209 | Corrected wiring | Adds closure-status contract. |
| `hana_filter` 1211–1238 | Corrected wiring | Adds complete range/escaping witnesses. |
| `utility` 1240–1245 | Corrected wiring | Adds JSON comparator and parser contracts. |
| `test_inlinecount_with_top_one` 1883–1958 | Corrected; runtime-dependent | Original pair could prove only nonduplication/local conditions. Exact pair-to-combined-prefix key order/membership now required; stable total checked before paging. |
| `test_top_zero` 2057–2115 | Corrected; runtime-dependent | Zero-row result alone was vacuous on empty data. Positive one-row/count baseline precedes zero-top query. |
| `test_filter_sort_and_paging` 2117–2169 | Corrected; runtime-dependent | Both adjacent pages must equal the complete corresponding ordered combined prefix, not merely be nonempty/disjoint. |
| `test_under_paging` 2171–2235 | Corrected; runtime-dependent | Same prefix-membership/order and positive two-page preconditions for Under. |
| `test_excl_paging` 2237–2301 | Corrected; runtime-dependent | Same for exclusion. |
| `test_excl_pstype_pages` 2402–2506 | Corrected; runtime-dependent | Both asc and desc page pairs now require positive windows, stable totals, unique combined-prefix keys, and exact position-by-position membership/order. Local PSTYPE and boundary checks remain. |
| `top_zero_not_requested_all` 2740–2756 | Corrected | Count-only omission check now compares the entire unchanged input table. |
| `sort_adds_default_ties` 2958–2994 | Corrected | PSTYPE and keys no longer correlate in Arrange. Exact whole-table tie order and concatenated three-page order distinguish missing default ties and wrong paging order. |
| `omitted_top_keeps_all_rows` 3060–3076 | Corrected | Full input preservation, not merely two rows. |
| `empty_contains_pattern` 3872–3892 | Corrected; HANA-dependent | Nonempty and empty-string witnesses; exact table including positional indexes, not count-only wildcard coverage. |
| `test_cp_case_sensitive_include` 4703–4727 | Corrected; HANA-dependent | Uppercase `Quantum` is a positive witness alongside `Quality`; lowercase `quantum` remains negative. |
| `test_cp_case_sensitive_exclude` 4729–4754 | Corrected; HANA-dependent | Uppercase `Quantum` must be excluded; lowercase `quantum` survives. |
| `test_multiple_cp_filters_or` 4820–4853 | Corrected; HANA-dependent | `Quality`, `Quantum`, and `BioClinica` survive the supplied SQL union; lowercase/nonmatching witnesses do not. This is not a general inference that same-property expressions mean OR. |
| `nested_and_or_rows` 4893–4918 | Corrected; HANA-dependent | Added PO2/company2000/EUR row must fail the grouped expression but would survive flattened OR precedence. |

### Every added method

| Method / final lines | Final verdict | Independent Arrange, Act and expected evidence / limits |
|---|---|---|
| `closed_pending_is_reviewed` 4065–4095 | **Production defect retained** | Actual private `ts_result` and `ts_status`; calls actual `calculate_visible_status`. Closed Pending and closed initial must become Reviewed by pinned XSA precedence; open Pending must remain Pending. First two assertions are expected from source to fail against current ABAP; no runtime failure claimed. |
| `observed_po_item_or` 4142–4170 | Correct; HANA-dependent | Empty options, authoritative exact observed OR; both exclusive arms and both/neither witnesses. Full expected keys/values/order and production-stamped source indexes 1/2/3. Supplied translation input, not a Gateway HTTP test. |
| `observed_po_item_and` 4172–4220 | Correct; HANA-dependent | Populated AND options plus equivalent complete select-only path; only both row/index1 survives either Act. Supplied inputs, not executed Gateway translation. |
| `json_oracle_contract` 5582–5636 | Correct; runtime-dependent | Literal backslashes versus escapes, BMP/space/surrogate decoding, aggregate multiplicity/empty slots, permutations, strict null/number versus quoted tokens, and one-way null allowance. Checks exact values and difference-count increments. |
| `json_parser_contract` 5638–5704 | Correct; runtime-dependent | Valid nested JSON and decoy nested results/count; exact keys/count/decoded property and distinguishing quoted sort value. Malformed grammar, duplicate keys/rows/envelope fields, nonstring keys, missing/wrong `d`, nested error/results, trailing data and absent true count must raise domain errors. Time normalization retains invalid/nonstring values and avoids integer overflow. |
| `range_sql_witnesses` 5706–5773 | Correct; HANA-dependent | Calls real extraction/filtering on include union intersected with exclusions; inclusive BT endpoints and excluded complement; literal `%`, `_`, quote, escaped star/plus versus negative witnesses. Exact complete tables and source indexes. Representable select-option tests, not Gateway translation evidence. |
| `assert_page_windows` 6614–6656 | Correct; runtime-dependent | Requires data on both pages and unchanged totals; split windows equal an independently requested doubled-top prefix at every exact PO/item position. Rejects duplicates in prefix index. Relative window oracle, not independent business output or complete-dataset ordering. |
| `find_odata_property` 6989–7079 | Corrected response contract; runtime-dependent | Scans actual root/`d` scopes; no textual-field matching or copied full envelope token. Rejects root errors, duplicate envelope names, missing commas, trailing data and absent requested data property. Uses inclusive string-end plus1 and exclusive value-end contracts deliberately. |

### Changed shared helpers

| Method / final lines | Final verdict | Confirmed defect and correction / remaining limit |
|---|---|---|
| `run_scope_case` 5809–5832 | Corrected; runtime-dependent | Empty snapshots could also pass with an absent role. Read-only SQL requires exactly one configured role for the exact case email, then existing full fixture parity. Intended role-field values still require environment preparation; not fabricated or seeded. |
| `append_filter` 6122–6196 | Corrected | Previously removed arbitrary outer characters/changed patterns into contains. Its deliberately substring-only CP contract now validates exactly outer stars and rejects inner wildcard/escape syntax; failure returns safely in grouped mode. General CP grammar is tested through production separately. |
| `read_inline_count` 6275–6302 | Corrected | Missing or nested-lookalike count no longer silently means zero. Requires real `d/__count` and nonempty nonnegative digits. |
| `get_result_count` 6304–6354 | Corrected | Requires object rows and validated array grammar, rather than counting invalid primitives as results. |
| `assert_all_rows_match_filter` 6365–6433 | Corrected | Uppercasing previously erased case-sensitive substring failures. Case-sensitive `find`; missing-property failure safely continues instead of unsafe dereference. |
| `assert_rows_sorted` 6435–6582 | Corrected | Reads raw token once, verifies presence, distinguishes JSON null from business string `"null"`, and does not trim/second-decode business strings. Numeric/epoch branches retained. Empty/tied live data can still limit discrimination outside positive paging prerequisites. |
| `build_expected_index` 6841–6971 | Corrected | Duplicate keys previously only logged differences that index-only callers could omit asserting. Now immediately raises; missing/empty/string-type keys rejected. |
| `find_results_array_bounds` 6973–6987 | Corrected | Uses actual `d/results`, requires array, and validates its full grammar. Nested/error lookalikes cannot supply it. |
| `read_json_row_key` 7081–7237 | Corrected | Requires nonempty string PO/item keys, not unquoted/null fallback. Optimized key extraction remains early-returning; full array validation occurs **before** it, so later duplicate row properties still reject. |
| `read_object_properties` 7436–7550 | Corrected | Mandatory separators/value boundaries; missing, repeated/trailing commas and duplicate ordinary properties reject. `__metadata` omission remains intentional. |
| `compare_raw_property` 7552–7717 | Corrected | Unordered allowance previously equated null/number with their quoted strings. Only two JSON strings enter aggregation; explicit one-way null list and multiset semantics remain. |
| `is_equivalent_null` 7719–7984 | Limited compatibility allowance; comments corrected | No behavior weakened. Removed unsupported blanket consumer-absence/equivalence and unexecuted Gateway-serialization claims; corrected literal-NULL COSTCENTERDESC description. See source evidence below. |
| `normalize_odata_time` 7986–8133 | Corrected | Only quoted tokens normalize; digit-component lengths guarded before conversion. Actual hour/minute/second bounds remain strict. |
| `read_json_string_end` 8278–8354 | Corrected | Negative offsets, illegal escapes/hex and raw controls reject. Inclusive end preserved. |
| `read_json_value_end` 8356–8474 | Corrected | Empty/invalid primitives, negative offsets, array endings/separators and nested object grammar validated; exclusive end preserved. |
| `unquote_json` 8669–8831 | Corrected; activation-dependent | Single-pass decoder does not reinterpret generated backslashes. General BMP escapes/control escapes and validated UTF-16 surrogate pairs replace chained replacement/partial Unicode handling. Converter encoding/signature must be activated on target SAP; Python audit cannot establish this. |
| `check_select` 8930–9009 | Corrected; Gateway-dependent | Now rejects nonselected ordinary properties apart from PO/item keys; retains selected-field presence/value comparison to same-key full response. Checks actual projection contract, not removed calculation-skip optimization. One-row representative test, not full-dataset projection coverage. |
| `matches_complex_fixture` 9011–9071 | Corrected within documented domain | Missing properties return safely after failure; regex status saved before assertion can overwrite it; invalid date does not proceed to unsafe conversion. Real snapshot/raw-JSON oracle remains independent of production. |

`Validation/audit_tests.py` also has three parser defects corrected: foreign
receiver calls no longer falsely reach local assertion helpers; indented star
arithmetic is not treated as a column-one comment; commented chained legacy
declarations map every test individually. Stale fixed leaf total was removed,
but exact declaration-to-dispatch Counter equality remains. Six new Python
selftests protect these corrections and observation/oracle structure (30 total).
They do **not** execute the JSON helpers, SQL predicates, SAP methods or Gateway.

## Retained production finding and uncovered boundaries

**Closure-status precedence:** base ABAP `zcl_fi_das_dashboard.txt` 1936–1941
returns Pending for initial/Pending stored status before inspecting closure.
Actual `apply_status` passes stored status (around1526); later flag assignment
does not repair visible status. Pinned XSA `TF_getPODetailQuery` 128–131 and
`TF_getOpenAllPO` 231–232 give closure=true Reviewed precedence. The new test
retains that expectation instead of changing production or gating the failure.
This is **not** a closure-zero accrual claim.

* `threshold_fixture_classes` remains **limited coverage**, not a threshold
  equality test. Fixture class/cardinality cannot establish `>`/`<=` at exact
  grouped USD equality. A prepared scoped-PO/rate/global-`*` configuration with
  equal and adjacent rounded totals is still needed on the real runtime.
* The original supplier cross-OR snapshot has27 matches:19 supplier-only,8 both,
  **zero PO-only**. It distinguishes OR from AND/PO-only, but not supplier-only.
  The added PO/item supplied-input test has both exclusive-arm witnesses; it
  does not manufacture a missing real-Gateway supplier fixture witness.
* Complex fixture:20131 candidates,1674 matches. Dropping description-not-b,
  PO-not5, description-a, date, supplier or item adds489/1176/638/776/1512/688
  rows respectively; inclusive date instead of strict `>` adds3 boundary rows.
  The lexical PO group `PO <= '977' OR PO > '9000600000'` is tautological for
  nonnull strings (`'9000600000' < '977'`), so no PO-group-only negative can
  exist. Do not numeric-convert it or invent witness coverage.
* Hash-indexed full fixture parity proves membership/values/duplicate checks,
  not row order. Combined-prefix paging checks strengthen tested windows;
  whole >window ordering, nonvacuous numeric/reviewer sort ties, and exact
  all-PSTYPE union identity remain narrower than full independent coverage.
* Correct snapshots can fail against changed live data, dates, roles, rates or
  thresholds. This sensitivity is an environment issue, not automatically a
  test implementation defect. All local JSON assets remain unchanged; execution
  reads separately deployed SAP MIME fixtures.

## Actual compatibility-source audit

UI was pinned to **`461761582d2bae0008a7b05d203ec1c15c65e28c`**.
Additional inspected XSA blobs at the XSA pin:
`TF_getOpenPO`=`d59c76f9c79d67235bbf68c4832a7f53386511f9`,
`TF_getExclusionPOs`=`d2f52e9071a6b3b327e790eed6acf8ee10907873`,
`ARIBA_ACCRUALS_JS/lib/xsodata/openOwnerPO.xsodata`=
`567d37d71387efa08130785d2da1a6cddf88f5e8`.

* Open132–220, Threshold140–240 and Exclusion150–190/260–340 use semicolon
  `STRING_AGG` without aggregate ORDER BY for the inspected assignment/rule
  columns. COSTCENTERDESC is literal SQL NULL. Unordered comparison deliberately
  preserves each field's multiset, including duplicates/empty slots; **it does
  not prove joint cost-center/account/percentage or rule-code/text associations**.
  It is not automatically a production defect where XSA supplies no ordering
  contract. Literal semicolons within segments remain ambiguous.
* Exclusion xsodata1–16/20–25 generates local ID, unlike Open/Threshold PO/item
  keys. Missing-ID allowance is an intentional metadata difference, but its
  name-only scope is broader than exclusion. No blanket absence of UI consumers
  was proved. Extra actual properties still fail fixture comparison.
* `model/common.js`110–145/235–265 (blob
  `5906a9732bf8461d296414251fa542908c677bed`) separately loads effective decimal
  format and uses exact `'X'` for notification. `model/formatter.js`510–527
  (blob `d416a9b36dc7bc9b23545a9e4374e64f9656c3c9`) explicitly normalizes USD
  null to numeric zero. Business/TBS checkbox snippets explicitly normalize
  EDGEWTDAMT null for those calculations; exact controller line coordinates
  remain unresolved, not invented. Inspected controller blobs:
  `87d89dfc0223a622c8a18a8efd446aa955c96194` /
  `e334d2d03ffbcddb266a820e2a113109ac383c65`.
* Typed initials/metadata are not exact Gateway serialization evidence.
  Retained null allowances are one-way and field-specific: null→`""` for
  COSTCENTERDESC/DATFM/DECIMAL_FORMAT/FULL_NAME/MANAGEUNIT/NOTIF_24_HR/
  REVIWED_BY/USERNAME; null→`"0.00"` for EDGEWTDAMT/GRVALUE_USD/INVVALUE_CAL/
  INVVALUE_USD/LASTMONTHWRKCOMP; null→`"PT00H00M00S"` for CHANGEDTIME.
  They can hide source-presence differences; no universal functional equivalence
  or absent-consumer claim is justified. INVVALUE is not relaxed.

## Execution evidence

Commands were run from `/home/runner/work/ABAP/ABAP` (no SAP runtime commands):

| Exact command / operation | Result |
|---|---|
| `git ls-remote origin refs/heads/copilot/abap-correct-incomplete-test-work` | Base SHA above. |
| `git rev-parse HEAD`; `git log -3 --oneline`; `git diff c2bf1b3 --stat` | Verified initial-plan descendant, no initial content diff. |
| `wc -l 'ABAP code/Unit test.txt' Validation/audit_tests.py Validation/REPORT.md` | Base: 8431 / 1024 / 547 lines. |
| `python3 Validation/audit_tests.py --self-test` (base) | 24 Python tests, OK. No ABAP/HANA execution. |
| `python3 Validation/audit_tests.py --json > /tmp/abap-audit-base.json` | 225 declarations/implementations, 175 testing methods; no structural errors; 45 fixture files, no unresolved LFS. |
| `command -v abaplint`; `command -v hdbsql`; `command -v sapcli`; environment variable-name check for SAP/HANA/GATEWAY | No configured runtime tool or runtime connection discovered. No credential values read/reported. |
| `python3 Validation/audit_tests.py --json > /tmp/abap-audit-observed.json` | After observation regressions: 227 methods, 177 testing methods, no structural errors. |
| `python3 Validation/audit_tests.py --self-test` (first observation iteration) | Failed only on stale hard-coded leaf count 164 versus 166. Replaced count with nonempty inventory; retained exact Counter equality against declarations. |
| `python3 Validation/audit_tests.py --self-test > /tmp/abap-selftest-observed.log 2>&1` | 25 Python selftests, OK, including observed-input/oracle structure check. |
| `git diff --check` (observation iteration) | Clean. |
| GitHub `actions_list(list_workflow_runs)` and `get_job_logs(run_id=37634428303, failed_only=true)` | Historical failed cloud-agent run has zero failed jobs (one total). No ABAP/HANA CI result is available from it. |
| `python3 Validation/audit_tests.py --self-test > /tmp/abap-selftest-corrections.log 2>&1` | After parser fixes:28 Python selftests, OK. |
| `python3 Validation/audit_tests.py --json > /tmp/abap-audit-strict-json.json` | Intermediate231 methods/181 testing methods, no structural errors. |
| `python3 Validation/audit_tests.py --self-test > /tmp/abap-selftest-final.log 2>&1` (envelope iteration) | One new structural test failed because it searched preserved literals in a literal-eliding parse. Corrected that selftest to preserve literals, not weakened response assertions. |
| `python3 Validation/audit_tests.py --self-test > /tmp/abap-selftest-final.log 2>&1` (corrected final code) | **30 Python selftests, OK**. |
| `python3 Validation/audit_tests.py --json > /tmp/abap-audit-final.json` | **233 declarations/implementations,181 testing methods; errors=[]**. |
| `for file in Validation/*.json; do jq --stream empty "$file" || exit; done` | All45 JSON fixtures valid; this validates assets, not ABAP parser execution or business expectations. |
| `git lfs fsck` | OK. |
| `git diff --check` | Clean after corrections. |

The matrix-completeness check parsed the full base with the existing auditor,
selected only each detailed document's method-matrix section, and compared
row-name Counters:225 rows, missing=[], duplicates={}. Whole-file method body
start/end offsets supplied the final coordinates above. That proves inventory
completeness only; the individual matrix evidence supplies the logical review.

Static parser success is **not an ABAP compiler**: signatures of exported local
methods/friend access/declaration parity/name limits can be inspected, but
installed SAP classes, external Gateway types, SQLScript execution, actual
argument/type checking, dynamic runtime invocation and assertion flow are not
compiled/executed here. Recursive strict JSON scanning adds work; no SAP
performance or memory benchmark was run.

**Unexecuted:** ABAP compilation/ATC, ABAP Unit (including pure ABAP leaves),
HANA AMDP/APPLY_FILTER, MIME-backed fixture parity, HTTP Gateway translation and
serialization. `/IWFND/GW_CLIENT` was not invoked. No blanket “all tests passed”
claim is made.
