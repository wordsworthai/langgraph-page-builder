"""Shared constants and helpers for routers."""
from wwai_agent_orchestration.core.database import db_manager, DocumentNotFoundError
from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import make_json_serializable

DEFAULT_MONGO_URI = "mongodb://localhost:27020"
DEFAULT_DB_NAME = "eval"


def _get_checkpoint_db():
    """Get checkpoint database from global db_manager."""
    return db_manager.get_database("checkpointing_db")
