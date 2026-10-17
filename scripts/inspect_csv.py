"""Read one explicitly selected CSV and report structure without interpreting records.

This development helper is separate from the qualified 0.1.0a1 preview. It never
repairs inputs, chooses a dialect, maps fields, computes totals or sends data.
"""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

MAX_BYTES = 16 * 1024 * 1024
MAX_FIELD_CHARACTERS = 131072
MAX_FINDINGS = 50
DELIMITERS = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}
MESSAGES = {
    "authority": ("Confirm authority to read the selected file before inspection.",
                  "Confirmez l'autorisation de lire le fichier choisi avant l'inspection."),
    "delimiter": ("Select comma, semicolon, tab or pipe explicitly.",
                  "Choisissez explicitement comma, semicolon, tab ou pipe."),
    "size": ("The selected file exceeds this helper's 16 MiB limit.",
             "Le fichier choisi dépasse la limite de 16 Mio de cet outil."),
    "unavailable": ("The selected file could not be read. No inspection is confirmed.",
                    "Le fichier choisi n'a pas pu être lu. Aucune inspection n'est confirmée."),
    "limit": ("Structure only: confirm mapping, identity, units, dates, basis, scope and export completeness separately. No records were accepted or changed.",
              "Structure uniquement : confirmez séparément les champs, les identifiants, les unités, les dates, la base, le périmètre et l'exhaustivité de l'export. Aucun enregistrement n'a été accepté ou modifié."),
}


class InspectionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def inspect_file(source, delimiter, *, confirm_authority=False):
    # Check authority before path resolution, metadata access or content reads.
    if not confirm_authority:
        raise InspectionError("authority")
    if delimiter not in DELIMITERS:
        raise InspectionError("delimiter")
    with Path(source).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InspectionError("size")
    report = {
        "report_version": "1.0.0", "state": "inspection_only",
        "source_sha256": hashlib.sha256(raw).hexdigest(), "source_bytes": len(raw),
        "dialect": {"delimiter": delimiter, "quotechar": '"', "doublequote": True,
                    "skipinitialspace": False, "first_record_is_header": True},
        "encoding": "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8",
        "parsed_to_end": False, "header": [], "header_line_end": None,
        "parsed_data_record_count": 0, "data_record_count": None,
        "blank_data_record_count": 0, "multiline_data_record_count": 0,
        "finding_counts": {}, "findings": [], "findings_truncated": False,
        "structure_status": "needs_review", "export_completeness": "unconfirmed",
        "semantic_mapping": "unconfirmed",
    }

    def finding(code, **location):
        counts = report["finding_counts"]
        counts[code] = counts.get(code, 0) + 1
        if len(report["findings"]) < MAX_FINDINGS:
            report["findings"].append({"code": code, **location})
        else:
            report["findings_truncated"] = True

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeError:
        report["encoding"] = "unsupported"
        finding("encoding.not_utf8")
        return report
    if "\x00" in content:
        finding("encoding.nul_character")
        return report
    reader = csv.reader(io.StringIO(content, newline=""), delimiter=DELIMITERS[delimiter],
                        quotechar='"', doublequote=True, skipinitialspace=False, strict=True)
    old_limit = csv.field_size_limit()
    csv.field_size_limit(MAX_FIELD_CHARACTERS)
    try:
        try:
            headers = next(reader)
        except StopIteration:
            finding("header.absent")
            report["parsed_to_end"] = True
            report["data_record_count"] = 0
            return report
        report["header"], report["header_line_end"] = headers, reader.line_num
        if not headers:
            finding("header.absent")
        if len(headers) == 1:
            finding("header.single_column_check_delimiter")
        counts = Counter(headers)
        for index, header in enumerate(headers, 1):
            if not header.strip():
                finding("header.empty", column=index)
            elif header != header.strip():
                finding("header.surrounding_whitespace", column=index)
            if counts[header] > 1:
                finding("header.duplicate", column=index)
        prior_line = reader.line_num
        for record_number, row in enumerate(reader, 1):
            start_line, end_line = prior_line + 1, reader.line_num
            prior_line = end_line
            report["parsed_data_record_count"] += 1
            if end_line > start_line:
                report["multiline_data_record_count"] += 1
            if not row or not any(cell.strip() for cell in row):
                report["blank_data_record_count"] += 1
                finding("record.blank", record=record_number, line_start=start_line, line_end=end_line)
            if len(row) != len(headers):
                finding("record.width", record=record_number, line_start=start_line,
                        line_end=end_line, expected_columns=len(headers), actual_columns=len(row))
        report["parsed_to_end"] = True
        report["data_record_count"] = report["parsed_data_record_count"]
        if report["data_record_count"] == 0:
            finding("record.absent")
    except csv.Error:
        # Do not echo parser errors or data cells into diagnostics.
        finding("csv.parse_or_field_limit", line_end=reader.line_num)
    finally:
        csv.field_size_limit(old_limit)
    if report["parsed_to_end"] and not report["finding_counts"]:
        report["structure_status"] = "ready_for_mapping_review"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="One selected local CSV; un fichier CSV local choisi")
    parser.add_argument("--delimiter", required=True, choices=DELIMITERS,
                        help="Explicit separator; séparateur explicite")
    parser.add_argument("--confirm-authority", action="store_true",
                        help="Confirm local read authority; confirmer l'autorisation de lecture locale")
    parser.add_argument("--language", choices=("en", "fr"), default="en")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        report = inspect_file(args.source, args.delimiter, confirm_authority=args.confirm_authority)
    except (InspectionError, OSError) as exc:
        code = exc.code if isinstance(exc, InspectionError) else "unavailable"
        print(json.dumps({"error": "inspection." + code,
                          "message": MESSAGES[code][args.language == "fr"]}, ensure_ascii=False), file=sys.stderr)
        return 2
    report["message"] = MESSAGES["limit"][args.language == "fr"]
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["structure_status"] == "ready_for_mapping_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
