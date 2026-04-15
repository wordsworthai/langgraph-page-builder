# core/database/operations.py
"""Common database operations for MongoDB collections."""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

from langsmith import traceable

from wwai_agent_orchestration.core.observability.logger import get_logger, get_request_context, is_perf_logging_enabled

logger = get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found in the collection."""
    pass


class OperationError(Exception):
    """Raised when a database operation fails."""
    pass


@traceable(run_type="tool", name="Mongo: fetch_from_collection")
def fetch_from_collection(
    collection_name: str,
    query: Dict[str, Any],
    database: Database,
    projection: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    sort: Optional[List[tuple]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch documents from a MongoDB collection based on query.
    
    Args:
        collection_name: Name of the collection to query
        query: MongoDB query filter (e.g., {"status": "active"})
        database: MongoDB Database instance
        projection: Fields to include/exclude (e.g., {"_id": 0, "name": 1})
        limit: Maximum number of documents to return
        sort: List of (field, direction) tuples (e.g., [("created_at", -1)])
        
    Returns:
        List of documents matching the query
        
    Raises:
        DocumentNotFoundError: If no documents match the query
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        templates = fetch_from_collection(
            "templates",
            {"type": "hero", "status": "active"},
            db,
            projection={"_id": 0},
            limit=10,
            sort=[("created_at", -1)]
        )
    """
    start = time.perf_counter()
    start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        collection: Collection = database[collection_name]

        # Build cursor
        cursor = collection.find(query, projection)

        if sort:
            cursor = cursor.sort(sort)

        if limit:
            cursor = cursor.limit(limit)

        # Execute query
        results = list(cursor)

        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if is_perf_logging_enabled():
            ctx = get_request_context()
            logger.info(
                "Mongo operation",
                metric_type="perf_mongo",
                operation="fetch",
                collection_name=collection_name,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
                **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
            )

        if not results:
            logger.warning(
                f"No documents found in '{collection_name}' with query: {query}"
            )
            raise DocumentNotFoundError(
                f"No documents found in collection '{collection_name}' "
                f"matching query: {query}"
            )

        logger.info(
            f"Fetched {len(results)} document(s) from '{collection_name}' "
            f"with query: {query}"
        )
        return results

    except DocumentNotFoundError:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching from collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to fetch from collection '{collection_name}': {str(e)}"
        )


@traceable(run_type="tool", name="Mongo: fetch_one_from_collection")
def fetch_one_from_collection(
    collection_name: str,
    query: Dict[str, Any],
    database: Database,
    projection: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single document from a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to query
        query: MongoDB query filter
        database: MongoDB Database instance
        projection: Fields to include/exclude
        
    Returns:
        Single document or None if not found
        
    Raises:
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        template = fetch_one_from_collection(
            "templates",
            {"template_id": "hero_001"},
            db
        )
    """
    start = time.perf_counter()
    start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        collection: Collection = database[collection_name]
        result = collection.find_one(query, projection)

        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if is_perf_logging_enabled():
            ctx = get_request_context()
            logger.info(
                "Mongo operation",
                metric_type="perf_mongo",
                operation="fetch_one",
                collection_name=collection_name,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
                **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
            )

        if result:
            logger.info(
                f"Found document in '{collection_name}' with query: {query}"
            )
        else:
            logger.info(
                f"No document found in '{collection_name}' with query: {query}"
            )

        return result

    except Exception as e:
        logger.error(
            f"Error fetching from collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to fetch from collection '{collection_name}': {str(e)}"
        )


@traceable(run_type="tool", name="Mongo: upsert_document")
def upsert_document(
    collection_name: str,
    query: Dict[str, Any],
    data: Dict[str, Any],
    database: Database
) -> Dict[str, Any]:
    """
    Upsert a document into a MongoDB collection.
    If a document matching the query exists, it is updated.
    If no matching document exists, the data is inserted as a new document.
    
    Args:
        collection_name: Name of the collection
        query: Query to find the document (e.g., {"template_id": "hero_001"})
        data: Data to insert or update
        database: MongoDB Database instance
        
    Returns:
        The upserted data
        
    Raises:
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        upsert_document(
            "templates",
            {"template_id": "hero_001"},
            {"name": "Hero Template", "status": "active"},
            db
        )
    """
    start = time.perf_counter()
    start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        collection: Collection = database[collection_name]

        # Perform upsert
        result: UpdateResult = collection.update_one(
            query,
            {"$set": data},
            upsert=True
        )

        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if is_perf_logging_enabled():
            ctx = get_request_context()
            logger.info(
                "Mongo operation",
                metric_type="perf_mongo",
                operation="upsert",
                collection_name=collection_name,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
                **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
            )

        if result.matched_count > 0:
            logger.info(
                f"Updated existing document in '{collection_name}' "
                f"with query: {query}"
            )
        elif result.upserted_id:
            logger.info(
                f"Inserted new document in '{collection_name}' "
                f"with _id: {result.upserted_id}"
            )
        else:
            raise OperationError(
                f"Upsert failed for collection '{collection_name}'"
            )
        
        return data
        
    except OperationError:
        raise
    except Exception as e:
        logger.error(
            f"Error upserting to collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to upsert to collection '{collection_name}': {str(e)}"
        )


@traceable(run_type="tool", name="Mongo: insert_document")
def insert_document(
    collection_name: str,
    data: Dict[str, Any],
    database: Database
) -> str:
    """
    Insert a single document into a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        data: Document data to insert
        database: MongoDB Database instance
        
    Returns:
        Inserted document ID as string
        
    Raises:
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        doc_id = insert_document(
            "templates",
            {"name": "New Template", "type": "hero"},
            db
        )
    """
    start = time.perf_counter()
    start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        collection: Collection = database[collection_name]
        result: InsertOneResult = collection.insert_one(data)

        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if is_perf_logging_enabled():
            ctx = get_request_context()
            logger.info(
                "Mongo operation",
                metric_type="perf_mongo",
                operation="insert",
                collection_name=collection_name,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
                **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
            )

        logger.info(
            f"Inserted document in '{collection_name}' "
            f"with _id: {result.inserted_id}"
        )

        return str(result.inserted_id)

    except Exception as e:
        logger.error(
            f"Error inserting to collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to insert to collection '{collection_name}': {str(e)}"
        )


@traceable(run_type="tool", name="Mongo: update_document")
def update_document(
    collection_name: str,
    query: Dict[str, Any],
    update_data: Dict[str, Any],
    database: Database,
    upsert: bool = False
) -> int:
    """
    Update document(s) in a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        query: Query to find document(s) to update
        update_data: Update operations (e.g., {"$set": {"status": "inactive"}})
        database: MongoDB Database instance
        upsert: If True, insert if no match found
        
    Returns:
        Number of documents modified
        
    Raises:
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        count = update_document(
            "templates",
            {"type": "hero"},
            {"$set": {"reviewed": True}},
            db
        )
    """
    start = time.perf_counter()
    start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        collection: Collection = database[collection_name]
        result: UpdateResult = collection.update_one(
            query,
            update_data,
            upsert=upsert
        )

        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if is_perf_logging_enabled():
            ctx = get_request_context()
            logger.info(
                "Mongo operation",
                metric_type="perf_mongo",
                operation="update",
                collection_name=collection_name,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
                **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
            )

        logger.info(
            f"Updated {result.modified_count} document(s) in '{collection_name}' "
            f"with query: {query}"
        )

        return result.modified_count

    except Exception as e:
        logger.error(
            f"Error updating collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to update collection '{collection_name}': {str(e)}"
        )


@traceable(run_type="tool", name="Mongo: delete_document")
def delete_document(
    collection_name: str,
    query: Dict[str, Any],
    database: Database
) -> int:
    """
    Delete document(s) from a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        query: Query to find document(s) to delete
        database: MongoDB Database instance
        
    Returns:
        Number of documents deleted
        
    Raises:
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        count = delete_document(
            "templates",
            {"status": "archived"},
            db
        )
    """
    try:
        collection: Collection = database[collection_name]
        result: DeleteResult = collection.delete_many(query)
        
        logger.info(
            f"Deleted {result.deleted_count} document(s) from '{collection_name}' "
            f"with query: {query}"
        )
        
        return result.deleted_count
        
    except Exception as e:
        logger.error(
            f"Error deleting from collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to delete from collection '{collection_name}': {str(e)}"
        )


@traceable(run_type="tool", name="Mongo: count_documents")
def count_documents(
    collection_name: str,
    query: Dict[str, Any],
    database: Database
) -> int:
    """
    Count documents in a MongoDB collection matching the query.
    
    Args:
        collection_name: Name of the collection
        query: MongoDB query filter
        database: MongoDB Database instance
        
    Returns:
        Count of matching documents
        
    Raises:
        OperationError: If the operation fails
        
    Example:
        db = db_manager.get_database()
        active_count = count_documents(
            "templates",
            {"status": "active"},
            db
        )
    """
    try:
        collection: Collection = database[collection_name]
        count = collection.count_documents(query)
        
        logger.debug(
            f"Counted {count} document(s) in '{collection_name}' "
            f"with query: {query}"
        )
        
        return count
        
    except Exception as e:
        logger.error(
            f"Error counting in collection '{collection_name}': {str(e)}"
        )
        raise OperationError(
            f"Failed to count in collection '{collection_name}': {str(e)}"
        )