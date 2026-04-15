"""
Prompt trace constants for recording LLM prompt calls by generation_version_id.

Controlled via environment variables:
- WWAI_AGENT_ORCHESTRATION_ENABLE_PROMPT_TRACE: Set to "true" to record prompt traces (default: "false")
- WWAI_AGENT_ORCHESTRATION_PROMPT_TRACE_WRITE_TO_DB: Set to "true"/"false" to persist to MongoDB (default: "true" when trace enabled)
"""

import os

_ENABLE = os.getenv("WWAI_AGENT_ORCHESTRATION_ENABLE_PROMPT_TRACE", "true").lower() == "true"
_WRITE_TO_DB = os.getenv("WWAI_AGENT_ORCHESTRATION_PROMPT_TRACE_WRITE_TO_DB", "true").lower() == "true"

ENABLE_PROMPT_TRACE: bool = _ENABLE
PROMPT_TRACE_WRITE_TO_DB: bool = _WRITE_TO_DB if _ENABLE else False
