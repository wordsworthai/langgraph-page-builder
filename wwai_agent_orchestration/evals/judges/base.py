"""Base classes for eval judge tasks."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class BaseJudgeTask(ABC):
    """Task-level judge config and prompt loading logic."""

    TASK_NAME: str = ""
    PROMPT_VERSION: str = "v1"

    def __init__(self, prompt_version: Optional[str] = None):
        if not self.TASK_NAME:
            raise ValueError("TASK_NAME must be set in subclass")
        self.prompt_version = prompt_version or self.PROMPT_VERSION

    def get_prompt_dir(self) -> Path:
        return Path(__file__).resolve().parent / "tasks" / self.TASK_NAME / "prompts"

    def get_prompt_path(self) -> Path:
        prompt_dir = self.get_prompt_dir()
        txt_path = prompt_dir / f"{self.prompt_version}.txt"
        if txt_path.exists():
            return txt_path
        json_path = prompt_dir / f"{self.prompt_version}.json"
        if json_path.exists():
            return json_path
        return txt_path

    def load_prompt_template(self) -> Dict[str, str]:
        path = self.get_prompt_path()
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")

        content = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            return json.loads(content)
        if "===SYSTEM===" in content and "===USER===" in content:
            system_part, user_part = content.split("===USER===", maxsplit=1)
            system = system_part.replace("===SYSTEM===", "").strip()
            return {"system": system, "user": user_part.strip()}
        return {"system": "", "user": content}


class BaseJudgeTaskInstance(ABC):
    """One judge evaluation instance for a run + extracted output."""

    def __init__(self, *, run: Dict[str, Any], state: Dict[str, Any], output: Dict[str, Any], task: BaseJudgeTask):
        self.run = run
        self.state = state
        self.output = output
        self.task = task

    @abstractmethod
    def build_input(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def build_output_for_eval(self) -> Dict[str, Any]:
        ...

    def get_prompt_label(self) -> str:
        return self.task.prompt_version

    def get_filled_prompt(self) -> Dict[str, str]:
        template = self.task.load_prompt_template()
        input_data = self.build_input()
        output_data = self.build_output_for_eval()

        user = template.get("user", "")
        user = user.replace("{{input}}", json.dumps(input_data, indent=2, default=str))
        user = user.replace("{{output}}", json.dumps(output_data, indent=2, default=str))
        return {"system": template.get("system", ""), "user": user}

    @abstractmethod
    def parse_llm_response(self, response: str) -> Dict[str, Any]:
        ...

