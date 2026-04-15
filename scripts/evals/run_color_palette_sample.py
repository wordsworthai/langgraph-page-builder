"""Run color-palette eval sample on real data and store results in Mongo.

Same template and business across all cases; varies only color palette.

poetry run python scripts/evals/run_color_palette_sample.py \
  --mongo_uri="mongodb://localhost:27020/" \
  --preset_template_id="default" \
  --max_cases=12

# Use only specific palettes (e.g. friendly-1, bold-2):
poetry run python scripts/evals/run_color_palette_sample.py \
  --mongo_uri="mongodb://localhost:27020/" \
  --palette_ids="bold-3"

# To resume an eval set.
poetry run python -m wwai_agent_orchestration.evals.cli \
  --store mongo \
  --mongo-uri="mongodb://localhost:27020/" \
  --db-name eval \
  resume \
  --eval-set-id="color_palette_sample_20260309_145548" \
  --max-concurrency 1

"""

from __future__ import annotations

import sys
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
    DEFAULT_SAMPLE_SIZE,
    print_json,
    sample_business_ids,
    timestamp_suffix,
)
from pipeline.fetch_business_ids import fetch_eval_business_ids
from wwai_agent_orchestration.evals.sets.factory import build_eval_set
from wwai_agent_orchestration.evals.entrypoints import run_async, run_eval_set_entrypoint
from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore

FLAGS = flags.FLAGS

flags.DEFINE_string("mongo_uri", DEFAULT_MONGO_URI, "MongoDB connection URI")
flags.DEFINE_string("db_name", DEFAULT_DB_NAME, "Database name for eval storage")
flags.DEFINE_integer("sample_size", 1, "Number of businesses (use 1 for palette comparison)")
flags.DEFINE_string("preset_template_id", "default", "Preset template from constants")
flags.DEFINE_string(
    "palette_ids",
    None,
    "Comma-separated palette IDs (e.g. friendly-1,bold-2). If set, only these palettes are used.",
)
flags.DEFINE_integer("max_cases", 999, "Max cases to run (caps generated eval set)")
flags.DEFINE_string("eval_set_id", None, "Eval set ID (default: auto-generated with timestamp)")
flags.DEFINE_integer("seed", 42, "Random seed for deterministic sampling")
flags.DEFINE_integer("max_concurrency", 2, "Max concurrent case executions")
flags.DEFINE_integer("max_attempts", 1, "Max retry attempts per case")
flags.DEFINE_bool("dry_run", False, "If True, skip actual execution")


def main(argv):
    del argv  # Unused.
    eval_set_id = FLAGS.eval_set_id or f"color_palette_sample_{timestamp_suffix()}"

    all_business_ids = fetch_eval_business_ids(mongo_uri=FLAGS.mongo_uri)
    business_ids = sample_business_ids(all_business_ids, FLAGS.sample_size)
    if not business_ids:
        raise RuntimeError(
            "No businesses found with tag=eval for color palette sample run."
        )
    print("Found", len(business_ids), "businesses for color palette sample run.")

    palette_ids = None
    if FLAGS.palette_ids:
        palette_ids = [pid.strip() for pid in FLAGS.palette_ids.split(",") if pid.strip()]

    eval_set = build_eval_set(
        eval_set_id=eval_set_id,
        eval_type="color_palette",
        version="v1",
        seed=FLAGS.seed,
        business_ids=business_ids,
        preset_template_id=FLAGS.preset_template_id,
        palette_ids=palette_ids,
        max_cases=FLAGS.max_cases,
    )

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
            "stage": "color_palette_sample",
            "eval_set_id": eval_set_id,
            "sample_size": len(business_ids),
            "case_count": len(eval_set.cases),
            "summary": {k: v for k, v in summary.items() if k != "results"},
        }
    )


if __name__ == "__main__":
    app.run(main)
