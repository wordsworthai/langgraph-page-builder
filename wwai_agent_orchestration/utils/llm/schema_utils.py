# utils/llm/schema_utils.py
"""
Schema utilities for LLM structured output.

Google Gemini does not support JSON Schema keys like $defs and "parameters".
This module converts Pydantic-style JSON schema to flat, Gemini-compatible schema.
"""

from typing import Any, Dict, Optional


def _resolve_ref_to_def(ref: str, defs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not ref.startswith("#/$defs/"):
        return None
    key = ref.replace("#/$defs/", "")
    if key not in defs:
        return None
    sub = defs[key].copy()
    return _inline_refs_in_place(sub, defs, root=False)


def _inline_refs_in_place(obj: Any, defs: Dict[str, Any], root: bool = True) -> Any:
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            inlined = _resolve_ref_to_def(ref, defs)
            if inlined is not None:
                other = {k: _inline_refs_in_place(v, defs, root=False) for k, v in obj.items() if k != "$ref"}
                result = {**inlined}
                for k, v in other.items():
                    result[k] = v
                return result
        out = {}
        for k, v in obj.items():
            if root and k in ("$defs", "parameters"):
                continue
            out[k] = _inline_refs_in_place(v, defs, root=False)
        return out
    if isinstance(obj, list):
        return [_inline_refs_in_place(i, defs, root=False) for i in obj]
    return obj


def _add_additional_properties_false(obj: Any, defs: Dict[str, Any]) -> Any:
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            resolved = _resolve_ref_to_def(ref, defs)
            if resolved is not None:
                out = _add_additional_properties_false(resolved, defs)
                if isinstance(out, dict) and ("properties" in out or out.get("type") == "object"):
                    out = {**out, "additionalProperties": False}
                return out
        out = {}
        for k, v in obj.items():
            out[k] = _add_additional_properties_false(v, defs)
        if "properties" in out or out.get("type") == "object":
            out["additionalProperties"] = False
        return out
    if isinstance(obj, list):
        return [_add_additional_properties_false(i, defs) for i in obj]
    return obj


def json_schema_openai_strict(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return JSON schema satisfying OpenAI's structured output requirements."""
    if not schema:
        return schema
    defs = schema.get("$defs", {})
    copy = {k: v for k, v in schema.items() if k != "$defs"}
    return _add_additional_properties_false(copy, defs)


def json_schema_to_gemini_compatible(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Pydantic-style JSON schema to Gemini-compatible form."""
    if not schema:
        return schema
    defs = schema.get("$defs", {})
    copy = {k: v for k, v in schema.items() if k not in ("$defs", "parameters")}
    return _inline_refs_in_place(copy, defs, root=True)
