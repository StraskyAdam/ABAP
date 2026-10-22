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

## Standalone exclusion refresh

`ZFI_DAS_EXCLUSION` replaces the exclusion snapshot independently of replication.
It does **not** extend or change `ZFI_DAS_REPLICATION`, and introduces no global
exclusion class. The report owns authorization checks, the target lock, transaction,
dry-run and status; its local final class calls the dashboard's narrow
`get_exclusion_candidates` API, not the paged/detail-producing dashboard outputs.
Selection and evaluation helpers do not commit.

### Source and parity contract

The inspected XSA revision is
[`e5fd6d0a36957baa795608f85abdc9d4e810e834`](https://github.com/StraskyAdam/XSA/tree/e5fd6d0a36957baa795608f85abdc9d4e810e834).
Relevant authoritative artifacts:

- `ARIBA_ACCRUALS_JS/lib/xsjs/exclusionPO.xsjs`: invokes staging, commits and
  reports scheduler status.
- `ARIBA_ACCRUALS_DB/src/Procedures/exclusionStaging.hdbprocedure`: unions
  over/under candidates separately for requested material/service categories,
  evaluates each category, then replaces the snapshot with a UTC timestamp.
- `ARIBA_ACCRUALS_DB/src/Functions/getOpenPOQueryWithEmail.hdbfunction`:
  **declares `TF_getOpenPOQueryWithEmail`**. The similarly named `_old` artifact
  declares a different symbol and is not the staging dependency.
- `ARIBA_ACCRUALS_DB/src/Functions/TF_checkPOExcl_Mod.hdbfunction`: authoritative
  joins, normalization, six match flags and final reason selection.

The shared candidate API requests modes `1`/`2`, categories `0`/`9`, email `*`,
blank PO-owner, no user filters and no paging. It bypasses existing exclusions;
normal dashboard calls still apply them by default. Mode `3` remains
excluded-only, not an all-candidates shortcut. Requested category is written as
`PSTYPE`, including material items classified as services by Japan/Brazil rules.
The AMDP receives the current client explicitly for source, scope, rate and
exclusion reads. Open SQL enrichment and writes use implicit current-client
handling; no cross-client refresh is supported.

Evaluation uses all EKKN assignments and left joins EKPO, EKKO, LFA1 and T001;
the company is from T001, and output keys come from joined EKPO. Missing joins
and SQL NULLs must not be equated to existing blank values. Leading-zero removal
and ranges are string operations, not numeric/ALPHA conversion. Company lower
equality can match even when the upper bound is unusable. PO/vendor comparisons
are intentionally not gated by rule type. Profit-center values remain unstripped;
the source's `00000000`/`9999` defaults and ineffective unassigned-variable
equality in the company-BETWEEN branch are preserved, not corrected.
`TR` appears in the rule extraction constraint but has no seventh match flag
in this XSA evaluator; like any other rule row it can still match ungated PO/VD
criteria. Rule threshold is not an evaluator predicate.

XSA DISTINCT applies to `(PO,item,GL,CC,IV,PC,PO-match,VD)`, separately per requested
category. Final priority is GL, CC, IV, PC, PO, VD **per vector**, not globally per
item. Distinct vectors can produce identical final rows. The evaluator retains
those rows; it does not deduplicate the final output.
The candidate counter records the over/under UNION ALL rows. Enrichment reads
each PO/item key once per category, since repeated identical inputs cannot
change the later vector DISTINCT; its assignment counter therefore measures
rows after that redundant-input reduction, not the raw XSA join expansion.

The verified image `Table definition/ZFI_DAS_PO_EXCL.png` shows:

| Field | Key | Metadata |
| --- | --- | --- |
| MANDT | yes | CLNT 3 |
| PONUMBER | yes | EBELN, CHAR 10 |
| ITEMNO | yes | EBELP, NUMC 5 |
| RULETYPE | yes | SSTRING 2 |
| LAST_REPLICATED_AT | no | TIMESTAMPL, DEC 21,7 |
| PSTYPE | no | SSTRING 2 |

That key cannot represent repeated final reasons or the same reason in both
categories. Such conflicts **abort before DELETE**, preserving the old snapshot;
they are an unresolved storage-contract difference, not successful parity.
Do not add `ACCEPTING DUPLICATE KEYS` or silently collapse them. Supporting SAP
metadata is not proof of the external XSA target's uniqueness constraints.
`Table definition/ZFI_DAS_EXCHRT.png` also confirms client-dependent rates:
key `(MANDT,SOURCE_CURR,TARGET_CURR)`, with `EXCHANGE_RATE` DEC 13,6. Selection
retains the existing source-currency-only rate join; client filtering does not
silently change it to a target-currency-filtered join.

### SAP setup and activation

These are transportable source artifacts, not an abapGit export. Installation
requires SAP ABAP 7.54+ on HANA (including internal-table SQL joins, SSTRING casts
and test seams); verify those features on the installed release. SQL string
projections and separate NULL flags avoid losing source spaces through implicit
CHAR-to-string assignment. This repository has no executable ABAP compiler,
test runner or CI test configuration.

1. Verify the existing DDIC objects in the target client/system: rule table
   `ZFI_ACCRUAL_EXCL`, target `ZFI_DAS_PO_EXCL`, dashboard configuration, rates,
   source tables and `ZI_FI_DAS_PO_BASE` / SQL view `ZIFIDASPOBASE`. Compare the
   installed target key with the image above. The report uses actual DDIC row
   types rather than creating replacement tables.
2. Activate the backward-compatible `ZCX_FI_DAS_ERROR` update from
   `ABAP code/zcx_fi_das_error.txt`: optional `i_text` and message-text override.
   Existing T100 exceptions retain their inherited text when no `i_text` is
   supplied. New report errors use descriptive text, not invented message IDs.
3. Activate the dashboard update, with its existing interface and CDS
   dependencies. Update/activate **all** installed callers of the private AMDP
   signature (including local tests) with client and apply-exclusions arguments.
4. Create executable report `ZFI_DAS_EXCLUSION` from
   `ABAP code/zfi_das_exclusion.txt`, and include `ZFI_DAS_EXCLUSION_DEF` from
   `ABAP code/zfi_das_exclusion_def.txt`. Install the supplied local test include
   `ZFI_DAS_EXCLUSION_TEST` from `ABAP code/zfi_das_exclusion_test.txt`.
   Activate the report/includes together. Run syntax checks, ATC and ABAP Unit
   in SAP before transporting or enabling a productive variant.
   Maintain selection texts `P_DRY` = “Dry run” and `P_EMPTY` = “Allow empty
   snapshot” in the report's language-dependent text elements.

No new global class, message class, target table or enqueue object is required.
`ENQUEUE_E_TABLE` must be available. Existing writers must honor the same
client/table lock; an enqueue does not prevent uncooperative direct SQL.
The report has effective `S_TABU_NAM` display checks for every source/configuration
table it reads and display/change checks for the target. Grant the batch user only
the required tables/activities (`03` read, `02` change), plus normal job/report
execution permissions. A wildcard candidate email is not an authorization check.

### Operation and scheduling

- Start with a **dry-run variant** (the default). Inspect candidate-item,
  assignment, match-vector/result and replacement counts in the spool.
- Create a productive variant with `P_DRY` off only after parity checks.
  Empty replacement is blocked by default; enable the explicit empty-snapshot
  option `P_EMPTY` only for an independently verified intentional empty population.
  Zero candidates alone neither proves nor disproves failed replication.
  Empty rule configuration, missing scope/configuration and missing/invalid
  rates must be investigated instead of interpreted as a valid empty result.
  Preflight requires nonblank H/I company scopes, a current-client role row,
  exactly one positive USD threshold row, and a nonempty Japan/Brazil
  configuration with existing company codes. The threshold guard avoids the
  shared selector's otherwise unordered `SELECT SINGLE` choice. The candidate
  API conservatively checks rates for every currency in the shared base, even
  if a particular call would not select that currency.
- Schedule refresh **after all required source replications, currency rates and
  configuration maintenance have completed successfully**, not merely after a
  single table replication job. Stop on upstream failure. Failure of the new
  report cancels a background job, rather than displaying an error as a
  successful status message.
- The checked-in `ZI_FI_DAS_PO_BASE` reads live EKKO/EKPO and the dashboard's
  access scope reads live EKKN/CSKS. The refresh consequently enriches from live
  tables too. There are no checked-in `zi_fi_das_ekko/ekpo/ekkn` definitions with
  `p_use_replication`, nor a replication report or configured source-mode switch
  in this checkout. Do not deploy this artifact unchanged against a separately
  modified replica-mode dashboard: first align both readers to its verified
  source API. A hardcoded mixture of live and replica transactional data is not
  supported.
- The target lock is acquired before reading/calculating and held through one
  atomic DELETE + INSERT + `COMMIT WORK AND WAIT`. Errors before commit roll back
  and release the lock; dry-run never replaces data. Another cooperating
  refresh cannot interleave. Existing valid data survives evaluation, authority,
  key-conflict and insert failures.
- This is **not a multi-table source-generation lock**. Live data, rules and
  rates can change between reads; separate replication table locks do not solve
  that problem. Use a coordinated maintenance window/upstream job chain with
  no concurrent source/configuration writers. No shared generation coordination
  infrastructure was found, and replication is intentionally unchanged.

### Validation and remaining SAP checks

Install existing dashboard tests from `ABAP code/Unit test.txt` and the new local
report tests. Execute the pure SHORT tests first, then HANA-backed candidate and
client-isolation tests, and finally aligned-data integration/parity tests.
Never run destructive replacement tests in a productive client.

Required acceptance checks in an isolated client:

- Compare default dashboard selection (old exclusions still removed), refresh
  bypass (old exclusions included), mode 3, scope `*`, requested PSTYPE, count and
  paging behavior. Check two clients containing identical PO/item keys but
  different exclusions, rates and assignments.
- Test every rule code, equality and reversed/blank/NULL bounds, zero stripping,
  lexicographic ranges, missing joined rows, multiple EKKN assignments, PC quirks,
  vector priority and duplicate output multiplicity.
- Run dry-run and repeated real refreshes against the same source. Inject lock,
  authorization, evaluation and INSERT failures; compare the previous snapshot,
  released locks and background cancellation. Test empty candidates, empty
  matches, missing prerequisites and deliberate empty opt-in separately.
- Freeze the same source generation, rate values and rule configuration in SAP
  and XSA. Compare input counts per requested PSTYPE, assignment counts, distinct
  vectors and **multisets** of final `(PONUMBER,ITEMNO,RULETYPE,PSTYPE)` rows.
  Compare counts per PSTYPE/RULETYPE and repeated-tuple frequencies, not just
  distinct keys. Exclude the UTC refresh timestamp from value parity.

Known validation boundaries: XSA external table DDL/nullability, runtime
deployment, collation, current configuration and rate cardinality are not
established by repository source. Rule field names are evidenced by source
extraction, but their installed DDIC lengths/nullability require SAP inspection.
Character padding/collation and ABAP SQL feature availability require activation
and aligned-data checks. XSA wildcard expansion requires matching role
configuration; the dashboard wildcard is broader, so the standalone preflight
requires role configuration rather than silently accepting an unconfigured run.
Existing selection/data-scope differences must be compared against
`Source system constraints/Constraints of replication.txt` before classifying
them as new exclusion defects.
In particular, the shared CDS retains its `ZFI_DAS_BUKRS` header/item scopes,
ZARP/PO-number/reason-code filters, deletion/final-invoice checks and special
2780 selection. Wildcard email does not bypass those predicates. Compare the
configured scopes to XSA's replicated subscription population; this refresh
does not introduce a second, independently maintained base query to bypass them.
The recorded subscription queries substantiate the PO-range, reason-code,
deletion and special-company filters upstream of XSA, but do not prove live
deployment state. Header and item subscription company lists differ and must
each be aligned with their corresponding H/I configuration.

No SAP activation, ABAP Unit execution, transactional fault injection or live
XSA/SAP parity success is claimed by these repository artifacts.
