from functools import lru_cache
import os


@lru_cache(maxsize=32)
def get_js(name: str) -> str:
    """
    Load a JS function source from section_rag_utils/js/<name>, cache in memory.
    """
    base_dir = os.path.join(os.path.dirname(__file__), "..", "js")
    path = os.path.normpath(os.path.join(base_dir, name))
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


