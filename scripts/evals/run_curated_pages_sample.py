"""Run curated pages eval sample: fetches curated pages from DB, runs preset_sections workflow.

Prerequisites:
  - Run create_homepage_demo.py first and pass its generation_version_id via --homepage_generation_version_id
  - Ensure curated_pages collection exists in template_generation DB

Usage:
  poetry run python scripts/evals/run_curated_pages_sample.py \
    --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \
    --homepage_generation_version_id=<ID_FROM_HOMEPAGE_DEMO> \
    --mongo_uri="mongodb://localhost:27020/" \
    --max_cases=999

  # Single curated page path:
  poetry run python scripts/evals/run_curated_pages_sample.py \
    --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \
    --homepage_generation_version_id=<ID_FROM_HOMEPAGE_DEMO> \
    --curated_page_paths=services \
    --max_cases=1

# To resume a eval set:
  poetry run python -m wwai_agent_orchestration.evals.cli \
    --store mongo \
    --mongo-uri="mongodb://localhost:27020/" \
    --db-name eval \
    resume \
    --eval-set-id="curated_pages_sample_20260310_120000" \
    --max-concurrency 1

"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
import os

if not os.environ.get("NODE_SERVER_URL"):
    os.environ["NODE_SERVER_URL"] = "http://localhost:3002"
if not os.environ.get("ENVIRONMENT"):
    os.environ["ENVIRONMENT"] = "local"

from absl import app, flags

from _real_data_common import (
    DEFAULT_DB_NAME,
    DEFAULT_MONGO_URI,
    print_json,
    timestamp_suffix,
)
from wwai_agent_orchestration.evals.entrypoints import run_async, run_eval_set_entrypoint
from wwai_agent_orchestration.evals.sets.factory import build_eval_set
from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore

FLAGS = flags.FLAGS

flags.DEFINE_string(
    "homepage_generation_version_id",
    None,
    "Generation version ID from homepage demo (create_homepage_demo.py). Required for non-homepage curated pages.",
    required=True,
)
flags.DEFINE_string(
    "business_id",
    None,
    "Business ID to run eval against (e.g. 660097b0-03df-42b5-b68e-5ccf18193b26 for Bailey Plumbing)",
)
flags.DEFINE_string(
    "curated_page_paths",
    None,
    "Comma-separated page_paths to eval (e.g. services,about). If omitted, all curated pages.",
)
flags.DEFINE_string("mongo_uri", DEFAULT_MONGO_URI, "MongoDB connection URI")
flags.DEFINE_string("db_name", DEFAULT_DB_NAME, "Database name for eval storage")
flags.DEFINE_integer("max_cases", 999, "Max cases to run (caps generated eval set)")
flags.DEFINE_string("eval_set_id", None, "Eval set ID (default: auto-generated with timestamp)")
flags.DEFINE_integer("seed", 42, "Random seed for deterministic sampling")
flags.DEFINE_integer("max_concurrency", 2, "Max concurrent case executions")
flags.DEFINE_integer("max_attempts", 1, "Max retry attempts per case")
flags.DEFINE_bool("dry_run", False, "If True, skip actual execution")


def main(argv):
    del argv  # Unused.
    eval_set_id = FLAGS.eval_set_id or f"curated_pages_sample_{timestamp_suffix()}"

    business_ids = [FLAGS.business_id or "your-business-id-here"]

    curated_page_paths = None
    if FLAGS.curated_page_paths:
        curated_page_paths = [p.strip() for p in FLAGS.curated_page_paths.split(",") if p.strip()]

    eval_set = build_eval_set(
        eval_set_id=eval_set_id,
        eval_type="curated_pages",
        version="v1",
        seed=FLAGS.seed,
        business_ids=business_ids,
        homepage_generation_version_id=FLAGS.homepage_generation_version_id,
        curated_page_paths=curated_page_paths,
        max_cases=FLAGS.max_cases,
    )

    print(f"Evaluating {len(eval_set.cases)} curated page(s)")

    store = MongoEvalStore(mongo_uri=FLAGS.mongo_uri, db_name=FLAGS.db_name)
    summary = run_async(
        run_eval_set_entrypoint(
            eval_set=eval_set,
            store=store,
            max_concurrency=FLAGS.max_concurrency,
            max_attempts=FLAGS.max_attempts,
            dry_run=FLAGS.dry_run,
        )
    )

    print_json(
        {
            "stage": "curated_pages_sample",
            "eval_set_id": eval_set_id,
            "case_count": len(eval_set.cases),
            "summary": {k: v for k, v in summary.items() if k != "results"},
        }
    )


if __name__ == "__main__":
    app.run(main)
