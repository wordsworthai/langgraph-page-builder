from typing import Protocol, List, Dict, Any


class Collector(Protocol):
    name: str
    async def collect(self, page, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...


