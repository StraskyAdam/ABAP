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

## Scope parity fixtures and ABAP Unit

The scope matrix contains **5 scenarios × 62 scopes = 310 fixtures/tests**.
All scenarios use `xsa-null-01@takeda.com` through
`xsa-null-62@takeda.com`, without owner mode. Configure these users in XSA
and the ABAP role table with identical company code, management unit and
cost center scopes before downloading.

| Scenario | Fixture pattern (`NN` = `01`…`62`) | ABAP Unit class |
|---|---|---|
| Over Service | `xsa-scope-over-service-NN.json` | `ltc_scope_over_service` |
| Over Material | `xsa-scope-over-material-NN.json` | `ltc_scope_over_material` |
| Under Service | `xsa-scope-under-service-NN.json` | `ltc_scope_under_service` |
| Under Material | `xsa-scope-under-material-NN.json` | `ltc_scope_under_material` |
| Exclusion | `xsa-scope-exclude-NN.json` | `ltc_scope_exclude` |

Over uses `openOwnerPO/openPOParameters`; Under uses
`thresholdPO/thresholdParameters`. Service sends `IP_PSTYPE='9'`, Material
sends `IP_PSTYPE='0'`. Exclusion uses
`exclusionPO/exclusionPOParameters` and omits `IP_PSTYPE`.

From an absolute checkout path, run the offline wiring regression check:

```powershell
$repo = '<absolute-checkout-path>'
& "$repo/Validation/test-scope-matrix.ps1"
# Optional: inspect all 325 requests without downloading or writing files.
& "$repo/Validation/download-xsa-json.ps1" -ListRequests
```

Remaining SAP/XSA runtime steps (not performed by the offline check):

1. In an authenticated XSA environment, change directory to
   `"$repo/Validation"` and run `& "$repo/Validation/download-xsa-json.ps1"`.
   This downloads all 310 scope fixtures plus the existing 15 non-scope
   fixtures, retaining pagination. Use matching XSA/ABAP data snapshots.
2. Import the JSON files as UTF-8 into the SAP MIME repository under
   `/SAP/PUBLIC/DAS/`, preserving each filename exactly. The checked-in
   legacy `xsa-scope-NN.json` samples cover only Over Service scopes 01–30;
   they are not consumed by the new tests and are not substitutes for the
   new downloads. Do not fabricate missing fixtures.
3. Load the complete `"$repo/ABAP code/Unit test.txt"` into the existing
   dashboard ABAP Unit test include, then syntax-check and activate it.
4. Run the five `ltc_scope_*` classes with LONG/HARMLESS tests enabled
   (62 methods each), then run `ltc_fi_das_gateway_parity` to check the
   preserved non-scope cases. Missing MIME fixtures must fail, not skip or
   become empty results. Gateway access and the SAP/HANA runtime are required.

## Objective

The objective of this repository is to support:

- analysis of the SAP DAS solution
- validation of generated ABAP artifacts
- comparison of business logic with XSA implementation
- identification of functional or technical gaps
- understanding of data replication and source-system limitations

For all validation and comparison activities, the XSA implementation remains the authoritative source of truth.
