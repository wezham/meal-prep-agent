#!/usr/bin/env python3
"""Meal prep memory helper for the meal-prep-agent plugin."""

from __future__ import annotations

import argparse
import os
import datetime as dt
import json
import pathlib
import re
import shutil
import sys
from typing import Any


PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_ROOT = PLUGIN_ROOT / "data"
PROFILE_TEMPLATE_PATH = DATA_ROOT / "profile.template.json"
HISTORY_TEMPLATE_PATH = DATA_ROOT / "history.template.json"
DEFAULT_RUNTIME_DATA_DIR = DATA_ROOT / "local"


def runtime_data_dir() -> pathlib.Path:
    configured = os.environ.get("MEAL_PREP_AGENT_DATA_DIR")
    if configured:
        return pathlib.Path(configured).expanduser().resolve()
    return DEFAULT_RUNTIME_DATA_DIR


def profile_path() -> pathlib.Path:
    return runtime_data_dir() / "profile.json"


def history_path() -> pathlib.Path:
    return runtime_data_dir() / "history.json"


def initialize_runtime_files(overwrite: bool = False) -> dict[str, str]:
    paths = {
        "profile_path": profile_path(),
        "history_path": history_path(),
    }
    templates = {
        "profile_path": PROFILE_TEMPLATE_PATH,
        "history_path": HISTORY_TEMPLATE_PATH,
    }

    for key, destination in paths.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if overwrite or not destination.exists():
            shutil.copyfile(templates[key], destination)

    return {key: str(path) for key, path in paths.items()}


def read_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "generated_plans": []}

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")

    data.setdefault("version", 1)
    data.setdefault("generated_plans", [])
    return data


def write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def tokens(values: list[str]) -> set[str]:
    joined = " ".join(values).lower()
    return {part for part in re.split(r"[^a-z0-9]+", joined) if len(part) > 2}


def collect_strings(plan: dict[str, Any], key: str) -> list[str]:
    values: list[str] = []
    for recipe in plan.get("recipes", []):
        raw = recipe.get(key, [])
        if isinstance(raw, list):
            values.extend(str(item) for item in raw)
        elif raw:
            values.append(str(raw))

    for meal_group in ("lunches", "dinners"):
        for meal in plan.get(meal_group, []):
            raw = meal.get(key, [])
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
            elif raw:
                values.append(str(raw))

    raw_top_level = plan.get(key, [])
    if isinstance(raw_top_level, list):
        values.extend(str(item) for item in raw_top_level)
    elif raw_top_level:
        values.append(str(raw_top_level))

    return values


def meal_names(plan: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for recipe in plan.get("recipes", []):
        name = recipe.get("name")
        if name:
            names.append(str(name))

    for meal_group in ("lunches", "dinners"):
        for meal in plan.get(meal_group, []):
            name = meal.get("name") or meal.get("recipe_name")
            if name:
                names.append(str(name))
    return list(dict.fromkeys(names))


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def summarize_history(limit: int) -> None:
    initialize_runtime_files()
    active_history_path = history_path()
    history = read_json(active_history_path)
    plans = history.get("generated_plans", [])
    if not isinstance(plans, list):
        raise ValueError("history.generated_plans must be a list")

    recent = plans[-limit:]
    summary = {
        "profile_path": str(profile_path()),
        "history_path": str(active_history_path),
        "total_plans": len(plans),
        "recent_plan_count": len(recent),
        "recent_meal_names": [],
        "recent_core_ingredients": [],
        "recent_cuisine_tags": [],
        "avoidance_guidance": "Prefer different primary proteins, sauce profiles, and cuisine tags from recent plans.",
    }

    ingredient_seen: set[str] = set()
    cuisine_seen: set[str] = set()

    for plan in recent:
        summary["recent_meal_names"].extend(meal_names(plan))
        for ingredient in collect_strings(plan, "core_ingredients"):
            key = ingredient.lower()
            if key not in ingredient_seen:
                ingredient_seen.add(key)
                summary["recent_core_ingredients"].append(ingredient)
        for cuisine in collect_strings(plan, "cuisine_tags"):
            key = cuisine.lower()
            if key not in cuisine_seen:
                cuisine_seen.add(key)
                summary["recent_cuisine_tags"].append(cuisine)

    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


def append_plan(plan_file: pathlib.Path) -> None:
    initialize_runtime_files()
    active_history_path = history_path()
    history = read_json(active_history_path)
    plans = history.get("generated_plans", [])
    if not isinstance(plans, list):
        raise ValueError("history.generated_plans must be a list")

    with plan_file.open("r", encoding="utf-8") as handle:
        plan = json.load(handle)

    if not isinstance(plan, dict):
        raise ValueError("accepted plan must be a JSON object")

    plan.setdefault("generated_at", dt.datetime.now(dt.timezone.utc).isoformat())
    plan.setdefault("core_ingredients", collect_strings(plan, "core_ingredients"))
    plan.setdefault("cuisine_tags", collect_strings(plan, "cuisine_tags"))

    plans.append(plan)
    history["generated_plans"] = plans
    write_json(active_history_path, history)

    print(json.dumps({"saved": True, "history_path": str(active_history_path), "total_plans": len(plans)}, indent=2))


def compare_plan(plan_file: pathlib.Path, limit: int) -> None:
    initialize_runtime_files()
    history = read_json(history_path())
    plans = history.get("generated_plans", [])
    if not isinstance(plans, list):
        raise ValueError("history.generated_plans must be a list")

    with plan_file.open("r", encoding="utf-8") as handle:
        plan = json.load(handle)

    candidate_tokens = tokens(
        meal_names(plan)
        + collect_strings(plan, "core_ingredients")
        + collect_strings(plan, "cuisine_tags")
    )

    comparisons: list[dict[str, Any]] = []
    for prior in plans[-limit:]:
        prior_tokens = tokens(
            meal_names(prior)
            + collect_strings(prior, "core_ingredients")
            + collect_strings(prior, "cuisine_tags")
        )
        comparisons.append(
            {
                "generated_at": prior.get("generated_at"),
                "meal_names": meal_names(prior),
                "similarity": round(similarity(candidate_tokens, prior_tokens), 3),
            }
        )

    json.dump({"candidate_vs_recent": comparisons}, sys.stdout, indent=2)
    sys.stdout.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage meal-prep-agent memory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create private runtime profile and history files from templates.")
    init_parser.add_argument("--overwrite", action="store_true", help="Replace existing runtime files with templates.")

    subparsers.add_parser("paths", help="Print active profile and history paths.")

    summary_parser = subparsers.add_parser("summary", help="Print compact repeat-avoidance context.")
    summary_parser.add_argument("--limit", type=int, default=8)

    append_parser = subparsers.add_parser("append-plan", help="Append an accepted plan to history.")
    append_parser.add_argument("--plan-file", required=True, type=pathlib.Path)

    compare_parser = subparsers.add_parser("compare-plan", help="Compare a candidate plan to recent history.")
    compare_parser.add_argument("--plan-file", required=True, type=pathlib.Path)
    compare_parser.add_argument("--limit", type=int, default=8)

    args = parser.parse_args()

    if args.command == "init":
        json.dump(initialize_runtime_files(overwrite=args.overwrite), sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.command == "paths":
        json.dump(
            {
                "profile_path": str(profile_path()),
                "history_path": str(history_path()),
                "data_dir": str(runtime_data_dir()),
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    elif args.command == "summary":
        summarize_history(args.limit)
    elif args.command == "append-plan":
        append_plan(args.plan_file)
    elif args.command == "compare-plan":
        compare_plan(args.plan_file, args.limit)
    else:
        parser.error(f"unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
