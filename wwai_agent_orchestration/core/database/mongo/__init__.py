# # core/database/mongo/__init__.py
# """MongoDB utilities for Wordsworth AI."""

# from .config import DatabaseConfig
# from .manager import DatabaseManager
# from .operations import (
#     fetch_from_collection,
#     fetch_one_from_collection,
#     upsert_document,
#     insert_document,
#     update_document,
#     delete_document,
#     count_documents,
#     DocumentNotFoundError,
#     OperationError
# )
# from .connection import ConnectionError

# __all__ = [
#     # Core classes
#     "DatabaseConfig",
#     "DatabaseManager",
    
#     # Operations
#     "fetch_from_collection",
#     "fetch_one_from_collection",
#     "upsert_document",
#     "insert_document",
#     "update_document",
#     "delete_document",
#     "count_documents",
    
#     # Exceptions
#     "DocumentNotFoundError",
#     "OperationError",
#     "ConnectionError",
# ]