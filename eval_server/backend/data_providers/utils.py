from typing import Any, Dict


def require_arg(args: Dict[str, Any], key: str) -> Any:
    value = args.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required arg: {key}")
    return value


def to_plain_object(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, list):
        return [to_plain_object(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain_object(v) for k, v in value.items()}
    return value

