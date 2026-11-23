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

## Reusable email service (ABAP 7.50 SP20)

Manual activation order: existing DDIC and `ZCX_FI_DAS_ERROR`, then
`ABAP code/ZIF_FI_DAS_EMAIL`, then `ABAP code/ZCL_FI_DAS_EMAIL`.
Paste `ABAP code/ZCL_FI_DAS_EMAIL test classes` into that class's **Test Classes**
include, not into the dashboard's existing `Unit test` include.

The service creates **one message**, with one language, body and personalization
shared by all TO/CC/BCC recipients. Jobs decide eligibility, manager/owner grouping,
50,000-row report splitting, tracking/audit and transaction boundaries. No jobs
are implemented here. The service never commits or rolls back.

```abap
DATA lo_email TYPE REF TO zif_fi_das_email.
DATA l_csv TYPE xstring.
lo_email = NEW zcl_fi_das_email( ).
DATA(l_language) = lo_email->get_language( 'manager@example.org' ).
" l_csv contains the already encoded XSTRING supplied by the caller.
lo_email->send(
  i_template = 'MANAGER_REMINDER'
  i_language = CONV string( l_language )
  it_recipients = VALUE #(
    ( email = 'manager@example.org' kind = zif_fi_das_email=>gc_to )
    ( email = 'owner1@example.org' kind = zif_fi_das_email=>gc_cc )
    ( email = 'owner2@example.org' kind = zif_fi_das_email=>gc_cc ) )
  it_params = VALUE #( ( name = 'USER' value = l_manager_name )
                      ( name = 'MONTH' value = l_month_description ) )
  it_attachments = VALUE #( ( name = 'Open POs.csv'
                             document_type = 'CSV' content = l_csv ) ) ).
" Caller handles ZCX_FI_DAS_ERROR and resolves the complete business LUW.
" Only the caller decides when a successful LUW is committed.
```

### Data and rendering contracts

- Current-client Open SQL reads `ZFI_DAS_EMAIL` by exact template/language;
  `i_require_active` defaults to `abap_true` and requires `STATUS = 'X'`.
  False deliberately permits inactive templates; there is no silent skip or
  template fallback. Template/language inputs are strings checked against the
  100/5-character DDIC limits before selection (no parameter truncation).
  Deployment must confirm a unique client/template/language key.
- Sender comes from `ZFI_DAS_CONF_VAL`, `CONFIG_NAME = 'EMAIL_FROM'`,
  field `CONFIG_VALUE`. Missing/empty/invalid configuration raises
  `ZCX_FI_DAS_ERROR`. The configuration utility exposes bulk/UI CRUD reads,
  not a lightweight checked single-value contract, so it is not a dependency.
- `get_language` returns `ZFI_DAS_EMAIL-LANGUAGE` and reads `ZFI_DAS_USR_LANG`
  by exact `EMAIL_ID`, preserving XSA's
  key matching. Only a missing record yields `EN`. An existing empty, oversized,
  whitespace/control-containing language is an error. Callers may instead pass
  their own explicit language; no locale remapping is performed. Convert the
  fixed-length return to `string` when passing it to `send`, as in the example.
- Parameter names are case-sensitive bare names (`USER`, not `&USER&`).
  Empty names, whitespace, ampersands and duplicates are errors, even when
  unused. Every matching occurrence in the **original** subject/body is replaced;
  inserted values are never scanned again. Unknown tokens (including Spanish
  names) remain unchanged. Empty values are allowed. Unicode, trailing text
  spaces and existing line breaks are not reformatted.
- Bodies are plain text, matching the XSA mail templates. Parameter replacement
  is literal; the service rejects control characters in the rendered subject
  and headers.
- Addresses must be individual bare SMTP addresses (no display names or lists),
  maximum 241 characters, with one `@` and no spaces/control characters.
  BCS still performs its own address validation; this is not a complete RFC
  mailbox validator or proof that a mailbox exists.
- Attachments contain raw XSTRING bytes, unchanged, plus an explicit three-character
  BCS/SAPoffice document type (for example `CSV` or `BIN`; not a MIME type).
  There is no CSV formatter or implicit decoding. Full names are carried in
  `&SO_FILENAME=` and the BCS attachment subject. Names exceeding the installed
  `SO_OBJ_DES` character length or the 242-character header limit are rejected,
  never silently truncated. Controls, path
  separators, quotes, semicolons and leading/trailing spaces are rejected.
  Filename and extension handling must still be verified per document type in
  the target SAPconnect environment. Empty binary attachments are allowed.
- The caller prepares the attachment bytes, including text encoding and BOM
  when applicable. A shared export utility is not implemented here. UTF-8 BOM
  matches the observed Excel CSV; an XSA declaration of UTF16BE is not evidence
  of the exported bytes.

### BCS, transactions and deployment limits

The adapter passes a plain-text `RAW` document using
`CL_BCS_CONVERT=>STRING_TO_SOLI`. Each attachment uses binary SOLIX content
and its original XSTRING byte length, independent of padding in the final
SOLIX row. No per-recipient personalization is attempted.

`SET_MESSAGE_SUBJECT( IP_SUBJECT = string )` receives the complete rendered
subject. The document's short internal title is only `DAS email`. The service
does **not** impose an invented 255-character subject limit, silently truncate
the template's CHAR1024 subject, or guarantee that downstream SAP/MIME/SMTP
preserves a long subject.

`SEND` false and `CX_BCS` are explicit errors. Even a true result only means
BCS accepted the pending request for the recipients; it is **not delivery
confirmation** or a per-recipient result. A failure may leave partial BCS work
in the caller's LUW. Do not catch the exception, mark the notification delivered
and commit anyway. The caller must choose its rollback/retry/audit strategy;
after a successful call, commit the request together with the intended business
tracking, then monitor SAPconnect/SOST separately. No interactive error screen,
COMMIT, ROLLBACK or immediate-send override is used.

Existing dashboard `user_details` calls the HANA `get_users` AMDP with all-users/
dynamic-filter processing, replication selection and user-type restrictions.
It is not a lightweight single-email lookup. Under the requested user-CDS freeze,
the email core does not duplicate that query, alter replicated user CDS, or pull dashboard dependencies
into sending. Callers supply `USER`/manager names through params; obtaining
those names efficiently remains a caller/integration dependency.

Before productive manual deployment, verify in the target SAP system:

1. Actual DDIC definitions/keys for the three configuration tables above
   (including EMAIL `SUBJECT CHAR1024`, `BODY STRING`, `STATUS CHAR10`) and
   existing exception class. This repository does not contain complete DDIC
   exports of these tables.
2. SAP 7.50 SP20 BCS signatures, especially `CREATE_DOCUMENT` with `I_HEX`/
   `I_LENGTH`, `ADD_ATTACHMENT` with `I_ATTACHMENT_HEADER`/`I_ATT_CONTENT_HEX`,
   `CL_BCS_CONVERT=>XSTRING_TO_SOLIX`, and `SET_MESSAGE_SUBJECT`.
   The latter's STRING parameter was checked in SE24; end-to-end MIME length
   remains unverified. Parser/stub checks cannot verify installed SAP APIs.
3. SAPconnect node, sender authorization/address, plain-text charset rendering,
   Unicode filenames and document-type MIME
   mappings. Inspect the received MIME, not only the SOST preview.
4. Multiple TO/CC/BCC, subject >255 characters, text >255 characters/line with
   Unicode and CRLF, and byte-for-byte attachment hashes after receipt.
   The real ~22 MB UTF-8 BOM CSV and 50,000 records have **not** been sent here;
   SAPconnect/SMTP size limits, memory and delivery remain unverified.

### Email validation

Run the dependency-free validation driver with an already installed
`@abaplint/core` module directory:

```sh
node Validation/validate-email.cjs /absolute/path/to/node_modules/@abaplint/core
```

It parses the new interface/class/test include for ABAP 7.50 and performs a
second syntax/type pass using explicitly labelled in-memory SAP/DDIC stubs.
Stubs only check internal consistency against assumed shapes, not SAP API
availability. No dependency download or SAP connection occurs.

Run ABAP Unit class `LTC_EMAIL` after activation in SAP. Its renderer tests
and subclass doubles cover language fallback, empty language,
exact-language template failure, active policy, manager TO/CC/BCC, binary
attachment forwarding, long Unicode content, invalid headers/configuration,
false BCS results and propagated errors. These tests are supplied but cannot
execute without an ABAP runtime; the doubled dispatch does not test real BCS.
Existing dashboard tests are not modified and need SAP/HANA to run.
