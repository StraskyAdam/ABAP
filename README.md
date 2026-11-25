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

## Dashboard Email Excel Report

`ZCL_FI_DAS_UTILITY` contains reusable CSV helpers independent of email. `to_csv_row` quotes and escapes caller-formatted string values and supports comma, pipe or other one-character separators, configurable empty values, and an optional trailing separator. `to_csv` joins already prepared lines with a configurable line ending, and `encode_utf8` converts text to bytes with an optional UTF-8 BOM. Callers prepare report-specific headers, Excel `sep=` lines, batching and destinations themselves. The same class provides value formatters used by the dashboard CSV: `format_amount` (RAW number without trailing decimal zeros), `format_text` (empty value becomes one space, matching XSA NULL output), `format_date` (`05 Sept 2026`), `format_timestamp` (`05 Sept 2026, 3:02:09 pm`, no time-zone conversion) and `get_month_name`/`get_short_month_name`. The dashboard keeps only the email rule that before the 7th day the previous month is reported. For other encodings, use the joined text and a suitable converter; XSA's declared attachment encoding must be verified against actual output.

For example, to prepare a pipe-delimited attachment:

```abap
DATA(lt_lines) = VALUE zcl_fi_das_utility=>tt_string(
  ( `"sep=|"` )
  ( `PO Number|Line Item|` )
  ( zcl_fi_das_utility=>to_csv_row(
      it_values = VALUE #( ( `8000001234` ) ( `00010` ) )
      i_separator = '|'
      i_trailing_separator = abap_true ) ) ).
DATA(l_csv) = zcl_fi_das_utility=>to_csv(
  it_lines = lt_lines
  i_line_separator = CONV string( cl_abap_char_utilities=>newline ) ).
DATA(l_content) = zcl_fi_das_utility=>encode_utf8( i_text = l_csv i_bom = abap_true ).
```

The dashboard interface's `send_export_via_email` method owns report selection, mapping and email orchestration in `ZCL_FI_DAS_DASHBOARD`. The OData handler calls that interface; no separate CSV or email-report class is needed. The ABAP artifacts expose the `EmailExcelReport` POST function import in `ZFI_DAS_SRV`. It accepts `EMAIL` and `POOWNER` and calls the existing `over`, `under`, and `exclude` methods sequentially with pages of 10,000 keys. Open and below-threshold rows are processed by type, followed by exclusions once for both types. Each page is converted to CSV and its result table is freed before the next page. Paging advances by the requested page size and uses the service's total count, so missing detail rows do not prematurely end the export. CSV attachments are sent through the shared email framework in batches of 50,000 rows, including across page and section boundaries. No email is sent when the combined result is empty.

`get_section` initializes per-call export state and returns the ordered sections. `export_section` owns paging, `get_page` loads one typed result page through `over`, `under` or `exclude` and returns the total count as `int8`, and `export_to_csv` appends the page's rows to the shared buffer and sends full batches. `get_report_csv_row` maps a typed section row directly to the report row and `get_dashboard_section` derives the section text from mode and type. `send_export` sends one attachment, advances its sequence number and resets the buffer only after successful submission. The interface sends any remaining rows after the section loop, without a last-section flag.

Paging reselects the ordered keys for each page, so changes to the underlying data during an export can cause rows to be missed or repeated; it is not a database snapshot. CSV text, attachment conversion and BCS requests still consume memory. The caller must commit successful requests, or roll back on failure; delivery must be checked separately in SAPconnect.

CSV values use `Service`/`Material`, six decimal places with a dot for exchange rates (independent of user settings), and unpadded fractional amounts for the two accrued-amount columns, matching the XSA samples. Other monetary columns retain two decimal places. Empty cost centers, internal orders, asset IDs and activity numbers remain empty strings; nullable display fields retain the single-space placeholder. The ABAP service types do not retain SQL NULL indicators, so exact NULL-versus-empty parity cannot be guaranteed for every text field. English dates use `Sept`, and the last-update column includes both date and time without converting the already-local dashboard timestamp a second time.

`Straight Line Method` is `true`/`false` for open and below-threshold rows, but XSA returns the original `X`/empty flag for exclusions. CSV export preserves that distinction.

The action intentionally preserves the XSA contract and trusts the caller-supplied `EMAIL` and `POOWNER`; Gateway/service authorization must be verified before exposing it.

The metadata snapshot and DPC extension are repository artifacts; SEGW activation, service registration, and runtime validation still need to be completed in SAP before the endpoint is considered deployable.

### Comparing XSA and ABAP CSV exports

Python 3 is sufficient; no extra packages are needed:

```shell
python Validation/compare_csv.py --xsa "xsa/*.csv" --abap "abap/*.csv"
```

Use the original email attachments, without opening and saving them in Excel. The script combines all selected parts on each side and compares headers and row multisets, ignoring row order but preserving duplicate counts. CSV quoting, delimiters, BOM and record line endings are parsed rather than compared as bytes. Embedded newlines inside values remain significant. UTF-8 is the default; override it explicitly with, for example, `--xsa-encoding cp1250` if needed. Delimiters are detected per file (including optional `sep=` directives), or can be specified with `--delimiter comma`.

Exit codes: `0` means matching content under the rules below, `1` means different headers or content, and `2` means an input/output error. For row differences, a new `csv_comparison` directory contains `only_xsa.csv` and `only_abap.csv` with original row values; `OCCURRENCES` records excess duplicate counts after matching equivalent content. When multiple original variants normalize to the same content, the excess variant is selected deterministically. An existing output directory is never overwritten; choose a fresh one using `--output-dir`. Export both systems with equivalent selection parameters and stable source data.

Comparison equates only empty strings with a single space, `9`/`0` with `Service`/`Material` in `PSTYPE Text`, `Sep` with `Sept` in date columns, and exact decimal values in explicitly listed numeric columns (including semicolon-separated split percentages). Only exchange rates accept a decimal comma; grouping separators are not inferred. Identifiers, nonblank text, additional whitespace, dates/times and numeric differences are not discarded or rounded. Invalid numeric values encountered during normalization are errors.

`column_differences.csv` aligns remaining rows by dashboard section, company, PO and item and reports only content differences. The console summarizes counts per column. Content matches are removed first; ambiguous duplicate keys are reported and not arbitrarily paired. Missing rows, multiplicity differences and ambiguous variants remain visible in the multiset difference files.

The source XSA procedure uses unordered `STRING_AGG` for account-assignment fields and exclusion rules, while ABAP emits account lists in `BBP_ACC_NO` order and sorts rules by code. Comparison sorts each designated semicolon-delimited list field independently, preserving duplicate values. This checks content in each field but does not prove that values across different account or rule fields remain paired.
