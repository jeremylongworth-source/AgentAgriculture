"""Deterministic totals and conservative identity review over normalized evidence."""

from collections import defaultdict
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import re
import unicodedata

from .records import VERSION, decimal_value
from .language import issue_text, text


def _candidate_reference(value):
    return re.sub(r"\W", "", unicodedata.normalize("NFKC", value or "").casefold())


def reconcile(working, records, task, manifest, correction_issues):
    t = lambda key: text(task["language"], key)
    by_id = {record["record_id"]: record for record in records}
    raw_by_id = {record.record_id: record for record in working}
    ledger, exceptions = [], []

    def exception(code, ids=(), details=None):
        item = {"exception_id": f"EX-{len(exceptions)+1:04d}", "code": code,
                "record_ids": list(ids), "details": details or {}}
        exceptions.append(item)
        return item

    for issue in correction_issues:
        exception(issue["code"], issue["record_ids"], {"correction_ids": issue["correction_ids"]})
    for source in manifest["inputs"]:
        if source["completeness"] != "complete":
            exception("export.partial" if source["completeness"] == "partial" else "export.unknown", details={"source_id": source["source_id"], "omitted_sections": source["omitted_sections"], "filters": source["filters"]})
    for record in records:
        if record["disposition"] != "excluded":
            for code in record["issue_codes"]:
                exception(code, [record["record_id"]])

    candidates = defaultdict(list)
    for record in records:
        if record["kind"] == "purchase" and record["disposition"] != "excluded" and record["reference"]["value"]:
            supplier = raw_by_id[record["record_id"]].values["supplier"] or ""
            key = (_candidate_reference(record["reference"]["value"]), record["enterprise"]["value"], unicodedata.normalize("NFKC", supplier).casefold().strip())
            candidates[key].append(record["record_id"])
    duplicate_ids = set()
    for ids in candidates.values():
        if len(ids) > 1:
            duplicate_ids.update(ids)
            exception("identity.possible_duplicate", ids, {"decision": issue_text(task["language"], "identity.possible_duplicate")})
            for record_id in ids:
                record = by_id[record_id]
                record["issue_codes"] = sorted(set(record["issue_codes"] + ["identity.possible_duplicate"]))
                record["disposition"] = "unresolved"

    def scoped(record):
        return record["source"].get("identity_status") != "provisional" and record["enterprise"]["status"] == "confirmed" and record["enterprise"]["value"] == task["enterprise_id"] and record["date"]["status"] == "confirmed" and task["reporting_period"]["start"] <= record["date"]["value"] <= task["reporting_period"]["end"] and record["reference"]["status"] == "confirmed" and not any(code.startswith("correction.") or code == "export.period_mismatch" for code in record["issue_codes"])

    def calc(identifier, entries, field, unit, *, method="sum", assumptions=(), status="checked", original=False):
        if not entries:
            return None
        inputs = []
        values = []
        for record in entries:
            if original:
                source = raw_by_id[record["record_id"]]
                value, _ = decimal_value(source.original_values[field], source.spec["decimal_separator"])
                record_version = 1
            else:
                value = record[field]["value"]
                record_version = record["version"]
            values.append(Decimal(value))
            inputs.append({"record_id": record["record_id"], "record_version": record_version, "field": field, "value": value, "unit": unit, "source": record["source"], "role": record["kind"]})
        with localcontext() as context:
            context.prec = max(28, sum(len(value.as_tuple().digits) + abs(value.as_tuple().exponent) for value in values) + 8)
            if method == "paired_quantity_difference":
                result = sum((value if entry["role"] == "receiving" else -value for value, entry in zip(values, inputs)), Decimal(0))
            else:
                result = values[0] - values[1] if method == "receiving_minus_purchase" else sum(values, Decimal(0))
            precision = 2 if field == "amount" else max(0, max(-value.as_tuple().exponent for value in values))
            result = result.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_EVEN)
            result_text = format(result, f".{precision}f")
        ledger.append({"schema_version": VERSION, "calculation_id": identifier, "task_id": task["task_id"],
                       "method": {"name": method, "version": VERSION}, "inputs": inputs,
                       "formula": "sum(receiving) - sum(purchase)" if method == "paired_quantity_difference" else (" - " if method == "receiving_minus_purchase" else " + ").join(item["value"] for item in inputs),
                       "result": {"value": result_text, "unit": unit}, "precision": precision,
                       "rounding": "ROUND_HALF_EVEN" if field == "amount" else "none", "assumptions": list(assumptions), "status": status,
                       "dependent_output_refs": ["totals.json/" + identifier, "summary.md"]})
        return result_text

    purchases = [record for record in records if record["kind"] == "purchase"]
    raw_currency_rows = defaultdict(list)
    for record in purchases:
        source = raw_by_id[record["record_id"]]
        value, status = decimal_value(source.original_values["amount"], source.spec["decimal_separator"])
        currency = source.original_values["currency"]
        if status == "confirmed" and currency and re.fullmatch("[A-Z]{3}", currency):
            raw_currency_rows[currency].append(record)
    raw_sums = {currency: calc("raw-purchase-" + currency, entries, "amount", currency, original=True,
                             assumptions=[t("raw_scope")])
                for currency, entries in sorted(raw_currency_rows.items())}
    excluded = [r for r in purchases if r["disposition"] == "excluded" and r["amount"]["status"] == "confirmed" and r["amount"]["currency"] == task["currency"]]
    included = [r for r in purchases if r["disposition"] != "excluded"]
    if not included:
        exception("scope.no_included_purchase", details={"scope": issue_text(task["language"], "scope.no_included_purchase")})
    eligible = [r for r in included if scoped(r) and r["record_id"] not in duplicate_ids and r["amount"]["status"] == "confirmed" and r["amount"]["currency"] == task["currency"]]
    complete_purchases = bool(purchases) and all(source["completeness"] == "complete" and source["declared_period"] == task["reporting_period"] for source in manifest["inputs"] if source["record_kind"] == "purchase")
    monetary_complete = complete_purchases and bool(eligible) and len(eligible) == len(included) and not correction_issues
    known_amount = calc("known-scoped-purchase-amount", eligible, "amount", task["currency"],
                       status="checked" if monetary_complete else "incomplete",
                       assumptions=[t("assumption.purchase"), t("assumption.fields")])
    excluded_amount = calc("excluded-purchase-amount", excluded, "amount", task["currency"], assumptions=[t("assumption.excluded")])

    matching = defaultdict(lambda: {"purchase": [], "receiving": []})
    for record in records:
        if record["disposition"] != "excluded" and scoped(record) and record["record_id"] not in duplicate_ids:
            supplier = raw_by_id[record["record_id"]].values["supplier"]
            matching[(record["reference"]["value"], supplier)][record["kind"]].append(record)
    purchase_pairs, receipt_pairs, discrepancies = [], [], []
    for pair in matching.values():
        if len(pair["purchase"]) != 1 or len(pair["receiving"]) != 1:
            if any(source["record_kind"] == "receiving" for source in manifest["inputs"]):
                exception("identity.ambiguous_match" if max(len(pair["purchase"]), len(pair["receiving"])) > 1 else "record.unmatched", [r["record_id"] for values in pair.values() for r in values])
            continue
        purchase, receipt = pair["purchase"][0], pair["receiving"][0]
        if any(record["quantity"]["status"] != "confirmed" or record["quantity"]["unit"] != "kg" for record in (purchase, receipt)):
            continue
        purchase_pairs.append(purchase)
        receipt_pairs.append(receipt)
        if Decimal(purchase["quantity"]["value"]) != Decimal(receipt["quantity"]["value"]):
            identifier = f"quantity-difference-{len(discrepancies)+1:04d}"
            difference = calc(identifier, [receipt, purchase], "quantity", "kg", method="receiving_minus_purchase",
                              assumptions=[t("assumption.pair")])
            item = {"purchase_id": purchase["record_id"], "receiving_id": receipt["record_id"], "value": difference, "unit": "kg", "calculation_id": identifier}
            discrepancies.append(item)
            exception("quantity.discrepancy", [purchase["record_id"], receipt["record_id"]], item)
    purchased_kg = calc("comparable-purchase-kg", purchase_pairs, "quantity", "kg", assumptions=[t("assumption.kg")])
    received_kg = calc("comparable-receiving-kg", receipt_pairs, "quantity", "kg", assumptions=[t("assumption.receiving")])
    difference_kg = None
    if purchased_kg is not None and received_kg is not None:
        difference_kg = calc("comparable-difference-kg", receipt_pairs + purchase_pairs, "quantity", "kg", method="paired_quantity_difference", assumptions=[t("assumption.pair")])
    unallocated = [r["record_id"] for r in records if r["disposition"] != "excluded" and r["quantity"]["status"] != "confirmed"]
    totals = {"schema_version": VERSION, "currency": task["currency"], "basis": task["transaction_basis"],
              "raw_purchase_amount_sum": raw_sums.get(task["currency"]), "raw_amount_sums_by_currency": raw_sums,
              "raw_amount_scope": t("raw_scope"),
              "included_purchase_amount": known_amount if monetary_complete else None, "known_scoped_purchase_amount": known_amount,
              "excluded_purchase_amount": excluded_amount, "monetary_scope_complete": monetary_complete,
              "comparable_purchase_kg": purchased_kg, "comparable_receiving_kg": received_kg,
              "difference_receiving_minus_purchase_kg": difference_kg, "unallocated_quantity_records": unallocated,
              "discrepancies": discrepancies, "package_status": "incomplete" if exceptions else "ready_for_review",
              "calculation_refs": {"raw_amount_sums_by_currency": {currency: "raw-purchase-" + currency for currency in raw_sums},
                                   "included_purchase_amount": "known-scoped-purchase-amount" if monetary_complete and known_amount is not None else None,
                                   "known_scoped_purchase_amount": "known-scoped-purchase-amount" if known_amount is not None else None,
                                   "excluded_purchase_amount": "excluded-purchase-amount" if excluded_amount is not None else None,
                                   "comparable_purchase_kg": "comparable-purchase-kg" if purchased_kg is not None else None,
                                   "comparable_receiving_kg": "comparable-receiving-kg" if received_kg is not None else None,
                                   "difference_receiving_minus_purchase_kg": "comparable-difference-kg" if difference_kg is not None else None}}
    return totals, ledger, exceptions
