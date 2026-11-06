import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path


SUPPORTED_DELIMITERS = ",;\t|"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Genericky konvertor CSV/TXT suborov do "
            "TAB-separated formatu pre SAP."
        )
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        default="data.csv",
        help="Vstupny subor. Predvolene: data.csv",
    )

    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Vystupny subor. Predvolene sa vytvori "
            "<vstupny_subor>_SAP.txt"
        ),
    )

    parser.add_argument(
        "--delimiter",
        choices=[
            "auto",
            "comma",
            "semicolon",
            "tab",
            "pipe",
        ],
        default="auto",
        help="Vstupny oddelovac. Predvolene: auto",
    )

    parser.add_argument(
        "--encoding",
        default="auto",
        help=(
            "Kodovanie vstupu: auto, utf-8-sig, utf-8, "
            "cp1250 alebo ine Python kodovanie."
        ),
    )

    parser.add_argument(
        "--skip-header",
        action="store_true",
        help="Preskoci prvy riadok vstupneho suboru.",
    )

    parser.add_argument(
        "--strict-columns",
        action="store_true",
        help=(
            "Ukonci konverziu chybou, ak riadky nemaju "
            "rovnaky pocet stlpcov."
        ),
    )

    parser.add_argument(
        "--timestamp-mode",
        choices=[
            "auto",
            "short",
            "long",
        ],
        default="auto",
        help=(
            "Konverzia timestampu: "
            "short = 14 cislic bez zlomku sekundy, "
            "long = 14 cislic + ciarka + 7 desatinnych miest, "
            "auto = zachova zlomok sekundy, ak je vo vstupe."
        ),
    )

    parser.add_argument(
        "--boolean-case",
        choices=[
            "keep",
            "lower",
            "upper",
        ],
        default="keep",
        help=(
            "Format boolean hodnot: keep, lower alebo upper. "
            "Predvolene: keep."
        ),
    )

    return parser.parse_args()


def detect_encoding(input_file, requested_encoding):
    if requested_encoding.lower() != "auto":
        return requested_encoding

    candidate_encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1250",
        "cp1252",
    ]

    for encoding in candidate_encodings:
        try:
            with input_file.open(
                mode="r",
                encoding=encoding,
            ) as source_file:
                source_file.read(65536)

            return encoding

        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Nepodarilo sa automaticky zistit kodovanie suboru."
    )


def detect_delimiter(input_file, encoding, delimiter_option):
    delimiter_mapping = {
        "comma": ",",
        "semicolon": ";",
        "tab": "\t",
        "pipe": "|",
    }

    if delimiter_option != "auto":
        return delimiter_mapping[delimiter_option]

    with input_file.open(
        mode="r",
        encoding=encoding,
        newline="",
    ) as source_file:
        sample = source_file.read(65536)

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=SUPPORTED_DELIMITERS,
        )
        return dialect.delimiter

    except csv.Error:
        return ","


def is_iso_date(value):
    return re.fullmatch(
        r"\d{4}-\d{2}-\d{2}",
        value,
    ) is not None


def is_european_date(value):
    return re.fullmatch(
        r"\d{2}\.\d{2}\.\d{4}",
        value,
    ) is not None


def is_time(value):
    return re.fullmatch(
        r"\d{1,2}:\d{2}(?::\d{2})?",
        value,
    ) is not None


def is_source_timestamp(value):
    return re.fullmatch(
        (
            r"\d{4}-\d{2}-\d{2}"
            r"[ T]"
            r"\d{1,2}:\d{2}:\d{2}"
            r"(?:\.\d+)?"
        ),
        value,
    ) is not None


def is_sap_short_timestamp(value):
    return re.fullmatch(
        r"\d{14}",
        value,
    ) is not None


def is_sap_long_timestamp(value):
    return re.fullmatch(
        r"\d{14}[.,]\d{1,7}",
        value,
    ) is not None


def is_decimal_with_dot(value):
    return re.fullmatch(
        r"[+-]?\d+\.\d+",
        value,
    ) is not None


def is_decimal_with_comma(value):
    return re.fullmatch(
        r"[+-]?\d+,\d+",
        value,
    ) is not None


def convert_date(value):
    parsed_date = datetime.strptime(
        value,
        "%Y-%m-%d",
    )

    return parsed_date.strftime("%d.%m.%Y")


def validate_european_date(value):
    datetime.strptime(
        value,
        "%d.%m.%Y",
    )

    return value


def convert_time(value):
    if value.count(":") == 1:
        parsed_time = datetime.strptime(
            value,
            "%H:%M",
        )
    else:
        parsed_time = datetime.strptime(
            value,
            "%H:%M:%S",
        )

    return parsed_time.strftime("%H:%M:%S")


def normalize_fraction(fraction):
    """
    Vrati presne 7 cislic zlomku sekundy.

    514     -> 5140000
    5140000 -> 5140000
    51400009 -> 5140000
    """
    if not fraction:
        return "0000000"

    fraction = re.sub(r"\D", "", fraction)

    if len(fraction) > 7:
        fraction = fraction[:7]

    return fraction.ljust(7, "0")


def convert_timestamp(value, timestamp_mode):
    """
    Podporovane konverzie:

    short:
    2026-06-15 09:26:21.5140000
    -> 20260615092621

    long:
    2026-06-15 09:26:21.5140000
    -> 20260615092621,5140000

    auto:
    Ak vstup obsahuje zlomok sekundy, vytvori long.
    Inak vytvori short.
    """
    normalized_value = value.replace("T", " ")

    timestamp_match = re.fullmatch(
        (
            r"(\d{4})-(\d{2})-(\d{2}) "
            r"(\d{1,2}):(\d{2}):(\d{2})"
            r"(?:\.(\d+))?"
        ),
        normalized_value,
    )

    if not timestamp_match:
        raise ValueError(
            f"Neplatny timestamp: {value}"
        )

    (
        year,
        month,
        day,
        hour,
        minute,
        second,
        fraction,
    ) = timestamp_match.groups()

    parsed_timestamp = datetime(
        year=int(year),
        month=int(month),
        day=int(day),
        hour=int(hour),
        minute=int(minute),
        second=int(second),
    )

    base_timestamp = parsed_timestamp.strftime(
        "%Y%m%d%H%M%S"
    )

    if timestamp_mode == "short":
        return base_timestamp

    if timestamp_mode == "long":
        normalized_fraction = normalize_fraction(
            fraction
        )

        return (
            f"{base_timestamp},"
            f"{normalized_fraction}"
        )

    # AUTO:
    # Ak povodna hodnota obsahuje zlomok sekundy,
    # zachovame ho ako TIMESTAMPL.
    if fraction is not None:
        normalized_fraction = normalize_fraction(
            fraction
        )

        return (
            f"{base_timestamp},"
            f"{normalized_fraction}"
        )

    return base_timestamp


def normalize_sap_long_timestamp(value):
    """
    Zjednoti existujuci TIMESTAMPL na desatinnu ciarku
    a presne 7 desatinnych miest.

    20260615092621.514
    -> 20260615092621,5140000
    """
    match = re.fullmatch(
        r"(\d{14})\d{1,7}",
        value,
    )

    if not match:
        return value

    base_timestamp = match.group(1)
    fraction = normalize_fraction(
        match.group(2)
    )

    datetime.strptime(
        base_timestamp,
        "%Y%m%d%H%M%S",
    )

    return f"{base_timestamp},{fraction}"


def convert_boolean(value, boolean_case):
    lowercase_value = value.lower()

    if lowercase_value not in (
        "true",
        "false",
    ):
        return value

    if boolean_case == "lower":
        return lowercase_value

    if boolean_case == "upper":
        return lowercase_value.upper()

    # keep
    return value


def convert_decimal(value):
    return value.replace(".", ",")


def convert_value(
    value,
    timestamp_mode,
    boolean_case,
):
    value = value.strip()

    if value == "":
        return ""

    if is_sap_short_timestamp(value):
        return value

    if is_sap_long_timestamp(value):
        if timestamp_mode == "short":
            return value[:14]

        return normalize_sap_long_timestamp(value)

    if is_source_timestamp(value):
        return convert_timestamp(
            value,
            timestamp_mode,
        )

    if is_iso_date(value):
        return convert_date(value)

    if is_european_date(value):
        return validate_european_date(value)

    if is_time(value):
        return convert_time(value)

    if value.lower() in (
        "true",
        "false",
    ):
        return convert_boolean(
            value,
            boolean_case,
        )

    if is_decimal_with_dot(value):
         return value

    if is_decimal_with_comma(value):
        return value

    return value


def get_output_file(
    input_file,
    output_argument,
):
    if output_argument:
        return Path(output_argument)

    return input_file.with_name(
        f"{input_file.stem}_SAP.txt"
    )


def convert_file(
    input_file,
    output_file,
    encoding,
    delimiter,
    skip_header,
    strict_columns,
    timestamp_mode,
    boolean_case,
):
    converted_rows = 0
    skipped_rows = 0
    warning_rows = 0
    reference_column_count = None

    with input_file.open(
        mode="r",
        encoding=encoding,
        newline="",
    ) as source_file:
        reader = csv.reader(
            source_file,
            delimiter=delimiter,
            quotechar='"',
            escapechar="\\",
            strict=True,
        )

        with output_file.open(
            mode="w",
            encoding="utf-8-sig",
            newline="",
        ) as target_file:
            writer = csv.writer(
                target_file,
                delimiter="\t",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )

            for row_number, row in enumerate(
                reader,
                start=1,
            ):
                if skip_header and row_number == 1:
                    skipped_rows += 1
                    continue

                if not row:
                    skipped_rows += 1
                    continue

                if all(
                    value.strip() == ""
                    for value in row
                ):
                    skipped_rows += 1
                    continue

                current_column_count = len(row)

                if reference_column_count is None:
                    reference_column_count = (
                        current_column_count
                    )

                elif (
                    current_column_count
                    != reference_column_count
                ):
                    message = (
                        f"Riadok {row_number} ma "
                        f"{current_column_count} stlpcov. "
                        f"Prvy datovy riadok ma "
                        f"{reference_column_count} stlpcov."
                    )

                    if strict_columns:
                        raise ValueError(message)

                    print(f"VAROVANIE: {message}")
                    warning_rows += 1

                try:
                    # Prazdne hodnoty sa neodstranuju.
                    # Stlpce preto zostanu na povodnych poziciach.
                    converted_row = [
                        convert_value(
                            value=value,
                            timestamp_mode=timestamp_mode,
                            boolean_case=boolean_case,
                        )
                        for value in row
                    ]

                except ValueError as error:
                    raise ValueError(
                        f"Chyba na riadku "
                        f"{row_number}: {error}"
                    ) from error

                writer.writerow(converted_row)
                converted_rows += 1

    return {
        "converted_rows": converted_rows,
        "skipped_rows": skipped_rows,
        "warning_rows": warning_rows,
        "column_count": reference_column_count,
    }


def print_file_list():
    print()
    print("Subory v aktualnom priecinku:")

    files = sorted(
        path
        for path in Path(".").iterdir()
        if path.is_file()
    )

    if not files:
        print(
            "  V priecinku nie su ziadne subory."
        )
        return

    for file_path in files:
        print(f"  {file_path.name}")


def main():
    args = parse_arguments()

    input_file = Path(args.input_file)

    output_file = get_output_file(
        input_file=input_file,
        output_argument=args.output,
    )

    if not input_file.exists():
        print()
        print(
            "CHYBA: Vstupny subor neexistuje:"
        )
        print(input_file.resolve())
        print_file_list()
        sys.exit(1)

    if input_file.resolve() == output_file.resolve():
        print()
        print(
            "CHYBA: Vstupny a vystupny "
            "subor su rovnake."
        )
        sys.exit(1)

    try:
        encoding = detect_encoding(
            input_file=input_file,
            requested_encoding=args.encoding,
        )

        delimiter = detect_delimiter(
            input_file=input_file,
            encoding=encoding,
            delimiter_option=args.delimiter,
        )

        result = convert_file(
            input_file=input_file,
            output_file=output_file,
            encoding=encoding,
            delimiter=delimiter,
            skip_header=args.skip_header,
            strict_columns=args.strict_columns,
            timestamp_mode=args.timestamp_mode,
            boolean_case=args.boolean_case,
        )

    except PermissionError:
        print()
        print("Konverzia zlyhala.")
        print(
            "Vstupny alebo vystupny subor "
            "je otvoreny v inom programe."
        )
        print(
            "Zatvor subor v Exceli alebo "
            "Poznamkovom bloku."
        )
        sys.exit(1)

    except UnicodeDecodeError:
        print()
        print("Konverzia zlyhala.")
        print(
            "Nepodarilo sa precitat kodovanie "
            "vstupneho suboru."
        )
        print()
        print("Mozes vyskusat napriklad:")
        print(
            "python .\\convert_for_sap.py "
            ".\\data.csv --encoding cp1250"
        )
        sys.exit(1)

    except csv.Error as error:
        print()
        print(
            "Konverzia zlyhala pri "
            "spracovani CSV:"
        )
        print(error)
        sys.exit(1)

    except ValueError as error:
        print()
        print("Konverzia zlyhala:")
        print(error)
        sys.exit(1)

    except Exception as error:
        print()
        print("Neocakavana chyba:")
        print(error)
        sys.exit(1)

    print()
    print("Konverzia dokoncena.")
    print(
        f"Vstup:               "
        f"{input_file.resolve()}"
    )
    print(
        f"Vystup:              "
        f"{output_file.resolve()}"
    )
    print(
        f"Kodovanie vstupu:    {encoding}"
    )
    print(
        f"Vstupny oddelovac:   "
        f"{repr(delimiter)}"
    )
    print(
        f"Timestamp mode:       "
        f"{args.timestamp_mode}"
    )
    print(
        f"Boolean case:         "
        f"{args.boolean_case}"
    )
    print(
        f"Pocet stlpcov:       "
        f"{result['column_count']}"
    )
    print(
        f"Konvertovane riadky: "
        f"{result['converted_rows']}"
    )
    print(
        f"Preskocene riadky:   "
        f"{result['skipped_rows']}"
    )
    print(
        f"Varovania:           "
        f"{result['warning_rows']}"
    )
    print()
    print(
        "Vystup je oddeleny TAB znakmi "
        "a je pripraveny pre SAP."
    )


if __name__ == "__main__":
    main()