"""Independent integer/rational checks for the existing decimal record engine.

Expected sums and cent rounding never call Decimal or the runtime calculation
helpers. All evidence is synthetic; this is not an accounting-policy review.
"""

import csv
from datetime import datetime, timezone
from fractions import Fraction
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_agriculture.contracts import load_document
from agent_agriculture.errors import PipelineError
from agent_agriculture.pipeline import run
from agent_agriculture.storage import digest, json_bytes, verify_snapshot

NOW = datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc)
HEADERS = ["source_record_id", "reference", "date", "enterprise_id", "supplier", "quantity", "unit", "amount", "currency"]


def exact_scaled_text(value, places, *, round_cents=False):
    """Integer nearest-even rounding; no binary float or Decimal arithmetic."""
    scaled = value * 10 ** places
    sign = -1 if scaled < 0 else 1
    numerator = abs(scaled.numerator)
    whole, remainder = divmod(numerator, scaled.denominator)
    if remainder:
        if not round_cents:
            raise AssertionError("Quantity oracle requires exact input scale")
        doubled = remainder * 2
        if doubled > scaled.denominator or (doubled == scaled.denominator and whole % 2):
            whole += 1
    prefix = "-" if sign < 0 and whole else ""
    if places == 0:
        return prefix + str(whole)
    digits = str(whole).zfill(places + 1)
    return prefix + digits[:-places] + "." + digits[-places:]


class ArithmeticOracleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ag26-arithmetic-")
        self.folder = Path(self.temporary.name).resolve()
        self.counter = 0

    def tearDown(self):
        self.temporary.cleanup()

    def execute(self, amounts, quantities=None, received=None, language="en"):
        self.counter += 1
        case = self.folder / str(self.counter)
        case.mkdir()
        quantities = quantities or ["1"] * len(amounts)
        self.assertEqual(len(quantities), len(amounts))
        if received is not None:
            self.assertEqual(len(received), len(amounts))
        task = load_document(ROOT / "tests/fixtures/cases/en-baseline/task.json")
        task["language"] = language
        manifest = load_document(ROOT / "tests/fixtures/cases/en-baseline/manifest.json")
        if received is None:
            manifest["inputs"] = manifest["inputs"][:1]
            task["permission"]["selected_source_ids"] = ["purchases"]
        originals = {}
        for spec in manifest["inputs"]:
            receipt = spec["record_kind"] == "receiving"
            spec["declared_record_count"] = len(amounts)
            spec["delimiter"] = ";" if language == "fr" else ","
            spec["decimal_separator"] = "," if language == "fr" else "."
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, HEADERS, delimiter=spec["delimiter"], lineterminator="\n")
            writer.writeheader()
            for index, amount in enumerate(amounts):
                quantity = received[index] if receipt else quantities[index]
                row = dict(zip(HEADERS, [f"{'R' if receipt else 'P'}-{index:03d}", f"INV-{index:03d}",
                                         "2026-09-03", "ENT-001", "Invented supplier", quantity,
                                         "kg", "" if receipt else amount, "" if receipt else "CAD"]))
                if language == "fr":
                    row["quantity"] = row["quantity"].replace(".", ",")
                    row["amount"] = row["amount"].replace(".", ",")
                writer.writerow(row)
            raw = output.getvalue().encode("utf-8")
            spec["sha256"] = digest(raw)
            (case / spec["path"]).write_bytes(raw)
            originals[spec["source_id"]] = raw
        (case / "task.json").write_bytes(json_bytes(task))
        (case / "manifest.json").write_bytes(json_bytes(manifest))
        result = run(case / "task.json", case / "manifest.json", case / "runs", now=NOW)
        snapshot = Path(result["path"])
        verify_snapshot(snapshot)
        for source_id, raw in originals.items():
            self.assertEqual((snapshot / "originals" / (source_id + ".csv")).read_bytes(), raw)
        ledger = load_document(snapshot / "calculations.json")
        for calculation in ledger:
            self.check_calculation(calculation)
        return load_document(snapshot / "totals.json"), load_document(snapshot / "normalized-records.json"), ledger

    def check_calculation(self, calculation):
        values = [Fraction(item["value"]) for item in calculation["inputs"]]
        method = calculation["method"]["name"]
        if method == "receiving_minus_purchase":
            exact = values[0] - values[1]
        elif method == "paired_quantity_difference":
            exact = sum((value if item["role"] == "receiving" else -value
                         for value, item in zip(values, calculation["inputs"])), Fraction(0))
        else:
            self.assertEqual(method, "sum")
            exact = sum(values, Fraction(0))
        money = calculation["inputs"][0]["field"] == "amount"
        expected = exact_scaled_text(exact, calculation["precision"], round_cents=money)
        actual = calculation["result"]["value"]
        # Signed zero is a valid Decimal representation; compare its value and scale.
        self.assertEqual(Fraction(actual), Fraction(expected), calculation["calculation_id"])
        self.assertEqual(len(actual.split(".")[1]) if "." in actual else 0, calculation["precision"])
        if Fraction(expected):
            self.assertEqual(actual, expected)

    def test_money_rounds_once_after_summing_positive_and_negative_half_cents(self):
        cases = [(["0.005", "0.005"], "0.01"), (["1.005"], "1.00"), (["1.015"], "1.02"),
                 (["-1.005"], "-1.00"), (["-1.015"], "-1.02"), (["-0.005"], "0.00"),
                 (["-0.005", "-0.005"], "-0.01"), (["1.005", "-1.000"], "0.00")]
        for amounts, expected in cases:
            with self.subTest(amounts=amounts):
                totals, records, _ = self.execute(amounts)
                self.assertEqual(Fraction(totals["included_purchase_amount"]), Fraction(expected))
                self.assertEqual([record["amount"]["value"] for record in records], amounts)

    def test_large_magnitudes_cancellation_and_tiny_terms_do_not_lose_cents(self):
        large = "9" * 60
        for amounts, expected in (([large + ".005", "-" + large + ".000", "0.005"], "0.01"),
                                  ([large + ".99", "0.01"], "1" + "0" * 60 + ".00")):
            with self.subTest(expected=expected):
                totals, _, _ = self.execute(amounts)
                self.assertEqual(totals["included_purchase_amount"], expected)

    def test_quantity_differences_retain_fine_scale_beside_large_magnitudes(self):
        first = "1" + "0" * 40 + ".00000001"
        second = "1" + "0" * 40 + ".00000002"
        tiny = "0.00000001"
        totals, _, ledger = self.execute(["10.00", "20.00"], [first, tiny], [second, "0.00000000"])
        self.assertEqual(totals["difference_receiving_minus_purchase_kg"], "0.00000000")
        differences = [item["result"]["value"] for item in ledger if item["method"]["name"] == "receiving_minus_purchase"]
        self.assertEqual(differences, [tiny, "-" + tiny])
        self.assertEqual(totals["package_status"], "incomplete")

    def test_quantity_scale_beyond_eight_places_refuses_save_without_rounding_evidence(self):
        for places in (9, 35):
            tiny = "0." + "0" * (places - 1) + "1"
            with self.subTest(places=places), self.assertRaises(PipelineError) as caught:
                self.execute(["10.00"], [tiny], ["0." + "0" * places])
            self.assertEqual(caught.exception.code, "contract.calculation")
            self.assertIn("schema.maximum at /precision", str(caught.exception))
            case = self.folder / str(self.counter)
            self.assertFalse((case / "runs").exists())
            manifest = load_document(case / "manifest.json")
            for spec in manifest["inputs"]:
                self.assertEqual(digest((case / spec["path"]).read_bytes()), spec["sha256"])

    def test_input_order_and_french_decimal_convention_do_not_change_value(self):
        amounts = ["123456789012345678901234567890.005", "-123456789012345678901234567890.000", "0.005"]
        results = []
        for language, values in (("en", amounts), ("en", list(reversed(amounts))), ("fr", amounts)):
            totals, _, _ = self.execute(values, language=language)
            results.append(totals["included_purchase_amount"])
        self.assertEqual(results, ["0.01"] * 3)

    def test_nonfinite_exponent_and_grouped_values_cannot_become_confirmed_money(self):
        for amount in ("NaN", "Infinity", "1e3", "1,000.00"):
            with self.subTest(amount=amount):
                totals, records, _ = self.execute([amount])
                self.assertIsNone(totals["included_purchase_amount"])
                self.assertIsNone(totals["raw_purchase_amount_sum"])
                self.assertEqual(records[0]["amount"]["status"], "unresolved")
                self.assertEqual(records[0]["amount"]["original_value"], amount)
                self.assertEqual(totals["package_status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
