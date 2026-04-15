"""CLI entrypoints for eval framework.

Invocation:
  python -m wwai_agent_orchestration.evals <command> [args]
  python -m wwai_agent_orchestration.evals.cli <command> [args]

Global args (apply to all commands):
  --store {local,mongo}     Storage backend (default: local)
  --local-store-dir DIR     Dir for local JSONL store (default: .evals_local)
  --mongo-uri URI           Mongo connection string (when store=mongo)
  --db-name NAME            Mongo db name (default: eval)

Commands and args:

  build-set
    Build an eval set from config.
    --eval-set-id ID        Required. Unique set identifier.
    --eval-type TYPE        Required. landing_page | template_selection | section_coverage | color_palette
    --version V             Version string (default: v1)
    --seed N                Random seed (default: 42)
    --business-ids ID1,ID2  Comma-separated business IDs, or omit to fetch from pipeline
    --middle-section-count N  For section_coverage only (default: 3)
    --section-filter JSON   For section_coverage: MongoDB filter (e.g. '{"status":"ACTIVE","tag":"smb"}')
    --preset-template-id ID For color_palette: preset template (default: default)
    --max-cases N           Cap eval set to first N cases (optional)
    --output-json PATH      Write eval set JSON to file
    --save-store            Persist eval set to store

  run-set
    Run an eval set (build or load from JSON).
    --eval-set-json PATH    Load eval set from JSON (skips build)
    --eval-set-id ID        Required if not using --eval-set-json
    --eval-type TYPE        landing_page | template_selection | section_coverage | color_palette
    --version, --seed, --business-ids, --middle-section-count, --section-filter, --max-cases  Same as build-set
    --max-concurrency N     Parallel cases (default: 4)
    --max-attempts N        Retries per case (default: 1)
    --enable-judge          Run LLM-as-judge after completion
    --dry-run               Skip execution, return summary with 0 completed/failed

  resume
    Re-run failed/running cases for an existing eval set.
    --eval-set-id ID        Required. Must exist in store.
    --max-concurrency N     Parallel cases (default: 4)
    --max-attempts N        Retries per case (default: 1)
    --enable-judge          Run judge on resumed runs
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline import fetch_business_ids
from wwai_agent_orchestration.evals.sets.factory import build_eval_set
from wwai_agent_orchestration.evals.entrypoints import (
    resume_eval_set_entrypoint,
    run_async,
    run_eval_set_entrypoint,
)
from wwai_agent_orchestration.evals.stores.local_jsonl_store import LocalJsonlEvalStore
from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def _resolve_store(args):
    if args.store == "mongo":
        return MongoEvalStore(mongo_uri=args.mongo_uri, db_name=args.db_name)
    return LocalJsonlEvalStore(root_dir=Path(args.local_store_dir))


def _resolve_business_ids(args) -> List[str]:
    if args.business_ids:
        return [value.strip() for value in args.business_ids.split(",") if value.strip()]
    return fetch_business_ids.fetch_eval_business_ids(mongo_uri=args.mongo_uri)


def _resolve_section_query_filter(args) -> Optional[Dict[str, Any]]:
    """Parse --section-filter JSON when eval_type is section_coverage."""
    if getattr(args, "section_filter", None) is None:
        return None
    try:
        return json.loads(args.section_filter)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid --section-filter JSON: {e}") from e


def cmd_build_set(args):
    kwargs = {
        "eval_set_id": args.eval_set_id,
        "eval_type": args.eval_type,
        "version": args.version,
        "seed": args.seed,
        "business_ids": _resolve_business_ids(args),
        "middle_section_count": args.middle_section_count,
        "max_cases": getattr(args, "max_cases", None),
    }
    if args.eval_type == "section_coverage":
        kwargs["section_query_filter"] = _resolve_section_query_filter(args)
    if args.eval_type == "color_palette":
        kwargs["preset_template_id"] = getattr(args, "preset_template_id", "default")
        palette_ids_str = getattr(args, "palette_ids", None)
        if palette_ids_str:
            kwargs["palette_ids"] = [p.strip() for p in palette_ids_str.split(",") if p.strip()]
    if args.eval_type == "curated_pages":
        kwargs["homepage_generation_version_id"] = getattr(args, "homepage_generation_version_id", None) or ""
        paths_str = getattr(args, "curated_page_paths", None)
        kwargs["curated_page_paths"] = (
            [p.strip() for p in paths_str.split(",") if p.strip()] if paths_str else None
        )
    eval_set = build_eval_set(**kwargs)
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(eval_set.model_dump(mode="json"), indent=2))
    if args.save_store:
        _resolve_store(args).save_eval_set(eval_set)
    print(json.dumps({"eval_set_id": eval_set.eval_set_id, "total_cases": len(eval_set.cases)}))


def _load_or_build_eval_set(args) -> EvalSet:
    if args.eval_set_json:
        payload = json.loads(Path(args.eval_set_json).read_text())
        return EvalSet.model_validate(payload)
    kwargs = {
        "eval_set_id": args.eval_set_id,
        "eval_type": args.eval_type,
        "version": args.version,
        "seed": args.seed,
        "business_ids": _resolve_business_ids(args),
        "middle_section_count": args.middle_section_count,
        "max_cases": getattr(args, "max_cases", None),
    }
    if args.eval_type == "section_coverage":
        kwargs["section_query_filter"] = _resolve_section_query_filter(args)
    if args.eval_type == "color_palette":
        kwargs["preset_template_id"] = getattr(args, "preset_template_id", "default")
        palette_ids_str = getattr(args, "palette_ids", None)
        if palette_ids_str:
            kwargs["palette_ids"] = [p.strip() for p in palette_ids_str.split(",") if p.strip()]
    if args.eval_type == "curated_pages":
        kwargs["homepage_generation_version_id"] = getattr(args, "homepage_generation_version_id", None) or ""
        paths_str = getattr(args, "curated_page_paths", None)
        kwargs["curated_page_paths"] = (
            [p.strip() for p in paths_str.split(",") if p.strip()] if paths_str else None
        )
    return build_eval_set(**kwargs)


def cmd_run_set(args):
    eval_set = _load_or_build_eval_set(args)
    summary = run_async(
        run_eval_set_entrypoint(
            eval_set=eval_set,
            store=_resolve_store(args),
            max_concurrency=args.max_concurrency,
            max_attempts=args.max_attempts,
            enable_judge=args.enable_judge,
            dry_run=args.dry_run,
            dump_output_dir=getattr(args, "dump_output_dir", None),
        )
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, default=str))


def cmd_resume(args):
    store = _resolve_store(args)
    eval_set_id = args.eval_set_id

    # Print progress summary before resume
    try:
        s = store.get_eval_set_summary(eval_set_id)
        total = s.get("total", 0)
        completed = s.get("completed", 0)
        failed = s.get("failed", 0)
        running = s.get("running", 0)
        progress_pct = s.get("progress_pct", 0.0)
        to_resume = failed + running

        print(f"Eval set: {eval_set_id}")
        print(f"  Total:     {total}")
        print(f"  Completed: {completed}")
        print(f"  Failed:   {failed}")
        running_suffix = "  (interrupted)" if running > 0 else ""
        print(f"  Running:  {running}{running_suffix}")
        print(f"  Progress: {progress_pct:.1f}%")
        if to_resume > 0:
            print(f"  Resuming: {to_resume} cases ({failed} failed, {running} running)")
        else:
            print("  All cases completed, nothing to resume")
        print()
    except Exception:
        pass  # Proceed even if summary fails (e.g. eval set not found yet)

    summary = run_async(
        resume_eval_set_entrypoint(
            eval_set_id=eval_set_id,
            store=store,
            max_concurrency=args.max_concurrency,
            max_attempts=args.max_attempts,
            enable_judge=args.enable_judge,
            dump_output_dir=getattr(args, "dump_output_dir", None),
        )
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evals-cli")
    parser.add_argument("--store", choices=["local", "mongo"], default="local")
    parser.add_argument("--local-store-dir", default=".evals_local")
    parser.add_argument(
        "--mongo-uri",
        default=os.environ.get("MONGO_CONNECTION_URI", "mongodb://localhost:27017/"),
    )
    parser.add_argument("--db-name", default="eval")

    subparsers = parser.add_subparsers(dest="command", required=True)

    build_set = subparsers.add_parser("build-set")
    build_set.add_argument("--eval-set-id", required=True)
    build_set.add_argument(
        "--eval-type",
        required=True,
        choices=["landing_page", "template_selection", "section_coverage", "color_palette", "curated_pages"],
    )
    build_set.add_argument("--version", default="v1")
    build_set.add_argument("--seed", type=int, default=42)
    build_set.add_argument("--business-ids")
    build_set.add_argument("--middle-section-count", type=int, default=3)
    build_set.add_argument(
        "--section-filter",
        help="JSON MongoDB filter for section_coverage (e.g. '{\"status\":\"ACTIVE\",\"tag\":\"smb\"}')",
    )
    build_set.add_argument(
        "--preset-template-id",
        default="default",
        help="For color_palette: preset template (default: default)",
    )
    build_set.add_argument(
        "--palette-ids",
        help="For color_palette: comma-separated palette IDs (e.g. friendly-1,bold-2). If set, only these palettes.",
    )
    build_set.add_argument(
        "--homepage-generation-version-id",
        help="For curated_pages: parent homepage generation_version_id (required for non-homepage pages)",
    )
    build_set.add_argument(
        "--curated-page-paths",
        help="For curated_pages: comma-separated page_paths to eval (e.g. services,about). If omitted, all pages.",
    )
    build_set.add_argument("--max-cases", type=int, default=None, help="Cap eval set to first N cases")
    build_set.add_argument("--output-json")
    build_set.add_argument("--save-store", action="store_true")
    build_set.set_defaults(func=cmd_build_set)

    run_set = subparsers.add_parser("run-set")
    run_set.add_argument("--eval-set-json")
    run_set.add_argument("--eval-set-id")
    run_set.add_argument(
        "--eval-type",
        choices=["landing_page", "template_selection", "section_coverage", "color_palette", "curated_pages"],
    )
    run_set.add_argument("--version", default="v1")
    run_set.add_argument("--seed", type=int, default=42)
    run_set.add_argument("--business-ids")
    run_set.add_argument("--middle-section-count", type=int, default=3)
    run_set.add_argument(
        "--section-filter",
        help="JSON MongoDB filter for section_coverage (e.g. '{\"status\":\"ACTIVE\",\"tag\":\"smb\"}')",
    )
    run_set.add_argument("--preset-template-id", default="default", help="For color_palette: preset template")
    run_set.add_argument("--palette-ids", help="For color_palette: comma-separated palette IDs")
    run_set.add_argument(
        "--homepage-generation-version-id",
        help="For curated_pages: parent homepage generation_version_id (required for non-homepage pages)",
    )
    run_set.add_argument(
        "--curated-page-paths",
        help="For curated_pages: comma-separated page_paths to eval (e.g. services,about). If omitted, all pages.",
    )
    run_set.add_argument("--max-cases", type=int, default=None, help="Cap eval set to first N cases")
    run_set.add_argument("--max-concurrency", type=int, default=4)
    run_set.add_argument("--max-attempts", type=int, default=1)
    run_set.add_argument("--enable-judge", action="store_true")
    run_set.add_argument("--dry-run", action="store_true")
    run_set.add_argument("--dump-output-dir", help="Write final state/history/extractor output to this dir for debugging")
    run_set.set_defaults(func=cmd_run_set)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--eval-set-id", required=True)
    resume.add_argument("--max-concurrency", type=int, default=4)
    resume.add_argument("--max-attempts", type=int, default=1)
    resume.add_argument("--enable-judge", action="store_true")
    resume.add_argument("--dump-output-dir", help="Write final state/history/extractor output to this dir for debugging")
    resume.set_defaults(func=cmd_resume)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

