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


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CATEGORIES = (
    "standard", "owner", "filter", "scope", "sort_paging", "selection", "format"
)
CATEGORIES = REQUIRED_CATEGORIES + ("request_processing", "hana_filter", "utility")
LEGACY_RENAMES = {
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


def tokens(source):
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
            i += 1
            continue
        line_start = False
        if char == '"':
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
            continue
        if char in "'`|":
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
            result.append("<literal>")
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


def statements(source):
    statement = []
    for token in tokens(source):
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


def parse(source):
    classes = {}
    friends = {}
    current = None
    method = None
    section = None
    for stmt in statements(source):
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
    flat = [token for stmt in body for token in stmt]
    return [flat[index] for index in range(len(flat) - 1)
            if flat[index] in declarations and flat[index + 1] == "("]


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
            flattened = [token for stmt in body for token in stmt]
            if name in CATEGORIES:
                calls = [
                    flattened[index] for index in range(len(flattened) - 1)
                    if flattened[index] in tests and flattened[index + 1] == "("
                ]
                matrix[name] = calls
                leaf_counts.update(calls)
                if not calls:
                    errors.append(f"Category has no testing leaves: {name}")
                if len(calls) != len(set(calls)):
                    errors.append(f"Category repeats a leaf internally: {name}")
                if any(call in CATEGORIES for call in calls):
                    errors.append(f"Category calls another category: {name}")
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
        for category in REQUIRED_CATEGORIES:
            if category not in matrix:
                errors.append(f"Missing testing category: {category}")
        tests = {name for name, decl in parity.declarations.items() if "testing" in decl}
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
            "Structural checks only. Dynamic calls, external SAP signatures, "
            "ABAP syntax/type checking, assertion semantics, ATC, ABAP Unit, "
            "HANA APPLY_FILTER and OData parity require SAP runtime review."
        ),
    }


class ParserTests(unittest.TestCase):
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
                         [tokens("reset_fixture( )")])
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
        if "testing" in declaration and len(declaration) > 1:
            legacy[owner].declarations.setdefault(declaration[1], declaration[2:])
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
