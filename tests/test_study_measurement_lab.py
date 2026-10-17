"""Independent expected denominators and effort arithmetic from the study rules."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from study_measurement_lab import analyze, main


def dataset():
    return {"synthetic": True, "allocation_rule": "equal_actual_started_comparable_episodes", "time_axis": "shared_synthetic_minute_axis", "groups": [], "episodes": [], "effort": []}


def add_group(data, participant="SYN-P1", condition="P", operation="SYN-F1", overhead_complete=True):
    data["groups"].append(dict(participant=participant, condition=condition, operation=operation, overhead_complete=overhead_complete))


def add_episode(data, identifier, participant="SYN-P1", condition="P", **changes):
    data["episodes"].append({"id": identifier, "participant": participant, "condition": condition,
        "started": True, "outcome": "useful", "assisted": False, "comparable": True,
        "comparison_eligible": True, "is_repeat": True, "effort_complete": True,
        "attempt_ids": [identifier + "-A1"], "pair_id": None, **changes})


def add_effort(data, identifier, episode, start, end, participant="SYN-P1", condition="P", kind="episode", actor="SYN-ACTOR", measurement="timed"):
    data["effort"].append(dict(id=identifier, participant=participant, condition=condition,
        episode_id=episode, start_minute=start, end_minute=end, kind=kind, actor=actor, measurement=measurement))


class StudyMeasurementTests(unittest.TestCase):
    def test_failed_abandoned_and_retry_denominators_keep_all_started_effort(self):
        data = dataset(); add_group(data)
        add_episode(data, "E1", attempt_ids=["E1-A1", "E1-A2"])
        add_episode(data, "E2", outcome="failed", assisted=True)
        add_episode(data, "E3", outcome="abandoned")
        add_episode(data, "E4", started=False, outcome="not_started", attempt_ids=[])
        add_effort(data, "W1", "E1", "0", "10")
        add_effort(data, "W2", "E2", "10", "15")
        add_effort(data, "W3", "E3", "15", "18")
        add_effort(data, "SETUP", None, "18", "24", kind="overhead")
        result = analyze(data); group = result["groups"][0]
        self.assertEqual((group["started_episodes"], group["attempts"], group["useful_completions"]), (3, 4, 1))
        self.assertEqual(group["unassisted_completion_rate"], "1/3")
        self.assertEqual(group["overhead_allocation_denominator"], 3)
        self.assertEqual(result["episodes"]["E1"]["full_person_minutes"], "12")
        self.assertEqual(group["all_attempt_effort_per_useful_result"], "24")
        self.assertEqual(group["not_started_episodes"], 1)

    def test_missing_effort_unknown_overhead_and_measured_zero_do_not_collapse(self):
        data = dataset(); add_group(data); add_episode(data, "ZERO")
        add_effort(data, "W0", "ZERO", "0", "0")
        self.assertEqual(analyze(data)["episodes"]["ZERO"]["full_person_minutes"], "0")
        add_effort(data, "UNKNOWN", "ZERO", None, None, measurement="unavailable")
        result = analyze(data)
        self.assertIsNone(result["episodes"]["ZERO"]["full_person_minutes"])
        self.assertIsNone(result["groups"][0]["all_attempt_effort_per_useful_result"])
        data["effort"].pop(); data["groups"][0]["overhead_complete"] = False
        self.assertIsNone(analyze(data)["episodes"]["ZERO"]["full_person_minutes"])

    def test_same_actor_overlap_refused_but_simultaneous_people_both_count(self):
        data = dataset(); add_group(data); add_episode(data, "E")
        add_effort(data, "W1", "E", "0", "10")
        add_effort(data, "W2", "E", "5", "10", actor="SYN-HELPER")
        self.assertEqual(analyze(data)["episodes"]["E"]["full_person_minutes"], "15")
        data["effort"][1]["actor"] = "SYN-ACTOR"
        with self.assertRaises(ValueError): analyze(data)

    def test_zero_completions_and_no_episodes_keep_cost_without_division(self):
        data = dataset(); add_group(data)
        add_effort(data, "SETUP", None, "0", "6", kind="overhead")
        group = analyze(data)["groups"][0]
        self.assertIsNone(group["overhead_per_comparable_episode"])
        self.assertEqual(group["unallocated_known_overhead"], "6")
        add_episode(data, "FAIL", outcome="failed")
        add_effort(data, "W", "FAIL", "6", "9")
        group = analyze(data)["groups"][0]
        self.assertEqual(group["known_active_person_minutes"], "3")
        self.assertIsNone(group["all_attempt_effort_per_useful_result"])

    def paired_data(self):
        data = dataset()
        for participant, operation, pairs in (("SYN-P1", "SYN-F1", [(10, 5), (10, 5), (10, 5)]), ("SYN-P2", "SYN-F1", [(10, 10)])):
            for condition in ("N", "P"): add_group(data, participant, condition, operation)
            for index, (native, proposed) in enumerate(pairs):
                for condition, duration in (("N", native), ("P", proposed)):
                    identifier = f"{participant}-{condition}-{index}"
                    add_episode(data, identifier, participant, condition, pair_id=str(index))
                    add_effort(data, identifier + "W", identifier, "0", str(duration), participant, condition, actor=identifier + "ACTOR")
        return data

    def test_repeated_pairs_are_summarized_per_person_before_people_median(self):
        result = analyze(self.paired_data())
        self.assertEqual(result["eligible_pairs"], 4)
        self.assertEqual(result["paired_participants"], 2)
        self.assertEqual(result["paired_operations"], 1)
        self.assertEqual(result["participant_median_percent_differences"], {"SYN-P1": "50", "SYN-P2": "0"})
        self.assertEqual(result["median_participant_percent_difference"], "25")
        self.assertEqual(result["decision"], "not_assessed")
        self.assertEqual(result["farmer_benefit"], "not_established")

    def test_estimated_timing_missing_pair_and_zero_baseline_cannot_imply_gain(self):
        data = self.paired_data()
        data["effort"][0]["measurement"] = "estimated"
        data["episodes"][2]["pair_id"] = "UNPAIRED"
        data["effort"][-2]["end_minute"] = "0"
        pairs = analyze(data)["pairs"]
        reasons = {reason for pair in pairs for reason in pair["issues"]}
        self.assertTrue({"timing_unavailable_or_estimated", "unpaired", "native_baseline_zero"} <= reasons)
        self.assertTrue(all(pair["percent_difference"] is None for pair in pairs if pair["issues"]))

    def test_research_burden_and_waiting_are_separate_from_active_task_work(self):
        data = dataset(); add_group(data); add_episode(data, "E")
        add_effort(data, "ACTIVE", "E", "0", "10")
        add_effort(data, "WAIT", None, "0", "20", kind="waiting")
        add_effort(data, "WAIT2", None, "0", "20", kind="waiting", actor="SYN-OTHER")
        add_effort(data, "RESEARCH", None, "20", "25", kind="research")
        result = analyze(data)
        self.assertEqual(result["episodes"]["E"]["full_person_minutes"], "10")
        self.assertEqual(result["waiting_interval_union_known_minutes"], "20")
        self.assertEqual(result["research_burden_known_person_minutes"], "5")
        self.assertEqual(result["end_to_end_elapsed"], "not_observed")

    def test_worked_fixture_exposes_why_paired_gain_does_not_establish_benefit(self):
        data = json.loads((ROOT / "examples/study/synthetic-measurement.json").read_text(encoding="utf-8"))
        result = analyze(data)
        by_condition = {group["condition"]: group for group in result["groups"]}
        self.assertEqual(result["median_participant_percent_difference"], "50")
        self.assertEqual(by_condition["N"]["all_attempt_effort_per_useful_result"], "24")
        self.assertEqual(by_condition["P"]["all_attempt_effort_per_useful_result"], "24")
        self.assertEqual(by_condition["P"]["unassisted_completion_rate"], "0")
        self.assertEqual(by_condition["P"]["started_episodes"], 3)
        self.assertTrue(result["pairs"][0]["assisted"])
        self.assertEqual(result["farmer_benefit"], "not_established")

    def test_duplicate_attempts_effort_and_wrong_episode_links_refused(self):
        data = dataset(); add_group(data); add_episode(data, "E")
        add_effort(data, "W", "E", "0", "1")
        for mutate in (lambda d: d["episodes"][0]["attempt_ids"].append("E-A1"),
                       lambda d: d["effort"].append(deepcopy(d["effort"][0])),
                       lambda d: d["effort"][0].update(episode_id="MISSING")):
            changed = deepcopy(data); mutate(changed)
            with self.assertRaises(ValueError): analyze(changed)

    def test_scope_confirmation_precedes_read_and_cli_rejects_duplicate_json_keys(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("No input read")), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["unread.json"])
        with tempfile.TemporaryDirectory(prefix="ag28-cli-") as directory:
            source = Path(directory) / "invented.json"
            source.write_text('{"synthetic":true,"synthetic":false}', encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr): code = main([str(source), "--confirm-synthetic"])
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(json.loads(stderr.getvalue())["error"], "synthetic_measurement.invalid")


if __name__ == "__main__":
    unittest.main()
