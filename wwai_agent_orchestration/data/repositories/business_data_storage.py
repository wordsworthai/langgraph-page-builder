"""
Business scraped data storage for workflow nodes.

NOTE:
- This module now uses the shared global db_manager proxy from
  wwai_agent_orchestration.core.database so that reads/writes here use
  the same Mongo connection configuration as the rest of the app
  (including providers and section cache utilities).
"""
import traceback
from typing import Dict, Any

from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.core.database.mongo.operations import (
    upsert_document,
    fetch_one_from_collection,
    OperationError
)

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)

COLLECTION_NAME = "business_scraped_data"
DATABASE_NAME = "businesses"  # Database where business_* collections live


def get_db_manager():
    """
    Return the shared global database manager proxy.
    
    This ensures business_data_storage uses the same Mongo connection
    as the rest of the application (configured via configure_database).
    """
    return db_manager


def store_yelp_data_sync(
    business_id: str,
    yelp_url: str,
    data: Dict[str, Any]
) -> bool:
    """
    Store Yelp scraped data in MongoDB (synchronous).
    
    Args:
        business_id: Business UUID as string
        yelp_url: Yelp URL (used as key)
        data: Yelp data dict to store
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get database - use "businesses" database
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)  # ✅ Pass database name
        
        # Get existing document (to preserve google_maps_data)
        existing_doc = fetch_one_from_collection(
            COLLECTION_NAME,
            {"business_id": business_id},
            db
        )
        
        # Prepare update dict
        update_dict = {
            "business_id": business_id,
            "yelp_data": {
                "key": yelp_url,
                "value": data
            }
        }
        
        # Preserve google_maps_data if exists
        if existing_doc and "google_maps_data" in existing_doc:
            update_dict["google_maps_data"] = existing_doc["google_maps_data"]
        
        # Upsert document
        upsert_document(
            COLLECTION_NAME,
            {"business_id": business_id},
            update_dict,
            db
        )
        
        logger.info(
            f"✅ Stored Yelp data for business {business_id}",
            node="business_data_storage",
            database=DATABASE_NAME,
            collection=COLLECTION_NAME
        )
        return True
        
    except OperationError as e:
        logger.error(f"❌ Failed to store Yelp data: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error storing Yelp data: {str(e)}")
        return False


def store_google_maps_data_sync(
    business_id: str,
    google_maps_url: str,
    data: Dict[str, Any]
) -> bool:
    """
    Store Google Maps scraped data in MongoDB (synchronous).
    
    Args:
        business_id: Business UUID as string
        google_maps_url: Google Maps URL
        data: Google Maps data dict to store
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get database - use "businesses" database
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)  # ✅ Pass database name
        
        # Prepare update dict
        update_dict = {
            "business_id": business_id,
            "google_maps_data": {
                "key": google_maps_url,
                "value": data
            }
        }
        
        # Upsert document
        upsert_document(
            COLLECTION_NAME,
            {"business_id": business_id},
            update_dict,
            db
        )
        
        logger.info(
            f"✅ Stored Google Maps data for business {business_id}",
            node="business_data_storage",
            database=DATABASE_NAME,
            collection=COLLECTION_NAME
        )
        return True
        
    except OperationError as e:
        logger.error(f"❌ Failed to store Google Maps data: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error storing Google Maps data: {str(e)}")
        return False


def get_yelp_data_sync(business_id: str) -> Dict[str, Any] | None:
    """
    Retrieve stored Yelp data for a business.
    
    Args:
        business_id: Business UUID as string
        
    Returns:
        Yelp data dict or None
    """
    try:
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)  # ✅ Pass database name
        
        doc = fetch_one_from_collection(
            COLLECTION_NAME,
            {"business_id": business_id},
            db
        )
        
        if doc and "yelp_data" in doc:
            return doc["yelp_data"].get("value")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve Yelp data: {str(e)}")
        return None


def get_google_maps_data_sync(business_id: str) -> Dict[str, Any] | None:
    """
    Retrieve stored Google Maps data for a business.
    
    Args:
        business_id: Business UUID as string
        
    Returns:
        Google Maps data dict or None
    """
    try:
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)  # ✅ Pass database name
        
        doc = fetch_one_from_collection(
            COLLECTION_NAME,
            {"business_id": business_id},
            db
        )
        
        if doc and "google_maps_data" in doc:
            return doc["google_maps_data"].get("value")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve Google Maps data: {str(e)}")
        return None
    

def store_trade_classification_by_cache_key_sync(
    cache_key: str,
    trade_assignments: Dict[str, Any]
) -> bool:
    """
    Store trade classification results in MongoDB (synchronous).
    Uses cache_key (business_id:location_id) as the unique document key.
    
    Args:
        cache_key: Composite key e.g. "business_id:place_id" or "anon:location_id"
        trade_assignments: Trade classification result dict (must include business_id if available)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not cache_key or not trade_assignments:
            logger.error(
                "❌ cache_key or trade_assignments empty",
                node="business_data_storage"
            )
            return False
        
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)
        
        document = {
            "cache_key": cache_key,
            **trade_assignments
        }
        
        upsert_document(
            "business_types",
            {"cache_key": cache_key},
            document,
            db
        )
        
        verification_doc = fetch_one_from_collection(
            "business_types",
            {"cache_key": cache_key},
            db
        )
        
        if not verification_doc:
            logger.error(
                f"❌ Verification failed after upsert for cache_key={cache_key}",
                node="business_data_storage"
            )
            return False
        
        logger.info(
            f"✅ Stored trade classification for cache_key={cache_key}",
            node="business_data_storage",
            trades_count=len(trade_assignments.get("assigned_trades", [])),
        )
        return True
        
    except OperationError as e:
        logger.error(
            f"❌ Failed to store trade classification: {str(e)}",
            node="business_data_storage",
            traceback=traceback.format_exc()
        )
        return False
    except Exception as e:
        logger.error(
            f"❌ Unexpected error storing trade classification: {str(e)}",
            node="business_data_storage",
            traceback=traceback.format_exc()
        )
        return False


def get_trade_classification_by_cache_key_sync(cache_key: str) -> Dict[str, Any] | None:
    """
    Retrieve stored trade classification by cache_key.
    
    Args:
        cache_key: Composite key e.g. "business_id:place_id"
        
    Returns:
        Trade classification dict or None
    """
    try:
        if not cache_key:
            return None
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)
        doc = fetch_one_from_collection(
            "business_types",
            {"cache_key": cache_key},
            db
        )
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve trade classification: {str(e)}")
        return None


def get_trade_classification_by_business_id_sync(business_id: str) -> Dict[str, Any] | None:
    """
    Retrieve most recent trade classification for a business (by business_id).
    Used by callers that don't have location context. Returns the latest doc.
    
    Args:
        business_id: Business UUID as string
        
    Returns:
        Trade classification dict or None
    """
    try:
        if not business_id:
            return None
        db_manager = get_db_manager()
        db = db_manager.get_database(DATABASE_NAME)
        collection = db["business_types"]
        doc = collection.find_one(
            {"business_id": business_id},
            sort=[("classified_at", -1)]
        )
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve trade classification by business_id: {str(e)}")
        return None