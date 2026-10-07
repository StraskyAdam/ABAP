#!/usr/bin/env python3
"""Structural audit of the exported ABAP suite; NOT an ABAP syntax checker.

Run: python3 Validation/audit_tests.py [--self-test] [--json]
Only the Python standard library is required. No fixtures are modified.
"""

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CATEGORIES = (
    "standard", "owner", "filter", "scope", "sort_paging", "selection", "format"
)
CATEGORIES = ("all_tests",) + REQUIRED_CATEGORIES + (
    "request_processing", "hana_filter", "utility"
)
LEGACY_RENAMES = {
    "translated_cross_or_rows": "po_group_and_supplier_rows",
    "threshold_equal_is_under": "threshold_fixture_classes",
    "default_order_has_unique_keys": "default_order_unique_keys",
    "compatible_default_prefix_is_removed": "default_prefix_removed",
    "non_default_order_is_preserved": "non_default_order_preserved",
    "requested_sort_adds_default_ties": "sort_adds_default_ties",
    "invalid_and_duplicate_sorts_are_ignored": "invalid_duplicate_sorts",
    "empty_orderby_preserves_input_order": "empty_order_preserves_input",
    "mixed_filter_keeps_generic_predicate": "mixed_filter_keeps_predicate",
    "cross_property_or_disables_prefilter": "cross_or_disables_prefilter",
    "unoptimizable_filter_without_predicate_fails": "company_range_hybrid_parity",
    "only_single_star_is_a_wildcard": "single_star_wildcard",
    "scope_normalization_is_field_specific": "scope_field_normalization",
    "empty_generic_filter_is_a_noop": "empty_generic_filter_noop",
    "nested_and_or_filters_synthetic_rows": "nested_and_or_rows",
    "escaped_apostrophe_matches_synthetic_row": "escaped_apostrophe_row",
    "amount_format_x_y_and_default": "amount_format_x_y_default",
    "decimal_truncation_is_toward_zero": "decimal_trunc_toward_zero",
}


def tokens(source, preserve_literals=False):
    """Lex comments/quoted strings before recognizing statement boundaries.

    In particular, DEFINITION DEFERRED and DEFINITION LOCAL FRIENDS are
    statements, not full class definitions. Periods inside strings, templates,
    decimal numbers and comments do not terminate ABAP statements here.
    SQLScript bodies are opaque to the declaration audit.
    """
    result = []
    i = 0
    line_start = True
    while i < len(source):
        char = source[i]
        if line_start and char == "*":
            i = source.find("\n", i)
            if i < 0:
                break
            continue
        if char == "\n":
            line_start = True
            i += 1
            continue
        if char.isspace():
            line_start = False
            i += 1
            continue
        line_start = False
        if char == '"':
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
            continue
        if char in "'`|":
            literal_start = i
            delimiter = char
            i += 1
            while i < len(source):
                if source[i] == "\\" and delimiter == "|":
                    i += 2
                elif delimiter == "|" and source[i] == "{":
                    start = i + 1
                    i += 1
                    depth = 1
                    quote = None
                    while i < len(source) and depth:
                        current = source[i]
                        if current == "\\":
                            i += 2
                            continue
                        if quote:
                            if current == quote:
                                if quote != "|" and source[i:i + 2] == quote * 2:
                                    i += 2
                                    continue
                                quote = None
                        elif current in "'`|":
                            quote = current
                        elif current == "{":
                            depth += 1
                        elif current == "}":
                            depth -= 1
                            if depth == 0:
                                result.extend(tokens(source[start:i]))
                        i += 1
                elif source[i] == delimiter:
                    if delimiter != "|" and source[i:i + 2] == delimiter * 2:
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    i += 1
            result.append(
                source[literal_start:i]
                if preserve_literals and delimiter in "'`" else "<literal>"
            )
            continue
        match = re.match(
            r"[A-Za-z_/][A-Za-z_0-9/~]*(?:-[A-Za-z_][A-Za-z_0-9]*)*"
            r"|\d+(?:\.\d+)?|->|=>", source[i:]
        )
        if match:
            result.append(match[0].lower())
            i += len(match[0])
        else:
            result.append(char)
            i += 1
    return result


def statements(source, preserve_literals=False):
    statement = []
    for token in tokens(source, preserve_literals):
        if token == ".":
            if statement:
                yield statement
            statement = []
        else:
            statement.append(token)
    if statement:
        yield statement


@dataclass
class Class:
    name: str
    testing: bool = False
    declarations: dict = field(default_factory=dict)
    implementations: dict = field(default_factory=dict)
    interfaces: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)


def parse(source, preserve_literals=False):
    classes = {}
    friends = {}
    current = None
    method = None
    section = None
    for stmt in statements(source, preserve_literals):
        if stmt[0] == "class" and len(stmt) > 2:
            name, kind = stmt[1:3]
            if kind == "definition" and "friends" in stmt:
                friends.setdefault(name, set()).update(stmt[stmt.index("friends") + 1:])
                if stmt[3:5] == ["local", "friends"]:
                    continue
            if kind == "definition" and "deferred" in stmt:
                continue
            if kind not in ("definition", "implementation"):
                continue
            current = classes.setdefault(name, Class(name))
            section = kind
            if kind == "definition":
                current.testing = "testing" in stmt
            continue
        if stmt[0] == "endclass":
            current, method, section = None, None, None
            continue
        if current is None:
            continue
        if section == "definition" and stmt[0] == "interfaces":
            current.interfaces.append(stmt[1])
        if section == "definition" and stmt[0] in ("methods", "class-methods"):
            # METHODS: a ..., b ... . (Commas delimit chained declarations.)
            groups = [[]]
            for token in stmt[1:]:
                if token == ":":
                    continue
                if token == ",":
                    groups.append([])
                else:
                    groups[-1].append(token)
            for group in groups:
                if not group:
                    continue
                name = group[0]
                if name in current.declarations:
                    current.duplicates.append(name)
                current.declarations[name] = group[1:]
        elif section == "implementation" and stmt[0] == "method":
            method = stmt[1]
            if method in current.implementations:
                current.duplicates.append(method)
            current.implementations[method] = []
        elif stmt[0] == "endmethod":
            method = None
        elif method:
            current.implementations[method].append(stmt)
    return classes, friends


def parameter_names(declaration):
    names = set()
    for index, token in enumerate(declaration):
        if token not in ("type", "like") or index == 0:
            continue
        previous = declaration[index - 1]
        if previous == ")" and index >= 3:
            previous = declaration[index - 2]
        if re.fullmatch(r"[a-z_][a-z_0-9]*", previous):
            names.add(previous)
    return names


def interface_declarations(source):
    converted = []
    for stmt in statements(source):
        if stmt[0] == "interface":
            stmt = ["class", stmt[1], "definition"]
        elif stmt[0] == "endinterface":
            stmt = ["endclass"]
        converted.append(" ".join(stmt) + ".")
    return parse("\n".join(converted))[0]


def named_arguments(body, opening):
    """Collect only top-level named arguments, not fields of nested VALUEs."""
    depth = 1
    names = set()
    index = opening + 1
    while index < len(body) and depth:
        if body[index] == "(":
            depth += 1
        elif body[index] == ")":
            depth -= 1
        elif depth == 1 and index + 1 < len(body) and body[index + 1] == "=":
            names.add(body[index])
        index += 1
    return names


def local_calls(body, declarations):
    calls = []
    for stmt in body:
        for index in range(len(stmt) - 1):
            if stmt[index] not in declarations or stmt[index + 1] != "(":
                continue
            if index and stmt[index - 1] in ("->", "=>"):
                if stmt[index - 1] != "->" or index < 2 or stmt[index - 2] != "me":
                    continue
            calls.append(stmt[index])
    return calls


def group_targets(body):
    """Read literal dynamic targets without interpreting comments or templates."""
    calls = []
    for stmt in body:
        if stmt[:2] == ["me", "->"]:
            stmt = stmt[2:]
        if stmt[:2] != ["run_group_test", "("]:
            continue
        arguments = stmt[2:-1]
        if arguments[:2] == ["i_test", "="]:
            arguments = arguments[2:]
        if len(arguments) != 1 or not re.fullmatch(
               r"['`][a-z_][a-z_0-9]*['`]", arguments[0], re.IGNORECASE):
            calls.append(None)
        else:
            calls.append(arguments[0][1:-1].lower())
    return calls


def reaches_assertion(cls, name, seen=None):
    seen = set() if seen is None else seen
    if name in seen:
        return False
    seen.add(name)
    body = cls.implementations.get(name, [])
    for stmt in body:
        for index in range(len(stmt) - 3):
            if (stmt[index] == "cl_abap_unit_assert"
                    and stmt[index + 1] == "=>"
                    and (stmt[index + 2].startswith("assert_")
                         or stmt[index + 2] == "fail")
                    and stmt[index + 3] == "("):
                return True
    return any(reaches_assertion(cls, called, seen)
               for called in local_calls(body, cls.declarations))


def archived_test_statements(source):
    pattern = re.compile(
        r"^\*\s*(?:cl_abap_unit_assert\s*=>\s*(?:assert_|fail)"
        r"|DATA\b.*(?:\bTYPE\b|=)"
        r"|METHODS?\s+[a-z_][a-z_0-9]*\s*\.)", re.IGNORECASE
    )
    return [number for number, line in enumerate(source.splitlines(), 1)
            if pattern.match(line)]


def calls_setup_directly(stmt):
    for index in range(len(stmt) - 1):
        if stmt[index:index + 2] != ["setup", "("]:
            continue
        if index == 0 or stmt[index - 1] not in ("->", "=>"):
            return True
        if index >= 2 and stmt[index - 2:index] == ["me", "->"]:
            return True
    return False


def audit(root):
    test_path = root / "ABAP code" / "Unit test.txt"
    suite, friends = parse(test_path.read_text())
    errors = []
    test_classes = [cls for cls in suite.values() if cls.testing]
    if [cls.name for cls in test_classes] != ["ltc_parity"]:
        errors.append("Expected exactly one testing class: ltc_parity")
    all_classes = {}
    source = test_path.read_text()
    literal_suite, _ = parse(source, preserve_literals=True)
    archived = archived_test_statements(source)
    if archived:
        errors.append(f"Archived executable test statements remain at lines: {archived}")
    normalized = " ".join(tokens(source))
    receivers = dict(re.findall(
        r"\b([a-z_][a-z_0-9]*) type ref to ([a-z_][a-z_0-9]*)", normalized
    ))
    receivers.update(dict(re.findall(
        r"\bdata \( ([a-z_][a-z_0-9]*) \) = new ([a-z_][a-z_0-9]*)", normalized
    )))
    for path in sorted((root / "ABAP code").glob("*.txt")):
        if path.name in ("Metadata for SEGW.txt", "Test cases.txt"):
            continue
        classes, _ = parse(path.read_text())
        if path.name.startswith("zif_"):
            classes.update(interface_declarations(path.read_text()))
        for cls in classes.values():
            if len(cls.name) > 30:
                errors.append(f"{path.name}: class identifier exceeds 30: {cls.name}")
            for name in set(cls.declarations) | set(cls.implementations):
                # Interface-qualified implementations have two ABAP identifiers.
                if any(len(part) > 30 for part in name.split("~")):
                    errors.append(f"{path.name}: method identifier exceeds 30: {name}")
            if path.name in (
                "zcl_fi_das_dashboard.txt", "ZCL_ZFI_DAS_DPC_EXT.txt",
                "zcl_fi_das_utility.txt", "zcx_fi_das_error.txt"
            ):
                for name in cls.duplicates:
                    errors.append(f"{path.name}: duplicate method {name}")
                for name in set(cls.declarations) - set(cls.implementations):
                    if "abstract" not in cls.declarations[name]:
                        errors.append(f"{path.name}: declaration without implementation: {name}")
                for name in set(cls.implementations) - set(cls.declarations):
                    if "~" not in name or name.split("~")[0] not in cls.interfaces:
                        errors.append(f"{path.name}: implementation without declaration: {name}")
            all_classes.update(classes)
    declared_interface_types = set(re.findall(
        r"\b(?:t_|ts_|tt_|tr_)[a-z0-9_]+\b",
        (root / "ABAP code" / "zif_fi_das_dashboard.txt").read_text().lower()
    ))
    for name in re.findall(
        r"zif_fi_das_dashboard\s*=>\s*((?:t_|ts_|tt_|tr_)[a-z0-9_]+)",
        " ".join(tokens(test_path.read_text()))
    ):
        if name not in declared_interface_types:
            errors.append(f"Stale interface type: {name}")
    matrix = {}
    leaf_counts = Counter()
    for cls in suite.values():
        for name in cls.duplicates:
            errors.append(f"{cls.name}: duplicate method {name}")
        declared = set(cls.declarations)
        implemented = set(cls.implementations)
        # A helper implementing an external interface need not redeclare it.
        for name in implemented - declared:
            if "~" not in name:
                errors.append(f"{cls.name}: implementation without declaration: {name}")
        for name in declared - implemented:
            if "abstract" not in cls.declarations[name]:
                errors.append(f"{cls.name}: declaration without implementation: {name}")
        tests = {name for name, declaration in cls.declarations.items()
                 if "testing" in declaration}
        for name in sorted(tests):
            body = cls.implementations.get(name, [])
            if not body:
                errors.append(f"{cls.name}: empty/comment-only test: {name}")
            if name in CATEGORIES:
                calls = group_targets(
                    literal_suite[cls.name].implementations.get(name, [])
                )
                matrix[name] = calls
                if name != "all_tests":
                    leaf_counts.update(call for call in calls if call is not None)
                if not calls:
                    errors.append(f"Category has no testing leaves: {name}")
                if None in calls:
                    errors.append(f"Category has a nonliteral group target: {name}")
                for call in calls:
                    if call is not None and call not in tests - set(CATEGORIES):
                        errors.append(f"Category {name} has unknown/non-leaf target: {call}")
                if len(calls) != len(set(calls)):
                    errors.append(f"Category repeats a leaf internally: {name}")
                if any(call in CATEGORIES for call in calls):
                    errors.append(f"Category calls another category: {name}")
                if local_calls(body, tests):
                    errors.append(f"Category bypasses run_group_test: {name}")
            else:
                if not reaches_assertion(cls, name):
                    errors.append(f"Test has no reachable ABAP Unit assertion: {name}")
                if body and body[0] not in (
                        ["reset_fixture", "(", ")"],
                        ["me", "->", "reset_fixture", "(", ")"]):
                    errors.append(f"Leaf does not reset fixture state first: {name}")
        for name in cls.implementations:
            for stmt in cls.implementations[name]:
                if cls.testing and calls_setup_directly(stmt):
                    errors.append(f"{cls.name}.{name}: special method setup cannot be called directly")
                for index in range(len(stmt) - 1):
                    called = stmt[index]
                    if (called in declared and stmt[index + 1] == "("
                            and (index == 0 or stmt[index - 1] not in ("->", "=>"))):
                        unknown_args = (named_arguments(stmt, index + 1)
                                        - parameter_names(cls.declarations[called]))
                        if unknown_args:
                            errors.append(
                                f"{cls.name}.{name}: local {called} "
                                f"unknown arguments {sorted(unknown_args)}"
                            )
                for index in range(len(stmt) - 3):
                    if (stmt[index:index + 2] == ["cl_abap_unit_assert", "=>"]
                            and (stmt[index + 2].startswith("assert_")
                                 or stmt[index + 2] == "fail")):
                        expected_quit = (
                            tokens("quit = if_aunit_constants=>no")
                            if name == "run_group_test"
                            else tokens("quit = mv_assert_quit")
                        )
                        if ("quit" not in named_arguments(stmt, index + 3)
                                or not any(
                                    stmt[position:position + len(expected_quit)]
                                    == expected_quit
                                    for position in range(index + 4, len(stmt))
                                )):
                            errors.append(f"{cls.name}.{name}: assertion lacks correct quit control")
                    if stmt[index:index + 2] == ["me", "->"]:
                        called = stmt[index + 2]
                        if stmt[index + 3] == "(" and called not in declared:
                            errors.append(f"{cls.name}.{name}: unknown me method {called}")
                    if stmt[index + 1] not in ("->", "=>") or stmt[index + 3] != "(":
                        continue
                    receiver, _, called = stmt[index:index + 3]
                    target_name = cls.name if receiver == "me" else receivers.get(receiver, receiver)
                    target = all_classes.get(target_name)
                    if "~" in called:
                        interface, called = called.split("~", 1)
                        target = all_classes.get(interface)
                    if not target:
                        continue  # SAP/external receiver: runtime review required.
                    signature = target.declarations.get(called)
                    if (signature is None and stmt[index + 1] == "=>"
                            and called.startswith(("t_", "ts_", "tt_", "tr_"))):
                        continue  # Qualified VALUE/CONV/CAST type, not a method.
                    if signature is None and "~" not in called:
                        errors.append(f"{cls.name}.{name}: unknown {target_name} method {called}")
                    elif signature is not None:
                        unknown_args = named_arguments(stmt, index + 3) - parameter_names(signature)
                        if unknown_args:
                            errors.append(
                                f"{cls.name}.{name}: {target_name}.{called} "
                                f"unknown arguments {sorted(unknown_args)}"
                            )
                    if target_name == "zcl_fi_das_dashboard" and cls.testing:
                        if cls.name not in friends.get(target_name, set()):
                            errors.append(f"{cls.name}: missing dashboard friend access")
    parity = suite.get("ltc_parity")
    if parity:
        for category in CATEGORIES:
            if category not in matrix:
                errors.append(f"Missing testing category: {category}")
        tests = {name for name, decl in parity.declarations.items() if "testing" in decl}
        leaves = tests - set(CATEGORIES)
        if Counter(matrix.get("all_tests", [])) != Counter(leaves):
            errors.append("all_tests must invoke every testing leaf exactly once")
        declared_tests = [name for name in parity.declarations if name in tests]
        implemented_tests = [name for name in parity.implementations if name in tests]
        if declared_tests[:len(CATEGORIES)] != list(CATEGORIES):
            errors.append("Group testing declarations must come first, starting with all_tests")
        if implemented_tests[:len(CATEGORIES)] != list(CATEGORIES):
            errors.append("Group testing implementations must come first, starting with all_tests")
        for name in tests - set(matrix):
            if leaf_counts[name] < 1:
                errors.append(f"Leaf does not appear in any category: {name}")
        if "ltc_parity" not in friends.get("zcl_fi_das_dashboard", set()):
            errors.append("Dashboard LOCAL FRIENDS does not include ltc_parity")
    fixture_pointers = []
    for path in sorted((root / "Validation").glob("*.json")):
        with path.open("rb") as stream:
            if stream.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
                fixture_pointers.append(path.name)
    if fixture_pointers:
        errors.append(f"Unresolved LFS payloads: {fixture_pointers}")
    metadata = (root / "ABAP code" / "Metadata for SEGW.txt").read_text()
    if re.search(r'<Property\b[^>]*\bName="(?:original_row_index|filter_row_index)"',
                 metadata, re.IGNORECASE):
        errors.append("Internal filter index is exposed in OData metadata")
    return {
        "full_test_classes": [cls.name for cls in test_classes],
        "declared_methods": sum(len(cls.declarations) for cls in suite.values()),
        "implemented_methods": sum(len(cls.implementations) for cls in suite.values()),
        "testing_methods": sum("testing" in decl for cls in suite.values()
                               for decl in cls.declarations.values()),
        "archived_test_statement_lines": archived,
        "category_leaf_matrix": matrix,
        "shared_category_leaves": {
            name: count for name, count in sorted(leaf_counts.items()) if count > 1
        },
        "fixture_files": len(list((root / "Validation").glob("*.json"))),
        "unresolved_lfs": fixture_pointers,
        "errors": sorted(set(errors)),
        "limitations": (
            "Structural checks only. Literal group targets are checked, but dynamic "
            "dispatch and external SAP signatures, "
            "ABAP syntax/type checking, assertion semantics, ATC, ABAP Unit, "
            "HANA APPLY_FILTER and OData parity require SAP runtime review."
        ),
    }


class ParserTests(unittest.TestCase):
    def test_column_one_comments_do_not_hide_multiplication(self):
        self.assertEqual(list(statements(
            "* real comment\nx = 2\n  * 3.\n  \" quote comment\n y = 4."
        )), [["x", "=", "2", "*", "3"], ["y", "=", "4"]])

    def test_foreign_calls_do_not_reach_local_assertions(self):
        classes, _ = parse("""
CLASS ltc DEFINITION FOR TESTING.
METHODS leaf FOR TESTING.
METHODS helper.
ENDCLASS.
CLASS ltc IMPLEMENTATION.
METHOD leaf.
other->helper( ).
foreign_class=>helper( ).
ENDMETHOD.
METHOD helper.
cl_abap_unit_assert=>assert_true( act = abap_true ).
ENDMETHOD.
ENDCLASS.
""")
        cls = classes["ltc"]
        self.assertFalse(reaches_assertion(cls, "leaf"))
        for call in ("helper( )", "me->helper( )"):
            cls.implementations["leaf"] = [tokens(call)]
            self.assertTrue(reaches_assertion(cls, "leaf"))

    def test_commented_legacy_method_chains_are_individual(self):
        source = """
CLASS ltc_old DEFINITION FOR TESTING.
* METHODS: one FOR TESTING,
*          helper,
*          two FOR TESTING.
ENDCLASS.
"""
        with patch("subprocess.check_output", return_value=source):
            mapping = legacy_mapping(ROOT, "unused", {
                "one": "observed_po_item_or", "two": "observed_po_item_and"
            })
        self.assertEqual(set(mapping), {"ltc_old.one", "ltc_old.two"})
        self.assertTrue(all(row["declared_for_testing"] for row in mapping.values()))

    def test_json_oracles_keep_types_and_decode_once(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        parity = classes["ltc_parity"]
        aggregate_guard = next(
            stmt for stmt in parity.implementations["compare_raw_property"]
            if stmt[:2] == ["if", "is_unordered_aggregate_field"]
        )
        self.assertIn("lv_expected_token", aggregate_guard)
        self.assertIn("lv_actual_token", aggregate_guard)
        self.assertEqual(aggregate_guard.count("strlen"), 2)
        decoder = parity.implementations["unquote_json"]
        self.assertFalse(any(stmt[0] == "replace" for stmt in decoder))
        self.assertIn(tokens("WHILE lv_position < lv_inner_length"), decoder)
        sort = parity.implementations["assert_rows_sorted"]
        self.assertTrue(any("read_object_properties" in stmt for stmt in sort))
        self.assertFalse(any("read_result_property" in stmt for stmt in sort))
        self.assertFalse(any("to_upper" in stmt or "trim_text" in stmt for stmt in sort))
        filter_assert = parity.implementations["assert_all_rows_match_filter"]
        self.assertFalse(any("to_upper" in stmt for stmt in filter_assert))
        self.assertTrue(any("find" in stmt and "abap_true" in stmt
                            for stmt in filter_assert))

    def test_response_oracles_reject_missing_counts_and_duplicate_keys(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text(), True)
        parity = classes["ltc_parity"]
        count = parity.implementations["read_inline_count"]
        self.assertIn(tokens(
            "lv_start = find_odata_property("
            " i_json = i_json i_property = '__count' )", True
        ), count)
        self.assertTrue(any(
            "find_odata_property" in stmt and "'results'" in stmt
            for stmt in parity.implementations["find_results_array_bounds"]
        ))
        envelope = parity.implementations["find_odata_property"]
        self.assertIn(tokens("IF lv_depth = 1 AND lv_name = i_property"), envelope)
        self.assertIn(tokens("IF lv_depth = 0 AND lv_name = 'error'", True), envelope)
        self.assertIn(tokens(
            "DATA(lv_key_end) = read_json_string_end("
            " i_text = i_json i_start = lv_position ) + 1"
        ), envelope)
        index = parity.implementations["build_expected_index"]
        duplicate = index.index(tokens("IF sy-subrc <> 0"))
        self.assertEqual(index[duplicate + 1][:4],
                         ["raise", "exception", "type", "zcx_fi_das_error"])
        self.assertIn(tokens(
            "e_array_to = read_json_value_end("
            " i_text = i_json i_start = e_array_from ) - 1"
        ), parity.implementations["find_results_array_bounds"])

    def test_group_targets_preserve_literals_but_ignore_comments_and_strings(self):
        body = list(statements("""
run_group_test( 'one' ).
me->run_group_test( i_test = `two` ).
" run_group_test( 'fake_comment' ).
* run_group_test( 'fake_star_comment' ).
message = `run_group_test( 'fake_string' ).`.
run_group_test( dynamic_name ).
""", preserve_literals=True))
        self.assertEqual(group_targets(body), ["one", "two", None])
        self.assertEqual(group_targets(list(statements(
            "run_group_test( 'one' )."
        ))), [None])

    def test_all_tests_covers_every_leaf_once_and_groups_are_first(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "Unit test.txt").read_text(),
            preserve_literals=True
        )
        parity = classes["ltc_parity"]
        tests = {name for name, decl in parity.declarations.items() if "testing" in decl}
        leaves = tests - set(CATEGORIES)
        self.assertTrue(leaves)
        self.assertEqual(
            Counter(group_targets(parity.implementations["all_tests"])),
            Counter(leaves)
        )
        for methods in (parity.declarations, parity.implementations):
            self.assertEqual(list(methods)[:len(CATEGORIES)], list(CATEGORIES))
            helpers = set(methods) - tests
            positions = {name: index for index, name in enumerate(methods)}
            self.assertGreater(min(positions[name] for name in helpers),
                               max(positions[name] for name in tests))
        for category in CATEGORIES:
            calls = group_targets(parity.implementations[category])
            self.assertTrue(calls)
            self.assertEqual(len(calls), len(set(calls)))
            self.assertLessEqual(set(calls), leaves)

    def test_group_runner_reports_exceptions_and_restores_quit_control(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        parity = classes["ltc_parity"]
        body = parity.implementations["run_group_test"]
        self.assertEqual(body, [
            tokens("DATA(lv_previous_quit) = mv_assert_quit"),
            tokens("DATA(lv_previous_test) = mv_group_test"),
            tokens("mv_assert_quit = if_aunit_constants=>no"),
            tokens("mv_group_test = i_test"),
            tokens("DATA(lv_method) = to_upper( i_test )"),
            tokens("TRY"),
            tokens("CALL METHOD me->(lv_method)"),
            tokens("CATCH cx_root INTO DATA(lx_error)"),
            tokens("cl_abap_unit_assert=>fail("
                   " msg = |{ i_test }: { lx_error->get_text( ) }|"
                   " quit = if_aunit_constants=>no )"),
            tokens("ENDTRY"),
            tokens("mv_assert_quit = lv_previous_quit"),
            tokens("mv_group_test = lv_previous_test"),
        ])
        for name, statements_ in parity.implementations.items():
            if name == "run_group_test":
                continue
            for stmt in statements_:
                if stmt[:2] == ["cl_abap_unit_assert", "=>"]:
                    with self.subTest(method=name, assertion=stmt[2]):
                        self.assertTrue(any(
                            stmt[index:index + 3] == ["quit", "=", "mv_assert_quit"]
                            for index in range(len(stmt) - 2)
                        ))

    def test_observed_po_item_inputs_and_exact_oracles(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        parity = classes["ltc_parity"]
        for name, operator, expected_rows in (
            ("observed_po_item_or", "OR", 3),
            ("observed_po_item_and", "AND", 1),
        ):
            body = parity.implementations[name]
            predicate = next(stmt for stmt in body if "filter_string" in stmt)
            if operator == "AND":
                self.assertIn("filter_select_options", predicate)
            else:
                self.assertNotIn("filter_select_options", predicate)
            source = (ROOT / "ABAP code" / "Unit test.txt").read_text()
            method = re.search(
                rf"  METHOD {name}\.\n(.*?)  ENDMETHOD\.", source, re.S
            ).group(1)
            self.assertIn(
                f"`(PONUMBER = '8000401022') {operator} (ITEMNO = '00001')`",
                method,
            )
            expected = re.search(
                r"DATA\(lt_expected\).*?VALUE.*?\((.*?)\)\.", method, re.S
            ).group(1)
            self.assertEqual(expected.count("ponumber ="), expected_rows)
            self.assertIn(tokens(
                "cl_abap_unit_assert=>assert_equals("
                " quit = mv_assert_quit act = lt_result exp = lt_expected"
                " msg = 'oracle' )"
            ), body)

    def test_extraction_copies_and_consumes_ranges_before_conversion(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "zcl_fi_das_dashboard.txt").read_text()
        )
        body = classes["zcl_fi_das_dashboard"].implementations["extract_filters"]
        copy = tokens("DATA(lt_filter_options) = cs_request-filter-filter_select_options")
        index = body.index(copy)
        self.assertEqual(body[index + 1],
                         tokens("CLEAR cs_request-filter-filter_select_options"))
        self.assertEqual(body[index + 2], tokens("IF lt_filter_options IS INITIAL"))
        loop = tokens(
            "LOOP AT lt_filter_options ASSIGNING FIELD-SYMBOL(<fs_filter_select_options>)"
        )
        self.assertGreater(body.index(loop), index + 2)
        self.assertNotIn("cs_request-filter-filter_select_options", [
            stmt[2] for stmt in body if stmt[:2] == ["loop", "at"]
        ])
        conversions = [index for index, stmt in enumerate(body)
                       if "convert_range_to_where" in stmt]
        self.assertTrue(conversions)
        self.assertTrue(all(position > index + 2 for position in conversions))

    def test_grouping_preserves_blank_separator(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "zcl_fi_das_utility.txt").read_text()
        )
        body = classes["zcl_fi_das_utility"].implementations["group_integer"]
        self.assertIn(tokens(
            "CONCATENATE lv_grouped i_grouping_separator lv_group"
            " INTO lv_grouped RESPECTING BLANKS"
        ), body)
        self.assertEqual(body[-1], tokens("rv_integer = lv_grouped"))

    def test_amount_assembly_preserves_blanks_and_numeric_sign_before_return(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "zcl_fi_das_utility.txt").read_text(),
            preserve_literals=True
        )
        body = classes["zcl_fi_das_utility"].implementations["format_odata_amount"]
        self.assertEqual(body[-8:], [
            tokens("DATA(lv_result) = ls_parts-integer", preserve_literals=True),
            tokens("IF i_decimals > 0"),
            tokens("CONCATENATE lv_result lv_decimal_sep ls_parts-fraction"
                   " INTO lv_result RESPECTING BLANKS"),
            tokens("ENDIF"),
            tokens("IF i_amount < 0"),
            tokens("lv_result = '-' && lv_result", preserve_literals=True),
            tokens("ENDIF"),
            tokens("r_value = lv_result"),
        ])

    def test_number_sign_is_independent_of_write_sign_placement(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "zcl_fi_das_utility.txt").read_text()
        )
        body = classes["zcl_fi_das_utility"].implementations["get_number_parts"]
        self.assertIn(tokens("DATA(lv_magnitude) = abs( i_amount )"), body)
        self.assertIn(tokens("IF i_amount < 0"), body)
        self.assertIn(tokens("rs_parts-sign = '-'"), body)
        self.assertIn(tokens(
            "WRITE lv_magnitude TO lv_write_text DECIMALS i_decimals NO-GROUPING"
        ), body)

    def test_format_cases_snapshot_actual_and_preserve_expectations(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "Unit test.txt").read_text(),
            preserve_literals=True
        )
        body = classes["ltc_parity"].implementations["amount_format_x_y_default"]
        flattened = [token for stmt in body for token in stmt]
        for expected in ("`12,345.67`", "`12 345,67`", "`12.345,67`",
                         "`123 456 789,67`", "`123456789,67`",
                         "`-12 345,67`", "`-12,345.67`", "`-12.345,67`",
                         "`-12345,67`", "`0,00`"):
            self.assertIn(expected, flattened)
        self.assertTrue(any(stmt[:6] == ["data", "(", "lv_actual", ")", "=",
                                       "zcl_fi_das_utility"] for stmt in body))
        self.assertIn("lv_actual", flattened)

    def test_range_consumption_postcondition_is_not_weakened(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        body = classes["ltc_parity"].implementations["extract_range"]
        self.assertEqual(body, [
            tokens("DATA(ls_request) = VALUE zcl_fi_das_dashboard=>ts_internal_request("
                   " filter = VALUE #( filter_select_options = it_filters ) )"),
            tokens("mo_cut->extract_filters( CHANGING cs_request = ls_request )"),
            tokens("DATA(lv_remaining_ranges) = lines( ls_request-filter-filter_select_options )"),
            tokens("cl_abap_unit_assert=>assert_equals("
            " quit = mv_assert_quit"
            " act = lv_remaining_ranges exp = 0"
            " msg = |{ mv_group_test } (extract_range): "
            "Unconsumed input filter ranges, not result rows; |"
            " && |input={ lines( it_filters ) }, remaining={ lv_remaining_ranges }, |"
            " && |SQL={ ls_request-filter-filter_string }| )"),
            tokens("rs_request = ls_request"),
        ])

    def test_basic_hana_leaves_use_sql_and_literal_result_expectations(self):
        classes, _ = parse(
            (ROOT / "ABAP code" / "Unit test.txt").read_text(),
            preserve_literals=True
        )
        parity = classes["ltc_parity"]
        cases = {
            "generic_eq_filters_rows": (
                "COMPANYCODE = '2028'", 1,
                [("lt_result[ 1 ]-companycode", "'2028'"),
                 ("lt_result[ 1 ]-ponumber", "'8000000001'")]),
            "generic_contains_filters_rows": (
                "POLINEDESC LIKE '%Local Support%'", 1,
                [("lt_result[ 1 ]-ponumber", "'8000000001'")]),
            "generic_two_props_are_anded": (
                "COMPANYCODE = '2028' AND POCURRENCY = 'JPY'", 1,
                [("lt_result[ 1 ]-ponumber", "'8000000001'")]),
            "generic_same_prop_is_ored": (
                "POCURRENCY = 'JPY' OR POCURRENCY = 'USD'", 2,
                [("lt_result[ 1 ]-pocurrency", "'JPY'"),
                 ("lt_result[ 2 ]-pocurrency", "'USD'")]),
            "generic_with_sort_and_paging": (
                "POCURRENCY = 'JPY'", 1,
                [("lt_result[ 1 ]-suppliername", "'Charlie'"),
                 ("lt_result[ 1 ]-ponumber", "'8000000003'")]),
        }
        for name, (predicate, count, rows) in cases.items():
            with self.subTest(method=name):
                body = parity.implementations[name]
                flattened = [token for stmt in body for token in stmt]
                self.assertNotIn("extract_range", flattened)
                self.assertNotIn("extract_filters", flattened)
                self.assertNotIn("apply_generic_filter", flattened)
                self.assertIn(tokens(
                    f"filter_rows( EXPORTING i_predicate = `{predicate}`"
                    " CHANGING ct_result = lt_result )",
                    preserve_literals=True
                ), body)
                for actual, expected in [("lines( lt_result )", str(count))] + rows:
                    self.assertIn(tokens(
                        "cl_abap_unit_assert=>assert_equals( quit = mv_assert_quit"
                        f" msg = |{{ mv_group_test }} ({name})|"
                        f" act = {actual} exp = {expected} )",
                        preserve_literals=True
                    ), body)
        paging = parity.implementations["generic_with_sort_and_paging"]
        self.assertIn(tokens(
            "ls_request-orderby = VALUE #( ( property = 'SUPPLIERNAME' ) )",
            preserve_literals=True
        ), paging)
        self.assertIn(tokens(
            "ls_request-paging = VALUE #( skip = 1 top = 1 top_requested = abap_true )"
        ), paging)
        filter_index = next(i for i, stmt in enumerate(paging) if "filter_rows" in stmt)
        sort_index = next(i for i, stmt in enumerate(paging)
                          if "apply_sort_and_paging" in stmt)
        self.assertLess(filter_index, sort_index)

    def test_sql_filter_helper_does_not_extract_or_assert_ranges(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        self.assertEqual(classes["ltc_parity"].implementations["filter_rows"], [
            tokens("DATA(ls_request) = VALUE zcl_fi_das_dashboard=>ts_internal_request("
                   " filter = VALUE #( filter_string = i_predicate ) )"),
            tokens("mo_cut->apply_generic_filter("
                   " EXPORTING is_request = ls_request CHANGING ct_result = ct_result )"),
        ])

    def test_grouped_po_supplier_test_uses_generated_range_predicates(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        parity = classes["ltc_parity"]
        self.assertNotIn("translated_cross_or_rows", parity.declarations)
        body = parity.implementations["po_group_and_supplier_rows"]
        self.assertTrue(any("extract_range" in stmt for stmt in body))
        self.assertNotIn("lv_sql", [token for stmt in body for token in stmt])
        self.assertIn(tokens(
            "filter_rows( EXPORTING i_predicate = ls_request-filter_for_amdp-ponumber"
            " CHANGING ct_result = lt_result )"
        ), body)
        self.assertIn(tokens(
            "filter_rows( EXPORTING i_predicate = ls_request-filter_for_amdp-suppliername"
            " CHANGING ct_result = lt_result )"
        ), body)

    def test_gateway_internal_index_assertion_captures_find_result(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        body = classes["ltc_parity"].implementations["execute_gateway_get"]
        find = tokens(
            """FIND REGEX '"original_row_index"[[:space:]]*:' """
            "IN rv_json IGNORING CASE"
        )
        index = body.index(find)
        self.assertEqual(body[index + 1], tokens("DATA(lv_find_subrc) = sy-subrc"))
        self.assertEqual(body[index + 2], tokens(
            "cl_abap_unit_assert=>assert_equals("
            " quit = mv_assert_quit"
            " act = lv_find_subrc exp = 4"
            " msg = 'The internal original_row_index must never be serialized by Gateway' )"
        ))

    def test_direct_setup_calls_are_rejected_case_insensitively(self):
        for call in ("setup( )", "SETUP( )", "me->setup( )", "ME->SETUP( )"):
            with self.subTest(call=call):
                self.assertTrue(calls_setup_directly(tokens(call)))
        for call in ("reset_fixture( )", "me->reset_fixture( )",
                     "other->setup( )", "result = 'setup( )'"):
            with self.subTest(call=call):
                self.assertFalse(calls_setup_directly(tokens(call)))

    def test_framework_setup_delegates_to_fixture_reset(self):
        classes, _ = parse((ROOT / "ABAP code" / "Unit test.txt").read_text())
        parity = classes["ltc_parity"]
        self.assertEqual(parity.implementations["setup"],
                         [tokens("mv_assert_quit = if_aunit_constants=>method"),
                          tokens("CLEAR mv_group_test"),
                          tokens("reset_fixture( )")])
        self.assertEqual(parity.implementations["reset_fixture"], [
            tokens("mo_cut = NEW #( )"),
            tokens("CLEAR: mt_differences, mv_difference_count"),
            tokens("CLEAR mv_unused"),
        ])
        for name, body in parity.implementations.items():
            with self.subTest(method=name):
                self.assertFalse(any(calls_setup_directly(stmt) for stmt in body))

    def test_deferred_and_friends_are_not_full_definitions(self):
        classes, friends = parse("""
CLASS ltc_parity DEFINITION DEFERRED.
CLASS zcl_cut DEFINITION LOCAL FRIENDS ltc_parity.
CLASS ltc_parity DEFINITION FINAL FOR TESTING.
METHODS: one FOR TESTING, two FOR TESTING.
ENDCLASS.
CLASS ltc_parity IMPLEMENTATION.
METHOD one.
* a fake METHOD two. and assertion
" another fake ENDMETHOD.
assert_equals( act = 'a.b''c' exp = `a.b` ).
ENDMETHOD.
METHOD two.
one( ).
ENDMETHOD.
ENDCLASS.
""")
        self.assertEqual(list(classes), ["ltc_parity"])
        self.assertEqual(set(classes["ltc_parity"].declarations), {"one", "two"})
        self.assertEqual(set(classes["ltc_parity"].implementations), {"one", "two"})
        self.assertEqual(friends["zcl_cut"], {"ltc_parity"})
        self.assertEqual(len(classes["ltc_parity"].implementations["one"]), 1)

    def test_comment_only_body_is_empty(self):
        classes, _ = parse("""
CLASS ltc_parity DEFINITION FOR TESTING.
METHODS empty FOR TESTING.
ENDCLASS.
CLASS ltc_parity IMPLEMENTATION.
METHOD empty.
* assert_equals( act = 1 exp = 1 ).
 " commented assertion
ENDMETHOD.
ENDCLASS.
""")
        self.assertEqual(classes["ltc_parity"].implementations["empty"], [])

    def test_global_friends_do_not_hide_full_definition(self):
        classes, friends = parse("""
CLASS zcl_cut DEFINITION CREATE PRIVATE GLOBAL FRIENDS ltc_parity.
METHODS execute.
ENDCLASS.
CLASS zcl_cut IMPLEMENTATION.
METHOD execute. ENDMETHOD.
ENDCLASS.
""")
        self.assertEqual(set(classes["zcl_cut"].declarations), {"execute"})
        self.assertEqual(set(classes["zcl_cut"].implementations), {"execute"})
        self.assertEqual(friends["zcl_cut"], {"ltc_parity"})

    def test_escaped_strings_templates_and_decimals(self):
        self.assertEqual(len(list(statements(
            "x = 1.25. y = 'it''s.a'. z = |a.b|. \" ignored .\n"
        ))), 3)

    def test_template_expressions_retain_method_references(self):
        result = tokens(r"x = |Text \{not a call\} { helper( 'a.b' ) }|.")
        self.assertIn("helper", result)
        self.assertNotIn("text", result)
        self.assertEqual(result.count("."), 1)

    def test_signature_arguments_exclude_nested_components(self):
        declaration = tokens("importing is_request type ts_request "
                             "returning value(rv_result) type abap_bool")
        self.assertEqual(parameter_names(declaration), {"is_request", "rv_result"})
        call = tokens("m( is_request = value #( field = 'x' ) )")
        self.assertEqual(named_arguments(call, 1), {"is_request"})

    def test_interface_signatures(self):
        classes = interface_declarations("""
INTERFACE zif_cut PUBLIC.
METHODS over IMPORTING is_request TYPE ts_request EXPORTING et_result TYPE tt_result.
ENDINTERFACE.
""")
        self.assertEqual(parameter_names(classes["zif_cut"].declarations["over"]),
                         {"is_request", "et_result"})

    def test_class_methods_and_component_tokens(self):
        classes, _ = parse("""
CLASS zcl_cut DEFINITION.
CLASS-METHODS convert IMPORTING is_request TYPE ts_request.
ENDCLASS.
CLASS zcl_cut IMPLEMENTATION.
METHOD convert. result = is_request-filter-filter_string. ENDMETHOD.
ENDCLASS.
""")
        self.assertEqual(set(classes["zcl_cut"].declarations), {"convert"})
        self.assertIn("is_request-filter-filter_string",
                      classes["zcl_cut"].implementations["convert"][0])

    def test_empty_helper_does_not_count_as_assertion(self):
        classes, _ = parse("""
CLASS ltc_parity DEFINITION FOR TESTING.
METHODS: test_one FOR TESTING, run_case, assert_result.
ENDCLASS.
CLASS ltc_parity IMPLEMENTATION.
METHOD test_one. run_case( ). ENDMETHOD.
METHOD run_case. assert_result( ). ENDMETHOD.
METHOD assert_result. ENDMETHOD.
ENDCLASS.
""")
        self.assertFalse(reaches_assertion(classes["ltc_parity"], "test_one"))
        classes["ltc_parity"].implementations["assert_result"] = [
            tokens("cl_abap_unit_assert=>assert_equals( act = actual exp = expected )")
        ]
        self.assertTrue(reaches_assertion(classes["ltc_parity"], "test_one"))


def legacy_mapping(root, ref, renames):
    """Compare each legacy test declaration, including comment-only bodies."""
    source = subprocess.check_output(
        ["git", "show", "--end-of-options", f"{ref}:ABAP code/Unit test.txt"],
        cwd=root, text=True
    )
    legacy, _ = parse(source)
    # Include fully commented test declarations, not just commented bodies.
    # This is limited to declaration lines and does not uncomment obsolete
    # statements or pretend to compile the old suite.
    owner = None
    lines = source.splitlines()
    for index, line in enumerate(lines):
        active = tokens(line)
        if active[:1] == ["class"] and "definition" in active:
            if "deferred" not in active and "friends" not in active:
                owner = active[1]
        elif active[:1] == ["endclass"]:
            owner = None
        if not owner or not re.match(r"^\*\s*METHODS\b", line, re.IGNORECASE):
            continue
        declaration = []
        for continuation in lines[index:]:
            if not continuation.startswith("*"):
                break
            declaration.extend(tokens(continuation[1:]))
            if "." in declaration:
                break
        groups = [[]]
        for token in declaration[1:]:
            if token == ".":
                break
            if token == ":":
                continue
            if token == ",":
                groups.append([])
            else:
                groups[-1].append(token)
        for group in groups:
            if group and "testing" in group and owner in legacy:
                legacy[owner].declarations.setdefault(group[0], group[1:])
    current, _ = parse((root / "ABAP code" / "Unit test.txt").read_text())
    parity = current.get("ltc_parity", Class("ltc_parity"))
    current_tests = {name for name, decl in parity.declarations.items() if "testing" in decl}
    mapping = {}
    for cls in legacy.values():
        for name, declaration in cls.declarations.items():
            if "testing" not in declaration:
                continue
            qualified = f"{cls.name}.{name}"
            replacement = renames.get(qualified, renames.get(name, name))
            mapping[qualified] = {
                "replacement": replacement,
                "declared_for_testing": replacement in current_tests,
                "executable_body": bool(parity.implementations.get(replacement)),
                "legacy_executable_body": bool(cls.implementations.get(name)),
            }
    return mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--legacy-ref", help="Audit all legacy tests at a git revision")
    parser.add_argument("--rename-map", type=Path,
                        help="JSON object of old [class.]method to replacement method")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(ParserTests)
        )
        return 0 if result.wasSuccessful() else 1
    result = audit(ROOT)
    if args.legacy_ref:
        renames = dict(LEGACY_RENAMES)
        if args.rename_map:
            renames.update(json.loads(args.rename_map.read_text()))
        result["legacy_mapping"] = legacy_mapping(ROOT, args.legacy_ref, renames)
        active_tokens = tokens((ROOT / "ABAP code" / "Unit test.txt").read_text())
        for old, mapping in result["legacy_mapping"].items():
            if not mapping["declared_for_testing"] or not mapping["executable_body"]:
                result["errors"].append(f"Legacy test not restored/mapped: {old}")
            old_name = old.rsplit(".", 1)[-1]
            if old_name != mapping["replacement"] and old_name in active_tokens:
                result["errors"].append(f"Stale renamed method reference: {old_name}")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
