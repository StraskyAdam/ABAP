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
- Size SAP memory/time limits for one full live/replica dataset pair and its
  comparison indexes, particularly EKBE/EKPO, and for full paginated service
  traversal. The suite does not keep all fourteen dataset pairs in memory
  simultaneously. The descending-order variant intentionally uses one row per
  page, with a LIVE and REPLICA request for every page; large result sets can
  make the maintenance window substantially longer than a few minutes.

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

### Installation and SAP execution

1. In the authorized backend, install/activate the changed
   `ZFI_DAS_REPLICATION_DEF` include and `ZFI_DAS_REPLICATION` executable report
   from their files under `ABAP code/`. Keep report parameters `p_table` and
   `p_del`; no temporary checker report is needed. Activate the changed
   `ZCL_FI_DAS_DASHBOARD` implementation from
   `ABAP code/zcl_fi_das_dashboard.txt` with its `das_replication_mode` seam.
2. In SE24/SE80 or ADT, open `ZCL_FI_DAS_DASHBOARD`'s **local test classes**
   source. Preserve the existing `ABAP code/Unit test.txt` contents. Append
   `ABAP code/Unit test replication.txt` to the same local test include
   (not to the DPC class and not to a standalone report), then syntax-check
   and activate the class. The file is self-contained and does not read MIME
   fixtures. ABAP Unit test seams and the Gateway client classes used by the
   existing suite must be available on the installed SAP release.
3. Keep `ltc_repl_integration=>enabled = abap_false`. Select only the local
   `ltc_repl_contract` test class in the ABAP Unit runner and execute its
   SHORT/HARMLESS in-memory regression tests. This does not refresh data or
   call Gateway. Existing harmless business test selections remain independent.
4. Confirm service registration/routing in `/IWFND/MAINT_SERVICE` and exercise a
   GET in `/IWFND/GW_CLIENT` in the intended client. The suite uses
   `/iwfnd/cl_sutil_client_proxy=>web_request`, as the existing tests do.
   A working manual GET does **not** prove the ABAP Unit injection can cross
   the configured dispatch boundary; only the per-request receipt can do that.
5. After obtaining destructive-test approval and starting the maintenance
   window, edit only the integration test's local opt-in constants:
   `enabled = abap_true`, `authorized_system = '<SID>'`,
   `authorized_client = '<client>'`, `authorized_user = '<SAP user>'`,
   `scenario_email = '<authorized nonowner dashboard email>'`. Use the real
   three-character SID/client and SAP logon user; placeholders must not remain.
   The test also rejects production/unknown client classification in T000.
   Owner requests reuse the five flow-specific identities from existing request
   definitions, selected in `refresh_verify_gateway`; review and, if necessary,
   adapt those test-only identities for the authorized client's data. Each
   required base case needs at least two rows for paging, and each filtered
   case at least one. Do not weaken the nonvacuity assertions to accommodate
   insufficient test data.
6. Activate this local nonproduction test version. In `SAUNIT_CLIENT_SETUP`,
   have the administrator permit LONG/DANGEROUS tests **only in this approved
   client/window**. In the ABAP Unit runner select only
   `ltc_repl_integration`, method `refresh_verify_gateway`, and run it. Do not
   run a package-wide suite to trigger this test. The method performs the
   ordered refresh, dataset verification and Gateway stages below.
7. Save the ABAP Unit result and failure details. A PRECONDITION failure means
   the service comparison was not completed; earlier replication commits may
   nevertheless exist. Resolve the cause and rerun from the beginning.
   Afterwards set `enabled = abap_false`, reactivate, and restore the client's
   previous ABAP Unit execution policy. The test clears its transient armed
   state and acknowledgement memory; it never edits `REPLICATION_TO`.

### Required execution order and interpretation

One orchestrated integration test, not test-method ordering, enforces:

1. Full refresh through `ZFI_DAS_REPLICATION`, with `p_del = abap_true`, for
   EKKO, EKPO, EKKN, EKBE, T001, LFA1, CSKS, CSKT, USR01, USR02, USR21,
   ADRP, ADR6 and ZFI_ACCRUAL_EXCL. Require a matching successful completion
   receipt from the production path **after** it returns from its commit.
   The report's success-style error messages and `SUBMIT ... AND RETURN` alone
   are not success evidence. The one-use ABAP memory request
   `ZFI_DAS_REPL_REQUEST` carries a UUID token; `ZFI_DAS_REPL_DONE` must return
   the same token, source table, full-delete flag and success flag. A stale,
   missing, failed or mismatched completion aborts the precondition.
2. Verify all fourteen current-client parameterized `zi_fi_das_*` projections:
   explicit columns matching `open_cursor`, sorted by every selected field,
   complete content and multiplicities, not merely counts. Source-system
   constraints still apply, including PO/company scope, EKPO eligibility,
   LFA1 replacement and exclusion rule types. No additional normalization is
   allowed. Database nullability must be checked before SQL results are
   converted to ABAP values: `NULL` must never be treated as an empty/initial
   value. Nullable data is a precondition blocker unless compared with explicit
   SQL null indicators. A failed refresh or dataset check blocks the service
   stage.
3. Execute identical real Gateway requests in forced LIVE and REPLICA modes,
   checking the execution receipts, all business properties, key sets,
   duplicates, inline counts and ordered page traversal. No XSA fixture values
   are used as expected business values. Empty required scenarios are failed
   prerequisites, not evidence of parity.

Mismatch diagnostics include live/replica counts, missing/extra source keys and
bounded field values; service diagnostics identify the request, PO and item.
The detail cap does not cap the total counted differences. Only OData
`__metadata` transport information is excluded from row comparison; business
strings and aggregate ordering are not normalized, and JSON `null` differs
from an empty string.

Keep the SAP application and HANA calendar dates stable and aligned throughout
the run; avoid midnight/month changes. Date-dependent validity and calculation
fields are compared, not ignored. Changed notifications/status timestamps are
also real differences; the maintenance window must prevent such changes.
Do not treat a mode-context blocker, empty scenario or incomplete traversal as
a passing result.

### Execution evidence

Performed in the coding environment: source-contract checks of all fourteen
live/replica projections, complete sort fields, pair freeing and null-preflight
coverage; flattened DDIC property lists against the published SEGW metadata;
test-method/structure checks and CRLF-aware whitespace checks. The new pure
suite contains ten ABAP Unit regression methods; these are source additions,
not ten claimed runtime passes.

Changed-file secret scanning reported no secrets, and read-only code review
reported no significant issues. CodeQL was invoked but performed **no analysis**
because it detected no changed code in a supported language; this is not a
CodeQL security pass for ABAP.

No authorized SAP/SEGW runtime is configured in the coding environment.
**SAP activation/syntax checking, ABAP Unit execution, actual replication and
real live/replica Gateway comparisons have not been run here.** Repository
review and security/static checks are not a substitute for these SAP checks.
Record system ID, client, user, Gateway routing, application/HANA dates,
activated transport versions, source counts, scenario counts and complete ABAP
Unit output when an authorized operator executes the suite.
