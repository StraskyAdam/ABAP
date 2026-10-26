# SAP DAS Migration Repository

## Purpose

This repository contains SAP DAS migration artifacts used to analyse the XSA implementation and support generation of ABAP deliverables.

The XSA repository is the system of record and the authoritative implementation for all functional and technical comparisons.

## Repository Structure

```text
ABAP code/                 Generated or derived ABAP artifacts
Source system constraints/ Source extraction and replication constraints
Table definition/          Table metadata and structures
Technical documentation/   Functional and technical documentation
UI example of data/        Example outputs and screenshots
Validation/                Validation materials and findings
Workflow/                  Business and process flow documentation
```

## Source of Truth

The XSA implementation is the authoritative source of truth.

This repository contains supporting artifacts used for analysis, validation, documentation, and generation of ABAP deliverables from the XSA solution.

When discrepancies are identified:

1. XSA implementation takes precedence.
2. ABAP artifacts must be validated against the XSA implementation.
3. Technical documentation should be treated as supporting information only.
4. Validation results, workflows, screenshots, and examples provide business context only.
5. If documentation conflicts with XSA code, the XSA implementation is considered correct.

## Source System Constraints

The `Source system constraints` folder contains source-system extraction and replication constraints used by the original SAP Accrual solution.

These constraints may explain differences between:

- ECC source data
- Replicated datasets
- Generated ABAP artifacts
- XSA implementation results

Examples include:

- table-specific replication filters
- purchase order restrictions
- company code restrictions
- custom exclusion rules
- source extraction predicates
- replicated data limitations

Before reporting any discrepancy between generated ABAP artifacts and XSA implementation, always verify whether the difference can be explained by source-system constraints.

## Usage Guidelines

When analysing or comparing SAP DAS functionality:

- Use the XSA implementation as the primary reference.
- Validate generated ABAP artifacts against the XSA implementation.
- Use technical documentation only for additional functional context.
- Use workflow documentation to understand business processes.
- Use UI examples only to understand expected output and user-facing behaviour.
- Review source-system constraints before classifying any difference as a defect or implementation gap.
- Distinguish between implementation differences and data-scope differences caused by source-system filtering.
- Document assumptions and unresolved findings.

## Objective

The objective of this repository is to support:

- analysis of the SAP DAS solution
- validation of generated ABAP artifacts
- comparison of business logic with XSA implementation
- identification of functional or technical gaps
- understanding of data replication and source-system limitations

For all validation and comparison activities, the XSA implementation remains the authoritative source of truth.

## Replication-aware data access

### Source and consumer inventory

Only **EKKO, EKPO, EKKN and EKBE** have replication-aware sources in this
branch. Each `ZI_FI_DAS_<table>` takes `p_use_replication`: space means live,
`X` means `ZFI_DAS_<table>`. Its `_SRC` view unions the intentional live
table read with the snapshot. Keep these live branches independent of the
active wrappers; routing them through a wrapper would create recursion.

| Consumer | Sources and flag handling |
|---|---|
| `ZI_FI_DAS_PO_BASE` (both exported definitions) | Existing identity and SQL view `ZIFIDASPOBASE` retained; parameter passed to EKKO and EKPO. T001/LFA1 remain live. Projection, keys and currency/unit annotations retained. |
| `ZCL_FI_DAS_DASHBOARD->execute_request` | One flag evaluation after request adjustment; internal request only, no public OData schema change. |
| Dashboard `get_keys` | Static AMDP receives the same flag and `sy-mandt`; calls generated PO_BASE/EKKN SQL functions. Client predicates cover base, accounts, CSKS, exclusions and exchange rates. Business filters, thresholding, count and paging remain in place. |
| Dashboard `get_context` | Passes the request flag unchanged to `get_details` (PO_BASE), `get_accounts` (EKKN), `get_history` (EKBE). Two-key FAE guards and aggregation/mapping retained. |
| Dashboard `get_exclusion_candidates` | Direct callers evaluate once; optional explicit flag lets snapshot producers force live without consulting configuration. |
| `ZFI_DAS_EXCLUSION` / `LCL_EXCLUSION` | Both candidate modes and EKPO/EKKO/EKKN enrichment explicitly force live; exclusion snapshot writes, authorization, locking and transaction flow unchanged. |
| `ZI_FI_DAS_EXCHANGE_RATE` / `ZFI_DAS_EXCHANGE_RATE` | Currency enumeration uses EKKO wrapper; refresh explicitly forces live, retaining conversion and transaction logic. Currencies now come from the supported EKKO business scope, not all EKKO records. |
| `ZFI_DAS_REPLICATION` | Existing four cursors already force live. Target DELETE/INSERT, whitelist, locks and commit/rollback behavior intentionally unchanged. |
| `ZCL_ZFI_DAS_DPC_EXT`, `ZFI_DAS_DASHBOARD_VIA_ABAP` | Delegate to dashboard entry methods, so inherit request-scoped selection without another flag lookup. |
| `ZIF_FI_DAS_DASHBOARD`, shared result types, `ZCL_FI_DAS_UTILITY`, `ZCX_FI_DAS_ERROR` | No supported PO-table reads to migrate. DDIC `TYPE ekpo-*`, `ekkn-*`, `ekbe-*` and similar technical references remain unchanged; a type reference is not a live read. |
| ABAP Unit, manual Gateway cases, validation JSON/PowerShell downloader | Existing diagnostics use the public dashboard/Gateway routes or synthetic data. No independent PO_BASE comparison/benchmark report exists in this checkout; none was fabricated. |

The only remaining direct reads of the four supported PO tables are the
live branches of their `_SRC` definitions. CSKS/CSKT, T001/LFA1, user/address
tables (USR21, USR01, USR02, ADR6, ADRP), role/threshold/configuration tables,
exclusion rules (`ZFI_ACCRUAL_EXCL`), exchange-rate configuration and runtime
status/audit/notification tables remain as designed: this branch contains no
replication wrappers for them. Currency conversion still uses SAP reference
data. In particular, runtime status/audit reads and transactional writes must
not be redirected to snapshots.

Source business rules are unchanged, including EKPO's left scope join and
the special 2780 branch (empty XERSY, or XERSY = X with a noninitial start
date). Do not add a required 2780/EKPO scope row or repeat header/item scope
joins or business predicates in PO_BASE. The legacy 2780/H and 2780/I
configuration and 2780/EKKO-only new scope are intentional.

### Flag contract

`ZCL_FI_DAS_DASHBOARD=>get_use_replication` reads `REPLICATION_TO` directly
from `ZFI_DAS_CONF_VAL`, without a class-data cache. Missing/empty means
live. The value is converted to an integer (`6` and `06` are equivalent)
and validated against constants 1..31. The recurring inclusive window is
day 1 through the configured day, every month. Omitted `i_day` uses today's
day; explicitly supplied zero is invalid. There is no `REPLICATION_FROM`,
fixed until-date, freeze function or AUTO testing view.

The specified messages are `006` (bad input day), `031` (conversion failure,
including overflow, retaining the previous exception) and `032` (configuration
outside 1..31), all in `ZFI_DAS`. **Message definitions are not exported.**
Existing code also uses 006 for missing email, 031 for refresh commit failure
and 032 for refresh deletion failure. These existing uses were not renumbered:
resolve compatible texts/transport coordination in SE91 before activation;
do not assume the message catalog already matches the requested contract.

### Snapshot readiness and activation prerequisites

- Snapshot DDIC definitions for `ZFI_DAS_EKKO`, `ZFI_DAS_EKPO`,
  `ZFI_DAS_EKKN`, `ZFI_DAS_EKBE`, and the new `ZFI_DAS_CC_SCOPE`
  definition/configuration are absent from this checkout. Validate them in
  SAP, including client dependence, complete source-compatible field types,
  currency/unit references, and unique source keys (especially EKKN ZEKKN
  and EKBE document/account-assignment keys). Missing objects block activation.
- Activate the target/scope DDIC objects, `_SRC` views, active wrappers, then
  PO_BASE and exchange-rate CDS, then classes/reports and local ABAP Unit
  include together. Parameterizing the existing PO_BASE requires activating
  its consumers together; do not deploy a parallel replacement identity.
- On the target ABAP/HANA release, syntax-check the AMDP `USING` CDS entities
  and generated DDIC SQL function calls `ZIFIDASPOBASE` and `ZDASEKKN` with
  named `p_use_replication` arguments and exposed MANDT. Open SQL supplies
  normal client handling; SQLScript explicitly uses the passed request client.
- Keep `REPLICATION_TO` absent/empty while initially populating **all four**
  snapshots and validating row counts, duplicates, client isolation and
  cross-table consistency. Also refresh exchange rates and exclusions from
  live data and check currency coverage before enabling replication.
- The population report commits one table at a time, with per-target locks.
  The common flag is **not atomic publication**, does not pin a snapshot
  version and does not protect active requests against snapshot replacement.
  Quiesce readers/jobs and keep replication disabled through refresh and
  validation; drain in-flight requests before replacing active snapshots.
  A production scheduler/versioned publication protocol is outside this
  checkout and remains an operational prerequisite.

### Validation and SAP regression plan

This repository contains text exports and SAP ABAP Unit classes, but no
local ABAP compiler, runnable build/lint configuration or SAP connection.
No SAP activation, ABAP Unit execution or runtime performance result is
claimed. Focused `LTC_REPLICATION` tests use test seams (no configuration
writes) for days 1/6/7/31 with TO=6, leading zeros, today's default,
missing/empty configuration, explicit invalid days, conversion/overflow,
out-of-range values, one evaluation per request without cross-request caching,
direct candidate calls, forced-live candidate calls and empty FAE guards.

In SAP:

1. Run syntax checks/ATC and `LTC_REPLICATION`, then existing SHORT tests;
   run HANA filter, Gateway and scope parity suites in both modes.
2. Use distinct live/snapshot fixtures for all four sources. Check both owner
   modes and all over/under/exclude paths, details/account/history enrichment,
   cutoff dates, financial conversions, nulls, duplicate multiplicity, sorting,
   count and paging. Change configuration between requests, not during one.
3. Verify same PO/item identifiers in another client cannot affect AMDP scope,
   threshold, exclusion or count; verify Open SQL enrichments stay in-client.
4. With REPLICATION_TO enabled and deliberately different snapshot values,
   run each refresh report in test mode first and then a controlled refresh.
   Confirm every population cursor and candidate/enrichment read uses live
   data, never the target being cleared. Check rollback/lock behavior.
5. For PO_BASE parity/performance, retain the **original live SQL projection**
   externally as the independent baseline. Comparing two selections of the
   new parameterized view would not establish parity. Compare every field and
   duplicate count, including 2780 and missing master records, then measure
   AMDP key selection plus FAE enrichment end-to-end in both modes.

The user-supplied full-SELECT benchmark (144670 rows each, content and
multiplicity equal; 2076.551 ms versus 1602.612 ms) is historical evidence
only. It was not rerun here and does not establish AMDP/FAE end-to-end
performance or successful activation of these changes.
