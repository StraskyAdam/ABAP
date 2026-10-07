# Independent filter audit: Unit test.txt 3590–5378

## Scope and evidence

Audited **all 67 complete method bodies** in the assigned interval, including their assertions, not merely their names. Line numbers below refer to `ABAP code/Unit test.txt` at base `c2bf1b3cc171dfe043648d7294d58e9bee78cd45`. At the initial inspection checkout HEAD was `aa635edee81d22ed04109858d42cbd7bcb2d4ed4` and `git diff c2bf1b3 -- 'ABAP code'` was empty. Neither tests nor production have been edited by this auditor. Concurrent agents subsequently changed working-tree code; final method-matrix verification used `git show c2bf1b3:...` exclusively, not their changed files. Existing REPORT/audit conclusions were not used as evidence.

This is a **static audit**, not an ABAP, SHDB, HANA, or Gateway execution report. Python was used only to enumerate method boundaries and independently inspect existing JSON fixture values. Those operations do not establish deployed behavior.

### Dependencies read independently

* Test declarations: 325–356, 361–383, 388–419; local friendship 15–16; case/index/property types 43–91; helper declarations 763–779.
* `reset_fixture` 5402–5411 replaces the CUT and clears accumulated differences; it does **not** reset SAP data, clock, exchange rates, scopes, or configuration.
* `extract_range` 8282–8295 creates a **select-only internal request**, invokes production extraction and asserts zero unconsumed input options. Zero remaining options is **not zero result rows**.
* `filter_rows` 8297–8302 calls the real production generic filter, not a mock predicate interpreter.
* `run_paged_case` 5428–5573 independently indexes MIME fixtures, optionally selects expected rows with the fixture oracle, requests bounded pages, compares raw properties, checks inline count and missing/extra/duplicate keys. `compare_actual_page` 6815–6857 marks expected rows matched without deleting them, so its total-count comparison against expected-index cardinality is valid.
* Gateway helpers: `get_gateway_response` 5591–5614, `build_resource_path` 5616–5714, `append_filter` 5716–5774, `odata_quote` 5776–5785, `execute_gateway_get` 5787–5817. MIME loader 6344–6391 requires deployed `/SAP/PUBLIC/DAS/` files; local fixture presence does not prove MIME deployment.
* `assert_all_rows_match_filter` 5957–6026 currently uppercases both operands and uses case-insensitive ABAP `CS`: a confirmed oracle weakness for case-sensitive substring filters. See patch below.
* `matches_complex_fixture` 8377–8430 reads five exact named properties, returns false for JSON null, uses explicit case-sensitive `find`, parses epoch milliseconds, and compares PO operands as strings. Its missing-property and malformed-date assertion continuation needs guarding (below).
* Production `zcl_fi_das_dashboard.txt`: result fields 189–194 (`PONUMBER` EBELN, `ITEMNO` EBELP, `POCREATEDAT` DATS), string range 475–476, `convert_range_to_where` 1549–1557 delegates to `cl_shdb_seltab=>combine_seltabs`; `extract_filters` 2017–2111 clears stale optimized state, preserves a nonempty complete expression and consumes its projection, otherwise converts select-only ranges; `apply_generic_filter` 1276–1303 stamps current positional indexes and wraps `cx_amdp_error`; `filter_result` 2113–2125 uses real HANA `APPLY_FILTER`, then orders by the positional index; full-processing decision 3745–3750.
* Production key processing: PO/supplier prefilters 2803–2809; scoped totals and threshold classification 2940–2998; item filter after threshold classification 3047–3049. Status: `apply_status` 1437–1533, `calculate_visible_status` 1933–1983, `get_review_action` 3378–3453, `get_statuses` 3622–3649, `apply_closure` 1158–1174, row assembly 3548–3578. Utilities: `parse_percentage` 420–471 and `truncate_decimal` 517–528 in `zcl_fi_das_utility.txt`.
* Gateway production `ZCL_ZFI_DAS_DPC_EXT.txt` 99–140 obtains both options and `get_osql_where_clause`; it rejects a nonempty raw filter/tree when neither representation is available.

### Pinned XSA source

Consulted actual GitHub files at **e5fd6d0a36957baa795608f85abdc9d4e810e834**, not current main:

* [getOpenPOQueryWithEmail.hdbfunction](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/getOpenPOQueryWithEmail.hdbfunction#L310-L383): active function name `TF_getOpenPOQueryWithEmail`; scoped PO totals, JPY/VND scaling, converted USD threshold, **Over `>`**, **Under `<=`**.
* [TF_getOpenAllThresholdPO.hdbfunction](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenAllThresholdPO.hdbfunction#L74-L84) calls that function with `'2'` and then `TF_getPODetail`.
* [TF_getOpenAllPO.hdbfunction](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/TF_getOpenAllPO.hdbfunction#L229-L267): closure overrides status; same-month review-day branches agree with the three assigned boundary assertions. Its returned PO/item types are NVARCHAR, not numeric.
* [TF_getPODetailQuery.hdbfunction](https://github.com/StraskyAdam/XSA/blob/e5fd6d0a36957baa795608f85abdc9d4e810e834/ARIBA_ACCRUALS_DB/src/Functions/TF_getPODetailQuery.hdbfunction#L95-L131): `to_dats(ekko.aedat)` and closure precedence over null/persisted status.
* Read `TF_getOpenPO`, `TF_getOpenThresholdPO`, `TF_getOpenPOFinal`, and `TF_getPODetail` to follow the facade/detail chain. The older `TF_filterPOByThreshold` compares item values directly; it must **not** substitute for the active scoped-PO-total oracle.

## Authoritative semantics and user observation

1. A nonempty complete logical SQL expression is authoritative. Options cannot replace, truncate or conjunctively prefilter it. With no expression, representable select-options mean `(OR includes) AND NOT(each exclusion)` within a property, AND across properties; exclusion-only means universe minus excluded values. Arbitrary cross-property OR is not representable by independent property ranges.
2. The observed `(PONUMBER eq '8000401022' or ITEMNO eq '00001')` with **empty `FILTER_SELECT_OPTIONS`** is valid. Empty options do not mean an empty predicate/result. The corresponding AND can have populated projections. The assigned suite does **not** faithfully test this exact OR/AND pair through Gateway; the supplier-OR tests do not replace it.
3. `mixed_filter_keeps_predicate` deliberately supplies an expression containing only COMPANYCODE with an extra PO range. `cross_or_disables_prefilter`, `predicate_clears_stale_ranges`, and `complex_filter_hana` deliberately supply partial/mismatched projections. They are valid **internal robustness tests**, not evidence Gateway produces those projections.
4. The actual case fixtures at 4515/4538 are **`quantum corp` with lowercase q**, not `Quantum corp`. Existing expected counts are correct for those literals. A real uppercase `Quantum` must match `*Q*`; add the proposed case witnesses, never “fix” uppercase Q by lowercasing real data.
5. Do not impose ABAP `CP`'s native case behavior on HANA LIKE or use ABAP case-insensitive `CS` as a text-filter oracle. The selected SQL representation and OData expression determine behavior. SHDB conversion/escaping details still require the actual installed SAP release.
6. Preserve raw DATS `'20251014'` in direct table filtering and the Gateway `datetime'2025-10-14T00:00:00'` expression. These are separate seams; epoch `1760400000000` is 2025-10-14 UTC midnight.
7. The complex PO group is **tautological for non-null strings**: `'9000600000' < '977'`, so `PO <= '977' OR PO > '9000600000'` already covers every string. The range and EQ arms are redundant, not independent branch witnesses. In particular **`8001984177` satisfies `<= '977'`**. Retain all seven expected HANA positives. There can be no PO-group-only negative under this invariant; PO NOT LIKE `%5%` still discriminates. Do not numeric-convert, pad `'977'`, remove the arm, or drop a correctly matching fixture row.

## Per-method matrix

Verdicts describe static correctness/coverage, never a runtime pass. **R** = real SHDB converter on installed SAP; **H** = HANA AMDP/APPLY_FILTER; **G** = deployed Gateway, stable live scope/data/config/clock; **F** = matching deployed MIME fixture plus raw-property comparator and its documented normalization rules. Every synthetic row method also depends on the production field types, not invented fields. “limited coverage-runtime-dependent” includes a correct narrow assertion whose claimed broader behavior is not discriminated.

| # | Method; exact body lines | Verdict | Independent Arrange / predicate | Act / independently expected | Discrimination and limits |
|---|---|---|---|---|---|
| 1 | `po_contains_builds_like` 3590–3607 | limited coverage-runtime-dependent | PO I/CP `*40102*`; select-only | extract; PO contains `%40102%` and LIKE, generic empty | R; proves text fragments, not matching/nonmatching rows or absence of extra constraints |
| 2 | `item_contains_keeps_zeros` 3609–3622 | limited coverage-runtime-dependent | ITEM I/CP `*2*` | extract; `%2%`, not `%00002%` | R; correctly distinguishes unwanted padding of the search operand, not actual result membership |
| 3 | `mixed_eq_and_contains` 3624–3642 | limited coverage-runtime-dependent | PO I/EQ `8000055868`, I/CP `*7*` | extract; both literals and OR | R; structural union check; `po_eq_and_cp_same_property` supplies result witnesses |
| 4 | `supplier_contains_builds_like` 3644–3657 | limited coverage-runtime-dependent | Supplier I/CP `*Fuji*` | extract; `%Fuji%`, LIKE | R; SQL fragments only; case of SQL value not independently established by `CS` |
| 5 | `supplier_pattern_no_wildcards` 3659–3672 | limited coverage-runtime-dependent | Supplier I/CP `*Fuji*` | extract; `%Fuji%`, no `*` | R; correctly checks translated outer wildcard, name does not mean wildcard-free input |
| 6 | `supplier_keeps_inner_spaces` 3674–3683 | limited coverage-runtime-dependent | Supplier I/CP `*Lee Hecht*` | extract; `%Lee Hecht%` | R; internal-space text check only |
| 7 | `item_contains_digit_two` 3685–3704 | correct | Items 00002,00020,00200,12345,00001; I/CP `*2*` | extract + filter; four first items retained; 00001 absent | R,H; all four really contain 2, establishes substring rather than padded EQ |
| 8 | `amdp_filter_empty_by_default` 3706–3714 | correct | No ranges | extract; optimized structure empty | No SHDB call needed; does not seed stale state (covered separately) |
| 9 | `po_multiple_eq_same_property` 3716–3728 | limited coverage-runtime-dependent | PO I/EQ 8000401022 and 8000000001 | extract; both and OR | R; two-value text presence, not full truth table |
| 10 | `po_eq_and_cp_same_property` 3730–3756 | correct | POs 8000055868,8000000007,8000000001; EQ first OR CP `*7*` | extract + filter; first two in that order | R,H; EQ-only and CP-only witnesses plus neither |
| 11 | `supplier_multiple_cp_same_prop` 3758–3770 | limited coverage-runtime-dependent | Supplier I/CP `*Fuji*`, `*Hitachi*` | extract; both patterns and OR | R; no row assertion; not cross-property OR |
| 12 | `item_multiple_eq_same_property` 3772–3784 | limited coverage-runtime-dependent | ITEM I/EQ 00001,00010 | extract; both zero-preserving literals and OR | R; no row assertion |
| 13 | `item_cp_digit_two` 3786–3799 | limited coverage-runtime-dependent | ITEM I/CP `*2*` | extract; `%2%`, no `00002` | R; duplicates structural part of #2 |
| 14 | `empty_contains_pattern` 3801–3815 | limited coverage-runtime-dependent | Two nonempty POs; I/CP `**` | extract + filter; both retained | R,H; no-op implementation also passes; no initial PO witness or exact generated predicate check |
| 15 | `item_number_with_leading_zeros` 3817–3826 | limited coverage-runtime-dependent | ITEM I/EQ 00001 | extract; contains 00001 | R; proves literal spelling only, not numeric/pattern discrimination |
| 16 | `exclude_sign_filters` 3828–3847 | correct | POs 8000000001,8000000002; E/EQ first | extract + filter; only second | R,H; correct exclusion-only universe, no include union/multiple exclusion |
| 17 | `unsupported_option_generic` 3849–3871 | limited coverage-runtime-dependent | PO I/BT [8000000001,8000000999], plus 8000001000 | extract + filter; two endpoints | R,H; expected correct; name obsolete (BT is supported and optimized), misses below-low/interior/E-BT |
| 18 | `supplier_filter_with_case_sens` 3873–3892 | correct | FUJI Electric,Fuji Electric; I/CP `*FUJI*` | extract + filter; only FUJI Electric | R,H; distinguishes case folding directly |
| 19 | `amdp_filter_mixed_properties` 3894–3917 | limited coverage-runtime-dependent | Three complete AND terms for PO,company,supplier and matching ranges | extract; all optimized empty, generic nonempty, full processing true | Expression-authority correct; should assert exact preserved expression and cleared projection as well |
| 20 | `threshold_fixture_classes` 3919–3935 | limited coverage-runtime-dependent | Over/Under Service fixtures, Adam scope | two full paged comparisons; no differences | G,F; class parity only; **no total=threshold witness**, no prepared threshold configuration or conversion boundary |
| 21 | `review_day_boundary` 3937–3967 | limited coverage-runtime-dependent | changed/current 20260906/06,06/07,07/07; review day 7 | direct helper; K,R,K | Correct and deterministic; covers same-month action only, not visible STATUS, closure, changeddate/time, other month/year/default clock |
| 22 | `known_ranges_are_optimized` 3969–3986 | limited coverage-runtime-dependent | PO 8000000001 AND ITEM 00001, select-only EQ | extract; both optimized nonempty, generic empty | R; representable AND, not observed Gateway OR/AND pair; lacks matching rows/negative witnesses |
| 23 | `mixed_filter_keeps_predicate` 3988–4010 | correct | Expression only COMPANYCODE=1000; ranges additionally PO=8000000001 | extract; PO optimization empty, exact expression retained, full processing | Deliberately inconsistent robustness input; not a complete PO AND company Gateway predicate |
| 24 | `cross_or_disables_prefilter` 4012–4029 | correct | `(PO=8000000001 OR company=1000)` plus only PO range | extract; PO optimized empty, exact expression retained | Internal partial-projection robustness; no rows, no proof Gateway emits partial ranges |
| 25 | `missing_predicate_fails` 4031–4050 | correct | Select-only NOT_A_COLUMN and ORIGINAL_ROW_INDEX EQ 1000 | extraction must raise domain error with nonempty reason | Actual result-field whitelist excludes internal index; `fail` reached if accepted; not testing loss of a valid logical expression |
| 26 | `generic_ranges_only` 4052–4092 | correct | Mixed-case company property includes 2028/6305; currency JPY; four rows | extract generic, full processing; apply; POs 1 and 3 | R,H; property case coalescing, include OR and cross-property AND; wrong currency/company negative witnesses |
| 27 | `mixed_ranges_only` 4094–4131 | correct | PO 1/2 OR group AND company 2028 AND supplier `*Fuji*`; four rows | generic extraction/filter; only PO1/Fuji Electric | R,H; independently rejects wrong company, wrong PO and wrong supplier |
| 28 | `predicate_clears_stale_ranges` 4133–4174 | correct | All three stale prefilters; complete PO1 OR company2028; partial PO projection; three rows | extract consumes options, clears all stale, preserves expression; rows1/2 | H; PO-only, company-only, neither discriminate OR and stale cleanup; deliberately partial projection |
| 29 | `empty_ranges_clear_stale` 4176–4204 | correct | Three stale prefilters, no expression/options | extract twice; all request filters empty, full=false | Deterministic clear/consume semantics; repeat must not resurrect state |
| 30 | `key_ranges_replace_stale` 4206–4248 | correct | Three stale prefilters plus new select-only PO1 | extract; new PO, no stale/item/supplier/generic/options, full=false; second extract empties optimized state | R; destructive extraction contract explicitly tested; not idempotent preservation of old optimized output |
| 31 | `company_range_hybrid_parity` 4250–4310 | correct | Company1000 select-only vs complete company expression with matching range; rows company1000,2000,1000 | extract/apply both; rows PO1/PO3; whole tables equal | R,H; exact identities independently asserted, avoids two wrong implementations agreeing |
| 32 | `po_group_and_supplier_rows` 4312–4360 | correct | `(PO8000401022 OR PO8000266248) AND Supplier contains Fuji`; two positives and one negative per property | extract optimized PO/supplier; sequential real filtering; two exact positives | R,H; representable inter-property AND, not cross-property OR; identity and supplier checks sound |
| 33 | `generic_eq_filters_rows` 4365–4388 | correct | company2028,6305; SQL company=2028 | real generic filter; PO1/company2028 | H; explicit keep/drop plus key |
| 34 | `generic_contains_filters_rows` 4390–4408 | correct | Local Support versus Enterprise Plan; SQL LIKE `%Local Support%` | real generic filter; PO1 | H; case/space/wildcard escaping variants absent |
| 35 | `generic_two_props_are_anded` 4410–4429 | correct | 2028/JPY,2028/USD,6305/JPY; SQL AND | real generic filter; PO1 only | H; each one-sided negative discriminates AND from OR |
| 36 | `generic_same_prop_is_ored` 4431–4453 | correct | JPY,USD,EUR; SQL OR first two | real generic filter; JPY then USD | H; tests supplied expression, not Gateway projection or SHDB grouping |
| 37 | `generic_unknown_prop_no_dump` 4455–4477 | correct | Nonempty rows; NOT_A_COLUMN SQL | real filter must raise domain exception with previous cx_amdp_error | H; invalid SQL is not silently ignored; exception hierarchy is installed-AMDP dependent |
| 38 | `generic_with_sort_and_paging` 4479–4509 | correct | CharlieJPY,AlphaJPY,BravoUSD; filter JPY; supplier ASC; skip1/top1 requested | filter then production sort/page; Charlie/PO3 | H; filtering before paging and sorting independent of input order |
| 39 | `test_cp_case_sensitive_include` 4511–4532 | limited coverage-runtime-dependent | Quality Solutions,**quantum corp**,Fuji Electric; I/CP `*Q*` | extract/filter; Quality only | R,H; expected correct for lowercase q; **uppercase Quantum witness missing**; patch is enhancement, not correction of count for present data |
| 40 | `test_cp_case_sensitive_exclude` 4534–4558 | limited coverage-runtime-dependent | Same three supplier values; E/CP `*Q*` | extract/filter; lowercase quantum and Fuji only | R,H; expected correct; missing uppercase Quantum exclusion witness |
| 41 | `test_eq_case_insensitive` 4560–4592 | correct | Fuji,fuji,FUJI,Hitachi; extracted EQ FUJI vs explicit UPPER SQL | EQ keeps FUJI only; UPPER keeps three, not Hitachi | R,H; misleading name explicitly qualified by comment; not default case-insensitive EQ |
| 42 | `test_cp_and_eq_combined` 4594–4622 | correct | Q,BioClinica Inc,bioclinica small,Fuji Electric,quantum; I/EQ Q OR I/CP `*Bio*` | extract/filter; Q then BioClinica Inc | R,H; exact-only/CP-only/case-negative/neither witnesses |
| 43 | `test_multiple_cp_filters_or` 4624–4651 | correct | Quality,BioClinica,quantum,Fuji; I/CP `*Q*` OR `*Bio*` | extract/filter; first two | R,H; both include alternatives and lowercase nonmatch |
| 44 | `test_cp_empty_pattern` 4653–4667 | limited coverage-runtime-dependent | Quality and initial supplier; I/CP `**` | extract/filter; both | R,H; desired universal string matching including initial ABAP value; empty-predicate no-op also passes, no SQL NULL fixture |
| 45 | `empty_generic_filter_noop` 4669–4689 | correct | PO2 then PO1, index initially zero; empty SQL | no-op retains count/order and first index initial | Early return; does not test preserving preexisting nonzero index/whole table |
| 46 | `nested_and_or_rows` 4691–4715 | limited coverage-runtime-dependent | `(company1000 AND (currencyUSD OR PO2))`; rows PO1/1000/USD,PO2/1000/EUR,PO3/2000/USD | filter; rows PO1/PO2 | H; expected correct but flattening to `(company1000 AND currencyUSD) OR PO2` also passes; needs PO2/company2000 witness |
| 47 | `escaped_apostrophe_row` 4717–4736 | correct | O'Brien Supplies versus Other; I/EQ exact apostrophe | extract/filter; PO1 only | R,H; real SQL escaping round trip, not only text fragments; CP/literal SQL wildcards/hash escape absent |
| 48 | `date_boundary_is_exclusive` 4738–4757 | correct | DATS Oct14/15; I/GT Oct14 | generic conversion/filter; PO2 only | R,H; boundary rejected, after retained; not Gateway datetime translation |
| 49 | `no_match_returns_no_rows` 4759–4771 | correct | company1000 row; I/EQ company9999 | extract/filter; empty result | R,H; discriminates ignored filter; no live data dependency |
| 50 | `generic_preserves_row_order` 4773–4806 | correct | PO3/1000/index77,PO1/2000/index99,PO2/1000/index11; company1000 SQL | filter; PO3,PO2, new indexes1,3 | H; proves stamping current position, not reusing stale metadata or sorting by PO |
| 51 | `complex_filter_hana` 4808–4899 | limited coverage-runtime-dependent | Exact complex expression, seven positives and seven mutated negatives; deliberately partial PO projection | extract consumes projection/no prefilters/exact SQL; filter; seven positives with original positional indexes | R not invoked for authoritative SQL; H. Every positive is valid including 8001984177. PO group is tautological, EQ/BT arms not independently discriminated; PO-with-5 negative also violates NOT LIKE and cannot isolate numeric range semantics |
| 52 | `empty_result_filter_noop` 4901–4915 | correct | Empty result, invalid SQL then empty SQL | both no-op, empty result | `apply_generic_filter` returns before AMDP; no validation/rejection guarantee for invalid predicate on empty input |
| 53 | `date_cp_range_rows` 4917–4951 | correct | DATS Sep30,Oct1,Oct31,Nov1; I/CP `202510*` | generic conversion/filter; Oct1/Oct31 | R,H; real raw-DATS SQL mapping must be confirmed on target; do not substitute formatted dates |
| 54 | `date_eq_range_rows` 4953–4986 | correct | DATS Oct14/15/16; I/EQ Oct15 | generic conversion/filter; PO2/Oct15 | R,H; lower/equal/upper witnesses; not Gateway |
| 55 | `date_bt_range_rows` 4988–5023 | correct | DATS Oct13/14/15/16; I/BT [Oct14,Oct15] | generic conversion/filter; both endpoints | R,H; good inclusive boundary and both outside witnesses; interior/E-BT missing |
| 56 | `test_filter` 5028–5050 | limited coverage-runtime-dependent | Patricia scope, Over Service, xsa-filter fixture; **no filter_raw or ranges** | full paged fixture comparison | G,F; can validate scope parity, **does not exercise a filter expression despite its name** |
| 57 | `test_filter_companycode` 5052–5073 | limited coverage-runtime-dependent | Live Adam Over Service; company2028; top100/count | Gateway; positive page, count>=page, every returned company2028 | G; soundness not completeness/count exactness; helper case folding immaterial for digits |
| 58 | `test_filter_polinedesc` 5075–5098 | corrected | Live substring `Local Support`; top100/count | Gateway; positive page/count lower bound; matching predicate oracle must use case-sensitive find | G; current helper could accept local support; correction below not applied; no completeness oracle |
| 59 | `test_filter_curr_company` 5100–5124 | limited coverage-runtime-dependent | Live JPY AND company2028; top100/count | Gateway; positive page/count lower bound; both properties asserted | G; uppercase currency oracle could accept jpy; helper correction tightens it; no rejected/unreturned identities or exact count |
| 60 | `test_filter_supplierid` 5126–5147 | limited coverage-runtime-dependent | Live supplierID='426870'; top100/count | Gateway; positive page/count lower bound; all supplier IDs exact digits | G; assumes result formatting consistent with actual contract, does not infer LIFNR padding from internal type; incomplete population/count checks |
| 61 | `test_filter_po_or_supplier` 5149–5211 | corrected | `(PO8002077142 OR PO8002077289) AND substring Hitachi`; live top100/count | Gateway; positive page; every PO in pair, every supplier case-sensitive contains Hitachi after helper patch | G; actual filter is **PO union AND supplier**, not cross-property OR; current helper accepts hitachi; no guarantee each PO branch exists or full expected set |
| 62 | `test_nonexistent_supplier` 5213–5233 | limited coverage-runtime-dependent | Live contains ZZZ_NO_SUCH_SUPPLIER_20260925 | Gateway; page0/count0 | G; sound if scope has rows and literal truly absent; could pass vacuously on empty scope; pair with positive baseline |
| 63 | `test_empty_contains_po` 5235–5309 | limited coverage-runtime-dependent | Same live scope no filter vs substringof('',PO); top10/count | Gateway; equal counts/page sizes/key sets | G; good differential check, but both empty succeeds; no positive baseline, no page-order/content equality or full key population |
| 64 | `complex_filter_gateway` 5311–5329 | limited coverage-runtime-dependent | Exact OData complex expression over complete Over Service fixture | full paged comparison against independent `matches_complex_fixture`; no differences | G,F; case/date/keys/count checked; guard patch below needed for graceful grouped oracle failure. PO group remains tautological; no claim about actual projections or generated SQL |
| 65 | `gateway_cross_or_sql` 5331–5341 | limited coverage-runtime-dependent | Exact PO8000401022 OR contains Fuji expression; complete fixture | filtered fixture oracle + paged comparison; requires supplier-only positives outside PO | G,F; detects PO-only prefilter/AND mutant but **not supplier-only mutant**: all eight selected-PO rows also contain Fuji, so no PO-only witness; no actual range/SQL extraction inspection and **not ITEMNO observed example** |
| 66 | `percentage_parsing_and_error` 5346–5364 | correct | 12,5 and malformed 1,2.3 | utility returns packed percentage12.5; domain exception with reason for mixed separators | Pure utility; no bounds/sign/empty/overflow/rounding cases in this method |
| 67 | `decimal_trunc_toward_zero` 5366–5374 | correct | decfloat34 -1.239, decimals2 | utility returns -1.23 | Pure utility; distinguishes truncation from floor/round; lacks positive/zero/invalid decimal-boundary cases |

## Confirmed correction patches (documentation only; not applied)

No existing assigned synthetic-row count or identity expectation is confirmed incorrect for its **actual current literals**. In particular do not rewrite seven complex positives or the lowercase-quantum case assertions. Corrections belong to helpers; additions close coverage gaps.

### C1 — Preserve case in the live filter oracle

Exact patch against `assert_all_rows_match_filter`, original lines 5970, 5993–6009. `CS` remains case-insensitive even without UPPER, hence replace it with explicit case-sensitive `find`. The missing-property CONTINUE also prevents unassigned/stale field-symbol use when group execution chooses assertion continuation.

```diff
@@
-    lv_expected = to_upper( i_value ).
+    lv_expected = i_value.
@@
       IF sy-subrc <> 0.
         cl_abap_unit_assert=>fail(
           quit = mv_assert_quit
           msg  =
             |Response row { lv_row_index } does not contain property { i_property }| ).
+        CONTINUE.
       ENDIF.
@@
-      lv_actual =
-        to_upper(
-          unquote_json(
-            i_token = <ls_property>-token ) ).
+      lv_actual = unquote_json( i_token = <ls_property>-token ).
@@
-          act  = xsdbool( lv_actual CS lv_expected )
+          act  = xsdbool( find( val = lv_actual sub = lv_expected
+                               case = abap_true ) >= 0 )
```

This tightens #58/#61 and currency-text assertions without imposing case-insensitive semantics on real SQL. Add helper regression with synthetic JSON `POLINEDESC="local support"` versus requested `"Local Support"`; uppercase/lowercase mismatch must be a failure, exact value a success. Run it in a harness that observes assertions rather than treating an intentionally failing assertion as a successful test.

### C2 — Oracle guards must not dump on grouped continuation

`matches_complex_fixture` uses table expressions immediately after assertions (8384–8391), and converts parsed milliseconds even if the regex assertion continues (8402–8419). Keep the assertion **and** safely return false, so the original meaningful failure survives instead of an unrelated table/conversion exception.

```diff
@@
         act  = xsdbool( line_exists( it_properties[ name = lv_name ] ) ) ).
+      IF NOT line_exists( it_properties[ name = lv_name ] ).
+        RETURN.
+      ENDIF.
       IF it_properties[ name = lv_name ]-token = 'null'.
@@
     FIND REGEX '^/Date\(([0-9]+)\)/$' IN lv_date SUBMATCHES lv_milliseconds.
+    DATA(lv_date_subrc) = sy-subrc.
     cl_abap_unit_assert=>assert_equals(
       quit = mv_assert_quit
-      act  = sy-subrc
+      act  = lv_date_subrc
       exp  = 0
       msg  = 'The XSA date oracle requires an epoch-millisecond token' ).
+    IF lv_date_subrc <> 0.
+      RETURN.
+    ENDIF.
```

An oversized otherwise regex-valid integer still needs a separately specified overflow guard if malformed fixtures are in scope; the checked-in actual positive epoch tokens do not establish such malformed input is normal Gateway data. Do not weaken null/absent property distinctions or remove the original failure assertion.

### C3 — URI CP helper only promises representable substring patterns

`append_filter` 5740–5748 currently removes outer stars even for `Fuji`, `Fuji*`, or `*Fuji`, then generates **contains**, changing those patterns' semantics. None of the assigned methods passes CP options through this helper (they use direct internal extraction or explicit raw OData). Therefore this is a confirmed helper input-limit gap, **not an explanation of an observed Gateway bug**.

For a substring-only contract, reject CP unless it has both outer `*` and no embedded wildcard/escape; do not claim this helper supports arbitrary ABAP CP. Exact insertion at the start of `WHEN 'CP'`, preserving existing conversion code:

```abap
            DATA(lv_cp_length) = strlen( ls_filter-low ).
            IF lv_cp_length < 2.
              cl_abap_unit_assert=>fail(
                quit = mv_assert_quit
                msg = 'Fixture CP requires a contains pattern with two outer stars' ).
              RETURN.
            ENDIF.
            DATA(lv_cp_last) = lv_cp_length - 1.
            IF ls_filter-low+0(1) <> '*'
               OR ls_filter-low+lv_cp_last(1) <> '*'
               OR ls_filter-low CS '#'.
              cl_abap_unit_assert=>fail(
                quit = mv_assert_quit
                msg = 'Fixture CP supports only unescaped outer-star contains patterns' ).
              RETURN.
            ENDIF.
```

The existing remaining `*`/`+` assertion must also be followed by RETURN on failure if assertion-continuation is enabled. Exact after its assertion:

```abap
            IF lv_low CS '*' OR lv_low CS '+'.
              RETURN.
            ENDIF.
```

This is deliberate refusal of nonrepresentable helper input, not a conversion “fix” that rewrites escaped stars, prefixes or suffixes. `**` remains allowed. Tests for escaped/literal patterns belong at direct SHDB/SQL and explicit OData seams.

## Needed faithful regression methods

All additions require `METHODS <name> FOR TESTING RAISING cx_static_check.` in the local class and registration in the relevant group/all_tests if group execution is desired. No declaration, test, production change or execution has been made here.

### R1 — Exact observed cross-property PO/ITEM OR; empty options

Proposed direct-seam method, complete body:

```abap
  METHOD observed_po_item_or_empty_ranges.
    reset_fixture( ).
    DATA(lv_predicate) =
      `(PONUMBER = '8000401022' OR ITEMNO = '00001')`.
    DATA(ls_request) = VALUE zcl_fi_das_dashboard=>ts_internal_request(
      filter_for_amdp = VALUE #(
        ponumber = `PONUMBER = 'stale'`
        item = `ITEMNO = 'stale'`
        suppliername = `SUPPLIERNAME = 'stale'` )
      filter = VALUE #( filter_string = lv_predicate ) ).
    mo_cut->extract_filters( CHANGING cs_request = ls_request ).
    cl_abap_unit_assert=>assert_initial(
      quit = mv_assert_quit act = ls_request-filter_for_amdp ).
    cl_abap_unit_assert=>assert_initial(
      quit = mv_assert_quit act = ls_request-filter-filter_select_options ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = ls_request-filter-filter_string
      exp = lv_predicate ).
    cl_abap_unit_assert=>assert_true(
      quit = mv_assert_quit
      act = mo_cut->is_full_processing_required( ls_request ) ).
    DATA(lt_result) = VALUE zcl_fi_das_dashboard=>tt_odata_result(
      ( ponumber = '8000401022' itemno = '00002' )
      ( ponumber = '8000000002' itemno = '00001' )
      ( ponumber = '8000401022' itemno = '00001' )
      ( ponumber = '8000000002' itemno = '00002' ) ).
    mo_cut->apply_generic_filter(
      EXPORTING is_request = ls_request CHANGING ct_result = lt_result ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = lines( lt_result ) exp = 3 ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = lt_result[ 1 ]-itemno exp = '00002' ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = lt_result[ 2 ]-ponumber exp = '8000000002' ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = lt_result[ 3 ]-ponumber exp = '8000401022' ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = lt_result[ 3 ]-itemno exp = '00001' ).
  ENDMETHOD.
```

Then add **`observed_po_item_and_ranges`** over the identical four rows, with the exact AND expression and **both** PO/ITEM I/EQ options. Because the expression is authoritative, extraction must still clear optimized predicates/options, retain exact AND SQL and require full processing; only the third row remains. Add a select-only AND control using `extract_range` with the two I/EQ options, sequential PO and ITEM filters, expecting the same single key. These distinguish expression authority from representable range optimization.

### R2 — Real Gateway OR/AND pair, complete fixture oracle

Add **`gateway_po_item_or`** and **`gateway_po_item_and`**, Adam/Over/Service and `xsa-over-service.json`, raw:

```text
(PONUMBER eq '8000401022' or ITEMNO eq '00001')
(PONUMBER eq '8000401022' and ITEMNO eq '00001')
```

Derive expected-index membership from the **entire fixture**, using exact string key comparisons (OR vs AND); reuse full `run_paged_case` missing/extra/duplicate/property/count checks. Add explicit helpers/parameters for these predicates; do **not** reuse `i_cross_or_filter`, which is hardcoded to supplier Fuji. Require fixture witnesses for PO-only, ITEM-only, both and neither before fetching. The local fixture has eight PO8000401022 keys including 00001 and 00002; this makes PO-only and both witnesses available. Require ITEM-only and neither explicitly, not implicitly.

Gateway extraction assertions need a separate request-context integration harness: record raw expression/tree, actual options and `get_osql_where_clause` for each request. Assert empty OR options and populated AND options only on the deployed release where that representation was actually observed; semantic result assertions must not depend on a universal projection-shape assumption. A GET response helper alone cannot inspect those structures.

The existing supplier cross-OR regression also needs a **PO-only** witness: all eight local `8000401022` rows have supplier `Fujifilm Diosynth Biotechnologies U`, so the current fixture cannot distinguish the intended OR from supplier-only filtering. Retain its 19 supplier-only witnesses and add a prepared scoped PO-only row (or choose independently validated operands having both one-sided witnesses), plus both/neither controls; never alter actual supplier text just to make an existing live fixture appear discriminating.

### R3 — Complete / absent / partial / inconsistent projections

Add **`predicate_projection_equivalence`**: run the same exact four-row OR truth table with (a) no options, (b) partial PO option, (c) PO and ITEM options deliberately supplied despite nonrepresentable OR, (d) mismatched PO value, (e) unsupported NOT_A_COLUMN projection. Seed all stale optimized fields for each. Extraction must consume every projection, clear all optimized fields, preserve the exact expression, require full processing, and keep the same three keys. (c)–(e) are **internal robustness inputs**, never “Gateway complete ranges for OR.”

Add **`predicate_complete_and_projection`**: complete AND expression with both matching ranges; same authority/state assertions and one exact result. Add repeated authoritative-expression extraction to prove the preserved SQL continues to work; do not expect a select-only optimized extraction to survive a second destructive call (#30 documents its different contract).

### R4 — Uppercase Quantum without losing lowercase case witness

Enhance #39 by **adding** `(ponumber='8000000004' itemno='00001' suppliername='Quantum corp')`, changing count1→2, asserting exact retained names `Quality Solutions` and `Quantum corp`, and explicitly asserting lowercase `quantum corp` absent.

Enhance #40 by adding `(suppliername='Quantum corp')`, **keeping count2**, asserting uppercase Quantum and Quality absent while existing lowercase quantum and Fuji positives remain.

These exact changes preserve the user’s uppercase-Q invariant and do not silently swap fixture labels. No patch is needed to the expectations for the current lowercase data.

### R5 — Range I/E algebra, inclusive BT and exclusions

Add **`range_include_exclude_algebra`**, using real direct extraction/row filtering rather than a hand-built SQL “expected” generated by the same converter:

* Supplier I/CP `*Fuji*`, I/EQ `Hitachi`, E/EQ `Fuji Electric`, E/CP `*Lab*`.
* Rows: Fuji Electric (excluded EQ), Fuji Lab (excluded CP), Fujifilm (included CP), Hitachi (included EQ), Other (not included).
* Expected **Fujifilm, Hitachi**, in source order. This detects ORing exclusions, ignoring exclusions, ANDing includes, and taking complement of the entire property group.
* E-only EQ Fuji Electric plus E/CP `*Lab*`; include Other and Hitachi, exclude both independent negative witnesses.

Add **`po_bt_include_exclude_boundaries`** with below-low, low, interior, high, above-high; I/BT keeps low/interior/high, E/BT keeps below/above. Add I/BT plus E/EQ interior to retain endpoints only. Use real fixed-width POs; do not numeric-coerce. Add **`date_bt_exclude_rows`** with raw DATS Oct13/14/15/16, E/BT [Oct14,Oct15] expecting Oct13/16. Range-to-SQL structure and all identities must be checked.

Add explicit EQ initial supplier and CP `**` assertions for both initial and nonempty ABAP strings with a verified nonempty predicate; empty SQL no-op must not satisfy a claimed converter test. ABAP result-table initial fields are not SQL NULL; JSON null needs its own fixture oracle checks.

### R6 — Escaping and genuine nested grouping discrimination

Add **`nested_or_outer_and_rejects`** with a row `PO8000000002/company2000/EUR` to the #46 fixture; correct parentheses must reject it although flattened `(... AND ...) OR PO2` would accept it. Keep both existing positives and the currency-only negative.

Add **`cp_literal_escape_rows`**: direct ranges `*O'Brien*`, `*100%*`, `*A_B*`, and escaped ABAP-CP literals `*A#*B*`, `*A#+B*`, `*A##B*`, paired with literal-match and wildcard-lookalike negatives. Expected literal meanings are apostrophe, percent, underscore, `*`, `+`, `#`, respectively. Let installed SHDB produce the actual escape syntax; do not assert unverified exact LIKE/ESCAPE spelling. Independently exercise corresponding literal `substringof` Gateway requests; percent must be URL-encoded, not treated as SQL wildcard. URI substring-only CP helper must reject unrepresentable patterns, not approximate them.

### R7 — Raw dates vs Gateway dates

Add **`gateway_date_gt_boundary`**, **`gateway_date_eq_boundary`**, **`gateway_date_bt_boundary`**: a prepared scoped dataset has rows before/on/after 2025-10-14; use exact `datetime'2025-10-14T00:00:00'`, and for BT a conjunction GE Oct14 / LE Oct15. Compare against independent fixture epoch/date oracle and exact keys/counts. Inspect actual SQL date mapping via request-context harness if asserting extraction; direct DATS tests #48/#53–55 cannot prove that mapping.

Add **`complex_fixture_oracle_controls`** using actual JSON-property tokens, all five properties, and epoch before/equal/after; explicit uppercase A/B and lowercase a/b, initial/JSON-null/absent properties; include `PO8001984177` positive. Expected expression is the original exact string predicate, not production-converted ranges. Missing/malformed fixture tests must observe failure assertions and guarded returns, not expect successful parsing.

### R8 — Prepared threshold boundary and visible status

Add **`threshold_exact_total_boundary`** through real production keys/Gateway on a prepared scope/config/exchange dataset:

* A multi-item scoped PO has production-calculated total exactly equal to converted USD threshold; **Under includes**, **Over excludes** all its eligible items.
* Adjacent totals strictly below and above independently discriminate `<=`/`>`; include JPY/VND conversion/scaling/rounding controls and document the precise rate/threshold actually used.
* An ITEMNO filter must not lower the PO total before classification; classifying only the requested item is not a faithful oracle.
* Require actual witness existence/configuration, otherwise report a fixture precondition failure, not “boundary covered.” No arbitrary made-up PO data should be labeled a deployed equality fixture.

Add **`closed_pending_status_is_reviewed`** (see production defect below), and **`review_action_visible_status`**: action keep/reset/none plus actual STATUS/CHANGEDDATE/CHANGEDTIME, empty/pending/reviewed/unknown persisted status, closure true/false, changed date initial, future/month/year transitions, configurable review day. The assigned day6/day7 helper test remains correct; do not change its expected K/R/K.

### R9 — Utility/empty/live controls

Add **`percentage_input_boundaries`**: empty→initial, zero, signed comma/dot, surrounding whitespace, invalid repeated separators/sign-only, overflow, target packed-decimal rounding; expected values from declared `t_percentage` precision, not assumed percent bounds.

Add **`decimal_trunc_boundaries`**: positive1.239→1.23, -1.239→-1.23, zero, decimals0, already exact value, supported maximum; invalid -1 and maximum+1 must raise domain error. Read `mc_max_decimals`, not an invented limit.

Add a nonempty baseline to #62/#63 so empty scopes cannot satisfy absence/empty-substring tests vacuously. Replace broad `count >= page` with fixture-derived exact filtered counts and complete paged keys where stable fixture parity is intended. Retain live-row soundness tests as live smoke tests, not complete filter proofs.

## Confirmed production defect — retain tests; do not alter production here

**Closure precedence is lost for pending/empty persisted status.** Active pinned XSA `TF_getPODetailQuery` 128–131 and Over `TF_getOpenAllPO` 231–232 choose Reviewed immediately when `PO_CLOSURE='true'`. ABAP `get_statuses` 3626–3642 loads persisted STATUS directly; `apply_status` passes it to `calculate_visible_status`. There, 1936–1941 returns **Pending** for pending/initial status **before** inspecting closure; closure only participates in the reviewed/reset branch 1969–1977. Later `apply_closure` sets flags only and does not repair STATUS.

Static reproducer using actual declared types/helper (`calculate_visible_status` signature at base 908–915 has `CHANGING cs_result TYPE ts_result`, not `ts_odata_result`):

```abap
  METHOD closed_pending_status_is_reviewed.
    reset_fixture( ).
    DATA(ls_status) = VALUE zcl_fi_das_dashboard=>ts_status(
      ponumber = '8000401022' itemno = '00001'
      status = 'Pending' po_closure = 'true'
      changed_date = '20260906' ).
    DATA ls_result TYPE zcl_fi_das_dashboard=>ts_result.
    mo_cut->calculate_visible_status(
      EXPORTING is_status = ls_status i_review_day = 7
      CHANGING cs_result = ls_result ).
    cl_abap_unit_assert=>assert_equals(
      quit = mv_assert_quit act = ls_result-status exp = 'Reviewed' ).
  ENDMETHOD.
```

This should expose a source-confirmed production mismatch; **do not change expected Reviewed to Pending to pass current production**. Also exercise `apply_status` with a supplied persisted status row and closure flag. Distinguish date/time rules from STATUS precedence. Scope extraction constraints cannot explain this helper-level branch-order mismatch, although existence of such a row in a live system is a data precondition. No runtime failure is claimed.

The assigned `review_day_boundary` and fixture-parity methods are retained. No assigned range/predicate test establishes an additional production filter defect from source alone. In particular, empty OR options are not a production defect; translation completeness of Gateway `get_osql_where_clause` remains runtime-dependent.

## Static fixture observations and audit limits

Read local JSON with UTF-8 BOM handling:

* `xsa-over-service.json`: **20,131** rows; independently evaluating the unchanged complex oracle selects **1,674**; PO8000401022 OR supplier contains Fuji selects **27**, including **19 outside that PO**. These are local snapshot oracle cardinalities, not Gateway returned counts or passed tests.
* That cross-OR snapshot has **zero PO-only witnesses**: its eight PO8000401022 rows all contain Fuji. A supplier-only implementation selects the same expected set and would pass this fixture. This was independently checked against the unchanged fixture payload.
* `xsa-under-service.json`: **40,030** rows; `xsa-filter.json`: **8**. Both Over/Under snapshots include Pending and Reviewed, but no configured total=threshold proof is encoded by the assigned boundary method.
* No supplier containing `quantum` in any case appeared in the inspected Over Service snapshot. The uppercase-Q regression is a synthetic case witness, not an invented claim about that live fixture.
* All 67 method names/boundaries were enumerated independently; matrix contains one row for each. Lines 5376–5378 are helper-section comments, not an omitted method.

Required runtime verification is on the same pinned code after intentionally accepted patches, deployed SAP types/converter release, HANA procedure, Gateway registration and matching stable fixtures/configuration. No tests were run against another agent’s changes, and no build/test/runtime success is asserted.

The paged expected index is hashed by key: it checks membership, duplicates, raw content and counts, **not expected response order or exact page slices**. Separate sorted-order/paging oracles are needed for claims about ordering. JSON token type/decoding and missing inline-count handling are additional cross-cutting helper dependencies being audited separately; do not interpret this matrix as certifying their implementation.

The required parallel-validation tool was invoked for this documentation-only contribution: CodeQL skipped trivial documentation; actual code review was unavailable because its configured model was missing. Its displayed “Success / no comments” wrapper is not evidence that a reviewer ran successfully.
