"""
TemplateDBService -- central authority for all MongoDB operations on the 3 template collections.

Collections managed:
  - generation_template_sections
  - autopopulation_snapshots
  - generated_templates_with_values

No business logic -- just clean read/write abstractions.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from template_json_builder.models.template_build_output import TemplateBuildOutput

from pymongo.results import UpdateResult

from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.core.observability.logger import get_logger, get_request_context, is_perf_logging_enabled
from wwai_agent_orchestration.utils.landing_page_builder.template.section_utils import (
    get_merged_all_from_groups,
    classify_sections,
    build_section_group,
)

logger = get_logger(__name__)

GENERATION_TEMPLATE_SECTIONS = "generation_template_sections"
AUTOPOPULATION_SNAPSHOTS = "autopopulation_snapshots"
GENERATED_TEMPLATES_WITH_VALUES = "generated_templates_with_values"


class TemplateDBService:
    def __init__(self, db_name: str = "template_generation"):
        self.db_name = db_name

    @property
    def db(self):
        return db_manager.get_database(self.db_name)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _upsert(self, collection_name: str, generation_version_id: str, document: Dict[str, Any]) -> UpdateResult:
        collection = self.db[collection_name]
        result = collection.update_one(
            {"generation_version_id": generation_version_id},
            {"$set": document},
            upsert=True,
        )
        if result.matched_count > 0:
            logger.info(
                f"Updated existing document in '{collection_name}': {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id,
            )
        elif result.upserted_id:
            logger.info(
                f"Inserted new document in '{collection_name}': {result.upserted_id}",
                collection=collection_name,
                generation_version_id=generation_version_id,
                inserted_id=str(result.upserted_id),
            )
        return result

    def _fetch(self, collection_name: str, generation_version_id: str) -> Optional[Dict[str, Any]]:
        collection = self.db[collection_name]
        doc = collection.find_one({"generation_version_id": generation_version_id})
        if doc:
            logger.info(
                f"Fetched document from '{collection_name}': {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id,
            )
        else:
            logger.warning(
                f"No document found in '{collection_name}' for: {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id,
            )
        return doc

    # ==================================================================
    # generation_template_sections
    # ==================================================================

    def save_template_sections(
        self,
        generation_version_id: str,
        document: Dict[str, Any],
    ) -> UpdateResult:
        """Upsert a generation_template_sections document."""
        return self._upsert(GENERATION_TEMPLATE_SECTIONS, generation_version_id, document)

    def get_template_sections(self, generation_version_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the full generation_template_sections document."""
        return self._fetch(GENERATION_TEMPLATE_SECTIONS, generation_version_id)

    def get_merged_all(self, generation_version_id: str) -> Dict[str, Any]:
        """Fetch generation_template_sections and derive merged header+body+footer."""
        doc = self.get_template_sections(generation_version_id)
        if not doc:
            raise ValueError(
                f"generation_template_sections not found for {generation_version_id}"
            )
        return get_merged_all_from_groups(doc)

    def get_source_section_data(
        self,
        generation_version_id: str,
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        Fetch generation_template_sections and return section_ids and unique map
        from the merged header+body+footer groups.
        """
        merged = self.get_merged_all(generation_version_id)
        section_ids = merged.get("section_ids", [])
        unique_map = merged.get("template_unique_section_id_map", {})
        return section_ids, unique_map

    def get_unique_section_id_map(
        self,
        generation_version_id: str,
    ) -> Dict[str, str]:
        """
        Fetch generation_template_sections and extract the merged
        template_unique_section_id_map (header+body+footer).

        Replaces ``get_id_idx_to_unique_section_id_map`` from template_utils.py.
        """
        collection = self.db[GENERATION_TEMPLATE_SECTIONS]

        start = time.perf_counter()
        start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        document = collection.find_one({"generation_version_id": generation_version_id})
        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        if is_perf_logging_enabled():
            ctx = get_request_context()
            logger.info(
                "Mongo operation",
                metric_type="perf_mongo",
                operation="get_unique_section_id_map",
                collection_name=GENERATION_TEMPLATE_SECTIONS,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
                **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
            )

        if not document:
            raise ValueError(
                f"No document found in {GENERATION_TEMPLATE_SECTIONS} collection "
                f"with generation_version_id: {generation_version_id}"
            )

        all_group = get_merged_all_from_groups(document)

        logger.info(
            "Found generation_template_sections document",
            generation_version_id=generation_version_id,
            doc_keys=list(document.keys()),
            page_type=document.get("page_type"),
            all_section_count=all_group.get("section_count"),
            header_section_count=(document.get("header") or {}).get("section_count"),
            body_section_count=(document.get("body") or {}).get("section_count"),
            footer_section_count=(document.get("footer") or {}).get("section_count"),
        )

        id_idx_map = all_group.get("template_unique_section_id_map", {})

        if not id_idx_map:
            raise ValueError(
                f"Document with generation_version_id {generation_version_id} "
                f"has no template_unique_section_id_map (header+body+footer). "
                f"Available top-level keys: {list(document.keys())}"
            )

        logger.info(
            "Extracted template_unique_section_id_map from generation_template_sections",
            generation_version_id=generation_version_id,
            map_size=len(id_idx_map),
            sample_keys=list(id_idx_map.keys())[:3],
        )

        return id_idx_map

    def patch_template_sections(
        self,
        generation_version_id: str,
        header: Dict[str, Any],
        body: Dict[str, Any],
        footer: Dict[str, Any],
    ) -> UpdateResult:
        """Update header/body/footer groups and ensure 'all' is not persisted."""
        doc = self.get_template_sections(generation_version_id)
        if not doc:
            raise ValueError(
                f"generation_template_sections not found for patching: {generation_version_id}"
            )
        doc["header"] = header
        doc["body"] = body
        doc["footer"] = footer
        doc.pop("_id", None)
        doc.pop("all", None)
        return self._upsert(GENERATION_TEMPLATE_SECTIONS, generation_version_id, doc)

    def rebuild_template_sections(
        self,
        generation_version_id: str,
        full_mapping: List[Tuple[str, int]],
        new_section_mapping: Dict[str, Any],
        target_index: int,
        mode: str,
    ) -> None:
        """
        Full rebuild of the generation_template_sections document after section
        insertion or replacement. Rebuilds header, body, footer groups so
        downstream compilation reads fully consistent data.

        Args:
            generation_version_id: The new generation's version ID.
            full_mapping: Merged (unique_section_id, index) tuples for all
                sections (source + new).
            new_section_mapping: Section mapping dict for the new section
                (must contain at least section_id, section_l0).
            target_index: 0-based position (insert or replace position).
            mode: "insert" or "replace".
        """
        doc = self.get_template_sections(generation_version_id)
        if not doc:
            logger.warning(
                "generation_template_sections not found for patching",
                generation_version_id=generation_version_id,
            )
            return

        # -- Rebuild section_ids and template_unique_section_id_map from full_mapping --
        new_section_ids: List[str] = []
        new_unique_map: Dict[str, str] = {}
        for unique_id, idx in full_mapping:
            bare_section_id = unique_id.rsplit("_", 1)[0]
            new_section_ids.append(bare_section_id)
            key = f"{bare_section_id}_{idx}"
            new_unique_map[key] = unique_id

        # -- Rebuild section_mappings --
        existing_mappings = list(get_merged_all_from_groups(doc).get("section_mappings", []))
        updated_mappings = list(existing_mappings)

        if mode == "replace":
            updated_mappings[target_index] = new_section_mapping
        else:
            updated_mappings.insert(target_index, new_section_mapping)

        for idx, m in enumerate(updated_mappings):
            m["section_index"] = idx + 1

        # -- Classify into header / body / footer --
        page_type = doc.get("page_type", "homepage")
        is_homepage = page_type == "homepage"

        if is_homepage:
            header_mappings, body_mappings, footer_mappings = classify_sections(updated_mappings)
        else:
            header_mappings, body_mappings, footer_mappings = [], updated_mappings, []

        # -- Build groups using the shared helpers --
        header_group = build_section_group(header_mappings, new_unique_map, new_section_ids)
        body_group = build_section_group(body_mappings, new_unique_map, new_section_ids)
        footer_group = build_section_group(footer_mappings, new_unique_map, new_section_ids)

        # -- Update the document --
        doc["header"] = header_group
        doc["body"] = body_group
        doc["footer"] = footer_group
        doc.pop("_id", None)
        doc.pop("all", None)

        self.save_template_sections(
            generation_version_id=generation_version_id,
            document=doc,
        )

        total_section_count = (
            header_group["section_count"] + body_group["section_count"] + footer_group["section_count"]
        )
        logger.info(
            "Patched generation_template_sections (full rebuild)",
            generation_version_id=generation_version_id,
            total_section_count=total_section_count,
            all_mappings_count=len(updated_mappings),
            all_unique_map_size=len(new_unique_map),
            header_count=header_group["section_count"],
            body_count=body_group["section_count"],
            footer_count=footer_group["section_count"],
        )

    def propagate_template_updates_to_sections(
        self,
        generation_version_id: str,
        old_enabled_section_ids: List[str],
        new_enabled_section_ids: List[str],
        new_section_id_list: List[str],
        page_type: str,
    ) -> None:
        """
        Propagate deletions and reordering from save_template_updates to generation_template_sections.
        Reuses existing section_mappings (which have correct section_id) instead of rebuilding from TBO.
        Handles both deleted_sections and section_order changes.

        Raises ValueError if generation_template_sections doc does not exist.
        """
        doc = self.get_template_sections(generation_version_id)
        if not doc:
            raise ValueError(
                f"generation_template_sections not found for {generation_version_id}. "
                "Cannot propagate updates without an existing document."
            )

        merged = get_merged_all_from_groups(doc)
        old_mappings = list(merged.get("section_mappings", []))

        # Build unique_id -> section_mapping from existing doc (1:1 with old_enabled)
        old_unique_to_mapping = {
            old_enabled_section_ids[i]: old_mappings[i]
            for i in range(min(len(old_enabled_section_ids), len(old_mappings)))
        }

        # New mappings in new order; skip any not in old (defensive)
        new_mappings = []
        for uid in new_enabled_section_ids:
            if uid in old_unique_to_mapping:
                m = dict(old_unique_to_mapping[uid])
                new_mappings.append(m)

        # Update section_index for new order
        for idx, m in enumerate(new_mappings):
            m["section_index"] = idx + 1

        # Build new template_unique_section_id_map from new order (1:1 with enabled_section_ids, section_id_list)
        new_unique_map = {
            f"{new_section_id_list[i]}_{i}": new_enabled_section_ids[i]
            for i in range(min(len(new_enabled_section_ids), len(new_section_id_list)))
        }

        # Classify and build groups
        is_homepage = page_type == "homepage"
        if is_homepage:
            header_mappings, body_mappings, footer_mappings = classify_sections(new_mappings)
        else:
            header_mappings, body_mappings, footer_mappings = [], new_mappings, []

        header_group = build_section_group(header_mappings, new_unique_map, new_section_id_list)
        body_group = build_section_group(body_mappings, new_unique_map, new_section_id_list)
        footer_group = build_section_group(footer_mappings, new_unique_map, new_section_id_list)

        doc["header"] = header_group
        doc["body"] = body_group
        doc["footer"] = footer_group
        doc.pop("_id", None)
        doc.pop("all", None)

        self.save_template_sections(
            generation_version_id=generation_version_id,
            document=doc,
        )

        total_section_count = (
            header_group["section_count"] + body_group["section_count"] + footer_group["section_count"]
        )
        logger.info(
            "Propagated template updates to generation_template_sections",
            generation_version_id=generation_version_id,
            total_section_count=total_section_count,
        )

    # ==================================================================
    # autopopulation_snapshots
    # ==================================================================

    def save_snapshot(
        self,
        generation_version_id: str,
        document: Dict[str, Any],
    ) -> UpdateResult:
        """Upsert an autopopulation_snapshots document."""
        return self._upsert(AUTOPOPULATION_SNAPSHOTS, generation_version_id, document)

    def get_snapshot(self, generation_version_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the full autopopulation_snapshots document."""
        return self._fetch(AUTOPOPULATION_SNAPSHOTS, generation_version_id)

    def get_snapshot_by_label(
        self,
        generation_version_id: str,
        label: str = "final_autopopulation",
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Fetch snapshot doc and extract a specific snapshot by label.

        Returns:
            (full_doc, snapshot_dict)

        Raises:
            ValueError: If document or label not found.
        """
        doc = self._fetch(AUTOPOPULATION_SNAPSHOTS, generation_version_id)
        if not doc:
            raise ValueError(
                f"autopopulation_snapshots not found for {generation_version_id}"
            )
        snapshots = doc.get("snapshots", {})
        snap = snapshots.get(label)
        if not snap:
            raise ValueError(
                f"Snapshot label '{label}' not found for {generation_version_id}. "
                f"Available: {list(snapshots.keys())}"
            )
        return doc, snap

    def validate_snapshot(
        self,
        generation_version_id: str,
    ) -> Dict[str, Any]:
        """
        Validate snapshot document and check for critical issues.

        Checks:
        1. If errors exist, ensure last_label is set (critical for template compilation)
        2. Logs warnings if issues are found

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "has_errors": bool,
                "has_last_label": bool,
                "last_label": Optional[str],
                "error_count": int,
                "warnings": List[str]
            }

        Raises:
            ValueError: If document not found.
        """
        from wwai_agent_orchestration.core.database import fetch_one_from_collection

        document = fetch_one_from_collection(
            collection_name=AUTOPOPULATION_SNAPSHOTS,
            query={"generation_version_id": generation_version_id},
            database=self.db,
        )

        if not document:
            raise ValueError(
                f"No document found in {AUTOPOPULATION_SNAPSHOTS} collection "
                f"with generation_version_id: {generation_version_id}"
            )

        errors = document.get("errors", [])
        has_errors = bool(errors)
        error_count = len(errors)

        last_label = document.get("last_label")
        has_last_label = last_label is not None

        warnings: List[str] = []
        valid = True

        if has_errors and not has_last_label:
            warning_msg = (
                f"CRITICAL: Document has {error_count} error(s) but no last_label set. "
                f"This will cause template compilation to fail. "
                f"generation_version_id: {generation_version_id}"
            )
            warnings.append(warning_msg)
            logger.error(
                warning_msg,
                generation_version_id=generation_version_id,
                error_count=error_count,
                available_keys=list(document.keys()),
            )
            valid = False
        elif has_errors:
            logger.warning(
                f"Document has {error_count} error(s) but last_label is preserved: {last_label}",
                generation_version_id=generation_version_id,
                error_count=error_count,
                last_label=last_label,
            )

        result = {
            "valid": valid,
            "has_errors": has_errors,
            "has_last_label": has_last_label,
            "last_label": last_label,
            "error_count": error_count,
            "warnings": warnings,
        }

        if warnings:
            logger.warning(
                "Snapshot validation found issues",
                generation_version_id=generation_version_id,
                warnings=warnings,
            )

        return result

    # ==================================================================
    # generated_templates_with_values
    # ==================================================================

    def save_compiled_template(
        self,
        generation_version_id: str,
        template_build_output: Union["TemplateBuildOutput", Dict[str, Any]],
        page_type: str,
        section_group_unique_ids: Dict[str, List[str]],
        template_unique_section_id_map: Dict[str, str],
    ) -> UpdateResult:
        """
        Save compiled template output to the generated_templates_with_values collection.

        Stores TemplateBuildOutput as a flat document. For non-homepage, only body
        sections are stored; header/footer come from parent at read time.
        """
        from template_json_builder.models.template_build_output import TemplateBuildOutput as TBO

        if isinstance(template_build_output, TBO):
            tbo_dict = template_build_output.model_dump()
        else:
            tbo_dict = template_build_output

        document = {
            "generation_version_id": generation_version_id,
            "page_type": page_type,
            "template_build_output": tbo_dict,
            "section_group_unique_ids": section_group_unique_ids,
            "template_unique_section_id_map": template_unique_section_id_map,
            "section_ids": tbo_dict.get("section_id_list", []),
            "section_count": len(tbo_dict.get("section_id_list", [])),
            "timestamp": datetime.utcnow().isoformat(),
        }

        sections = tbo_dict.get("sections", {})
        enabled_ids = tbo_dict.get("enabled_section_ids", [])
        logger.info(
            "Saving generated_templates_with_values",
            generation_version_id=generation_version_id,
            page_type=page_type,
            section_count=len(tbo_dict.get("section_id_list", [])),
            total_sections=len(sections),
            total_enabled=len(enabled_ids),
        )

        return self._upsert(GENERATED_TEMPLATES_WITH_VALUES, generation_version_id, document)

    def get_compiled_template(self, generation_version_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a generated_templates_with_values document."""
        return self._fetch(GENERATED_TEMPLATES_WITH_VALUES, generation_version_id)

    def get_template_build_output(
        self,
        generation_version_id: str,
        page_type: str,
        parent_generation_version_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Read compiled template from DB and return TemplateBuildOutput structure.

        For homepage: returns current doc's template_build_output as-is.
        For non-homepage: fetches parent doc, extracts header/footer by
        section_group_unique_ids, merges with current body, returns merged result.

        Returns:
            Dict matching TemplateBuildOutput (sections, enabled_section_ids, section_id_list)
        """
        doc = self.get_compiled_template(generation_version_id)
        if not doc:
            raise ValueError(
                f"generated_templates_with_values not found for {generation_version_id}. "
                "Ensure template_compilation has run and saved successfully."
            )

        tbo = doc.get("template_build_output")
        if not tbo:
            raise ValueError(
                f"Document {generation_version_id} has no template_build_output. "
                "Re-run template_compilation to save in new format."
            )

        if page_type == "homepage" or not parent_generation_version_id:
            groups = doc.get("section_group_unique_ids") or {}
            page_structure_info = {
                "page_type": doc.get("page_type", "homepage"),
                "header_unique_ids": groups.get("header_unique_ids", []),
                "body_unique_ids": groups.get("body_unique_ids", []),
                "footer_unique_ids": groups.get("footer_unique_ids", []),
            }
            return {
                **dict(tbo),
                "page_structure_info": page_structure_info,
            }

        # If page type is non homepage, and parent generation version id is provided,
        #  we need to merge the parent header and footer with the current body.
        parent_doc = self.get_compiled_template(parent_generation_version_id)
        if not parent_doc:
            raise ValueError(
                f"Parent generated_templates_with_values not found for "
                f"{parent_generation_version_id}"
            )

        parent_tbo = parent_doc.get("template_build_output")
        parent_groups = parent_doc.get("section_group_unique_ids") or {}
        header_ids = set(parent_groups.get("header_unique_ids", []))
        footer_ids = set(parent_groups.get("footer_unique_ids", []))

        parent_sections = parent_tbo.get("sections", {})
        parent_enabled = parent_tbo.get("enabled_section_ids", [])

        header_sections = {
            k: v for k, v in parent_sections.items() if k in header_ids
        }
        footer_sections = {
            k: v for k, v in parent_sections.items() if k in footer_ids
        }
        header_enabled = [sid for sid in parent_enabled if sid in header_ids]
        footer_enabled = [sid for sid in parent_enabled if sid in footer_ids]

        current_sections = tbo.get("sections", {})
        body_enabled = tbo.get("enabled_section_ids", [])

        merged_sections = {**header_sections, **current_sections, **footer_sections}
        merged_enabled = list(header_enabled) + list(body_enabled) + list(footer_enabled)

        parent_section_id_list = parent_tbo.get("section_id_list", [])
        parent_enabled = parent_tbo.get("enabled_section_ids", [])
        schema_to_idx = {sid: i for i, sid in enumerate(parent_enabled)}
        header_section_ids = [
            parent_section_id_list[schema_to_idx[sid]]
            for sid in header_enabled
            if sid in schema_to_idx
        ]
        footer_section_ids = [
            parent_section_id_list[schema_to_idx[sid]]
            for sid in footer_enabled
            if sid in schema_to_idx
        ]
        body_section_id_list = tbo.get("section_id_list", [])
        merged_section_id_list = header_section_ids + body_section_id_list + footer_section_ids

        current_groups = doc.get("section_group_unique_ids") or {}
        body_unique_ids = current_groups.get("body_unique_ids", []) or list(current_sections.keys())

        page_structure_info = {
            "page_type": page_type,
            "header_unique_ids": list(header_ids),
            "body_unique_ids": body_unique_ids,
            "footer_unique_ids": list(footer_ids),
        }

        logger.info(
            "Read template_build_output (non-homepage merge)",
            generation_version_id=generation_version_id,
            total_sections=len(merged_sections),
            total_enabled=len(merged_enabled),
        )

        return {
            "sections": merged_sections,
            "enabled_section_ids": merged_enabled,
            "section_id_list": merged_section_id_list,
            "page_structure_info": page_structure_info,
        }


template_db_service = TemplateDBService()
