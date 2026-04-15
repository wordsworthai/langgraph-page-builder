"""
Database utility functions for common save and read operations.

Provides generic upsert/fetch helpers keyed by generation_version_id.

Template-specific DB operations have been moved to:
  ``utils.landing_page_builder.template.db_service.TemplateDBService``
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pymongo.results import UpdateResult

from wwai_agent_orchestration.core.database import db_manager

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)

PROMPT_TRACES_COLLECTION = "prompt_traces"
PROMPT_TRACES_DB_NAME = "eval"


def upsert_by_generation_version_id(
    collection_name: str,
    generation_version_id: str,
    document: Dict[str, Any],
) -> UpdateResult:
    """
    Upsert a document to a MongoDB collection using generation_version_id as the key.

    This is a common pattern for saving workflow outputs where each generation
    run is identified by a unique generation_version_id.

    Args:
        collection_name: Name of the MongoDB collection
        generation_version_id: Unique identifier for the generation run (used as query key)
        document: Document data to upsert

    Returns:
        UpdateResult from MongoDB with matched_count and upserted_id

    Raises:
        Exception: If database connection fails or upsert operation fails
    """

    try:
        db_name = 'template_generation'
        db = db_manager.get_database(db_name)
        collection = db[collection_name]

        result = collection.update_one(
            {"generation_version_id": generation_version_id},
            {"$set": document},
            upsert=True
        )

        if result.matched_count > 0:
            logger.info(
                f"Updated existing document in '{collection_name}': {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id
            )
        elif result.upserted_id:
            logger.info(
                f"Inserted new document in '{collection_name}': {result.upserted_id}",
                collection=collection_name,
                generation_version_id=generation_version_id,
                inserted_id=str(result.upserted_id)
            )

        return result

    except Exception as e:
        logger.error(
            f"Failed to upsert document in '{collection_name}': {str(e)}",
            collection=collection_name,
            generation_version_id=generation_version_id,
            error=str(e)
        )
        raise


def fetch_by_generation_version_id(
    collection_name: str,
    generation_version_id: str,
    db_name: str = "template_generation",
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single document from a MongoDB collection by generation_version_id.

    Args:
        collection_name: Name of the MongoDB collection
        generation_version_id: Unique identifier for the generation run
        db_name: MongoDB database name (default: template_generation)

    Returns:
        The document dict if found, None otherwise.

    Raises:
        Exception: If database connection fails
    """

    try:
        db = db_manager.get_database(db_name)
        collection = db[collection_name]

        doc = collection.find_one({"generation_version_id": generation_version_id})

        if doc:
            logger.info(
                f"Fetched document from '{collection_name}': {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id
            )
        else:
            logger.warning(
                f"No document found in '{collection_name}' for: {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id
            )

        return doc

    except Exception as e:
        logger.error(
            f"Failed to fetch document from '{collection_name}': {str(e)}",
            collection=collection_name,
            generation_version_id=generation_version_id,
            error=str(e)
        )
        raise


def append_prompt_trace(
    generation_version_id: str,
    trace: Dict[str, Any],
    db_name: str = PROMPT_TRACES_DB_NAME,
    collection_name: str = PROMPT_TRACES_COLLECTION,
) -> None:
    """
    Append a single prompt trace to the document for generation_version_id.

    Uses $push to append to traces array and $set for updated_at.
    Creates the document if it does not exist.

    Args:
        generation_version_id: Unique identifier for the generation run
        trace: Trace record dict (prompt_name, task_name, invoke_input, result, timestamp_iso, duration_ms, mode)
        db_name: MongoDB database name (default: template_generation)
        collection_name: MongoDB collection name (default: prompt_traces)

    Raises:
        Exception: If database connection fails or update operation fails
    """
    try:
        db = db_manager.get_database(db_name)
        collection = db[collection_name]
        updated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        result = collection.update_one(
            {"generation_version_id": generation_version_id},
            {
                "$push": {"traces": trace},
                "$set": {
                    "generation_version_id": generation_version_id,
                    "updated_at": updated_at,
                },
            },
            upsert=True,
        )

        if result.matched_count > 0 or result.upserted_id:
            logger.debug(
                f"Appended prompt trace to '{collection_name}': {generation_version_id}",
                collection=collection_name,
                generation_version_id=generation_version_id,
            )

    except Exception as e:
        logger.error(
            f"Failed to append prompt trace in '{collection_name}': {str(e)}",
            collection=collection_name,
            generation_version_id=generation_version_id,
            error=str(e)
        )
        raise
