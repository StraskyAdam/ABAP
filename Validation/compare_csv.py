"""Compare CSV exports as multisets, preserving duplicate row counts."""

import argparse
from collections import Counter
import csv
from decimal import Decimal
import glob
from pathlib import Path
import re
import sys


DELIMITERS = {"comma": ",", "semicolon": ";", "pipe": "|", "tab": "\t"}
NUMERIC_COLUMNS = {
    "PO Value", "PO Value(USD)", "Services Completed Amount",
    "Services Completed Amount(USD)", "% of Services Completed",
    "Goods Reciept to date", "Goods Reciept to date(USD)",
    "Invoice Amount to Date", "Invoice Amount to Date(USD)",
    "Amount to be Accrued", "Amount to be Accrued(USD)", "Exchange Rate",
    "Split Accounting %",
}
AGGREGATE_LIST_COLUMNS = {
    "GL Account", "Cost Center", "Management Unit", "Internal Order",
    "Profit Center", "Asset Id", "Split Accounting %",
}
KEY_COLUMNS = ("PO Dashboard Section", "Company Code", "PO Number", "Line Item")
DECIMAL_PATTERN = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


def normalize_cell(column, value):
    # Never strip identifiers or nonblank text, and never round numbers.
    if value in ("", " "):
        return ""
    if column == "PSTYPE Text":
        return {"9": "Service", "0": "Material"}.get(value, value)
    if column in NUMERIC_COLUMNS:
        parts = value.split(";") if column == "Split Accounting %" else [value]
        normalized = []
        for part in parts:
            number = part.replace(",", ".") if column == "Exchange Rate" else part
            if not DECIMAL_PATTERN.fullmatch(number):
                raise ValueError(f"{column}: invalid numeric value {value!r}")
            decimal = Decimal(number)
            text = format(decimal, "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            normalized.append("0" if decimal == 0 else text)
        return ";".join(normalized)
    if column in ("Service Start Date", "Service End Date", "PO Creation Date", "Last Update On"):
        return re.sub(r"\bSep\b", "Sept", value)
    return value


def normalize_rows(header, rows):
    result = Counter()
    for row, count in rows.items():
        result[tuple(normalize_cell(column, value) for column, value in zip(header, row))] += count
    return result


def normalize_list_order(header, rows):
    """Diagnostic only: canonicalize each XSA STRING_AGG field independently."""
    result = Counter()
    for row, count in rows.items():
        normalized = []
        for column, value in zip(header, row):
            cell = normalize_cell(column, value)
            if column in AGGREGATE_LIST_COLUMNS and cell:
                cell = ";".join(sorted(cell.split(";")))
            normalized.append(cell)
        result[tuple(normalized)] += count
    return result


def write_column_differences(path, header, xsa, abap):
    """Pair only unambiguous keys after removing exact matches."""
    if not all(column in header for column in KEY_COLUMNS):
        print("Column diagnostics skipped: dashboard key columns are missing.")
        return
    indexes = [header.index(column) for column in KEY_COLUMNS]

    def group(rows):
        result = {}
        for row, count in rows.items():
            key = tuple(row[index] for index in indexes)
            result.setdefault(key, Counter())[row] = count
        return result

    left = group(xsa)
    right = group(abap)
    totals = Counter()
    ambiguous = 0
    with path.open("x", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target)
        writer.writerow([*KEY_COLUMNS, "OCCURRENCES", "COLUMN", "XSA", "ABAP", "KIND"])
        for key in sorted(left.keys() & right.keys()):
            a, b = left[key], right[key]
            if len(a) != 1 or len(b) != 1:
                ambiguous += 1
                continue
            row_a, row_b = next(iter(a)), next(iter(b))
            count = min(a[row_a], b[row_b])
            for column, value_a, value_b in zip(header, row_a, row_b):
                if value_a != value_b:
                    normalized_a = normalize_cell(column, value_a)
                    normalized_b = normalize_cell(column, value_b)
                    if normalized_a == normalized_b:
                        kind = "representation"
                    elif (column in AGGREGATE_LIST_COLUMNS and normalized_a and normalized_b
                          and ";".join(sorted(normalized_a.split(";"))) ==
                          ";".join(sorted(normalized_b.split(";")))):
                        kind = "list-order"
                    else:
                        kind = "value"
                    writer.writerow([*key, count, column, value_a, value_b, kind])
                    totals[column, kind] += count
    for (column, kind), count in totals.most_common():
        print(f"  {column}: {count} ({kind})")
    if ambiguous:
        print(f"Skipped {ambiguous} ambiguous duplicate key(s); inspect only_*.csv.")


def expand_paths(patterns):
    paths = []
    seen = set()
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if not matches:
            raise ValueError(f"No files match: {pattern}")
        for match in matches:
            path = Path(match).resolve()
            if not path.is_file():
                raise ValueError(f"Not a file: {path}")
            if path in seen:
                raise ValueError(f"File selected more than once: {path}")
            seen.add(path)
            paths.append(path)
    return paths


def read_export(paths, encoding="utf-8-sig", delimiter="auto"):
    header = None
    counts = Counter()
    for path in paths:
        with path.open(encoding=encoding, newline="") as source:
            first = source.readline()
            directive = first.rstrip("\r\n")
            if directive.startswith('"') and directive.endswith('"'):
                directive = directive[1:-1]
            has_directive = len(directive) == 5 and directive.lower().startswith("sep=")
            if delimiter != "auto":
                separator = DELIMITERS[delimiter]
            elif has_directive:
                separator = directive[-1]
            else:
                try:
                    separator = csv.Sniffer().sniff(first, delimiters=",;|\t").delimiter
                except csv.Error as error:
                    raise ValueError(
                        f"{path}: cannot detect delimiter; specify --delimiter"
                    ) from error
            if not has_directive:
                source.seek(0)
            reader = csv.reader(source, delimiter=separator, strict=True)
            current_header = next(reader, None)
            if not current_header:
                raise ValueError(f"{path}: missing CSV header")
            if header is None:
                header = current_header
            elif current_header != header:
                raise ValueError(f"{path}: header differs from the previous file")
            for row in reader:
                if len(row) != len(header):
                    raise ValueError(
                        f"{path}: CSV line {reader.line_num}: "
                        f"expected {len(header)} fields, found {len(row)}"
                    )
                counts[tuple(row)] += 1
    return header, counts


def write_difference(path, header, rows):
    with path.open("x", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["OCCURRENCES", *header])
        for row, count in sorted(rows.items()):
            writer.writerow([count, *row])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsa", nargs="+", required=True, help="XSA files or quoted globs")
    parser.add_argument("--abap", nargs="+", required=True, help="ABAP files or quoted globs")
    parser.add_argument("--xsa-encoding", default="utf-8-sig")
    parser.add_argument("--abap-encoding", default="utf-8-sig")
    parser.add_argument("--delimiter", choices=["auto", *DELIMITERS], default="auto")
    parser.add_argument("--output-dir", type=Path, default=Path("csv_comparison"))
    args = parser.parse_args(argv)

    try:
        xsa_paths = expand_paths(args.xsa)
        abap_paths = expand_paths(args.abap)
        overlap = set(xsa_paths) & set(abap_paths)
        if overlap:
            raise ValueError(f"Same input selected on both sides: {sorted(overlap)}")
        xsa_header, xsa = read_export(xsa_paths, args.xsa_encoding, args.delimiter)
        abap_header, abap = read_export(abap_paths, args.abap_encoding, args.delimiter)
        print(f"XSA:  {sum(xsa.values())} rows in {len(xsa_paths)} file(s)")
        print(f"ABAP: {sum(abap.values())} rows in {len(abap_paths)} file(s)")
        if xsa_header != abap_header:
            print("DIFFERENT HEADERS (names, order or column count):")
            print(f"XSA:  {xsa_header!r}")
            print(f"ABAP: {abap_header!r}")
            return 1

        only_xsa = xsa - abap
        only_abap = abap - xsa
        if not only_xsa and not only_abap:
            print("MATCH: identical headers, values and duplicate counts; row order ignored.")
            return 0

        print(f"DIFFERENT: {sum(only_xsa.values())} excess row(s) on XSA side; "
              f"{sum(only_abap.values())} on ABAP side.")
        normalized_xsa = normalize_rows(xsa_header, xsa)
        normalized_abap = normalize_rows(abap_header, abap)
        semantic_xsa = normalized_xsa - normalized_abap
        semantic_abap = normalized_abap - normalized_xsa
        if not semantic_xsa and not semantic_abap:
            print("NORMALIZED MATCH: differences are representation-only under the documented rules.")
        else:
            print(f"NORMALIZED DIFFERENT: {sum(semantic_xsa.values())} excess XSA row(s); "
                  f"{sum(semantic_abap.values())} excess ABAP row(s).")
        list_xsa = normalize_list_order(xsa_header, xsa)
        list_abap = normalize_list_order(abap_header, abap)
        list_only_xsa = list_xsa - list_abap
        list_only_abap = list_abap - list_xsa
        if not list_only_xsa and not list_only_abap:
            print("LIST-ORDER MATCH: remaining differences can be explained by independent "
                  "ordering of aggregated account lists.")
        else:
            print(f"LIST-ORDER NORMALIZED DIFFERENT: {sum(list_only_xsa.values())} excess XSA row(s); "
                  f"{sum(list_only_abap.values())} excess ABAP row(s).")
        args.output_dir.mkdir(parents=True, exist_ok=False)
        write_difference(args.output_dir / "only_xsa.csv", xsa_header, only_xsa)
        write_difference(args.output_dir / "only_abap.csv", abap_header, only_abap)
        write_difference(args.output_dir / "normalized_only_xsa.csv", xsa_header, semantic_xsa)
        write_difference(args.output_dir / "normalized_only_abap.csv", abap_header, semantic_abap)
        write_difference(args.output_dir / "list_order_only_xsa.csv", xsa_header, list_only_xsa)
        write_difference(args.output_dir / "list_order_only_abap.csv", xsa_header, list_only_abap)
        write_column_differences(
            args.output_dir / "column_differences.csv", xsa_header, only_xsa, only_abap
        )
        print(f"Difference files: {args.output_dir.resolve()}")
        print("OCCURRENCES is the excess count, not the total count in the source.")
        return 1
    except (OSError, UnicodeError, LookupError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
