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

Cost-center role text `NULL` is a blank/space scope value, matching XSA;
it does not grant access to SQL NULL cost centers (including a missing
EKKN row). A singleton `*` retains wildcard behavior; in a list it is
an ordinary value. Company-code and management-unit scoping are unchanged.
The account loader retains its CSKT/CSKS joins and validity-date columns,
but no longer selects or aggregates cost-center descriptions. The result
field remains available and exclusion still clears it.

Run `ltc_dash_pure_branches` for parser/mapping regressions and
`ltc_account_aggregation` for the Open SQL test-double regression that
checks join multiplicity, account values, quantity, and management units
without a description aggregate. These ABAP Unit tests require SAP;
the offline wiring check does not execute ABAP or HANA SQLScript.

## Invoice history: calculation versus nullable output

Reference checked: XSA `main` at
`e5fd6d0a36957baa795608f85abdc9d4e810e834`.
The active `TF_getPOInvValue` inner join groups only eligible EKBE invoices
(`BEWTP Q/N`, `VGABE 2/3`, posting date through the cutoff).
An absent invoice group is not an existing zero-sum group.
`CV_getPO_INVvalue` cannot create missing groups with its projection `IFNULL`.
After the left join, both
[`CV_getOpenPO`](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Models/CV_getOpenPO.hdbcalculationview#L529-L543)
and `CV_getThresholdPO` display `INVVALUE = IFNULL(raw INVVALUE, 0)`,
but calculate `INVVALUE_CAL = IF(raw INVVALUE <= 0, 0, raw INVVALUE)`.
Their COLUMN_ENGINE accrued formula is `IF(base - INVVALUE_CAL < 0, 0,
base - INVVALUE_CAL)`, with service completed work or material GR as the
base; USD is `ROUND(rate * AMOUNTACCRUED, 2)`.
The final table functions/views pass these numeric results through.
Closure is independent; company-currency accrued uses its separate formula.

**A nullable helper does not establish a nullable accrued result.**
Existing checked-in XSA responses contradict that proposed inference:

| Fixture, PO/item | `INVVALUE_CAL` | Base | `AMOUNTACCRUED` | Accrued USD |
|---|---|---:|---:|---:|
| `Validation/xsa-under-service-owner.json`, 8002048875/00001 | null | 280.00 | 280.00 | 280.00 |
| `Validation/xsa-under-material-owner.json`, 8002086613/00001 | null | 249.17 | 249.17 | 273.01 |
| `Validation/xsa-over-material.json`, 8000964740/00001 | 0.00 | 60156.82 | 60156.82 | 60156.82 |

Consequently, no production calculation or presence flag is changed.
For a synthetic service base of 100, before and after these regressions:
missing invoice → displayed invoice 0, accrued 100; existing zero invoice
(including debit 40 / credit 40) → displayed invoice 0, accrued 100.
Zeroing accrued solely because the invoice group is absent would break the
observed XSA behavior.

`ltc_invoice_history` exercises production `get_history` with EKBE Open SQL
doubles, then `get_row`: no history, GR only, cutoff/excluded rows, eligible
zero, net-zero debit/credit, positive/negative invoices and negative-difference
clamping. It checks service/material, Over/Under, open/closed status, USD
rounding and formatted accrued fields. Run it in SAP alongside
`ltcl_invoice_null_propagation`, `ltc_dash_pure_branches` and
`ltc_account_aggregation`; these tests have not been executed in the offline
environment. Existing snapshots are evidence, not a new SAP/HANA execution
or proof for every deployed engine revision.

Output policy is unchanged: ABAP numeric INITIAL is zero, **not SQL/OData
NULL**. The existing field-specific comparator accepts XSA `INVVALUE_CAL=null`
versus ABAP `0.00`; it still rejects that substitution for `AMOUNTACCRUED`.
No Gateway null indicators, schema changes or comparator exceptions are added.
Before any nullable-output change, verify both deployed XSA endpoints and
Gateway using matching snapshots, including raw invoice group presence,
helper, accrued, USD and character fields. Do not use a SQLScript IF test as
proof of COLUMN_ENGINE behavior.

## Objective

The objective of this repository is to support:

- analysis of the SAP DAS solution
- validation of generated ABAP artifacts
- comparison of business logic with XSA implementation
- identification of functional or technical gaps
- understanding of data replication and source-system limitations

For all validation and comparison activities, the XSA implementation remains the authoritative source of truth.
