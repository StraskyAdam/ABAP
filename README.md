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

## ABAP test suite

The maintained ABAP Unit source is `ABAP code/Unit test.txt`; manual endpoint
scenarios remain in `ABAP code/Test cases.txt`. These are SAP source artifacts,
not a locally executable test project.

| Category | Test classes / coverage |
| --- | --- |
| Arithmetic/currency | Preserved seven invoice/accrual regressions; `ltc_dash_pure_branches` calculation boundaries and seeded exchange-rate cache |
| History/mapping and assembly | `ltc_dash_pure_branches` injected context/row assembly; existing package projection/order |
| Filters | Unit tests for AMDP predicate extraction; `ltc_amdp_filters` for actual HANA EQ/LIKE, case sensitivity, generic property AND/OR |
| Sorting/paging | Stable ties, supported sort prefixes, explicit zero top, skip/window boundaries |
| Request/context/errors | Full-processing decisions and deterministic dashboard validation/helpers |
| Utilities | Email/list normalization, delimiters, dates, percentage parsing, truncation and amount formatting |
| Serialization contracts | `ltc_parity_helpers`: synthetic JSON, field-specific one-way NULL mappings, time normalization, aggregate multiplicity and parser errors |
| Integration/parity | `ltc_fi_das_gateway_parity`: live Gateway requests and MIME fixtures, including scope/filter/selection/count/page scenarios |

Pure unit classes use `DURATION SHORT` / `RISK LEVEL HARMLESS`. The live
integration/parity class uses `DURATION LONG` / `RISK LEVEL HARMLESS` and requires
the deployed service, authorized test user, representative database contents
and fixtures under `/SAP/PUBLIC/DAS/`. The pure parity-helper class creates an
in-memory helper instance only; it does not invoke Gateway or load fixtures.
Existing local-friend access is retained; no production API is exposed for tests.
The preserved generic-filter tests are separated into `ltc_amdp_filters`
(`DURATION MEDIUM` / `RISK LEVEL HARMLESS`): their inputs are synthetic, but
`apply_generic_filter` executes a HANA AMDP rather than an ABAP-only filter.

### Remaining runtime gaps

- Database loaders, history aggregation from EKBE, authorization/configuration
  lookup, and complete request execution need controlled SAP database fixtures.
- CDS/AMDP selection, SQL joins, authorization scope and database paging need
  SAP HANA execution; ABAP-only tests cannot establish their correctness.
- DPC request-context/filter-tree translation and exception wrapping need
  generated Gateway classes/interfaces and a Gateway runtime or suitable doubles.
- Exchange-rate/currency customizing and non-initial timezone conversion need
  SAP configuration; current-day notification behavior also needs clock control.
- Live parity tests depend on the deployed datasets and MIME exports. Synthetic
  JSON tests protect the comparator contract, not the XSA SQL implementation.

Static source review checks test structure, short identifiers and private-access
patterns. No SAP runtime is available in this checkout: **SAP activation and
ABAP Unit execution remain unverified**. Run the SHORT unit classes first in the
dashboard class's test include, then explicitly run the MEDIUM HANA filters and
LONG integration/parity class with their runtime prerequisites. No numerical coverage percentage
or XSA SQL parity is claimed.

### Separate audit follow-ups (production unchanged)

- `apply_currency` derives `amountaccrued_cocdecurr` from work totals minus
  invoice without the material GR base or nonnegative clamp used by
  `calculate_accrued_amount`. Check the intended company-currency contract
  against functional requirements/XSA before changing this behavior.
- `get_row` looks up users using the raw detail owner email, whereas
  `apply_detail` normalizes that email. Check whether mixed-case/space-padded
  source owners can miss normalized user-cache keys.

These are source-review candidates, not SAP-executed defects or proven XSA
parity failures; neither behavior was changed to make the new tests pass.
