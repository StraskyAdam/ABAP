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

`ZFI_DAS_EXCLUSION` is a standalone report with a local final class for
SAP_BASIS **750 SP0020** on HANA. It does not change `ZFI_DAS_REPLICATION`,
add a global exclusion class, or change `ZCX_FI_DAS_ERROR`. No new unit tests
or test seams are delivered; the existing dashboard tests remain unchanged.

### XSA transformation

Source revision:
[`e5fd6d0a36957baa795608f85abdc9d4e810e834`](https://github.com/StraskyAdam/XSA/tree/e5fd6d0a36957baa795608f85abdc9d4e810e834).
`exclusionPO.xsjs` invokes `exclusionStaging.hdbprocedure`, which obtains
over/under candidates for material/service, evaluates `TF_checkPOExcl_Mod`,
replaces the target and commits. The active candidate function is declared
in `getOpenPOQueryWithEmail.hdbfunction`, not the `_old` file.

The report reuses dashboard `get_required_keys` through the small public
`get_exclusion_candidates` wrapper: modes `1`/`2`, categories `0`/`9`, email `*`,
blank owner, no filters or paging. Only existing-exclusion filtering is bypassed;
ordinary dashboard calls retain their default behavior. There is no additional
prerequisites, role, configuration, rule-count or rate validation in the refresh.
Existing shared-selector configuration handling is unchanged.

Enrichment reads live EKPO/EKKO/LFA1/T001/EKKN, matching the checked-in dashboard
source. Guarded PO ranges and keyed item lookup replace the newer internal-table
SQL join; no `FROM @itab` or SQL `SSTRING` cast is required on 750. All account
assignments participate. Company comes from T001; missing EKPO rows cannot
produce a match and are omitted. NULL flags remain separate from blank values.
Leading-zero stripping and ranges are string operations, not numeric/ALPHA.
PO/vendor matches are company-scoped but not gated by rule type.
The unusual PC bounds and unassigned-variable equality branch are preserved.
TR has no separate match flag, but its PO/vendor fields remain eligible.

DISTINCT applies to the six match flags per item and requested category before
the per-row priority GL > CC > IV > PC > PO > VD. Final duplicate rows are not
silently removed. Requested category is written to PSTYPE, with one UTC
`TIMESTAMPL` per replacement. Candidate counts include over/under UNION ALL;
enrichment reads unique item keys because repeated inputs cannot change the
later match-vector DISTINCT.

### Activation and use

1. Maintain messages in the existing `ZFI_DAS` class as specified in
   `ABAP code/ZFI_DAS messages.txt` (020 authorization, 021 lock, 022 refresh
   error). Check 021/022 are available before assigning them.
2. Activate the dashboard update with its existing DDIC/CDS dependencies.
3. Create report `ZFI_DAS_EXCLUSION` from `ABAP code/zfi_das_exclusion.txt`
   and include `ZFI_DAS_EXCLUSION_DEF` from
   `ABAP code/zfi_das_exclusion_def.txt`. Maintain selection text `P_DRY`
   as “Dry run”. No test include or exception-class update is needed.
4. Check syntax and run a dry-run in SAP, then compare aligned XSA/SAP data
   including counts per PSTYPE/RULETYPE and duplicate multiplicities before
   enabling a productive variant.

The only explicit table authorization is `S_TABU_NAM` for
`ZFI_DAS_PO_EXCL`, activity `02`, using
`RAISE EXCEPTION TYPE zcx_fi_das_error MESSAGE e020(zfi_das)`.
No source-table or target-read authorization checks are added.
Exceptions use the existing T100 convention, not `RAISE EXCEPTION NEW`
or a custom `i_text` constructor.

`P_DRY` defaults on and performs no replacement. With it off, the report
replaces the current client's entire snapshot, **including clearing it when
candidates, rules or matches are empty**, as XSA does. There is no empty-result
opt-in or extra preflight. Schedule after upstream replication/rates/configuration
are ready; the report does not validate their completion.

The target lock is held from selection through DELETE, packaged INSERTs and
one `COMMIT WORK AND WAIT`. A failure before commit rolls back and unlocks;
background failures cancel the job. `ZFI_DAS_PO_EXCL` has the verified key
`(MANDT,PONUMBER,ITEMNO,RULETYPE)`; PSTYPE is not part of it. If XSA multiplicity
cannot fit that key, normal INSERT fails and the replacement rolls back—no
`ACCEPTING DUPLICATE KEYS` or separate key-validation framework is used.

The target lock does not freeze live sources or coordinate multi-table
replication. Align source generations and H/I company scopes with the recorded
subscription constraints before comparing results. Existing wildcard-scope,
source-currency rate-join and configuration behavior belongs to the shared
dashboard selector and is not independently reimplemented or validated here.
Installed DDIC types, NULL/blank/padding behavior and collation require SAP-side
comparison. No SAP activation, runtime execution or parity success is claimed:
this repository has no executable ABAP compiler or test runner.
