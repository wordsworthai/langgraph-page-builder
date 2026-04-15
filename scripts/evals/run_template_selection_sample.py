"""Run template-selection eval sample on real data with optional AI judge.

poetry run python scripts/evals/run_template_selection_sample.py \
  --mongo_uri="mongodb://localhost:27020/" \
  --sample_size=1 \
  --max_cases=1 \  
  --enable_judge \
  --judge_provider=openai \
  --judge_model=gpt-4.1

"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
# Ensure compiler service URL is set before bundle_pipeline_pkg is imported
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
from wwai_agent_orchestration.evals.judges.runner import JudgeRunner
from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore

FLAGS = flags.FLAGS

flags.DEFINE_string("mongo_uri", DEFAULT_MONGO_URI, "MongoDB connection URI")
flags.DEFINE_string("db_name", DEFAULT_DB_NAME, "Database name for eval storage")
flags.DEFINE_integer("sample_size", DEFAULT_SAMPLE_SIZE, "Number of businesses to sample")
flags.DEFINE_integer("max_cases", DEFAULT_SAMPLE_SIZE, "Max cases to run (caps generated eval set)")
flags.DEFINE_string("eval_set_id", None, "Eval set ID (default: auto-generated with timestamp)")
flags.DEFINE_integer("seed", 42, "Random seed for deterministic sampling")
flags.DEFINE_integer("max_concurrency", 2, "Max concurrent case executions")
flags.DEFINE_integer("max_attempts", 1, "Max retry attempts per case")
flags.DEFINE_bool("enable_judge", True, "Enable LLM-as-judge evaluation")
flags.DEFINE_string("judge_provider", "openai", "LLM provider for judge (openai or anthropic)")
flags.DEFINE_string("judge_model", "gpt-4.1", "Model name for judge")
flags.DEFINE_bool("dry_run", False, "If True, skip actual execution")


def main(argv):
    del argv  # Unused.
    eval_set_id = FLAGS.eval_set_id or f"template_selection_sample_{timestamp_suffix()}"

    all_business_ids = fetch_eval_business_ids(mongo_uri=FLAGS.mongo_uri)
    business_ids = sample_business_ids(all_business_ids, FLAGS.sample_size)
    if not business_ids:
        raise RuntimeError("No businesses found with tag=eval for template selection sample run.")

    if FLAGS.enable_judge and FLAGS.judge_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print_json(
            {
                "warning": "OPENAI_API_KEY is not set; judge execution may produce parse_error results.",
                "judge_provider": FLAGS.judge_provider,
                "judge_model": FLAGS.judge_model,
            }
        )

    eval_set = build_eval_set(
        eval_set_id=eval_set_id,
        eval_type="template_selection",
        version="v1",
        seed=FLAGS.seed,
        business_ids=business_ids,
        max_cases=FLAGS.max_cases,
    )
    store = MongoEvalStore(mongo_uri=FLAGS.mongo_uri, db_name=FLAGS.db_name)
    judge_runner = (
        JudgeRunner(provider=FLAGS.judge_provider, model_name=FLAGS.judge_model)
        if FLAGS.enable_judge
        else None
    )
    summary = run_async(
        run_eval_set_entrypoint(
            eval_set=eval_set,
            store=store,
            max_concurrency=FLAGS.max_concurrency,
            max_attempts=FLAGS.max_attempts,
            enable_judge=FLAGS.enable_judge,
            judge_runner=judge_runner,
            dry_run=FLAGS.dry_run,
        )
    )
    print_json(
        {
            "stage": "template_selection_sample",
            "eval_set_id": eval_set_id,
            "sample_size": len(business_ids),
            "case_count": len(eval_set.cases),
            "judge_enabled": FLAGS.enable_judge,
            "judge_provider": FLAGS.judge_provider if FLAGS.enable_judge else None,
            "judge_model": FLAGS.judge_model if FLAGS.enable_judge else None,
            "summary": {k: v for k, v in summary.items() if k != "results"},
        }
    )


if __name__ == "__main__":
    app.run(main)
