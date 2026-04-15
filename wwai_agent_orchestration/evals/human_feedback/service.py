"""Strict feedback validation and persistence service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from wwai_agent_orchestration.evals.human_feedback.storage import (
    CanonicalFeedbackKeys,
    FeedbackStore,
    ResolvedRun,
    RunResolver,
    validate_feedback_keys,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.registry import get_taxonomy
from wwai_agent_orchestration.evals.human_feedback.types import HumanFeedbackSnapshot


class FeedbackService:
    """Validates taxonomy and writes latest feedback snapshot."""

    def __init__(
        self,
        store: FeedbackStore,
        *,
        run_resolver: Optional[RunResolver] = None,
    ) -> None:
        self._store = store
        self._run_resolver = run_resolver

    def save_feedback_by_case(
        self,
        eval_set_id: str,
        case_id: str,
        feedback: Dict[str, Any],
        *,
        schema_version: str = "v1",
        updated_by: Optional[str] = None,
    ) -> bool:
        """Save feedback by eval_set_id + case_id; resolves run and infers task_type."""
        if self._run_resolver is None:
            raise ValueError(
                "save_feedback_by_case requires run_resolver; "
                "pass run_resolver=... when constructing FeedbackService"
            )
        resolved = self._run_resolver.resolve(eval_set_id, case_id)
        if resolved is None:
            raise ValueError(
                f"No run found for eval_set_id={eval_set_id!r}, case_id={case_id!r}"
            )
        snapshot = self._build_snapshot_from_resolved(
            eval_set_id=eval_set_id,
            case_id=case_id,
            feedback=feedback,
            resolved=resolved,
            schema_version=schema_version,
            updated_by=updated_by,
        )
        return self.save_snapshot(snapshot)

    def _build_snapshot_from_resolved(
        self,
        *,
        eval_set_id: str,
        case_id: str,
        feedback: Dict[str, Any],
        resolved: ResolvedRun,
        schema_version: str,
        updated_by: Optional[str],
    ) -> HumanFeedbackSnapshot:
        return HumanFeedbackSnapshot(
            eval_set_id=eval_set_id,
            case_id=case_id,
            run_id=resolved.run_id,
            thread_id=resolved.thread_id,
            task_type=resolved.task_type,
            feedback=feedback,
            feedback_schema_version=schema_version,
            updated_by=updated_by,
        )

    def save_snapshot(self, snapshot: HumanFeedbackSnapshot) -> bool:
        """
        Validate a feedback snapshot against the taxonomy and persist it to the store.

        Steps:
        1. Validate required identifiers (eval_set_id, case_id, run_id, etc.)
        2. Load taxonomy for the snapshot's task_type
        3. Validate and normalize feedback (keys must match taxonomy; values must match types)
        4. Upsert the snapshot into the store (latest per run)

        overall_pass is not derived here: it is either an explicit feedback field
        (validated by taxonomy) or computed on the fly when computing metrics.
        """
        # 1. Validate required identifiers and format (e.g. run_id matches run_* pattern)
        validate_feedback_keys(
            CanonicalFeedbackKeys(
                eval_set_id=snapshot.eval_set_id,
                case_id=snapshot.case_id,
                run_id=snapshot.run_id,
                thread_id=snapshot.thread_id,
                task_type=snapshot.task_type,
            )
        )
        # 2. Load taxonomy for this task type (defines allowed keys, value types, required fields)
        taxonomy = get_taxonomy(
            task_type=snapshot.task_type,
            version=snapshot.feedback_schema_version,
        )
        # 3. Validate feedback keys against taxonomy; ensure values match types (bool, text, enum, number)
        normalized_feedback = self._validate_and_normalize(
            feedback=snapshot.feedback,
            taxonomy=taxonomy,
        )
        # 4. Persist to store (upsert; one snapshot per run)
        normalized_snapshot = snapshot.model_copy(update={"feedback": normalized_feedback})
        return self._store.save_feedback(normalized_snapshot)

    @staticmethod
    def _validate_and_normalize(
        *,
        feedback: Dict[str, Any],
        taxonomy: Any,
    ) -> Dict[str, Any]:
        categories = [c for c in taxonomy.categories if c.active]
        allowed_keys = {c.key for c in categories}
        invalid = sorted(set(feedback.keys()) - allowed_keys)
        if invalid:
            raise ValueError(f"Invalid feedback keys: {invalid}")

        by_key = {c.key: c for c in categories}
        normalized: Dict[str, Any] = {}

        for key, value in feedback.items():
            category = by_key[key]
            FeedbackService._validate_value(key=key, value=value, category=category)
            normalized[key] = value

        missing_required = [
            c.key for c in categories if c.required and c.key not in normalized
        ]
        if missing_required:
            raise ValueError(f"Missing required feedback keys: {missing_required}")

        return normalized

    @staticmethod
    def _validate_value(*, key: str, value: Any, category: Any) -> None:
        value_type = category.value_type
        if value_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"{key} expects boolean value")
        if value_type == "text" and not isinstance(value, str):
            raise ValueError(f"{key} expects text value")
        if value_type == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"{key} expects number value")
        if value_type == "enum":
            if not isinstance(value, str):
                raise ValueError(f"{key} expects enum string value")
            options = category.options or []
            if value not in options:
                raise ValueError(f"{key} must be one of: {options}")

