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

`ZCL_FI_DAS_UTILITY` contains reusable CSV helpers independent of email. `format_csv_row` quotes and escapes caller-formatted string values and supports comma, pipe or other one-character separators, configurable empty values, and an optional trailing separator. `join_csv_lines` joins already prepared lines with a configurable line ending, and `encode_utf8` converts text to bytes with an optional UTF-8 BOM. Callers prepare report-specific headers, Excel `sep=` lines, formatting, batching and destinations themselves. For other encodings, use the joined text and a suitable converter; XSA's declared attachment encoding must be verified against actual output.

For example, to prepare a pipe-delimited attachment:

```abap
DATA(lt_lines) = VALUE zcl_fi_das_utility=>tt_string(
  ( `"sep=|"` )
  ( `PO Number|Line Item|` )
  ( zcl_fi_das_utility=>format_csv_row(
      it_values = VALUE #( ( `8000001234` ) ( `00010` ) )
      i_separator = '|'
      i_trailing_separator = abap_true ) ) ).
DATA(l_csv) = zcl_fi_das_utility=>join_csv_lines(
  it_lines = lt_lines
  i_line_separator = CONV string( cl_abap_char_utilities=>newline ) ).
DATA(l_content) = zcl_fi_das_utility=>encode_utf8( i_text = l_csv i_bom = abap_true ).
```

The dashboard interface's `send_open_po_report` method owns report selection, mapping and email orchestration in `ZCL_FI_DAS_DASHBOARD`. The OData handler calls that interface; no separate CSV or email-report class is needed. The ABAP artifacts expose the `EmailExcelReport` POST function import in `ZFI_DAS_SRV`. It accepts `EMAIL` and `POOWNER`, gathers the open, below-threshold, and exclusion rows, and sends CSV attachments through the shared email framework in batches of 50,000 rows. No email is sent when the combined result is empty.

The action intentionally preserves the XSA contract and trusts the caller-supplied `EMAIL` and `POOWNER`; Gateway/service authorization must be verified before exposing it.

The metadata snapshot and DPC extension are repository artifacts; SEGW activation, service registration, and runtime validation still need to be completed in SAP before the endpoint is considered deployable.
