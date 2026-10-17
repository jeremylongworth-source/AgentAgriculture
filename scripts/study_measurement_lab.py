"""Synthetic-only study measurement arithmetic; no participant intake or decisions."""

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from statistics import median
import sys

CONDITIONS = {"C", "N", "P"}
OUTCOMES = {"useful", "failed", "abandoned", "refused", "unknown", "not_started"}


def number(value):
    if not isinstance(value, str) or not value or any(c not in "0123456789.-" for c in value):
        raise ValueError("Durations require explicit decimal strings")
    return Fraction(value)


def render(value):
    return None if value is None else str(value)


def analyze(data):
    if data.get("synthetic") is not True or data.get("allocation_rule") != "equal_actual_started_comparable_episodes" or data.get("time_axis") != "shared_synthetic_minute_axis":
        raise ValueError("Explicit synthetic scope and allocation rule required")
    groups, operations = {}, {}
    for group in data["groups"]:
        key = (group["participant"], group["condition"])
        if key in groups or key[1] not in CONDITIONS or type(group["overhead_complete"]) is not bool:
            raise ValueError("Unique declared groups/conditions and completeness required")
        if key[0] in operations and operations[key[0]] != group["operation"]:
            raise ValueError("Participant operation identity conflicts")
        operations[key[0]] = group["operation"]
        groups[key] = group
    episodes, attempts = {}, set()
    for episode in data["episodes"]:
        key = (episode["participant"], episode["condition"])
        if episode["id"] in episodes or key not in groups or episode["outcome"] not in OUTCOMES:
            raise ValueError("Unique episode, declared group and explicit outcome required")
        for flag in ("started", "assisted", "comparable", "comparison_eligible", "is_repeat", "effort_complete"):
            if type(episode[flag]) is not bool:
                raise ValueError("Explicit episode flags required")
        if episode["started"] == (episode["outcome"] == "not_started") or bool(episode["attempt_ids"]) != episode["started"]:
            raise ValueError("Start/outcome/attempt records disagree")
        for identifier in episode["attempt_ids"]:
            if identifier in attempts:
                raise ValueError("Attempt IDs cannot count twice")
            attempts.add(identifier)
        episodes[episode["id"]] = episode
    active, overhead = defaultdict(Fraction), defaultdict(Fraction)
    estimated_episode, estimated_setup, missing_episode, missing_setup = set(), set(), set(), set()
    actor_intervals, effort_ids = defaultdict(list), set()
    research, waiting = Fraction(0), Fraction(0)
    waiting_intervals = []
    research_unknown = waiting_unknown = 0
    for row in data["effort"]:
        key = (row["participant"], row["condition"])
        if row["id"] in effort_ids or key not in groups:
            raise ValueError("Unique effort and declared group required")
        effort_ids.add(row["id"])
        kind, state, episode_id = row["kind"], row["measurement"], row["episode_id"]
        if kind not in {"episode", "overhead", "research", "waiting"} or state not in {"timed", "estimated", "unavailable"}:
            raise ValueError("Explicit effort kind and measurement state required")
        if kind == "episode":
            if episode_id not in episodes or not episodes[episode_id]["started"] or key != (episodes[episode_id]["participant"], episodes[episode_id]["condition"]):
                raise ValueError("Effort must reference its started episode/group")
        elif episode_id is not None:
            raise ValueError("Non-episode rows cannot be allocated twice through an episode")
        if state == "unavailable":
            if row["start_minute"] is not None or row["end_minute"] is not None:
                raise ValueError("Unavailable duration cannot contain an observed interval")
            if kind == "episode": missing_episode.add(episode_id)
            elif kind == "overhead": missing_setup.add(key)
            elif kind == "research": research_unknown += 1
            else: waiting_unknown += 1
            continue
        start, end = number(row["start_minute"]), number(row["end_minute"])
        if start < 0 or end < start:
            raise ValueError("Valid nonnegative interval required")
        duration = end - start
        if kind != "waiting":
            actor_intervals[row["actor"]].append((start, end, row["id"]))
        if kind == "episode":
            active[episode_id] += duration
            if state == "estimated": estimated_episode.add(episode_id)
        elif kind == "overhead":
            overhead[key] += duration
            if state == "estimated": estimated_setup.add(key)
        elif kind == "research": research += duration
        else: waiting_intervals.append((start, end))
    for intervals in actor_intervals.values():
        previous_end = None
        for start, end, identifier in sorted(intervals):
            if start == end:
                continue
            if previous_end is not None and start < previous_end:
                raise ValueError("Same-actor effort overlaps; allocate with a reason before analysis")
            previous_end = end
    # Waiting is elapsed time on the declared shared fixture clock, not summed
    # person-minutes. Concurrent waiting by two people must not double it.
    waiting_end = None
    for start, end in sorted(waiting_intervals):
        if waiting_end is None or start > waiting_end:
            waiting += end - start
        elif end > waiting_end:
            waiting += end - waiting_end
        waiting_end = max(waiting_end, end) if waiting_end is not None else end
    group_results, episode_results = [], {}
    for key, group in sorted(groups.items()):
        selected = [episode for episode in episodes.values() if (episode["participant"], episode["condition"]) == key]
        started = [episode for episode in selected if episode["started"]]
        comparable = [episode for episode in started if episode["comparable"]]
        setup_known = group["overhead_complete"] and key not in missing_setup
        allocation = overhead[key] / len(comparable) if setup_known and comparable else None
        complete_effort = setup_known and all(episode["effort_complete"] and episode["id"] not in missing_episode for episode in started)
        known_active = sum((active[episode["id"]] for episode in started), Fraction(0))
        useful = sum(episode["outcome"] == "useful" for episode in started)
        unassisted = sum(episode["outcome"] == "useful" and not episode["assisted"] for episode in started)
        for episode in selected:
            full = active[episode["id"]] + allocation if episode["started"] and episode["comparable"] and allocation is not None and episode["effort_complete"] and episode["id"] not in missing_episode else None
            episode_results[episode["id"]] = {"known_active_person_minutes": render(active[episode["id"]]),
                "allocated_overhead_person_minutes": render(allocation if episode["started"] and episode["comparable"] else None),
                "full_person_minutes": render(full), "timed_comparison_available": full is not None and episode["id"] not in estimated_episode and key not in estimated_setup}
        group_results.append({"participant": key[0], "operation": group["operation"], "condition": key[1],
            "started_episodes": len(started), "not_started_episodes": len(selected) - len(started),
            "attempts": sum(len(episode["attempt_ids"]) for episode in started),
            "useful_completions": useful, "unassisted_useful_completions": unassisted,
            "assisted_episodes": sum(episode["assisted"] for episode in started),
            "outcomes": dict(sorted(Counter(episode["outcome"] for episode in selected).items())),
            "unassisted_completion_rate": render(Fraction(unassisted, len(started))) if started else None,
            "known_active_person_minutes": render(known_active), "known_overhead_person_minutes": render(overhead[key]),
            "overhead_allocation_denominator": len(comparable), "overhead_per_comparable_episode": render(allocation),
            "unallocated_known_overhead": render(overhead[key] if not comparable else Fraction(0)),
            "effort_complete": complete_effort,
            "all_attempt_effort_per_useful_result": render((known_active + overhead[key]) / useful) if complete_effort and useful else None})
    candidate_pairs = defaultdict(dict)
    for episode in episodes.values():
        if episode.get("pair_id") and episode["condition"] in {"N", "P"}:
            key = (episode["participant"], episode["pair_id"])
            if episode["condition"] in candidate_pairs[key]:
                raise ValueError("A paired comparison cannot silently pool duplicate condition episodes")
            candidate_pairs[key][episode["condition"]] = episode
    pairs, participant_gains = [], defaultdict(list)
    for key, conditions in sorted(candidate_pairs.items()):
        reasons = []
        if set(conditions) != {"N", "P"}: reasons.append("unpaired")
        for episode in conditions.values():
            if not (episode["started"] and episode["comparable"] and episode["comparison_eligible"] and episode["is_repeat"] and episode["outcome"] == "useful"):
                reasons.append("episode_ineligible_or_incomplete")
            if not episode_results[episode["id"]]["timed_comparison_available"]:
                reasons.append("timing_unavailable_or_estimated")
        native = Fraction(episode_results[conditions["N"]["id"]]["full_person_minutes"]) if not reasons else None
        proposed = Fraction(episode_results[conditions["P"]["id"]]["full_person_minutes"]) if not reasons else None
        gain = 100 * (native - proposed) / native if native is not None and native > 0 else None
        if not reasons and native == 0: reasons.append("native_baseline_zero")
        if gain is not None: participant_gains[key[0]].append(gain)
        pairs.append({"participant": key[0], "pair_id": key[1], "native_full_minutes": render(native),
                      "proposed_full_minutes": render(proposed), "percent_difference": render(gain),
                      "assisted": any(episode["assisted"] for episode in conditions.values()), "issues": sorted(set(reasons))})
    participant_medians = {participant: median(values) for participant, values in sorted(participant_gains.items())}
    values = list(participant_medians.values())
    return {"synthetic": True, "decision": "not_assessed", "farmer_benefit": "not_established",
            "number_format": "exact rational person-minute and percentage strings",
            "groups": group_results, "episodes": episode_results, "pairs": pairs,
            "paired_participants": len(values), "paired_operations": len({operations[p] for p in participant_medians}),
            "eligible_pairs": sum(len(items) for items in participant_gains.values()),
            "participant_median_percent_differences": {key: render(value) for key, value in participant_medians.items()},
            "median_participant_percent_difference": render(median(values)) if values else None,
            "participant_percent_range": [render(min(values)), render(max(values))] if values else None,
            "research_burden_known_person_minutes": render(research), "research_unknown_rows": research_unknown,
            "waiting_interval_union_known_minutes": render(waiting), "waiting_unknown_rows": waiting_unknown,
            "end_to_end_elapsed": "not_observed"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if not args.confirm_synthetic:
        parser.error("Confirm synthetic input before reading it")
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        if not isinstance(data, dict):
            raise ValueError("Expected a synthetic object")
        print(json.dumps(analyze(data), ensure_ascii=False, sort_keys=True, indent=2))
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError):
        print(json.dumps({"error": "synthetic_measurement.invalid", "message": "Inspect synthetic scope, declarations, identities, intervals and missing states; no result confirmed."}), file=sys.stderr)
        return 2
    return 0


def unique_object(items):
    result = {}
    for key, value in items:
        if key in result: raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


if __name__ == "__main__":
    raise SystemExit(main())
