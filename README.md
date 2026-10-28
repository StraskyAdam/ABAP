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

## Opt-in live versus replication integration

This verification has a different oracle: the **same SEGW request against live
and replicated SAP data**, not XSA JSON fixtures. It does not change audit
selection, roles, thresholds, account rules or user ranking.

The additional ABAP Unit-hosted integration suite is deliberately separate from
`ABAP code/Unit test.txt`. Do not install or enable it as part of ordinary
harmless test execution. It is **RISK LEVEL DANGEROUS / DURATION LONG**:
it deletes and reloads all fourteen replication targets in the current client.
ABAP Unit hosting does not make this a harmless unit test.

### Prerequisites and maintenance window

- Use only an explicitly authorized **nonproduction** SAP HANA system/client
  with the repository DDIC objects, CDS views, AMDP dashboard, DPC and active
  `ZFI_DAS_SRV` service installed. Gateway must route to that same backend/client.
- Use an authorized SAP user with source read access, the replication report's
  existing target-table change authorization and enqueue permissions, and
  permission to execute the report, ABAP Unit and Gateway client requests.
- Reserve an exclusive maintenance/test window. Stop dashboard users, background
  replication jobs and updates to source data, company scope, configuration,
  exchange rates, audit, status, notifications and exclusions until completion.
  Production replication locks a target only during that table's refresh;
  those locks do **not** freeze all source data or all dashboard dependencies.
- Each table refresh commits independently. There is **no atomic fourteen-table
  snapshot**, and a later failure does not undo earlier committed refreshes.
  Arrange recovery/backup beforehand. Neither test assertions nor `ROLLBACK WORK`
  restore already committed replication data.
- Size SAP memory/time limits for one full live/replica dataset pair, particularly
  EKBE/EKPO, and for full paginated service traversal. The suite does not keep
  all fourteen dataset pairs in memory simultaneously.

### Mode forcing and its explicit blocker

`adjust_request` normally overwrites the request source using
`get_use_replication()` and `REPLICATION_TO`; changing a helper's `i_day` does not
force an HTTP service request. The integration uses an ABAP Unit-only test seam
at that source-selection boundary, not a public forced-mode OData option and
not temporary persistent configuration updates. With no injection, production
source selection and business output are unchanged.

The suite requires an execution receipt from the injected dashboard code for
**each** real Gateway request. ABAP Unit injections and test class state are
local to their execution context: a separate HTTP/RFC/backend session does not
inherit them. `SESSION_CONTEXT('CLIENT')` in SQLScript is a client restriction,
not proof that Gateway shares the ABAP Unit session. A missing/wrong receipt is
a PRECONDITION blocker, never a successful live/replica comparison. This can
block normal hub/HTTP deployments; do not bypass the guard or replace it with a
local call to the dashboard. No cross-session forcing is claimed to work
without SAP runtime evidence.

### Required execution order and interpretation

One orchestrated integration test, not test-method ordering, enforces:

1. Full refresh through `ZFI_DAS_REPLICATION`, with `p_del = abap_true`, for
   EKKO, EKPO, EKKN, EKBE, T001, LFA1, CSKS, CSKT, USR01, USR02, USR21,
   ADRP, ADR6 and ZFI_ACCRUAL_EXCL. Require a matching successful completion
   receipt from the production path **after** it returns from its commit.
   The report's success-style error messages and `SUBMIT ... AND RETURN` alone
   are not success evidence.
2. Verify all fourteen current-client parameterized `zi_fi_das_*` projections:
   explicit columns matching `open_cursor`, sorted by every selected field,
   complete content and multiplicities, not merely counts. Source-system
   constraints still apply, including PO/company scope, EKPO eligibility,
   LFA1 replacement and exclusion rule types. No additional normalization is
   allowed. A failed refresh or dataset check blocks the service stage.
3. Execute identical real Gateway requests in forced LIVE and REPLICA modes,
   checking the execution receipts, all business properties, key sets,
   duplicates, inline counts and ordered page traversal. No XSA fixture values
   are used as expected business values. Empty required scenarios are failed
   prerequisites, not evidence of parity.

Keep the SAP application and HANA calendar dates stable and aligned throughout
the run; avoid midnight/month changes. Date-dependent validity and calculation
fields are compared, not ignored. Changed notifications/status timestamps are
also real differences; the maintenance window must prevent such changes.
Do not treat a mode-context blocker, empty scenario or incomplete traversal as
a passing result.

### Execution evidence

No authorized SAP/SEGW runtime is configured in the coding environment.
**SAP activation/syntax checking, ABAP Unit execution, actual replication and
real live/replica Gateway comparisons have not been run here.** Repository
review and security/static checks are not a substitute for these SAP checks.
Record system ID, client, user, Gateway routing, application/HANA dates,
activated transport versions, source counts, scenario counts and complete ABAP
Unit output when an authorized operator executes the suite.
