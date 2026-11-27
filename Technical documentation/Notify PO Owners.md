# Notify PO Owners

## Scope and authoritative behavior

Backend only. The source contract is `reviewPOLine.xsjs` and procedure
`reviewPOLine`. This is not the scheduled PO Owner or Manager reminder and does
not mark PO items reviewed, close a PO, or call Ariba.

`ZCL_FI_DAS_DASHBOARD->GET_NOTIFY_ITEMS` reuses the over-threshold key selection
with wildcard email, all item types, exclusions enabled and the existing
live/frozen source selection. A PO-only predicate is applied before threshold
aggregation; the paired PO/item predicate is applied after that aggregation.
Restricting items before calculating the PO total would change eligibility.
Only eligible selected items are used; absent/ineligible items do not
produce a new result message, matching XSA.

`ZCL_FI_DAS_NOTIFY` reads all audit flags in the inclusive UTC interval
`[now - 86400 seconds, now]`, inserts eligible audit records and commits them
before looking up languages, translations, templates or sending any email.
An email failure does not remove that audit or permit an immediate retry.
An earlier recipient's accepted BCS message is committed before attempting the
next recipient. The shared email service itself remains commit-free.

The class must run only in the dedicated RFC session, not directly in Gateway
or an unrelated application LUW. `NOTIFY_PO_OWNERS` calls the synchronous,
remote-enabled `Z_FI_DAS_NOTIFY_PO_OWNERS` with destination `NONE`, retaining
the current user and client. The endpoint rejects batch changesets before the
RFC call: RFC can itself create an implicit database commit boundary in the
caller. Use a standalone POST with no unrelated pending application work;
do not treat this operation as part of an atomic Gateway changeset.
RFC communication failure can leave an unknown outcome; do not retry blindly.

No new enqueue behavior is introduced: like XSA, two concurrent requests can
both pass the audit read before either commits. There is no exactly-once
delivery guarantee.

## Deployment

1. Create client-dependent `ZFI_DAS_TEXT_TR` using its SE11 specification in
   `Table definition`. No equivalent translation table is present in the
   repository. Migrate the three exact XSA texts for every supported language.
   If a deployed equivalent already exists, agree its mapping before activation.
2. Verify `ZFI_DAS_PO_AUDIT` against the existing table definition: key client,
   PO, item, long timestamp; email fields/notifier capacity 225 characters.
3. Activate the interface and dashboard changes, `ZCL_FI_DAS_NOTIFY` and its
   local test classes.
4. Create function group `ZFI_DAS_NOTIFY`, then create **remote-enabled**
   function module `Z_FI_DAS_NOTIFY_PO_OWNERS`. Import `I_USER`, `I_ITEMS` and
   export `E_MESSAGE`, `E_ERROR`, all passed by value with type `STRING`.
   Paste its provided implementation. `I_ITEMS` is internal ABAP identity
   transformation XML, not a public JSON input. Restrict its RFC authorization
   to the intended service identity; verify the destination-NONE call in SAP.
5. Add the metadata delta to SEGW `ZFI_DAS`: entity types `notifyRequestType`
   and `notifyItemType`, entity sets `NotifyPOOwners` and `NotifyPOOwnerItems`,
   association `notifyRequest_to_items`, navigation `Items` (1:*).
   ABAP property names are `ID`, `USER`, `MESSAGE`, `PONUMBER`, `ITEMNO`;
   deep navigation component is `ITEMS`. Generate runtime artifacts and
   activate the DPC extension. Do not overwrite the entire model from this
   repository's metadata snapshot.
6. Maintain `EMAIL_FROM`, **`ACCRUALS_EDGE_LINK`** (not the differently spelled
   manager-job key), active `REVIEW_PO` templates and user languages.
7. Clear Gateway metadata caches as required and verify the resulting
   `$metadata`, request, response and SOST with a sandbox PO.

The Gateway identity/authorization configuration must restrict this action to
the same allowed UI users. XSA accepts the notifier email from the request;
this implementation retains that contract rather than inventing a mapping
from the shared destination's technical SAP user to an end user. `USER` is
therefore supplied identity, not proof of the caller's personal identity.

## Service handoff

```http
POST /sap/opu/odata/sap/ZFI_DAS_SRV/NotifyPOOwners
Content-Type: application/json
Accept: application/json
X-CSRF-Token: <token>
```

```json
{
  "ID": "1",
  "USER": "adam.strasky@takeda.com",
  "Items": [
    { "PONUMBER": "8000130083", "ITEMNO": "00001" }
  ]
}
```

This operation must be sent outside `$batch` changesets (for example with
batching disabled for this call in the consuming client). No UI code is
provided or changed.

Successful deep create returns the header and items with a `Message` string
(normally HTTP 201). The consumer displays this string. The backend does not
change the UI or reproduce XSA's HTTP-200/invalid-JSON parsing trick.
Requests require at least one numeric, full-width PO/item pair and a notifier
email no longer than 225 characters. `ID` is a transient OData key, not stored
or used for idempotency. GET/update/delete are not implemented.

The message order is missing-email items, blocked items, then accepted-mail
lines per recipient. For the supplied example:

```text
8000130083 - 00001 - adam.strasky@takeda.com - Mail Sent
```

The words come from migrated translations, not hardcoded English.
Configuration, SQL, template, conversion or BCS failures return a Gateway error.
Earlier committed audit/messages remain. A success means BCS accepted and
committed the send request, not that SMTP delivered it; inspect SOST.

## Email and attachment

Each unique valid owner/preparer candidate receives a separate message and the
matching selected eligible PO items. The source's owner-only candidate lookup
is retained, including its cross-row ordering peculiarity. Do not replace it
with an all-recipient union without approving the behavioral change.
Regex validation matches XSA. Invalid candidates are not sent mail.

Language is per recipient, defaulting to EN only when no language row exists.
Notifier language controls result translations. Names come from the existing
user-details implementation, with email fallback when no user exists.
The current calendar month/year is used (no days-1-to-6 prior-month rule).
Month names are English, as in the supplied XSA email. Check the deployed
JavaScript runtime's locale/timezone at a month boundary before asserting
equivalence with the UTC month used here.
Notify explicitly selects first-occurrence replacement and separate subject
parameters in the shared email service, matching XSA's replacement order and
subject/body placeholder sets. Existing email callers retain their previous
all-occurrences behavior through optional parameters with unchanged defaults.
Notify also reads language preferences with fallback only for a missing row;
an existing blank language is not silently replaced with EN.

`OpenPOs.csv` contains the exact separator preamble, four column headings,
quoted fields, trailing pipes, LF and final LF. Posting date is the last day
of the current UTC month, formatted `30 Nov 2026`. The initial implementation
uses the source-declared **UTF-16LE without an added BOM** (SAP codepage 4103).
This is provisional: the uploaded CSV is 112 UTF-8 bytes but Outlook displays
426 bytes for the attachment. Validate original attachment bytes and adjust
only this notification encoder before claiming byte parity. Do not change
the already delivered dashboard export encoding.

Other explicit adaptations:

- SQL NULL/empty/space contact values are represented by ABAP initial strings
  and treated as missing. XSA's literal single-space/null distinctions are
  not reproducible from the existing typed ABAP source in every case.
- XSA can accidentally label an empty recipient bucket as "sent"; this backend
  never reports a send for that bucket.
- More than 225 characters in an audit email is rejected rather than silently
  truncating the existing DDIC fields.
- The database source has no guaranteed row order. ABAP sorts/deduplicates the
  grouped rows; email/CSV row order is not a guaranteed XSA contract.

## Verification

Install `Unit test for ZCL_FI_DAS_NOTIFY` as the notify class's local test include.
Tests replace all SQL, timestamp, commit and mail operations and must never
send email or commit the ABAP Unit caller's transaction.

Run ABAP Unit in SAP, then sandbox integration: metadata/deep create, correct
report scope (including one selected item below the threshold on a PO whose
complete eligible total exceeds it), owner/preparer split, repeat within
24 hours, missing translations,
missing template after audit commit, later-recipient BCS failure, Gateway
changeset rejection before any audit/mail effects, response text and original attachment bytes. Database
selection and RFC/BCS signatures cannot be executed or certified in this
repository-only environment.
