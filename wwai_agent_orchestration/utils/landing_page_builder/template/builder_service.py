"""
TemplateBuilderService -- orchestrates template compilation pipeline.

Resolves sections from DB, calls build_template_versions_response (external),
validates, persists results. Callers get a single entry point.
"""

import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from wwai_agent_orchestration.contracts.landing_page_builder.page_structure import (
    PageStructureInfo,
    TemplateWithPageInfo,
)
from template_json_builder.db.queries import SECTION_REPO_PROD_DB
from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import TemplateDBService, template_db_service
from wwai_agent_orchestration.contracts.landing_page_builder.template_update import SaveTemplateRequest
from wwai_agent_orchestration.utils.landing_page_builder.template.section_utils import (
    build_section_group,
    classify_sections,
    create_stable_mapping,
    create_stable_mapping_with_insert,
    create_stable_mapping_with_replace,
    extract_ordered_unique_ids,
    extract_section_ids,
    get_merged_all_from_groups,
    validate_insert_mode,
    validate_replace_mode,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.template_update_utils import (
    apply_template_updates,
    recompute_metadata_from_tbo,
)

logger = get_logger(__name__)


class TemplateBuilderService:
    def __init__(self, db_service: TemplateDBService):
        self.db_service = db_service

    # ------------------------------------------------------------------
    # Section resolution (DB-driven)
    # ------------------------------------------------------------------

    def get_section_ids_and_map(
        self,
        generation_version_id: str,
    ) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]], str]:
        """
        Resolve section_ids, template_unique_section_id_map, and per-group unique IDs
        entirely from the generation_template_sections DB collection.

        Replaces ``get_section_ids_and_map_from_db`` from section_merge_utils.py.

        Returns:
            Tuple of:
              - merged_section_ids
              - merged_template_unique_section_id_map
              - section_group_unique_ids (header_unique_ids, body_unique_ids, footer_unique_ids)
              - page_type

        Raises:
            ValueError: If required documents or fields are missing.
        """
        logger.info(
            "get_section_ids_and_map called",
            generation_version_id=generation_version_id,
        )

        current_doc = self.db_service.get_template_sections(generation_version_id)
        if not current_doc:
            raise ValueError(
                f"generation_template_sections not found for "
                f"generation_version_id={generation_version_id}"
            )

        page_type = current_doc.get("page_type")
        if not page_type:
            raise ValueError(
                f"page_type not found in generation_template_sections for "
                f"generation_version_id={generation_version_id}"
            )

        logger.info(
            "Fetched generation_template_sections document",
            generation_version_id=generation_version_id,
            doc_keys=list(current_doc.keys()),
            page_type_in_doc=page_type,
            all_section_count=get_merged_all_from_groups(current_doc).get("section_count"),
            header_section_count=(current_doc.get("header") or {}).get("section_count"),
            body_section_count=(current_doc.get("body") or {}).get("section_count"),
            footer_section_count=(current_doc.get("footer") or {}).get("section_count"),
        )

        if page_type == "homepage":
            section_ids, unique_map, group_ids = self._resolve_homepage(current_doc, generation_version_id)
        else:
            section_ids, unique_map, group_ids = self._resolve_non_homepage(current_doc, generation_version_id, page_type)

        return section_ids, unique_map, group_ids, page_type

    def _resolve_homepage(
        self,
        current_doc: Dict[str, Any],
        generation_version_id: str,
    ) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]]]:
        all_group = get_merged_all_from_groups(current_doc)
        section_ids = all_group.get("section_ids", [])
        unique_map = all_group.get("template_unique_section_id_map", {})

        if not section_ids:
            raise ValueError(
                f"No section_ids in generation_template_sections (header+body+footer) for "
                f"generation_version_id={generation_version_id}"
            )

        header_unique_ids = list(
            (current_doc.get("header") or {}).get("template_unique_section_id_map", {}).values()
        )
        body_unique_ids = list(
            (current_doc.get("body") or {}).get("template_unique_section_id_map", {}).values()
        )
        footer_unique_ids = list(
            (current_doc.get("footer") or {}).get("template_unique_section_id_map", {}).values()
        )

        logger.info(
            "Homepage resolution complete",
            section_count=len(section_ids),
            map_size=len(unique_map),
            header_unique=len(header_unique_ids),
            body_unique=len(body_unique_ids),
            footer_unique=len(footer_unique_ids),
        )

        return section_ids, unique_map, {
            "header_unique_ids": header_unique_ids,
            "body_unique_ids": body_unique_ids,
            "footer_unique_ids": footer_unique_ids,
        }

    def _resolve_non_homepage(
        self,
        current_doc: Dict[str, Any],
        generation_version_id: str,
        page_type: str,
    ) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]]]:
        body_group = current_doc.get("body") or {}
        body_ids = body_group.get("section_ids", [])
        body_map = body_group.get("template_unique_section_id_map", {})

        if not body_ids:
            raise ValueError(
                f"No body section_ids in generation_template_sections for "
                f"generation_version_id={generation_version_id}"
            )

        body_unique_ids = extract_ordered_unique_ids(body_map)

        logger.info(
            "Non-homepage: returning body-only (merge deferred to compilation)",
            page_type=page_type,
            body_count=len(body_ids),
            body_map_size=len(body_map),
        )

        return body_ids, body_map, {
            "header_unique_ids": [],
            "body_unique_ids": body_unique_ids,
            "footer_unique_ids": [],
        }

    def _reindex_merged_map(
        self,
        section_ids: List[str],
        header_ids: List[str],
        body_ids: List[str],
        footer_ids: List[str],
        header_map: Dict[str, str],
        body_map: Dict[str, str],
        footer_map: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Reindex template_unique_section_id_map from per-group indices to global indices.
        template_version_builder expects lookup_key = f"{section_id}_{global_index}".
        """
        result: Dict[str, str] = {}

        def get_value_for_section(section_id: str, source_map: Dict[str, str]) -> str:
            for key, value in source_map.items():
                if key.startswith(section_id + "_"):
                    return value
            raise ValueError(
                f"section_id {section_id} not found in source map (keys: {list(source_map.keys())})"
            )

        for global_idx, section_id in enumerate(section_ids):
            if section_id in header_ids:
                value = get_value_for_section(section_id, header_map)
            elif section_id in body_ids:
                value = get_value_for_section(section_id, body_map)
            elif section_id in footer_ids:
                value = get_value_for_section(section_id, footer_map)
            else:
                raise ValueError(
                    f"section_id {section_id} not in header, body, or footer"
                )
            result[f"{section_id}_{global_idx}"] = value
        return result

    def _get_section_ids_and_map_with_parent(
        self,
        generation_version_id: str,
        parent_generation_version_id: str,
    ) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]], str]:
        """
        Resolve section_ids and map by merging parent header/footer with current body.
        Used for non-homepage compile when parent_generation_version_id is provided.

        Fetches header/footer from parent's generation_template_sections,
        body from current's generation_template_sections.
        """
        current_doc = self.db_service.get_template_sections(generation_version_id)
        if not current_doc:
            raise ValueError(
                f"generation_template_sections not found for "
                f"generation_version_id={generation_version_id}"
            )

        parent_doc = self.db_service.get_template_sections(parent_generation_version_id)
        if not parent_doc:
            raise ValueError(
                f"generation_template_sections not found for parent "
                f"generation_version_id={parent_generation_version_id}"
            )

        page_type = current_doc.get("page_type") or "homepage"

        body_group = current_doc.get("body") or {}
        body_ids = list(body_group.get("section_ids", []))
        body_map = dict(body_group.get("template_unique_section_id_map", {}))

        header_group = parent_doc.get("header") or {}
        header_ids = list(header_group.get("section_ids", []))
        header_map = dict(header_group.get("template_unique_section_id_map", {}))

        footer_group = parent_doc.get("footer") or {}
        footer_ids = list(footer_group.get("section_ids", []))
        footer_map = dict(footer_group.get("template_unique_section_id_map", {}))

        if not body_ids:
            raise ValueError(
                f"No body section_ids in generation_template_sections for "
                f"generation_version_id={generation_version_id}"
            )

        section_ids = header_ids + body_ids + footer_ids
        # Reindex merged map: Previously we used {**header_map, **body_map, **footer_map},
        # but that fails for ipsum_lorem subpages because each group map uses per-group
        # local indices (e.g. body's first section is body_id_0, footer's first is footer_id_0).
        # template_version_builder expects lookup_key = f"{section_id}_{global_index}" where
        # global_index is the position in the full merged list [header + body + footer].
        # Without reindexing, the first body section (global index 1) would be looked up as
        # body_id_1, but body_map only has body_id_0, causing "lookup_key not found".
        template_unique_section_id_map = self._reindex_merged_map(
            section_ids=section_ids,
            header_ids=header_ids,
            body_ids=body_ids,
            footer_ids=footer_ids,
            header_map=header_map,
            body_map=body_map,
            footer_map=footer_map,
        )

        header_unique_ids = extract_ordered_unique_ids(header_map)
        body_unique_ids = extract_ordered_unique_ids(body_map)
        footer_unique_ids = extract_ordered_unique_ids(footer_map)

        section_group_unique_ids = {
            "header_unique_ids": header_unique_ids,
            "body_unique_ids": body_unique_ids,
            "footer_unique_ids": footer_unique_ids,
        }

        logger.info(
            "Resolved sections with parent merge",
            generation_version_id=generation_version_id,
            parent_generation_version_id=parent_generation_version_id,
            page_type=page_type,
            header_count=len(header_ids),
            body_count=len(body_ids),
            footer_count=len(footer_ids),
        )

        return section_ids, template_unique_section_id_map, section_group_unique_ids, page_type

    # ------------------------------------------------------------------
    # Template section creation and modification
    # ------------------------------------------------------------------

    def create_and_save_template_sections(
        self,
        generation_version_id: str,
        section_mappings: List[Dict[str, Any]],
        section_ids: List[str],
        page_type: str,
        existing_map: Optional[Dict[str, str]],
        template_id: Optional[str],
        template_name: Optional[str],
    ) -> Dict[str, str]:
        """
        Create or reuse stable mapping, classify sections, build document, save.

        Returns template_unique_section_id_map.
        """
        if existing_map:
            template_unique_section_id_map = existing_map
            logger.info(
                "Using existing template_unique_section_id_map",
                node="create_and_save_template_sections",
                mapping_size=len(template_unique_section_id_map),
            )
        else:
            template_unique_section_id_map = create_stable_mapping(
                section_ids=section_ids,
                generation_version_id=generation_version_id,
            )
            logger.info(
                "Created template_unique_section_id_map",
                node="create_and_save_template_sections",
                mapping_size=len(template_unique_section_id_map),
            )

        is_homepage = page_type == "homepage"
        if is_homepage:
            header_mappings, body_mappings, footer_mappings = classify_sections(section_mappings)
        else:
            header_mappings, body_mappings, footer_mappings = [], section_mappings, []

        header_group = build_section_group(
            header_mappings, template_unique_section_id_map, section_ids
        )
        body_group = build_section_group(
            body_mappings, template_unique_section_id_map, section_ids
        )
        footer_group = build_section_group(
            footer_mappings, template_unique_section_id_map, section_ids
        )

        logger.info(
            "Classified sections",
            node="create_and_save_template_sections",
            header_count=header_group["section_count"],
            body_count=body_group["section_count"],
            footer_count=footer_group["section_count"],
        )

        document = {
            "generation_version_id": generation_version_id,
            "page_type": page_type,
            "template_id": template_id,
            "template_name": template_name,
            "timestamp": datetime.utcnow().isoformat(),
            "header": header_group,
            "body": body_group,
            "footer": footer_group,
        }

        self.db_service.save_template_sections(
            generation_version_id=generation_version_id,
            document=document,
        )

        return template_unique_section_id_map

    def apply_section_modification(
        self,
        mode: str,
        existing_mappings: List[Dict[str, Any]],
        new_section_mapping: Dict[str, Any],
        section_doc: Dict[str, Any],
        source_thread_id: str,
        generation_version_id: str,
        insert_index: int,
        replace_index: Optional[int],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Validate, update mappings list, create stable mapping with hash preservation.

        Returns (updated_mappings, template_unique_section_id_map).
        """
        source_section_ids, source_unique_map = self.db_service.get_source_section_data(
            source_thread_id
        )

        if mode == "replace":
            if replace_index is None:
                raise ValueError("add_section_replace_index is required for replace mode")

            validate_replace_mode(replace_index, existing_mappings, section_doc)

            updated_mappings = list(existing_mappings)
            new_section_mapping["section_index"] = replace_index + 1
            updated_mappings[replace_index] = new_section_mapping

            for idx, m in enumerate(updated_mappings):
                m["section_index"] = idx + 1

            new_section_ids = extract_section_ids(updated_mappings)

            template_unique_section_id_map = create_stable_mapping_with_replace(
                section_ids=new_section_ids,
                generation_version_id=generation_version_id,
                source_unique_map=source_unique_map,
                source_section_ids=source_section_ids,
                replace_index=replace_index,
            )
        else:
            validate_insert_mode(insert_index, existing_mappings, section_doc)

            updated_mappings = list(existing_mappings)
            new_section_mapping["section_index"] = insert_index + 1
            updated_mappings.insert(insert_index, new_section_mapping)

            for idx, m in enumerate(updated_mappings):
                m["section_index"] = idx + 1

            new_section_ids = extract_section_ids(updated_mappings)

            template_unique_section_id_map = create_stable_mapping_with_insert(
                new_section_ids=new_section_ids,
                generation_version_id=generation_version_id,
                source_unique_map=source_unique_map,
                source_section_ids=source_section_ids,
                inserted_section_id=new_section_mapping.get("section_id", ""),
                insert_index=insert_index,
            )

        return updated_mappings, template_unique_section_id_map

    # ------------------------------------------------------------------
    # Template build (calls external package)
    # ------------------------------------------------------------------

    async def build_template_versions(
        self,
        section_ids: list,
        template_unique_section_id_map: Dict[str, str],
        populated_template_json_override: Optional[Tuple[Dict[str, Any], List]] = None,
    ):
        """
        Call build_template_versions_response with DB connection setup.

        When populated_template_json_override is provided, uses it directly.
        When None, uses ipsum lorem (template_json_builder default).

        Returns TemplateBuildOutput from template_json_builder.
        Replaces ``_build_template_versions`` from db_html_compilation_node.py.
        """
        from template_json_builder.builders.template_version_builder import build_template_versions_response

        mongo_db = db_manager.client[SECTION_REPO_PROD_DB]
        assert isinstance(mongo_db, AsyncIOMotorDatabase), "Expected AsyncIOMotorDatabase"

        return await build_template_versions_response(
            section_id_list=section_ids,
            db_instance=mongo_db,
            populated_template_json_override=populated_template_json_override,
            template_unique_section_id_map=template_unique_section_id_map,
        )

    # ------------------------------------------------------------------
    # Full compile pipeline
    # ------------------------------------------------------------------

    async def compile_template_from_section_ids(
        self,
        generation_version_id: str,
        populated_template_json_override: Optional[Tuple[Dict[str, Any], List]] = None,
        parent_generation_version_id: Optional[str] = None,
    ):
        """
        Compile template from section IDs (DB-driven). Returns TemplateBuildOutput only.
        Does NOT save to DB. Use save_template_build_output to persist.

        When populated_template_json_override is provided (e.g. regenerate_section flow),
        uses it. When None, uses ipsum lorem.

        When parent_generation_version_id is provided (non-homepage), merges parent
        header/footer with current body from generation_template_sections.
        """
        logger.info(
            "compile_template_from_section_ids called",
            generation_version_id=generation_version_id,
            parent_generation_version_id=parent_generation_version_id,
        )

        # STEP 1: Resolve section_ids + map from DB
        if parent_generation_version_id:
            section_ids, template_unique_section_id_map, section_group_unique_ids, page_type = (
                self._get_section_ids_and_map_with_parent(
                    generation_version_id=generation_version_id,
                    parent_generation_version_id=parent_generation_version_id,
                )
            )
        else:
            section_ids, template_unique_section_id_map, section_group_unique_ids, page_type = (
                self.get_section_ids_and_map(generation_version_id)
            )
        if not page_type:
            raise ValueError(
                f"page_type not found for generation_version_id={generation_version_id}"
            )

        if not section_ids:
            raise ValueError(
                f"No section IDs resolved for generation_version_id={generation_version_id}"
            )
        if not template_unique_section_id_map:
            raise ValueError(
                f"template_unique_section_id_map is empty for "
                f"generation_version_id={generation_version_id}"
            )

        logger.info(
            "Resolved sections from DB",
            generation_version_id=generation_version_id,
            section_count=len(section_ids),
            map_size=len(template_unique_section_id_map),
        )

        # STEP 2: Build template (returns TemplateBuildOutput)
        template_build_output = await self.build_template_versions(
            section_ids=section_ids,
            template_unique_section_id_map=template_unique_section_id_map,
            populated_template_json_override=populated_template_json_override,
        )

        if not template_build_output:
            raise Exception("build_template_versions_response returned None")

        logger.info(
            "Template compilation result",
            generation_version_id=generation_version_id,
            sections_count=len(template_build_output.sections),
            enabled_ids_count=len(template_build_output.enabled_section_ids),
        )

        page_structure_info = PageStructureInfo(
            page_type=page_type,
            header_unique_ids=section_group_unique_ids.get("header_unique_ids", []),
            body_unique_ids=section_group_unique_ids.get("body_unique_ids", []),
            footer_unique_ids=section_group_unique_ids.get("footer_unique_ids", []),
        )
        return TemplateWithPageInfo(
            template_build_output=template_build_output,
            page_structure_info=page_structure_info,
        )

    def save_template_build_output(
        self,
        generation_version_id: str,
        template_build_output: Any
    ):
        """
        Save TemplateBuildOutput to generated_templates_with_values.
        Fetches page_type, section_group_unique_ids, template_unique_section_id_map
        from DB via get_section_ids_and_map.
        """
        _, template_unique_section_id_map, section_group_unique_ids, page_type = (
            self.get_section_ids_and_map(generation_version_id)
        )
        self.db_service.save_compiled_template(
            generation_version_id=generation_version_id,
            template_build_output=template_build_output,
            page_type=page_type,
            section_group_unique_ids=section_group_unique_ids,
            template_unique_section_id_map=template_unique_section_id_map,
        )

    async def compile_section_template(
        self,
        section_id: str,
        save_response_to_database: bool = False,
    ):
        """
        Compile template JSON for a single section.
        Uses ipsum_lorem (no autopopulation).
        Returns TemplateBuildOutput. Optionally saves to DB.
        """
        compile_start = time.time()
        section_hash = hashlib.md5(section_id.encode()).hexdigest()[:8]
        lookup_key = f"{section_id}_0"
        unique_id = f"{section_id}_{section_hash}"
        template_unique_section_id_map = {lookup_key: unique_id}

        template_build_output = await self.build_template_versions(
            section_ids=[section_id],
            template_unique_section_id_map=template_unique_section_id_map,
            populated_template_json_override=None,
        )

        if not template_build_output:
            raise Exception("build_template_versions returned None")

        if save_response_to_database:
            generation_version_id = f"single_section_{section_id}"
            section_group_unique_ids = {
                "header_unique_ids": [],
                "body_unique_ids": [unique_id],
                "footer_unique_ids": [],
            }
            self.db_service.save_compiled_template(
                generation_version_id=generation_version_id,
                template_build_output=template_build_output,
                page_type="homepage",
                section_group_unique_ids=section_group_unique_ids,
                template_unique_section_id_map=template_unique_section_id_map,
            )

        total_ms = (time.time() - compile_start) * 1000
        if total_ms > 500:
            logger.warning(
                "Slow section compilation",
                section_id=section_id,
                total_ms=round(total_ms, 2),
            )

        return template_build_output

    async def compile_batch_section_templates(
        self,
        section_ids: List[str]
    ):
        """
        Compile template JSON for multiple sections in a single call.
        Uses ipsum_lorem only (no autopopulation). Does NOT save to DB.
        Returns TemplateBuildOutput.
        """
        from template_json_builder.models.template_build_output import TemplateBuildOutput

        if not section_ids:
            return TemplateBuildOutput(
                sections={},
                enabled_section_ids=[],
                section_id_list=[],
            )

        template_unique_section_id_map = {
            f"{sid}_{index}": f"{sid}_{hashlib.md5(sid.encode()).hexdigest()[:8]}"
            for index, sid in enumerate(section_ids)
        }

        template_build_output = await self.build_template_versions(
            section_ids=section_ids,
            template_unique_section_id_map=template_unique_section_id_map,
            populated_template_json_override=None,
        )

        if not template_build_output:
            raise Exception("build_template_versions returned None")

        return template_build_output

    # ------------------------------------------------------------------
    # Template build output (for HTML compilation, frontend, etc.)
    # ------------------------------------------------------------------

    def get_template_build_output(
        self,
        generation_version_id: str,
        page_type: str,
        parent_generation_version_id: Optional[str],
    ) -> TemplateWithPageInfo:
        """
        Read compiled template from DB and return TemplateWithPageInfo.

        For non-homepage, merges parent header+footer with current body automatically.
        Callers that need (deps, tfa) for HTML compilation must use .template_build_output.
        """
        from template_json_builder.models.template_build_output import TemplateBuildOutput

        raw = self.db_service.get_template_build_output(
            generation_version_id=generation_version_id,
            page_type=page_type,
            parent_generation_version_id=parent_generation_version_id,
        )
        tbo = TemplateBuildOutput.model_validate({
            "sections": raw["sections"],
            "enabled_section_ids": raw["enabled_section_ids"],
            "section_id_list": raw["section_id_list"],
        })
        psi = PageStructureInfo.model_validate(raw["page_structure_info"])
        return TemplateWithPageInfo(
            template_build_output=tbo,
            page_structure_info=psi,
        )

    def save_template_updates(
        self,
        generation_version_id: str,
        request: SaveTemplateRequest,
    ) -> None:
        """
        Apply SaveTemplateRequest to the existing document and overwrite in DB.
        Fetches current doc, applies section_updates, section_order, deleted_sections,
        recomputes metadata, and saves back to the same generation_version_id.
        """
        from template_json_builder.models.template_build_output import TemplateBuildOutput as TBO

        doc = self.db_service.get_compiled_template(generation_version_id)
        if not doc:
            raise ValueError(
                f"generated_templates_with_values not found for {generation_version_id}. "
                "Fetch the template first before applying updates."
            )

        tbo_dict = doc.get("template_build_output")
        if not tbo_dict:
            raise ValueError(
                f"Document {generation_version_id} has no template_build_output."
            )

        page_type = doc.get("page_type", "homepage")

        tbo = TBO.model_validate(tbo_dict)
        existing_ids = doc.get("section_group_unique_ids") or {}
        old_enabled_section_ids = list(tbo_dict.get("enabled_section_ids", []))
        modified_tbo = apply_template_updates(
            tbo,
            request,
            existing_section_group_unique_ids=existing_ids,
        )
        section_group_unique_ids, template_unique_section_id_map = recompute_metadata_from_tbo(
            modified_tbo,
            existing_section_group_unique_ids=existing_ids,
        )

        self.db_service.save_compiled_template(
            generation_version_id=generation_version_id,
            template_build_output=modified_tbo,
            page_type=page_type,
            section_group_unique_ids=section_group_unique_ids,
            template_unique_section_id_map=template_unique_section_id_map,
        )

        if request.deleted_sections or request.section_order:
            self.db_service.propagate_template_updates_to_sections(
                generation_version_id=generation_version_id,
                old_enabled_section_ids=old_enabled_section_ids,
                new_enabled_section_ids=list(modified_tbo.enabled_section_ids),
                new_section_id_list=list(modified_tbo.section_id_list),
                page_type=page_type,
            )

        logger.info(
            "Saved template updates",
            generation_version_id=generation_version_id,
            sections_count=len(modified_tbo.sections),
        )


template_builder_service = TemplateBuilderService(template_db_service)
