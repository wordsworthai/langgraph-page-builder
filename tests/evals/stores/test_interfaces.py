from wwai_agent_orchestration.evals.stores.interfaces import EvalStore
from wwai_agent_orchestration.evals.stores.local_jsonl_store import LocalJsonlEvalStore


def test_local_jsonl_implements_eval_store_protocol(tmp_path):
    store = LocalJsonlEvalStore(root_dir=tmp_path)
    assert isinstance(store, EvalStore)

