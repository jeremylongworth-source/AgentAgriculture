"""Readable bilingual exports, preserving source text and machine identifiers."""

import csv
import html
import io
import re

from .language import issue_text, number_text, text


def safe_cell(value, numeric=False):
    value = "" if value is None else str(value)
    if numeric and re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", value):
        return value
    stripped = value.lstrip("\ufeff \t\r\n")
    return "'" + value if value.startswith(("\t", "\r", "\n")) or stripped.startswith(("=", "+", "-", "@")) else value


def escaped(value):
    return re.sub(r"([\\`*_{}\[\]()#!|])", r"\\\1", html.escape(str(value), quote=False)).replace("\r", " ").replace("\n", " ")


COLUMNS = ["record_id", "version", "kind", "source_id", "source_row", "enterprise", "date", "reference", "quantity", "unit", "quantity_status", "amount", "currency", "amount_status", "disposition", "issue_codes", "issue_messages"]
FRENCH_COLUMNS = ["identifiant_enregistrement", "version", "type", "identifiant_source", "ligne_source", "entreprise", "date", "référence", "quantité", "unité", "état_quantité", "montant", "devise", "état_montant", "disposition", "codes_exception", "messages_exception"]


def normalized_csv(records, language):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";" if language == "fr" else ",", lineterminator="\n")
    writer.writerow(FRENCH_COLUMNS if language == "fr" else COLUMNS)
    for record in records:
        values = [record["record_id"], record["version"], text(language, record["kind"]), record["source"]["source_id"], record["source"]["row_number"],
                  record["enterprise"]["value"], record["date"]["value"], record["reference"]["value"], record["quantity"]["value"], record["quantity"]["unit"], text(language, record["quantity"]["status"]),
                  record["amount"]["value"], record["amount"]["currency"], text(language, record["amount"]["status"]), text(language, record["disposition"]),
                  ";".join(record["issue_codes"]), " | ".join(issue_text(language, code) for code in record["issue_codes"])]
        row = []
        for column, value in zip(COLUMNS, values):
            cell = safe_cell(value, column in {"quantity", "amount", "version", "source_row"})
            if column in {"quantity", "amount"} and value is not None:
                cell = number_text(language, cell)
            row.append(cell)
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def summary(task, totals, exceptions, manifest, *, minimized=False):
    lang = task["language"]
    t = lambda key: text(lang, key)
    lines = ["# " + t("title"), "", escaped(task["question"]), "", "**" + t("status") + ":** " + t(totals["package_status"]),
             "", "**" + t("scope") + ":** " + escaped(task["enterprise_id"]) + ", " + task["reporting_period"]["start"] + " — " + task["reporting_period"]["end"],
             "", t("currency") + ": " + task["currency"] + ". " + t("basis") + ".", "",
             "| " + t("result") + " | " + t("value") + " |", "| --- | --- |"]
    for key in ("raw_purchase_amount_sum", "included_purchase_amount", "known_scoped_purchase_amount", "excluded_purchase_amount", "comparable_purchase_kg", "comparable_receiving_kg", "difference_receiving_minus_purchase_kg"):
        value = number_text(lang, totals[key]) if totals[key] is not None else t("not_established")
        lines.append("| " + t(key) + " | " + escaped(value) + " |")
    lines.extend(["", t("raw_scope"), "", t("comparison_scope"), "", "## " + t("exceptions"), ""])
    lines.extend("- " + escaped(item["exception_id"] + " (" + item["code"] + ")") + ": " + escaped(issue_text(lang, item["code"])) + (" — " + escaped(", ".join(item["record_ids"])) if item["record_ids"] else "") for item in exceptions)
    if not exceptions:
        lines.append(t("no_exceptions"))
    lines.extend(["", "## " + t("sources"), ""])
    lines.extend("- " + escaped(source["source_id"]) + ("; " if minimized else ": `originals/" + source["source_id"] + ".csv`; ") + "SHA-256 `" + source["sha256"] + "`." for source in manifest["inputs"])
    lines.extend(["", "## " + t("omissions"), ""])
    omissions = [item for source in manifest["inputs"] for item in source["omitted_sections"]]
    lines.extend("- " + escaped(item) for item in omissions)
    if not omissions:
        lines.append(t("no_omissions"))
    lines.extend(["", t("recipient") + ": " + escaped(task["recipient_scope"]), "", t("review_link"), "", t("handoff.omitted" if minimized else "exit_note"), "", t("limits"), ""])
    return "\n".join(lines).encode("utf-8")


def record_review(records, history, language):
    t = lambda key: text(language, key)
    lines = ["# " + t("source_review"), "", t("limits"), ""]
    for record in records:
        lines.extend(["## " + escaped(record["record_id"]), "", t("state") + ": " + t(record["disposition"]),
                      "", "Source: " + escaped(record["source"]["source_id"]) + ", " + t("row") + " " + str(record["source"]["row_number"]) + "; SHA-256 `" + record["source"]["sha256"] + "`.",
                      "", "| " + " | ".join(t(key) for key in ("field", "original", "interpreted", "state")) + " |", "| --- | --- | --- | --- |"])
        fields = [(key, record[key]["original"], record[key]["value"], record[key]["status"]) for key in ("enterprise", "reference", "date")]
        for field, unit_key in (("quantity", "unit"), ("amount", "currency")):
            item = record[field]
            fields.extend([(field, item["original_value"], item["value"], item["status"]), (unit_key, item["original_" + unit_key], item[unit_key], item["status"])])
        for key, original, interpreted, state in fields:
            displayed = number_text(language, interpreted) if key in {"quantity", "amount"} and interpreted is not None else interpreted
            lines.append("| " + " | ".join(escaped(value) for value in (t(key), original if original not in {None, ""} else t("blank"), displayed if displayed is not None else t("not_established"), t(state))) + " |")
        if record["correction_ids"]:
            lines.extend(["", t("corrections") + ": " + escaped(", ".join(record["correction_ids"]))])
        paper = record["original_fields"].get("paper_reference") or record["original_fields"].get("référence_papier")
        if paper:
            lines.extend(["", t("paper_reference") + ": " + escaped(paper)])
        if record["exclusion_reason"]:
            lines.extend(["", escaped(record["exclusion_reason"])])
        lines.extend(["", *["- " + escaped(code) + ": " + escaped(issue_text(language, code)) for code in record["issue_codes"]], ""])
    if history:
        lines.extend(["## " + t("corrections"), ""])
        for item in history:
            lines.append("- " + escaped(item["correction_id"] + " / " + item["record_id"]) + ": " + t(item["status"]) + (" — " + escaped(issue_text(language, item["issue_code"])) if item["issue_code"] else ""))
    return ("\n".join(lines) + "\n").encode("utf-8")
