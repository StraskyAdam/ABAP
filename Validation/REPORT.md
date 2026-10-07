# ABAP test repair: installation and failure interpretation

## Install this revision, not the older base or PR #30 alone

- Test implementation: commit **`d2d5716ccdfeb6965837b968da55b6b59caff4aa`**,
  `ABAP code/Unit test.txt` (the complete local test-class include of
  `ZCL_FI_DAS_DASHBOARD`, including its local diagnostic exception classes).
- Production prerequisites: the corresponding dashboard, utility, interface,
  domain exception, Gateway adapter/metadata and CDS exports at
  **`c2bf1b3cc171dfe043648d7294d58e9bee78cd45`**. Activate dependent DDIC/CDS
  objects and classes together. This repair changes no production business logic.
- Target: `copilot/abap-correct-incomplete-test-work`. The assigned working PR
  branch is `copilot/copilotabap-correct-incomplete-test-work-again`; no branch was
  merged. Read-only fetch verified PR #30 remains unmerged at
  `bc1a1dea2dff88b103da46fe63a572b71b335e7b`, descending from the target's
  `c2bf1b3`. Its useful test/auditor implementation (`b940032`, `2e769288`) is
  incorporated here, then repaired; its redundant audit documents are not copied.
- Upload the existing UTF-8 `Validation/*.json` assets to `/SAP/PUBLIC/DAS/`
  with their existing filenames, including hydrated LFS payloads. A single UTF-8
  BOM is legitimate and is removed before conversion; retained Unicode BOMs are
  also accepted without changing indexed offsets. Invalid UTF-8, malformed JSON,
  wrong root/`d`/`results` envelopes, duplicates and unpaired surrogates still fail.
- Gateway service `ZFI_DAS_SRV`, matching replicated snapshot/configuration,
  users, formats and one configured flat role per scope user are prerequisites.
  Snapshot membership failures are not proof that today's live data is wrong.

No project dependency was added. The existing auditor uses Python 3's standard
library; the supplementary ABAP **statement-parser** check used
`@abaplint/core` **2.120.70** outside the repository. SAP_BASIS, SAP_GWFND and
HANA release/SP versions are not recorded here and cannot be asserted from the
cloud. Activation must verify the target APIs, including `CL_ABAP_CONV_IN_CE`,
`SYSTEM_CALLSTACK`, `CL_SHDB_SELTAB`, ABAP Unit and the Gateway proxy.

## What a failure means

| Output | Interpretation / next check |
|---|---|
| `DAS XSA vs SEGW OData parity failed. Difference count: N.` | Actual compared row/property differences. The first 20 have newline-separated fixture, PO, ITEMNO, field and original XSA/SEGW tokens. Total N includes omitted differences. Tokens above 256 characters and lines above 2048 are bounded with original lengths. Spaces, minus signs, Unicode and JSON token types are not normalized away. |
| `Exception[n]=...; Reason=...; Source=include:line` | Helper/environment failure, **not invented field differences**. Test, fixture/request, phase, domain `reason`, nonempty fallback text and up to eight exceptions in the previous chain identify where to debug. Genuine differences recorded before an interrupted comparison are retained separately. |
| `EXPECTED fixture decoding/indexing`, `find_odata_property`, offset/length | Failure happened before owner values were compared. Verify MIME bytes/filename, UTF-8 and the root/`d`/`results` envelope. Do not diagnose this as owner selection. |
| `unquote_json`, token/inner length and offset | Decoder failure. Fixed code retains UCCPI's fixed `char2` before blank-preserving string construction and bounds-checks UTF-16 pairs. The supplied screenshot did not identify the internal throw line; no SAP reproduction is claimed. |
| `Unconsumed input filter ranges, not result rows` | Expected remaining input ranges = 0. Generic SQL can legitimately be empty when PO/ITEM/SUPPLIER optimized SQL is populated; all four channels are now shown. On this prerequisite revision extraction copies and clears ranges before SHDB conversion. Remaining 4/1 indicates a violated active-version contract; inspect active `EXTRACT_FILTERS`, not result-row counts. SHDB exceptions retain their previous class/reason. Do not clear test inputs or invent SQL. |
| `Amount formatting contract failed. Difference count: N.` followed by `format_odata_amount: amount=..., decimals=2, format=..., grouping=...; Expected="..." ... Actual="..."` | All numeric cases are compared before reporting, so missing grouping **and** minus signs remain visible in one run. Y grouping requires spaces and negative inputs require a leading minus. Current prerequisite utility already preserves both. Inspect active utility/version and call arguments if screenshots differ; expectations remain strict for X, Y and blank formats, signs and multiple groups. |

Native leaves and groups use the same parity report. Groups stop the failed
leaf, retain the original registered ABAP Unit assertion (rather than report
its blank quit exception again), and attempt the next leaf. Other catchable
exceptions receive contextual reports. A later leaf's reset does not reset
the framework's recorded failure. Run the class for separate native leaf nodes;
a selected category remains one aggregate result. Uncatchable SAP terminations
cannot be made continuable by this runner.

## Scope, meaningful witnesses and remaining real failures

- Reviewed every actual leaf and helper, not declarations/search-indexed main.
  Live filter/value-help checks now compare independent fixture total counts and
  exact ordered PO/item windows (value-help `$select` explicitly requests both
  keys); all-PSTYPE checks use both fixture sets and PSTYPE-descending ordering.
  JPY/2780 is the positive company/currency witness (654 supplied rows);
  JPY/2028 remains a zero-row witness. The Hitachi PO OR case now exercises both
  branches (18 supplied items), rather than accepting a single surviving branch.
- Original predicates remain authoritative. The observed PO/item OR has empty
  select-options; AND has complete options. Deliberately inconsistent range
  projections remain labelled robustness inputs, not Gateway observations.
  Legacy `skip_true_*`/`skip_false_*` leaf names describe projection/processing
  checks only: they do **not** prove that calculations were skipped.
- `stored_method_read_contract` independently expects WTD 300/25%/accrued 280
  versus STL 1200/100%/accrued 1180 with USD rate 1 and invoice 20, for open and
  closed historical service rows. Closure does not zero the read formula.
- **Retained production discrepancy:** `closed_pending_is_reviewed` expects
  closure-first Reviewed, whereas prerequisite ABAP returns Pending first.
  This is supported by XSA `TF_getPODetailQuery` and `TF_getPODetail` at
  `e5fd6d0a36957baa795608f85abdc9d4e810e834`. That stored-detail read path calls
  `SF_accrualMethod`; its formula has no closure parameter. No universal
  “Under Service always STL” or “closure makes amounts zero” expectation is used.
- Scope/wildcard, global company `*` threshold, USD-only target rates and public
  `REVIWED_BY` spelling are unchanged. Fixture classification does not claim a
  threshold-equality witness; that requires controlled scoped NETWR/rates data.

## Validation evidence (not SAP PASS)

Executed: **30 Python auditor selftests**, structural audit (zero errors),
`git diff --check`, secret scan, and ABAP statement parsing (zero parser findings).
New ABAP diagnostic/fixture/Unicode/stored-method regressions are supplied but
**unexecuted**. No SAP activation/ATC, ABAP Unit, HANA or Gateway run was possible.
The mandatory validation tool reported its review binary unavailable and
skipped CodeQL for test-only changes; this is not a clean security/runtime scan.
A separate read-only reviewer identified misplaced parser guards and an
incorrect combined-PSTYPE ordering oracle; both were fixed, then re-reviewed
with no remaining high-confidence findings.

## Historical PR #29 report (not current installation instructions)

## Branches and prior work

This is the corrective PR [#29](https://github.com/StraskyAdam/ABAP/pull/29),
head `copilot/abap-correct-incomplete-test-work`, **base `Complete-refactoring`**
at `2b8877649b7dbae31d8e554e2b79bbba752ad84f`. Nothing in this report means
these changes have merged into the base branch.

Prior draft PR [#27](https://github.com/StraskyAdam/ABAP/pull/27) has head
`copilot/complete-refactoring` at
`85dcba12b5aa5138fba2897b642069d314fc9815`, with the same base revision.
Its production diff, added tests, and report were inspected as prior work.
`Validation/REPORT.md` exists at that PR's head, not at the base revision.
This corrective PR is separate because this environment is assigned PR #29;
it does not switch to or write PR #27's branch.

The inherited source had 122 `FOR TESTING` declarations in two test classes.
That is a declaration count, **not executable coverage**. In particular,
`test_selection` and many `ltc_request_processing` methods had only commented
bodies. The previous claims that those bodies were acceptable or validated
are rejected.

## Fixture integrity and SAP configuration

The real `Validation/*.json` files have not been rewritten. All 45 files
passed `jq --stream empty`. `git lfs pull` hydrated all five tracked payloads;
`git lfs fsck` passed. The SHA-256 of each hydrated payload matched its pointer:

| Fixture | LFS SHA-256 |
|---|---|
| `xsa-over-service.json` | `18a244f720afe3016e13f08d3631144c1e7bd51b3eee6210ad5aefe489e509b2` |
| `xsa-scope-16.json` | `78bac24a1a1dfb67cdc7f3af3f8c4589c62db29a5c16894be24ff41308df2ac7` |
| `xsa-scope-23.json` | `850d76a2cbda00618aa0dce444cd9fc66fd9ee4500da71c759d33953b6bce8c8` |
| `xsa-under-material.json` | `3e689453a019c430fa3763cb4a1106d22e2b5dac6a046a71df862bfd9ec84900` |
| `xsa-under-service.json` | `bb3b66e9f255debcf187e9d3e78afe35ef7837f4eb4efd2e736e83b773e3d5cc` |

The fixture suite requires these payloads in the SAP MIME repository at
`/SAP/PUBLIC/DAS/` using their existing filenames, the `ZFI_DAS_SRV` Gateway
service, and the corresponding users, authorization scopes, user formats,
replicated PO data and configuration. Local JSON parsing does not establish
that this SAP configuration exists. Do not use local synthetic results to
claim real-fixture parity.

The existing paged comparison is retained: fixture indexing stores PO/item
keys and object offsets; one Gateway page is compared at a time without
materializing a complete table of JSON properties. Running the class executes
all group methods and their independently runnable leaves, so repeated scenario
execution is expected. Nested method calls do not automatically invoke ABAP Unit
`setup`; each leaf explicitly calls `reset_fixture( )`. The framework hook sets
method-level assertion quit control before resetting the fixture, because the
special method `setup` cannot be called directly.

## Failure fixes and group execution

`extract_filters` copies range projections, clears the request's projections,
and only then checks/converts the copy. The prior export already cleared these
projections on successful exit; early consumption additionally covers conversion
exception paths. The original range-consumption postcondition is unchanged.
The range test helper now constructs a separate local request, passes that
request to extraction, snapshots the remaining range count, checks it is zero,
and only then assigns its return value. This keeps the check independent of the
functional method's returning parameter and generic table assertion. It does
not establish the cause of the previously reported SAP failure: if the count
remains nonzero, inspect the actual request and active extraction implementation
in SAP rather than removing the postcondition.
The helper diagnostic explicitly counts **input filter ranges**, not result
rows, and includes the input/remaining counts and generated SQL. In
`generic_eq_filters_rows`, one matching COMPANYCODE result still must be `2028`;
it now supplies SQL directly and does not assert input-range consumption.
Zero remaining **input** projections is separately required by `extract_range`,
not a requirement for zero output rows. The five basic HANA leaves (EQ, Contains,
AND, OR, and sort/paging) use `filter_rows`, whose only job is to construct an
internal SQL request and call `apply_generic_filter`. It no longer extracts
filters or asserts request lifecycle behavior already covered elsewhere.
A reported failure of that successful-exit assertion could indicate a stale
deployed version, not a defect reproduced in the current export. Its runtime
root cause has **not been verified** without SAP execution. Activate the current
dashboard, utility, and test-class versions together before rerunning ABAP Unit
and diagnosing any remaining failure. Existing empty/stale-range tests now also
check repeated extraction.
The inherited `group_integer` already used `CONCATENATE ... RESPECTING BLANKS`,
and `get_number_parts` already derived the sign from the numeric input while
writing its absolute magnitude. Those mechanisms should theoretically preserve
Y-format grouping spaces and negative signs; the reported failures have not
been reproduced locally. Current assembly uses local `lv_grouped`/`lv_result`
buffers, explicit blank-preserving decimal concatenation, and a numeric-input
sign check before assigning the final return value. This strengthens explicit
assembly and avoids mutating return parameters during construction; it is not
a verified runtime fix for previously correct exported behavior.
Amount assertions retain the original X/Y/default expectations, multiple Y
groups, ungrouped and negative X/Y/default cases, and zero. Captured actual
values and diagnostics identify the amount, decimal format, and grouping flag.
A deployed `12345,67` instead of `12 345,67`, or a positive result for a negative
input, still requires the **actual active SAP method** and call arguments,
including `i_use_grouping`, to be checked rather than weakening expected values.
SAP execution is unavailable here.
The internal `original_row_index` assertions remain intact.

All 164 leaf tests remain `FOR TESTING`. Eleven group methods are declared and
implemented first, starting with `all_tests`; individual methods have starred
topic sections, shared leaves appear only once in the source, and helpers are
last. `all_tests` calls every unique leaf exactly once, not the category groups.
Every group dispatches leaves through `run_group_test`, which temporarily sets
assertion quit control to `if_aunit_constants=>no`, records catchable exceptions
as ABAP Unit failures with the leaf name, and restores the previous control.
The dynamic method identifier is normalized to uppercase before dispatch, as
required by older ABAP releases; the lowercase diagnostic name is unchanged.
Assertions in leaves and shared helpers use that control, so an assertion
failure does not prevent the group from attempting later leaves. Standalone
leaves retain method-level fail-fast behavior. Added assertion messages identify
the active leaf where no existing diagnostic was present; the shared
range-consumption postcondition also identifies the active grouped leaf.

**Native result-tree limitation:** run the whole `ltc_parity` class for separate
green/error results on its independently registered leaf methods. Selecting
only `all_tests` or a category creates one aggregate native result, not separate
child test nodes for dynamically called methods. Groups do not suppress failures
or fabricate green results. Uncatchable runtime terminations still require SAP
diagnosis; continuation here covers assertions and catchable exceptions.

The exported test class was formatted using the ABAP ecosystem
`@abaplint/core` 2.120.70 pretty-printer and parameter/alignment quick fixes,
parsed in memory as a `.clas.testclasses.abap` file. No formatter configuration,
dependency manifest, fixture, or production formatting change was added.

## HANA leaf expectation review

All 25 `hana_filter` targets were reviewed against their literal input rows and
predicates. These are **logical expected results, not executed HANA results**.
Rows below are in expected preserved input order unless sorting is explicit.
PO/item values are keys where supplied; supplier/currency identifies rows in
fixtures without keys. No expected result was changed to match a reported
failure. `generic_eq_filters_rows` still expects one row, not zero.

| Leaf | Expected count and retained rows / behavior | Predicate source |
|---|---|---|
| `generic_eq_filters_rows` | 1: PO `8000000001`, company `2028` | Direct SQL EQ |
| `generic_contains_filters_rows` | 1: PO `8000000001`, `GSD Local Support (Jan, 2027)` | Direct SQL LIKE `%Local Support%` |
| `generic_two_props_are_anded` | 1: PO `8000000001`, company `2028` and currency `JPY` | Direct SQL AND |
| `generic_same_prop_is_ored` | 2: currencies `JPY`, `USD`; not `EUR` | Direct SQL OR |
| `generic_unknown_prop_no_dump` | Nonempty input: domain exception with previous `cx_amdp_error`; no result-count expectation | Invalid direct SQL column |
| `generic_with_sort_and_paging` | Filter retains PO `8000000003`/Charlie and `8000000001`/Alpha; ascending supplier sort, skip 1/top 1 yields 1: PO `8000000003`/Charlie | Direct SQL JPY, separate sorting/paging request |
| `test_cp_case_sensitive_include` | 1: PO `8000000001`/`00001`, `Quality Solutions`; lowercase `quantum corp` excluded | Retained supplier CP range `*Q*` |
| `test_cp_case_sensitive_exclude` | 2: `quantum corp`, `Fuji Electric` | Retained excluding supplier CP `*Q*` |
| `test_eq_case_insensitive` | Extracted EQ: 1, `FUJI`; explicit UPPER: 3, `Fuji`, `fuji`, `FUJI`; not `Hitachi` | Retained EQ range and separate direct UPPER SQL |
| `test_cp_and_eq_combined` | 2: `Q`, `BioClinica Inc`; lowercase `bioclinica small`/`quantum` excluded | Retained same-property EQ/CP OR conversion |
| `test_multiple_cp_filters_or` | 2: `Quality`, `BioClinica` | Retained two supplier CP ranges, OR |
| `test_cp_empty_pattern` | 2: `Quality` and empty supplier | Retained CP `**` conversion to match-all LIKE |
| `empty_generic_filter_noop` | 2 unchanged: PO `8000000002`/`00001`, then `8000000001`/`00001`; internal index remains initial | Empty direct SQL |
| `nested_and_or_rows` | 2: PO `8000000001`/`00001`, `8000000002`/`00001`; company `2000` row excluded | Direct nested SQL |
| `escaped_apostrophe_row` | 1: PO `8000000001`/`00001`, `O'Brien Supplies` | Retained EQ range/SQL quote escaping |
| `date_boundary_is_exclusive` | 1: PO `8000000002`/`00001`, date `20251015`; boundary `20251014` excluded | Retained date GT range |
| `no_match_returns_no_rows` | 0: company `1000` does not equal `9999` | Retained company EQ range |
| `generic_preserves_row_order` | 2: PO `8000000003`, `8000000002`; regenerated original indexes 1, 3 (not stale 77, 11) | Direct company `1000` SQL |
| `complex_filter_hana` | 7: `0000000010`/`00001`, `9999999999`/`00003`, `8000006000`/`00004`, `8000906000`/`00001`, `8000096102`/`00003`, `8000097224`/`00004`, `8001984177`/`00001`; appended seven negative controls excluded, indexes 1–7 | Retained full SQL plus stale range precedence/consumption |
| `empty_result_filter_noop` | 0 for invalid SQL and then empty SQL: empty input short-circuits before HANA | Direct SQL |
| `date_cp_range_rows` | 2: PO `8000000002`/`20251001`, `8000000003`/`20251031`; September/November excluded | Retained date CP `202510*` |
| `date_eq_range_rows` | 1: PO `8000000002`, date `20251015` | Retained date EQ |
| `date_bt_range_rows` | 2: PO `8000000002`/`20251014`, `8000000003`/`20251015`; both bounds inclusive | Retained date BT |
| `company_range_hybrid_parity` | 2 in each path: PO `8000000001`/`00001`, `8000000003`/`00001`; entire filtered tables equal | Retained range-only vs complete hybrid SQL |
| `po_group_and_supplier_rows` | 2: PO `8000401022`/`00001`/`Fuji Electric`, `8000266248`/`00001`/`Fujifilm`; selected PO with `Other Supplier` and Fuji supplier with unselected PO excluded (item is only an identifier) | Retained generated PO OR and supplier CP, sequential AND |

`PONUMBER` is character-based (`EBELN`), so the complex predicate's
`PONUMBER <= '977'` is **lexical, not numeric**. In particular, `8001984177`
is retained by that branch although it lies outside the explicit bounded
interval; removing it would contradict the predicate. The negative controls
each fail a separate description, PO, case, date, supplier, or item condition.
Case-sensitive LIKE/EQ, SAP range converter output (including empty CP and
date strings), character/date AMDP type mapping, invalid-column exception
wrapping, and HANA execution on the target release remain runtime uncertainties.
Range conversion deliberately stays under test in the CP/date/quote/no-match,
hybrid and shared leaves, and extensively in `request_processing`.

## Reproducible checks

From the repository root:

```sh
python3 Validation/audit_tests.py --self-test
python3 Validation/audit_tests.py --json
python3 Validation/audit_tests.py --json --legacy-ref 2b8877649b7dbae31d8e554e2b79bbba752ad84f
python3 Validation/audit_tests.py --json --legacy-ref 85dcba12b5aa5138fba2897b642069d314fc9815
git -c core.whitespace=cr-at-eol diff HEAD --check
git lfs fsck
for file in Validation/*.json; do jq --stream empty "$file" || exit 1; done
```

The audit lexes comments and quoted literals before statement boundaries.
It excludes `DEFINITION DEFERRED` and `DEFINITION LOCAL FRIENDS` from full
definitions. It checks declaration/implementation pairs, duplicate methods,
class and method identifier lengths, comment-only test bodies, category
calls to independently declared leaves, known receiver calls/named arguments,
local friend access, removed interface types, assertion reachability through
helpers, internal-index metadata leakage, and unresolved LFS pointers.
Group target recognition preserves quoted literals from the original bodies
while ignoring comments and strings containing fake calls. It rejects unknown
or non-leaf targets, duplicates, direct group-to-leaf calls, and incomplete
`all_tests` coverage; shared-category counts exclude `all_tests`.
Its 24 regression tests passed, including range-copy/clear ordering before
conversion, blank-preserving grouping, non-aborting exception reporting,
quit-control restoration, group-first/helper-last ordering, all 164 leaves,
preservation of the original range and Gateway internal-index assertions,
SQL-only basic HANA leaves with literal output counts/rows, SQL-helper lifecycle
separation, and final blank/sign assembly.
The JSON audit reports **225 declared/implemented methods, 175 testing methods
(164 leaves + 11 groups), 45 fixture files, and zero errors**.
An earlier comparison against `HEAD` using the existing parser verified that
all original leaf/helper statements and all 368 original assertions remain in
order, ignoring only added quit control, diagnostic labels, and explicit naming
of formerly positional `act` arguments. That historical statement predates the
intentional removal of three redundant lifecycle assertions from `filter_rows`
and replacement of extraction in five basic HANA leaves described above.
These checks **are not ABAP syntax,
activation, type checking, or proof of meaningful runtime assertions**.
Literal targets are structurally checked, but dynamic dispatch and external SAP
signatures still require SAP review.
The prior-head mapping command requires that commit locally; if necessary,
fetch it read-only with `git fetch origin copilot/complete-refactoring`.
Rename defaults are versioned in the audit script; no temporary mapping file
is required. Each mapping command emits every old test's original qualified
name, replacement name, declaration/body status and whether the inherited
body was executable.

## Execution limits and outstanding runtime validation

| Check | Status |
|---|---|
| Audit-parser and failure/group regression tests | EXECUTED: 24 passed |
| Combined structural JSON audit | EXECUTED: zero errors; all 164 leaves retained |
| Exported ABAP test-class formatting | EXECUTED: ecosystem pretty-printer/quick fixes |
| CodeQL Python scan | EXECUTED: zero alerts; does not validate ABAP |
| Automated code review | UNAVAILABLE: review binary missing despite tool success wrapper |
| Fixture JSON parsing | EXECUTED: 45 passed |
| LFS integrity and hydrated payload hashes | EXECUTED: 5 matched; fsck passed |
| SAP activation / syntax check / ATC | **NOT EXECUTED**: no SAP endpoint/runtime |
| ABAP Unit (individual leaves, categories, run-all) | **NOT EXECUTED** |
| HANA `APPLY_FILTER`, exception behavior on target release | **NOT EXECUTED** |
| Gateway filter translation, OData responses and fixture parity | **NOT EXECUTED** |
| XSA/UI live business parity, currency/date/threshold boundary parity | **NOT EXECUTED** |

The available GitHub Actions runs were inspected. Failed run `36745459100`
ended with a Copilot monthly-quota error, not an ABAP test/build failure.
Its failed-job logs were retrieved. No repository ABAP build/lint/test
configuration was found; the agent workflow is not SAP validation.

Before accepting runtime parity, activate the exports on SAP, run ATC and
all category and leaf tests, exercise the real HANA filters and the Gateway
complex expression from the issue, and record the actual results. In
particular verify optimized/full request equivalence, count before paging,
no double paging, `$top=0` versus omitted `$top`, stable concatenated pages,
all 30 scope fixtures, selection, formats, and threshold/currency/review
calculations against the unchanged reference data.

## Read-only XSA/UI comparison

The reference repositories were inspected, not modified or cloned:

| Repository | Revision |
|---|---|
| `StraskyAdam/XSA` (`main`) | `e5fd6d0a36957baa795608f85abdc9d4e810e834` |
| `StraskyAdam/UI` (`main`) | `461761582d2bae0008a7b05d203ec1c15c65e28c` |

Verified paths and Git blob SHAs (not interchangeable with commit SHAs):

| Repository/path | Blob SHA |
|---|---|
| UI `Accrual_UI5/webapp/manifest.json` | `7dbd4cc6f7be36527c84de1214b6e3ce26fccf90` |
| UI `Accrual_UI5/webapp/controller/Business.controller.js` | `87d89dfc0223a622c8a18a8efd446aa955c96194` |
| UI `Accrual_UI5/webapp/model/poValueHelp.js` | `cd5030ee47b57067e5e56131180837f667021550` |
| UI `Accrual_UI5/webapp/model/lineItemValueHelp.js` | `a2c08d8ea277cb9a76a8d319b5e3aa019efb59a5` |
| UI `Accrual_UI5/webapp/model/supplierValueHelp.js` | `e4864534fd1bb4bb0c677bfe224e77a2c21dd366` |
| UI `Accrual_UI5/webapp/serviceBinding.js` | `e8a9caeb57fa292956663bcb9a4e5f08efc38336` |
| XSA `ARIBA_ACCRUALS_JS/lib/xsodata/openOwnerPO.xsodata` | `567d37d71387efa08130785d2da1a6cddf88f5e8` |
| XSA `ARIBA_ACCRUALS_JS/lib/xsodata/thresholdPO.xsodata` | `47558accce3a96fc441ca6f5290b46637dc60232` |
| XSA `ARIBA_ACCRUALS_JS/lib/xsodata/exclusionPO.xsodata` | `1f4512ac6a4c42e31afef861388311b007db68ae` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/getOpenPOQueryWithEmail.hdbfunction` | `ba1d9d162e3817f1f7ccfbfaab84800f2b5a175d` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenPOQuery.hdbfunction` | `5d71c11190481aa3f06893c79073e21cbc4eeb6d` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenAllThresholdPO.hdbfunction` | `734260ed0af1371a583d5dbf20df14bff71e5e50` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getExclusionPOFinal.hdbfunction` | `f11bea3b505125dedeeaa6b5a07805d430d70703` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_filterPOByThreshold.hdbfunction` | `78f0fa922254a3e2cec198b402f0dbacb9429dc5` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_UserConfigCompanyCodes.hdbfunction` | `767e1987cc9840dfe60bca197807534927da6eb5` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_UserConfigCostCenter.hdbfunction` | `c735eae370b6e0e4ea0b843f713dc6a95c388003` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_UserConfigManagementUnit.hdbfunction` | `ff3adb724f75373fae6dd2c0589dbcfc3450add2` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getPODetail.hdbfunction` | `976127a927d796d178e3685fbc4d1d67249f5dec` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getPODetailQuery.hdbfunction` | `a5927bb9cec4971a407f2b023ecba2e797678f18` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/SF_ConvertCurrency.hdbfunction` | `561f00b9fd011eb6a34fc6b13a4e39dc0106f9d4` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/SF_accrualMethod.hdbfunction` | `168b2d5b60583ef176da26dd6c5cbfba6b7ec381` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getServicePOStatus.hdbfunction` | `f96fd2a0b52f11e1c86d4e73a513059d6ed485be` |
| XSA `ARIBA_ACCRUALS_DB/src/Functions/TF_getServPOStatus.hdbfunction` | `3f7e23e6e177f7735c71ebb2306691aa34b55aee` |
| XSA `ARIBA_ACCRUALS_DB/src/Procedures/updateServPOStatus.hdbprocedure` | `06d3f051ec546c5d080cc16abd53b0e218e43aea` |

Corrections to prior assertions and static contract findings:

- The prior report interchanged the PO and line-item value-help blob SHAs.
  The corrected paths are above. UI requests Contains filters, selected
  PO/item/supplier fields, pages of 1000, and inline counts. Its controller
  adds descending PSTYPE only when no user sorter exists. Client-side
  deduplication is not a substitute for server paging/count correctness.
- UI's inspected manifest still points to XSA, **not `ZFI_DAS_SRV`**. Reading
  those contracts does not establish a deployed ABAP migration.
- External metadata and XSA preserve the historical `REVIWED_BY` spelling.
  Internal ABAP `REVIEWED_BY` maps to that external name; do not rename the
  public property. XSA formats service dates as `yyyyMMdd`, converts
  `CHANGED_ON` using CET, and supplies current UTC date/time on review updates.
- XSA source uses scoped PO totals and strict Over `>` versus inclusive
  Under `<=`; currency conversion has source decimal scale, JPY/VND
  normalization and final rounding. Static similarity is not proof of
  threshold/currency/calculation parity.
- Active XSA detail source emits a blank invoice currency, with its invoice
  currency function call commented out. Thus ABAP's unpopulated value alone
  is **not** a confirmed divergence. The manual “last relevant invoice”
  expectation is not supported by that inspected active source.
- Scope remains field-specific. XSA wildcard expansion differs by field:
  company codes enumerate EKPO; cost centers include blank; management units
  include SQL NULL. XSA role-email LIKE/token trimming is not universally
  equivalent to ABAP exact role lookup and normalization. The existing ABAP
  parsers are retained; the 30 fixture cases remain the integration oracle.
- Exclusion identity differs: XSA uses a generated local ID; ABAP metadata
  uses PO/item. This is a migration contract difference, not proven parity.
- Unchanged source differences require business/runtime follow-up: XSA's
  review grace branch additionally checks `MONTHS_BETWEEN(...)=0`; ABAP's
  previous-calendar-month retention is not identical. XSA prioritizes closure
  as Reviewed, whereas ABAP can retain Pending in its Pending branch.
  This test-restoration task does not silently rewrite those business rules.
- `$select` is not a field of the current dashboard request interface and
  calculations are unconditional there. Old assertions invoking nonexistent
  `should_skip_calculations` cannot be restored literally; actual Gateway
  projection comparisons replace them without claiming that optimization.

## Audited production changes carried forward

PR #27's complete-predicate precedence and fail-closed conversion are retained
and tested in the single class. Its blanket rejection of supported generic
select-only properties is **not** carried forward: those ranges are converted
with the existing SAP range converter, grouped by normalized property (OR
within a property and AND between properties). Unknown/internal properties
and conversion failures raise the domain exception, preserving the previous
exception where available. Complete generic SQL takes precedence over range
projections and clears stale key prefilters; it is never silently discarded.
No generic scope builder or unrelated business-rule rewrite was introduced.

The Gateway handler now obtains `get_osql_where_clause()` for the SQL predicate
instead of passing raw `get_filter_string()` OData (`eq`, `substringof`,
`datetime`) to HANA `APPLY_FILTER`. Raw text is only presence evidence.
An error is raised only when neither SQL nor select-options represents a
present filter; select-only and both-populated inputs remain legitimate.
The request-context API was corroborated against public open-abap interface
commit `2b47b5f0f5b9f171c5555a72f791dfae1986410a`, blob
`767da44a3db3ab45cb5c3bbb867d23eb36477457`; this is **not** installed-SAP-release
signature validation. Actual conversion of nested expressions and date
values remains an integration check.

`tt_key` now transports rows in AMDP order rather than reordering them by its
old sorted primary PO/item key, which lost `PSTYPE DESC`. `get_details` uses a
separate sorted unique lookup, preserving efficient lookup and uniqueness
checking without reordering output transport. AMDP selects distinct keys;
runtime replicated-data integrity remains a prerequisite. The existing
pre-filter `original_row_index` assignment, AMDP order restoration, count
after filtering, and single post-filter sorting/paging pass are retained.
Missing checked-exception propagation declarations were added only to the
directly coupled methods.

## Restored selection scenario

`ltc_parity.selection` invokes the independently runnable
`ltc_parity.test_selection`. Its restored body uses the same real fixture,
user, flow and supplier check as the original, adapting the removed separate
PO/item/contains members into current `filter_select_options`:

```abap
METHOD test_selection.
  reset_fixture( ).
  DATA(ls_case) = VALUE ts_case(
    fixture = 'xsa-selection.json' email = 'adam.strasky@takeda.com'
    flow = zif_fi_das_dashboard=>mc_over
    pstype = zif_fi_das_dashboard=>mc_pstype_service
    filter_select_options = VALUE #(
      ( property = 'PONUMBER' sign = 'I' option = 'EQ' low = '8000401022' )
      ( property = 'ITEMNO' sign = 'I' option = 'EQ' low = '00002' )
      ( property = 'SUPPLIERNAME' sign = 'I' option = 'CP' low = '*Fuji*' ) ) ).
  run_paged_case( ls_case ).
  assert_no_differences( ).
ENDMETHOD.
```

The fixture has the actual `8000401022` / `00002` row. Item leading zeros are
preserved as strings, and the contains check is represented with explicit CP
wildcards. This is a real JSON comparison, not an assertion about method
existence. Its SAP execution is still **NOT EXECUTED**.

## Legacy mapping and assertion adaptations

The complete mapping rule is: every test in `ltc_fi_das_gateway_parity` and
`ltc_request_processing` moves to the **same method name in `ltc_parity`**,
unless explicitly renamed below. This includes the fully commented
`test_all_pstype_request` and `generic_contains_filters_rows` declarations,
not only the 122 active declarations. All 23 focused regression leaves from
PR #27 also move into `ltc_parity`; unchanged names follow the same rule.
The reproducible mapping commands above enumerate the complete per-test
mapping, rather than inferring coverage from method existence.

| Old method | `ltc_parity` replacement |
|---|---|
| `threshold_equal_is_under` | `threshold_fixture_classes` |
| `default_order_has_unique_keys` | `default_order_unique_keys` |
| `compatible_default_prefix_is_removed` | `default_prefix_removed` |
| `non_default_order_is_preserved` | `non_default_order_preserved` |
| `requested_sort_adds_default_ties` | `sort_adds_default_ties` |
| `invalid_and_duplicate_sorts_are_ignored` | `invalid_duplicate_sorts` |
| `empty_orderby_preserves_input_order` | `empty_order_preserves_input` |
| `mixed_filter_keeps_generic_predicate` | `mixed_filter_keeps_predicate` |
| `cross_property_or_disables_prefilter` | `cross_or_disables_prefilter` |
| `unoptimizable_filter_without_predicate_fails` | `company_range_hybrid_parity` |
| `only_single_star_is_a_wildcard` | `single_star_wildcard` |
| `scope_normalization_is_field_specific` | `scope_field_normalization` |
| `empty_generic_filter_is_a_noop` | `empty_generic_filter_noop` |
| `nested_and_or_filters_synthetic_rows` | `nested_and_or_rows` |
| `escaped_apostrophe_matches_synthetic_row` | `escaped_apostrophe_row` |
| `amount_format_x_y_and_default` | `amount_format_x_y_default` |
| `decimal_truncation_is_toward_zero` | `decimal_trunc_toward_zero` |

Changes to obsolete checks are deliberate, not silent weakening:

- `test_selection` retains its original fixture/user/filter intent; the exact
  adapted body is shown above. Standard, owner, scope and format leaves keep
  their real MIME JSON comparisons.
- The six `skip_true_*` / `skip_false_*` cases and
  `pstype_sort_noop_for_over` no longer call nonexistent selection/skip APIs.
  They compare actual Gateway projection/full-row results and current
  processing decisions. They do not assert that calculations are skipped.
- Contains/range leaves use current internal requests and SAP SQL range
  conversion, with explicit `*` CP wildcards for contains. A wildcard-free
  CP pattern is exact matching, not an implicit contains operation.
- Generic EQ/CP/AND/OR, hybrid, negation, no-match and date cases execute the
  actual `apply_generic_filter`/AMDP path on synthetic input rows. This is
  **HANA integration**, not locally executed mock proof.
- `test_eq_case_insensitive` distinguishes case-sensitive equality from an
  explicit `UPPER` predicate. Default HANA EQ is not asserted case-insensitive.
- `generic_unknown_prop_no_dump` verifies rejection and a preserved previous
  exception rather than silently ignoring an unknown field.
  `missing_predicate_fails` rejects unavailable/internal columns, not valid
  COMPANYCODE select-only filters. `company_range_hybrid_parity` replaces the
  prior blanket-rejection scenario with actual valid select-only/hybrid HANA
  equivalence; the invalid-column rejection is supplementary.
- Exclusion signs and BT operators use actual supported SQL conversion,
  replacing obsolete assertions about removed generic-filter arrays.
- Paging advances by raw response row count, not deduplicated index size.
  Page buffers are freed, page size is 1000, and a fixture-cardinality guard
  bounds runaway requests. `run_scope_case` now uses `NUMC2`, not an implicit
  one-character `TYPE n` which truncated scope numbers 10–30.
- `complex_filter_gateway` sends the complete expression from the issue,
  including negation, contains/startswith, the exclusive datetime boundary,
  nested PO disjunction and item values. Its independent oracle filters a
  compact offset index of the **unchanged real `xsa-over-service.json`**;
  it asserts positive witnesses and compares complete matching row sets,
  properties and inline counts through the existing paged comparator.
  No new fixture is fabricated.
- `po_group_and_supplier_rows` replaces the misleadingly named
  `translated_cross_or_rows`, which supplied hand-written SQL rather than
  exercising Gateway translation. It uses actual converted select-options:
  alternatives within PONUMBER are ORed, then ANDed with SUPPLIERNAME. Both
  selected POs match; a PO-only match and a supplier-only match are excluded.
  This matches the grouped-PO/supplier request documented in `Test cases.txt`.
  Actual cross-property OR remains covered separately by
  `predicate_clears_stale_ranges` and the Gateway integration request
  `gateway_cross_or_sql`; OR is not changed into AND in production.
  The XSA service `ARIBA_ACCRUALS_JS/lib/xsodata/openOwnerPO.xsodata` exposes
  SUPPLIERNAME from `LFA1.NAME1` through its calculation view/table function.
  Neither that projection nor the local metadata proves Gateway's exact
  substring SQL or case folding. Mixed-case Gateway equivalence remains a
  runtime integration check, not a claim established by synthetic rows.
- `complex_filter_hana` executes the corresponding SQL predicate on positive
  and one-condition-negative rows, checking surviving keys and original
  order. A partial PO range is supplied alongside the complete predicate to
  verify it cannot prefilter away matches. PO relational operands remain
  strings—including `'977'`; numeric conversion would change the meaning.
- `empty_result_filter_noop` supplies an invalid predicate with no rows and
  verifies the early exit; that test does not prove HANA `APPLY_FILTER`.
- `key_table_preserves_order` checks the actual transport type.
  `default_exclude_key_order` derives ordered keys from the unchanged real
  exclusion fixture and probes first/service-material boundary/last positions,
  also checking the full inline count.
- `threshold_fixture_classes` replaces the arithmetic-only comparison of two
  hardcoded 100 values with strict real Over/Under Gateway/MIME classification
  comparisons. **It is not exact-equality boundary proof.** A separately
  prepared authorized, scoped, non-excluded PO is required whose currency-
  adjusted candidate sum equals the rounded converted `ZFI_DAS_THRESH`
  threshold using `ZFI_DAS_EXCHRT`. Then assert that the exact PO/item appears
  in Under and is absent from Over. Neither labeled equality fixture/control
  data nor a SAP runtime is supplied; this integration gap remains blocked,
  rather than retaining a fake arithmetic assertion.

## Category/leaf matrix

All categories and leaves are `FOR TESTING` instance methods of `ltc_parity`.
Every leaf resets `mo_cut`, discrepancy logs and counters with `reset_fixture( )`
before executing. Categories call those same methods, not copied assertions.
Shared membership is intentional; run-all executes standalone leaves plus
their categories/subsets. Category execution may stop at its first failure.

| Category | Independently runnable scenarios |
|---|---|
| `standard` | `test_over_material`, `test_over_service`, `test_under_material`, `test_under_service`, `test_exclude` |
| `owner` | `test_over_material_owner`, `test_over_service_owner`, `test_under_material_owner`, `test_under_service_owner`, `test_exclude_owner` |
| `filter` | All repaired Gateway, range-conversion/lifecycle, generic HANA, hybrid, date, complex-expression and filter/paging scenarios; direct leaf calls, not category-to-category calls |
| `scope` | `test_scope_01`–`test_scope_30`, `single_star_wildcard`, `scope_field_normalization` and field-specific parser edge cases |
| `sort_paging` | Inline counts, top/skip boundaries, default/custom directions and tie-breakers, invalid/duplicate fields, deterministic page concatenation, Exclude ordering and actual key transport |
| `selection` | `test_selection`, calculation/status projection, PO/item/supplier value helps, all-PSType and replacements of legacy selection/skip checks |
| `format` | `test_x_format`, `test_y_format`, `test_empty_format`, `amount_format_x_y_default` |
| `request_processing` | Predicate/range lifecycle, optimized/full decisions, conversion failures, stale-state cleanup, review boundary and `threshold_fixture_classes` |
| `hana_filter` | Real AMDP integration subset: EQ/CP/AND/OR/negation, case behavior, apostrophes, dates CP/EQ/BT, no-match/order, complex expression; empty-filter/result early-return checks do not prove HANA execution |
| `utility` | `percentage_parsing_and_error`, `decimal_trunc_toward_zero` |

The audit JSON prints the **complete explicit category-to-method matrix**
and shared-leaf memberships, not just this contextual summary. Its structural
results must not be relabeled as runtime test results.

## Final available-check results

The restoring agent executed the final source checks:

| Check | Result |
|---|---|
| Full definitions/declarations/implementations | PASS: one parity test class; 220 declared / 220 implemented methods |
| Test structure / identifiers / state reset | PASS: 172 testing methods, 162 leaves + 10 categories; all identifiers at most 30; leaves reset first |
| Main filter completeness / category sharing | PASS: 71 direct leaf calls; 62 intentionally shared leaves |
| Obsolete commented executable blocks | PASS: zero archived statements; arithmetic-only threshold assertion removed |
| Original legacy mapping | PASS: 124/124 restored, including the two fully commented declarations |
| PR #27 head mapping | PASS: 147/147 restored; all 23 focused regressions incorporated |
| Known signatures/references/friends/types | PASS: no structural audit errors or stale renamed references |
| Audit parser self-tests | PASS: 9/9 |
| Changed-source whitespace | PASS: `git -c core.whitespace=cr-at-eol diff HEAD --check` |
| Fixture preservation | PASS: 45 unchanged payloads; JSON/LFS checks recorded above |
| Additional read-only source review | No significant issues reported for production/audit and restored test changes |

These are source/structural and fixture-integrity checks, **not passing ABAP
Unit results**. Synthetic HANA test inputs still invoke real AMDP and require
SAP/HANA; they were not locally executed. The complex fixture oracle has
1,674 positive witnesses among 20,131 over-service rows; that is local
reference-data analysis, not evidence of an actual SAP response.

SAP activation/ATC/ABAP Unit, HANA filtering, OData runtime parity, deployed
API signatures, exact threshold equality and the source-only business
differences identified above remain blocked or unresolved.

Final security/automated-review tool results are recorded after committing.
