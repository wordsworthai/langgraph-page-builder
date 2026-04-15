"""Eval sets, runs, outputs, and judge results adapters."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._common import get_db


def get_eval_set(
    eval_set_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
) -> Optional[Dict[str, Any]]:
    """Load eval set doc from eval_sets."""
    db = get_db(mongo_uri, db_name)
    return db["eval_sets"].find_one({"eval_set_id": eval_set_id})


def get_latest_run_per_case(
    eval_set_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
) -> Dict[str, Dict[str, Any]]:
    """Return latest run per case_id (by updated_at). Case-centric view."""
    db = get_db(mongo_uri, db_name)
    all_runs = list(
        db["eval_runs"]
        .find({"eval_set_id": eval_set_id})
        .sort("updated_at", -1)
    )
    latest: Dict[str, Dict[str, Any]] = {}
    for run in all_runs:
        cid = run.get("case_id")
        if cid and cid not in latest:
            latest[cid] = run
    return latest


def resolve_case_id_from_run(
    eval_set_id: str,
    run_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
) -> Optional[str]:
    """Resolve case_id from eval_outputs given eval_set_id and run_id."""
    db = get_db(mongo_uri, db_name)
    doc = db["eval_outputs"].find_one(
        {"eval_set_id": eval_set_id, "run_id": run_id}
    )
    return doc.get("case_id") if doc else None


def resolve_run_id_from_thread(
    thread_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
) -> Optional[str]:
    """Resolve run_id from eval_runs given thread_id."""
    db = get_db(mongo_uri, db_name)
    run = db["eval_runs"].find_one({"thread_id": thread_id})
    return run.get("run_id") if run else None


def get_all_eval_sets(
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get all eval sets with case-centric summary statistics."""
    db = get_db(mongo_uri, db_name)
    eval_sets_coll = db["eval_sets"]

    eval_sets = list(eval_sets_coll.find().sort("updated_at", -1).limit(limit))

    result = []
    for es in eval_sets:
        eval_set_id = es.get("eval_set_id", "")
        cases = es.get("cases", [])
        total = len(cases)
        latest_by_case = get_latest_run_per_case(
            eval_set_id, mongo_uri=mongo_uri, db_name=db_name
        )
        completed = sum(
            1 for r in latest_by_case.values() if r.get("status") == "completed"
        )
        failed = sum(1 for r in latest_by_case.values() if r.get("status") == "failed")
        running = sum(
            1 for r in latest_by_case.values() if r.get("status") == "running"
        )
        valid_runs = [r for r in latest_by_case.values() if r.get("updated_at")]
        latest_run = (
            max(valid_runs, key=lambda r: r["updated_at"])
            if valid_runs
            else next(iter(latest_by_case.values()), None)
        )
        latest_timestamp = (
            latest_run.get("updated_at") if latest_run else es.get("updated_at")
        )

        result.append({
            "eval_set_id": eval_set_id,
            "task_type": es.get("eval_type")
            or (latest_run.get("task_type", "landing_page") if latest_run else "landing_page"),
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "progress_pct": (completed / total * 100) if total > 0 else 0,
            "latest_timestamp": latest_timestamp,
        })

    return result


def get_eval_runs(
    eval_set_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get case-centric runs: one per case with latest run data. Optionally filter by status."""
    eval_set = get_eval_set(eval_set_id, mongo_uri=mongo_uri, db_name=db_name)
    if not eval_set:
        return []

    cases = eval_set.get("cases", [])
    latest_by_case = get_latest_run_per_case(
        eval_set_id, mongo_uri=mongo_uri, db_name=db_name
    )

    result = []
    for case in cases:
        case_id = case.get("case_id")
        if not case_id:
            continue
        run = latest_by_case.get(case_id)
        if not run:
            continue
        if status_filter and run.get("status") != status_filter:
            continue
        merged = dict(run)
        merged.setdefault("task_details", {}).update(case.get("set_inputs", {}))
        result.append(merged)

    return result


def get_eval_output(
    eval_set_id: str,
    run_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "checkpointing_db",
) -> Optional[Dict[str, Any]]:
    """Get extracted output for a run from eval_outputs collection."""
    db = get_db(mongo_uri, db_name)
    doc = db["eval_outputs"].find_one(
        {"eval_set_id": eval_set_id, "run_id": run_id}
    )
    if not doc:
        return None
    return doc.get("output")


def get_eval_set_summary(
    eval_set_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "eval",
) -> Dict[str, Any]:
    """Get case-centric summary: total from eval set, counts from latest run per case."""
    eval_set = get_eval_set(eval_set_id, mongo_uri=mongo_uri, db_name=db_name)
    latest_by_case = get_latest_run_per_case(
        eval_set_id, mongo_uri=mongo_uri, db_name=db_name
    )

    if eval_set and "cases" in eval_set:
        total = len(eval_set["cases"])
    else:
        total = len(latest_by_case)

    completed = sum(
        1 for r in latest_by_case.values() if r.get("status") == "completed"
    )
    failed = sum(1 for r in latest_by_case.values() if r.get("status") == "failed")
    running = sum(
        1 for r in latest_by_case.values() if r.get("status") == "running"
    )

    first_run = next(iter(latest_by_case.values()), None)
    task_type = (
        first_run.get("task_type", "landing_page") if first_run else "landing_page"
    )

    return {
        "eval_set_id": eval_set_id,
        "task_type": task_type,
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "progress_pct": (completed / total * 100) if total > 0 else 0,
    }


def get_eval_judge_results_for_eval_set(
    eval_set_id: str,
    task_name: Optional[str] = "template_eval",
    mongo_uri: Optional[str] = None,
    db_name: str = "checkpointing_db",
) -> List[Dict[str, Any]]:
    """Get raw judge result docs for an eval set (for AI feedback count in metrics)."""
    db = get_db(mongo_uri, db_name)
    query: Dict[str, Any] = {"eval_set_id": eval_set_id}
    if task_name:
        query["task_name"] = task_name
    return list(db["eval_judge_results"].find(query))


def get_eval_results_for_set(
    eval_set_id: str,
    task_name: Optional[str] = None,
    mongo_uri: Optional[str] = None,
    db_name: str = "checkpointing_db",
) -> List[Dict[str, Any]]:
    """Get AI eval (judge) results for an eval set, one per run_id."""
    db = get_db(mongo_uri, db_name)
    judge_coll = db["eval_judge_results"]
    runs_coll = db["eval_runs"]

    query: Dict[str, Any] = {"eval_set_id": eval_set_id}
    if task_name:
        query["task_name"] = task_name

    judge_docs = list(judge_coll.find(query).sort("updated_at", -1))

    run_by_run_id: Dict[str, Dict[str, Any]] = {}
    for j in judge_docs:
        run_id = j.get("run_id")
        if run_id and run_id not in run_by_run_id:
            run = runs_coll.find_one({"eval_set_id": eval_set_id, "run_id": run_id})
            if run:
                run_by_run_id[run_id] = run

    results = []
    for j in judge_docs:
        run_id = j.get("run_id")
        run = run_by_run_id.get(run_id)
        if not run:
            continue

        result_data = j.get("result") or {}
        has_error = result_data.get("parse_error", False)
        status = "failed" if has_error else "completed"

        task_details = run.get("task_details") or {}
        results.append({
            "_id": j.get("_id"),
            "eval_set_id": eval_set_id,
            "task_name": j.get("task_name", task_name or "template_eval"),
            "run_id": run_id,
            "status": status,
            "task_details": task_details,
            "output": result_data,
            "prompt_version": result_data.get("prompt_version", "v1"),
            "generation_version_id": run.get("generation_version_id"),
            "model_name": result_data.get("model_name"),
            "created_at": j.get("created_at"),
            "updated_at": j.get("updated_at"),
        })

    return results


def get_eval_result_by_run_id(
    eval_set_id: str,
    run_id: str,
    task_name: str = "template_eval",
    mongo_uri: Optional[str] = None,
    db_name: str = "checkpointing_db",
) -> Optional[Dict[str, Any]]:
    """Get a single AI eval result by eval_set_id + run_id + task_name (direct DB lookup)."""
    db = get_db(mongo_uri, db_name)
    judge_coll = db["eval_judge_results"]
    runs_coll = db["eval_runs"]

    j = judge_coll.find_one({
        "eval_set_id": eval_set_id,
        "run_id": run_id,
        "task_name": task_name,
    })
    if not j:
        return None

    run = runs_coll.find_one({"eval_set_id": eval_set_id, "run_id": run_id})
    if not run:
        return None

    result_data = j.get("result") or {}
    has_error = result_data.get("parse_error", False)
    status = "failed" if has_error else "completed"
    task_details = run.get("task_details") or {}

    return {
        "_id": j.get("_id"),
        "eval_set_id": eval_set_id,
        "task_name": j.get("task_name", task_name),
        "run_id": run_id,
        "status": status,
        "task_details": task_details,
        "output": result_data,
        "prompt_version": result_data.get("prompt_version", "v1"),
        "generation_version_id": run.get("generation_version_id"),
        "model_name": result_data.get("model_name"),
        "created_at": j.get("created_at"),
        "updated_at": j.get("updated_at"),
    }
