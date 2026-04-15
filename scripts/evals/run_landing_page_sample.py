"""Run landing-page eval sample on real data and store results in Mongo.

poetry run python scripts/evals/run_landing_page_sample.py \
  --mongo_uri="mongodb://localhost:27020/" \
  --sample_size=1

"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
# Ensure compiler service URL is set before bundle_pipeline_pkg is imported
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
from wwai_agent_orchestration.evals.entrypoints import  run_async, run_eval_set_entrypoint
from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore

FLAGS = flags.FLAGS

flags.DEFINE_string("mongo_uri", DEFAULT_MONGO_URI, "MongoDB connection URI")
flags.DEFINE_string("db_name", DEFAULT_DB_NAME, "Database name for eval storage")
flags.DEFINE_integer("sample_size", DEFAULT_SAMPLE_SIZE, "Number of businesses to sample")
flags.DEFINE_string("eval_set_id", None, "Eval set ID (default: auto-generated with timestamp)")
flags.DEFINE_integer("seed", 42, "Random seed for deterministic sampling")
flags.DEFINE_integer("max_concurrency", 2, "Max concurrent case executions")
flags.DEFINE_integer("max_attempts", 1, "Max retry attempts per case")
flags.DEFINE_bool("dry_run", False, "If True, skip actual execution")
flags.DEFINE_string("dump_output_dir", None, "Directory to dump output")


def main(argv):
    del argv  # Unused.
    eval_set_id = FLAGS.eval_set_id or f"landing_page_sample_{timestamp_suffix()}"

    all_business_ids = fetch_eval_business_ids(mongo_uri=FLAGS.mongo_uri)
    business_ids = sample_business_ids(all_business_ids, FLAGS.sample_size)
    if not business_ids:
        raise RuntimeError("No businesses found with tag=eval for landing page sample run.")

    eval_set = build_eval_set(
        eval_set_id=eval_set_id,
        eval_type="landing_page",
        version="v1",
        seed=FLAGS.seed,
        business_ids=business_ids,
    )
    store = MongoEvalStore(mongo_uri=FLAGS.mongo_uri, db_name=FLAGS.db_name)
    summary = run_async(
        run_eval_set_entrypoint(
            eval_set=eval_set,
            store=store,
            max_concurrency=FLAGS.max_concurrency,
            max_attempts=FLAGS.max_attempts,
            dry_run=FLAGS.dry_run,
            dump_output_dir=FLAGS.dump_output_dir,
        )
    )
    print_json(
        {
            "stage": "landing_page_sample",
            "eval_set_id": eval_set_id,
            "sample_size": len(business_ids),
            "summary": {k: v for k, v in summary.items() if k != "results"},
        }
    )


if __name__ == "__main__":
    app.run(main)
