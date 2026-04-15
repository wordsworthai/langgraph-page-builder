from wwai_agent_orchestration.evals.checkpoints.checkpoint_reader import CheckpointReader


class _State:
    def __init__(self, values):
        self.values = values


class _Graph:
    def __init__(self, values):
        self._values = values

    def get_state(self, _config):
        return _State(self._values)


class _Workflow:
    def __init__(self, values):
        self.config = {"foo": "bar"}
        self.graph = _Graph(values)


def test_checkpoint_reader_uses_workflow_graph_state():
    reader = CheckpointReader(history_fetcher=lambda _: [])
    workflow = _Workflow({"generation_version_id": "gen_1"})
    state = reader.get_final_state("thread_1", workflow=workflow)
    assert state["generation_version_id"] == "gen_1"


def test_checkpoint_reader_falls_back_to_history():
    history = [{"channel_values": {"generation_version_id": "gen_hist"}}]
    reader = CheckpointReader(history_fetcher=lambda _: history)
    state = reader.get_final_state("thread_2")
    assert state["generation_version_id"] == "gen_hist"
    assert reader.get_history("thread_2") == history

