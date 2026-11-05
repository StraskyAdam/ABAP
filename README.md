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

## User and Role Reads

`ZFI_DAS_SRV` exposes the read-only application endpoints
`roleParameters(IP_EMAIL='...')/Results`, `userRole`, and `user`.
The generated DPC methods are `ROLETYPESET_GET_ENTITYSET`,
`USERROLE_GET_ENTITYSET`, and `USERTYPESET_GET_ENTITYSET`; the technical
method names are intentionally preserved after the Entity Set renames.

Role reads use `ZFI_DAS_ROLES`. User details reuse `GET_USERS` and its
local/replicated source selection. `EMAILADDR` is normalized for lookup;
`EMAILADDR_SAP` retains the source SMTP address, including its case.
The existing deterministic user-per-email selection is retained.

`userRole` accepts a single `USER_EMAILID eq '...'` filter and `user`
accepts a single `EMAILADDR eq '...'` filter. Both also support unfiltered
reads and `$top`/`$skip`, including `$top=0`. Unsupported filters and sorting
raise message 037 rather than returning an unfiltered success response.
Email lookup normalization and deterministic ordering are intentional
differences from XSA; IDs remain 32-character UUIDs.

Add message 037 from `Table definition/Message Class ZFI_DAS` in SE91.
Activate the interface, dashboard and DPC extension together in SAP.
Run `LTC_USER_REQUEST` for request checks and `LTC_USER_ROLE` for live reads.
The latter requires a normalized role email and a valid dialog user with
an email in the selected source. No test writes business data.

## Objective

The objective of this repository is to support:

- analysis of the SAP DAS solution
- validation of generated ABAP artifacts
- comparison of business logic with XSA implementation
- identification of functional or technical gaps
- understanding of data replication and source-system limitations

For all validation and comparison activities, the XSA implementation remains the authoritative source of truth.
