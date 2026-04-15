"""API routers for the eval server."""
from .checkpoints import router as checkpoints_router
from .code_editor import router as code_editor_router
from .curated_pages import router as curated_pages_router
from .eval import router as eval_router
from .feedback import router as feedback_router
from .metrics import router as metrics_router
from .prompt_traces import router as prompt_traces_router
from .task_config import router as task_config_router
from .business import router as business_router
from .section_repo import router as section_repo_router
from .health import router as health_router


def get_all_routers():
    return [
        checkpoints_router,
        code_editor_router,
        eval_router,
        feedback_router,
        metrics_router,
        task_config_router,
        business_router,
        section_repo_router,
        curated_pages_router,
        prompt_traces_router,
        health_router,
    ]
