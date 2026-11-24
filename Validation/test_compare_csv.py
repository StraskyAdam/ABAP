import contextlib
from collections import Counter
import csv
import io
from pathlib import Path
import tempfile
import unittest

from compare_csv import (
    expand_paths, main, normalize_cell, normalize_list_order, normalize_rows, read_export,
)


class CompareCsvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_csv(self, name, rows, delimiter=",", directive=False):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as target:
            if directive:
                target.write(f'"sep={delimiter}"\n')
            writer = csv.writer(target, delimiter=delimiter)
            writer.writerows(rows)
        return path

    def run_comparison(self, xsa, abap):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main([
                "--xsa", *map(str, xsa), "--abap", *map(str, abap),
                "--output-dir", str(self.root / "differences"),
            ])

    def test_reordered_split_files_and_quoted_values(self):
        header = ["PO", "Description", ""]
        a = ["001", 'A, "quoted"\nvalue', ""]
        b = ["002", "Z\u017d", ""]
        xsa = self.make_csv("xsa.csv", [header, a, b], "|", True)
        abap1 = self.make_csv("abap1.csv", [header, b])
        abap2 = self.make_csv("abap2.csv", [header, a])
        self.assertEqual(self.run_comparison([xsa], [abap1, abap2]), 0)

    def test_duplicate_count_is_not_ignored(self):
        xsa = self.make_csv("xsa.csv", [["PO", ""], ["001", ""], ["001", ""]])
        abap = self.make_csv("abap.csv", [["PO", ""], ["001", ""]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)
        with (self.root / "differences" / "only_xsa.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            self.assertEqual(list(csv.reader(source)), [
                ["OCCURRENCES", "PO", ""], ["1", "001", ""],
            ])

    def test_spaces_and_numeric_format_are_significant(self):
        xsa = self.make_csv("xsa.csv", [["A", "B"], [" ", "1.00"]])
        abap = self.make_csv("abap.csv", [["A", "B"], ["", "1"]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)

    def test_bad_column_count_fails(self):
        path = self.make_csv("bad.csv", [["A", "B"], ["1"]])
        with self.assertRaisesRegex(ValueError, "expected 2 fields"):
            read_export([path])

    def test_headers_must_match_between_parts(self):
        a = self.make_csv("a.csv", [["A", "B"]])
        b = self.make_csv("b.csv", [["B", "A"]])
        with self.assertRaisesRegex(ValueError, "header differs"):
            read_export([a, b])

    def test_headers_must_match_between_exports(self):
        a = self.make_csv("a.csv", [["A", "B"]])
        b = self.make_csv("b.csv", [["A", "C"]])
        self.assertEqual(self.run_comparison([a], [b]), 1)

    def test_missing_and_repeated_inputs_fail(self):
        with self.assertRaisesRegex(ValueError, "No files match"):
            expand_paths([str(self.root / "*.csv")])
        a = self.make_csv("a.csv", [["A", "B"]])
        with self.assertRaisesRegex(ValueError, "more than once"):
            expand_paths([str(a), str(a)])
        self.assertEqual(self.run_comparison([a], [a]), 2)

    def test_representation_differences_are_reported_separately(self):
        header = [
            "PO Dashboard Section", "Company Code", "PO Number", "Line Item",
            "Amount to be Accrued", "PSTYPE Text", "Exchange Rate", "Internal Order",
        ]
        key = ["Below $50k Indirect Service", "3390", "8002156800", "00001"]
        xsa = self.make_csv("xsa.csv", [header, [*key, "1250", "Service", "1.000000", ""]])
        abap = self.make_csv("abap.csv", [header, [*key, "1250.00", "9", "1,000000", " "]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)
        with (self.root / "differences" / "normalized_only_xsa.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            self.assertEqual(len(list(csv.reader(source))), 1)
        with (self.root / "differences" / "column_differences.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["KIND"] for row in rows}, {"representation"})

    def test_normalization_preserves_values_identifiers_and_duplicates(self):
        self.assertNotEqual(normalize_cell("PO Number", "001"), normalize_cell("PO Number", "1"))
        self.assertNotEqual(normalize_cell("Supplier Name", " A"), normalize_cell("Supplier Name", "A"))
        self.assertNotEqual(normalize_cell("PO Value", "1.01"), normalize_cell("PO Value", "1.00"))
        self.assertEqual(normalize_cell("Split Accounting %", "14.0;13.00"), "14;13")
        self.assertEqual(normalize_cell("PO Creation Date", "01 Sep 2026"), "01 Sept 2026")
        self.assertEqual(normalize_rows(["PO Value"], Counter({("1.00",): 2, ("1",): 1})),
                         Counter({("1",): 3}))
        with self.assertRaisesRegex(ValueError, "invalid numeric"):
            normalize_cell("PO Value", "1,250.00")

    def test_value_difference_is_not_normalized_away(self):
        header = ["PO Dashboard Section", "Company Code", "PO Number", "Line Item", "PO Value"]
        key = ["Indirect Services", "3390", "001", "00001"]
        xsa = self.make_csv("xsa.csv", [header, [*key, "1.00"]])
        abap = self.make_csv("abap.csv", [header, [*key, "1.01"]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)
        with (self.root / "differences" / "column_differences.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(rows[0]["KIND"], "value")
        self.assertEqual(rows[0]["XSA"], "1.00")
        self.assertEqual(rows[0]["ABAP"], "1.01")

    def test_ambiguous_keys_are_not_arbitrarily_paired(self):
        header = ["PO Dashboard Section", "Company Code", "PO Number", "Line Item", "PO Value"]
        key = ["Indirect Services", "3390", "001", "00001"]
        xsa = self.make_csv("xsa.csv", [header, [*key, "1"], [*key, "2"]])
        abap = self.make_csv("abap.csv", [header, [*key, "3"], [*key, "4"]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)
        with (self.root / "differences" / "column_differences.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            self.assertEqual(len(list(csv.reader(source))), 1)

    def test_normalization_keeps_duplicate_excess(self):
        header = ["PO Value", "PSTYPE Text"]
        xsa = self.make_csv("xsa.csv", [header, ["1", "Service"], ["1", "Service"]])
        abap = self.make_csv("abap.csv", [header, ["1.00", "9"]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)
        with (self.root / "differences" / "normalized_only_xsa.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            self.assertEqual(list(csv.reader(source)), [
                ["OCCURRENCES", *header], ["1", "1", "Service"],
            ])

    def test_account_lists_report_order_only_separately(self):
        header = [
            "PO Dashboard Section", "Company Code", "PO Number", "Line Item",
            "Cost Center", "Split Accounting %",
        ]
        key = ["Indirect Services", "3390", "001", "00001"]
        xsa = self.make_csv("xsa.csv", [header, [*key, "100;200", "10;90"]])
        abap = self.make_csv("abap.csv", [header, [*key, "200;100", "90.0;10.00"]])
        self.assertEqual(self.run_comparison([xsa], [abap]), 1)
        with (self.root / "differences" / "list_order_only_xsa.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            self.assertEqual(len(list(csv.reader(source))), 1)
        with (self.root / "differences" / "column_differences.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        self.assertEqual({row["KIND"] for row in rows}, {"list-order"})
        self.assertEqual(
            normalize_list_order(header[-2:], Counter({("100;200", "10;90"): 1})),
            normalize_list_order(header[-2:], Counter({("200;100", "90;10"): 1})),
        )

    def test_rule_lists_order_is_separate_and_duplicates_remain(self):
        header = ["Rule Type Text", "Rule Type"]
        xsa = Counter({("IV;CC", "Internal Order;Cost Center"): 1})
        abap = Counter({("CC;IV", "Cost Center;Internal Order"): 1})
        self.assertNotEqual(normalize_rows(header, xsa), normalize_rows(header, abap))
        self.assertEqual(normalize_list_order(header, xsa), normalize_list_order(header, abap))
        repeated = Counter({("CC;CC;IV", "Cost Center;Cost Center;Internal Order"): 1})
        self.assertNotEqual(normalize_list_order(header, xsa), normalize_list_order(header, repeated))


if __name__ == "__main__":
    unittest.main()
