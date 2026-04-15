from typing import Any, Callable, Dict, TypedDict


DebugHandler = Callable[[Dict[str, Any], bool], Any]


class DataDebugTargetConfig(TypedDict):
    label: str
    category: str
    description: str
    external_call: bool
    sample_args: Dict[str, Any]
    handler: DebugHandler
    result_renderer: str | None
    random_args_generator: str | None

