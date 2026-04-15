"""
Checkpoint utilities for fetching and decoding LangGraph checkpoints from MongoDB.
"""
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo.database import Database
import msgpack
import zlib

from wwai_agent_orchestration.core.observability.logger import get_logger, get_request_context, is_perf_logging_enabled

logger = get_logger(__name__)


def _decode_msgpack_bytes(raw: bytes) -> Any:
    """Decode raw bytes as msgpack, with zlib decompression fallback."""
    try:
        raw = zlib.decompress(raw)
    except zlib.error:
        pass
    try:
        return msgpack.unpackb(raw, raw=False, strict_map_key=False)
    except Exception:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return f"<undecoded binary: {len(raw)} bytes>"


def _decode_langgraph_serde_value(value: Any) -> Any:
    """Decode LangGraph's serialization format.

    Handles [type_id, bytes] format where type_id may be "msgpack" or a numeric code (e.g. 5).
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        _, data = value
        if isinstance(data, (bytes, bytearray)):
            return _decode_msgpack_bytes(bytes(data))
    if isinstance(value, (bytes, bytearray)):
        return _decode_msgpack_bytes(bytes(value))
    try:
        raw = bytes(value)
        return _decode_msgpack_bytes(raw)
    except (TypeError, ValueError):
        pass
    return value


def _decode_nested_serde(obj: Any) -> Any:
    """Recursively decode LangGraph serde blobs in nested structures."""
    if obj is None:
        return None
    if isinstance(obj, (list, tuple)) and len(obj) == 2:
        _, data = obj
        if isinstance(data, (bytes, bytearray)):
            decoded = _decode_langgraph_serde_value(obj)
            return _decode_nested_serde(decoded)
    if isinstance(obj, dict):
        return {k: _decode_nested_serde(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_decode_nested_serde(item) for item in obj]
    return obj


def _decode_metadata(metadata: dict) -> dict:
    """Recursively decode all metadata values."""
    if not isinstance(metadata, dict):
        return metadata
    decoded = {}
    for key, value in metadata.items():
        if isinstance(value, dict):
            decoded[key] = _decode_metadata(value)
        else:
            decoded[key] = _decode_langgraph_serde_value(value)
    return decoded


def _is_uuid(s: str) -> bool:
    import re
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    return bool(uuid_pattern.match(s))


def _extract_node_name_from_writes(writes: List[Dict], source: str = None) -> Optional[str]:
    for write in writes:
        if write.get("channel") == "ui_execution_log":
            value = write.get("value")
            if isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict) and "node_name" in value[0]:
                    return value[0]["node_name"]
    return None


def fetch_full_checkpoint_history(
    db: Database,
    thread_id: str,
    checkpoint_collection: str = "checkpoints",
    writes_collection: str = "checkpoint_writes",
) -> List[Dict[str, Any]]:
    """Fetch ALL checkpoints for a thread_id and build the execution history chain."""
    ckpt_col = db[checkpoint_collection]
    wr_col = db[writes_collection]

    start = time.perf_counter()
    start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    all_ckpts = list(ckpt_col.find({"thread_id": thread_id}))
    duration_ms = (time.perf_counter() - start) * 1000
    end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if is_perf_logging_enabled():
        ctx = get_request_context()
        logger.info("Mongo operation", metric_type="perf_mongo", operation="checkpoint_list",
            collection_name=checkpoint_collection, start_time=start_time_iso, end_time=end_time_iso,
            duration_ms=round(duration_ms, 2), **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")})

    if not all_ckpts:
        return []

    ckpt_map = {doc["checkpoint_id"]: doc for doc in all_ckpts}
    roots = [doc for doc in all_ckpts if doc.get("parent_checkpoint_id") is None]
    child_map: Dict[str, List[str]] = {}
    for doc in all_ckpts:
        parent_id = doc.get("parent_checkpoint_id")
        if parent_id:
            if parent_id not in child_map:
                child_map[parent_id] = []
            child_map[parent_id].append(doc["checkpoint_id"])

    execution_order = []
    queue = [r["checkpoint_id"] for r in roots]
    visited = set()

    while queue:
        ckpt_id = queue.pop(0)
        if ckpt_id in visited:
            continue
        visited.add(ckpt_id)
        doc = ckpt_map[ckpt_id]
        checkpoint_blob = doc.get("checkpoint")
        decoded_checkpoint = _decode_langgraph_serde_value(checkpoint_blob) if checkpoint_blob else None
        if isinstance(decoded_checkpoint, str):
            decoded_checkpoint = {}
        decoded_metadata = _decode_metadata(doc.get("metadata", {}))

        wr_start = time.perf_counter()
        wr_start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        writes_cursor = wr_col.find({"thread_id": thread_id, "checkpoint_id": ckpt_id}).sort([("idx", 1)])
        writes = []
        for wdoc in writes_cursor:
            val_blob = wdoc.get("value")
            decoded_val = _decode_langgraph_serde_value(val_blob) if val_blob else None
            decoded_val = _decode_nested_serde(decoded_val) if decoded_val is not None else None
            writes.append({"idx": wdoc.get("idx"), "channel": wdoc.get("channel"), "task_id": wdoc.get("task_id"), "value": decoded_val})

        wr_duration_ms = (time.perf_counter() - wr_start) * 1000
        wr_end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if is_perf_logging_enabled():
            logger.info("Mongo operation", metric_type="perf_mongo", operation="checkpoint_writes",
                collection_name=writes_collection, start_time=wr_start_time_iso, end_time=wr_end_time_iso,
                duration_ms=round(wr_duration_ms, 2), **{k: v for k, v in get_request_context().items() if k in ("request_id", "workflow_id")})

        step = decoded_metadata.get("step", "?")
        source = decoded_metadata.get("source", "?")
        node_name = _extract_node_name_from_writes(writes, source)
        if node_name and not _is_uuid(node_name):
            display_name = node_name
        elif source and not _is_uuid(source) and source != "?":
            display_name = source
        else:
            display_name = "__start__" if step == -1 or step == 0 else f"step_{step}"

        raw_channel_values = decoded_checkpoint.get("channel_values", {}) if isinstance(decoded_checkpoint, dict) else {}
        channel_values = _decode_nested_serde(raw_channel_values)

        execution_order.append({
            "checkpoint_id": ckpt_id, "parent_checkpoint_id": doc.get("parent_checkpoint_id"),
            "step": step, "source": source, "node_name": display_name, "metadata": decoded_metadata,
            "checkpoint_state": decoded_checkpoint, "writes": writes,
            "channel_values": channel_values,
            "updated_channels": decoded_checkpoint.get("updated_channels", []) if isinstance(decoded_checkpoint, dict) else [],
        })
        for child_id in child_map.get(ckpt_id, []):
            queue.append(child_id)

    execution_order.sort(key=lambda x: x["step"] if isinstance(x["step"], int) else -999)
    execution_order = _resolve_loop_node_names(execution_order)
    return execution_order


def _resolve_loop_node_names(execution_order: List[Dict]) -> List[Dict]:
    if len(execution_order) < 2:
        return execution_order
    parallel_count = 0
    for entry in execution_order:
        if entry.get("node_name") == "loop":
            parallel_count += 1
            entry["node_name"] = f"parallel_{parallel_count}"
            entry["is_parallel"] = True
    return execution_order


def get_all_thread_ids(db: Database, checkpoint_collection: str = "checkpoints", limit: int = 50) -> List[Dict[str, Any]]:
    ckpt_col = db[checkpoint_collection]
    pipeline = [{"$group": {"_id": "$thread_id", "count": {"$sum": 1}, "latest": {"$max": "$_id"}}}, {"$sort": {"latest": -1}}, {"$limit": limit}]
    results = list(ckpt_col.aggregate(pipeline))
    return [{"thread_id": r["_id"], "checkpoint_count": r["count"]} for r in results]


def make_json_serializable(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return f"<binary {len(obj)} bytes>"
    if isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    if hasattr(obj, '__dict__'):
        return str(obj)
    return str(obj)
