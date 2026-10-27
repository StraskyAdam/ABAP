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

## Accrual method endpoint

The `methodParameters(...)/Results` exports extend `ZFI_DAS_SRV` without writes.
`ZCL_ZFI_DAS_DPC_EXT` maps the ten named keys and delegates once to
`zif_fi_das_dashboard~method_parameters`. The dashboard reuses
`calculate_accrual`, `calculate_straight_line`, `get_month_difference`,
`get_japan_brazil`, `get_exchrt` and `convert_to_usd`; it does not duplicate
their formulas. `IV_EDGEWTDAMT` is retained but does not select the returned WTD
amount, just as in the active XSA code. The legacy `TOTWRKCOMPAMT_COCDECURR`
name means **USD**, not company-code currency. Each response contains one row
with a new UUID string, not a business-derived or cached identifier.

### SAP deployment (manual)

1. Create/activate `zfi_das_method` from its DDIC text export, then activate the
   interface and dashboard. Its percentage is DEC(13,1) and flag is CHAR(1);
   the existing shared dashboard structure remains unchanged.
2. In SEGW, add the two entity types, sets, ten-key parameter entity and
   `Results` 1:* association from `ABAP code/Metadata for SEGW ZFI_DAS.txt`.
   Bind the result to `zfi_das_method`; retain the exact external names and
   types, including the non-addressable `methodParameters` set.
   Explicit numeric input facets follow the TF signature: PO DEC(13,3),
   percentage DEC(13,1), EDGE DEC(13,2). XSA's CV omits input scales;
   omitting them in Gateway would default to scale zero. The parameter PO
   field uses built-in DECFLOAT34 because the shared DEC(13,2) would lose
   its third decimal; no parallel packed amount type is introduced.
3. Regenerate the SEGW project/runtime artifacts **manually**. The exported
   redefinition is named `methodset_get_entityset`; use the actual method name
   produced by the generated DPC artifact (it depends on the technical entity
   name). Activate the DPC extension and refresh Gateway metadata caches.
4. Append `ABAP code/Method unit test.txt` to the dashboard's local test include
   containing `ABAP code/Unit test.txt`. Import
   `ABAP code/Gateway method unit test.txt` into the DPC extension's local test
   include. Run both ABAP Unit classes and the existing dashboard tests in SAP.
   This export repository has no ABAP compiler, test runner or lint/build setup;
   the new tests have not been executed here.
5. Replay the UI URLs against Gateway. XSA accepts quoted numeric/date values;
   Gateway may reject them **before DPC dispatch**, requiring standard numeric
   literals and `datetime'yyyy-MM-ddT00:00:00'` in the UI. Do not change the
   metadata to strings to bypass this. The mapping accepts ISO dates, ISO
   datetimes, datetime literals and internal DATS/timestamp values, checks
   calendar validity, and raises `zcx_fi_das_error` on invalid dates (wrapped
   with `previous` at the Gateway boundary). Verify the actual key-table format
   on the target Gateway release.

### Known parity differences and assumptions

These are deliberately visible rather than claiming unconditional XSA parity.
The existing Over/Under calculation and WTD branch are preserved.

- **Rates:** XSA `TF_accrualMethod` rounds `SF_getExchangeRate`'s six-decimal
  NYB2 rate into DECIMAL(13,2), using 1 April of the current calendar year
  (including January–March). ABAP uses the replicated six-decimal rate.
  The replicated `zfi_das_exchrt` data must contain that year's 1 April
  PO-currency-to-USD rate, including USD-to-USD; this adapter does not refresh
  or write rates. A missing required rate raises an error. Only the USD amount
  is affected by the precision difference. `rate_precision_delta` measures
  2,073,313.53 versus 2,081,532.60 for rates 1.09 versus 1.094321, a difference
  of 8,219.07. No explicit rounded-rate parameter was added; the owner must
  decide whether one is needed.
- **Empty/unknown method:** for service items XSA only handles SQL NULL,
  `WTD` and `STL`; empty/unknown strings leave NULL outputs. Shared ABAP treats
  an empty method as automatic WTD/STL selection and unknown methods as cleared
  outputs (zeros/blanks, not serialized NULL). Material items return STL/zeros
  regardless of method. Non-null OData keys cannot represent SQL NULL inputs.
  These behaviors are asserted in `unsupported_and_blank`.
- **Supplied WTD:** XSA passes the amount string through, while ABAP truncates
  the amount to two decimals. For example `123.4567` yields ABAP `123.45`;
  final XSA DEC(13,2) assignment may round it instead. The raw input remains
  a string, so blank triggers STL and `'0'` remains WTD, with no EKPO field
  truncation. Percentage inputs also bypass the unknown custom EKPO field
  widths. Normal dashboard loading explicitly retains the original EKPO
  conversions and initial-value test; actual custom DDIC definitions must
  still be verified in SAP.
- **JPY/VND are not equivalent:** both conversion helpers multiply by 100,
  but shared ABAP accrual first divides its amount by the currency factor,
  cancelling that multiplier. XSA passes the amount directly to
  `SF_ConvertCurrency`. With amount 100 and rate 0.01, JPY produces ABAP USD 1
  versus XSA USD 100. `currency_factor_delta` also measures VND at the same
  six-decimal helper rate (before XSA's separate TF rate rounding). ABAP's
  pre-conversion two-decimal truncation after division can lose further
  sub-unit precision. This is not changed globally, to avoid changing
  Over/Under behavior; a later endpoint-specific currency policy needs approval.
- **Months:** ordinary valid dates match `SF_getMonthDiff`: days 1–6 retain
  the previous period, day 7 advances it, work days 1–15 use the current-month
  bucket and day 16 the next. End-month overrides and nonpositive-month floors
  match. XSA's extra increment checks occur after normalization to day 1 and
  add zero. ABAP explicitly returns zero for missing work dates; XSA lacks that
  guard and SQL NULL/zero-date coercion is not assumed equivalent. Invalid
  external dates are rejected rather than silently made initial.
- **STL precision:** ABAP truncates monthly division to eight decimals;
  XSA has no explicit equivalent intermediate truncation. Extremely sensitive
  rounding cases may differ by a cent. The amount is not recomputed from the
  rounded percentage. Both supplied reference cases are covered with a fixed
  date of 27 October 2026.
- **Configuration/keys:** Japan/Brazil configuration is assumed to contain
  company codes that fit BUKRS. Metadata retains the XSA 13-character
  company/item-category limits, but the ABAP mapping uses BUKRS and the existing
  single-character category; overlong nonrepresentable keys are rejected,
  not silently truncated. Runtime UUID values differ from XSA's locally
  generated IDs, while preserving their technical-key role.

Sources: XSA `ARIBA_ACCRUALS_DB/src/Functions/{TF_accrualMethod,
SF_accrualMethod,SF_calcSTL_wtdAmountPer,SF_getMonthDiff,SF_ConvertCurrency,
SF_getExchangeRate}.hdbfunction`, `Models/CV_accrualMethod.hdbcalculationview`
and `ARIBA_ACCRUALS_JS/lib/xsodata/accrualMethod.xsodata`; UI
`Accrual_UI5/webapp/controller/{Business,TBS}.controller.js` checkbox handlers.
The UI currently forces STL/service, consumes `results[0]`, and does not use
the returned USD amount in those handlers.

### Live parity checklist

- [ ] Run existing Over/Under/Exclude ABAP Unit tests plus both new local classes.
- [ ] With date 2026-10-27 and USD rate 1, replay
  `/methodParameters(IV_POVALUE='1604136.00',IV_POCURRENCY='USD',IV_WRKSTRTDATE='2019-04-01',IV_WRKENDDATE='2026-09-01',IV_ACCRUALMETHOD='STL',IV_TOTWRKCOMPAMT='561447.6',IV_EDGEWTDAMT='1491846.48',IV_TOTWRKCOMPPER='35',IV_PSTYP='9',IV_COMPANY='8036')/Results`.
  Expect `X`, `STL`, `1604136.00`, USD `1604136.00`, `100.0`.
- [ ] With the same date and EUR rate 1.09, replay
  `/methodParameters(IV_POVALUE='1926200.00',IV_POCURRENCY='EUR',IV_WRKSTRTDATE='2020-04-01',IV_WRKENDDATE='2026-11-30',IV_ACCRUALMETHOD='STL',IV_TOTWRKCOMPAMT='963100',IV_EDGEWTDAMT='1082524.40',IV_TOTWRKCOMPPER='50.0',IV_PSTYP='9',IV_COMPANY='3317')/Results`.
  Expect `X`, `STL`, `1902122.50`, USD `2073313.53`, `98.8` (79/80).
- [ ] Verify fresh UUIDs, missing keys, invalid dates and typed Gateway literals.
- [ ] Exercise WTD filled/blank/zero, explicit zero PO, Japan/Brazil material
  overrides, material elsewhere, JPY/VND, days 6/7 and 15/16, blank/unknown
  method, missing dates/rates, and six-versus-two-decimal rates. Record the
  differences above before approving migration.
