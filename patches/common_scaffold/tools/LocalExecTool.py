"""
LocalExecTool — drop-in replacement for ExecTool that runs Python code
directly in the current process via subprocess, without needing Docker-in-Docker
(autogen_core / autogen_ext).

Maintains an identical interface to ExecTool so DataAgent can use it unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

from common_scaffold.tools.BaseTool import BaseTool, FatalError
from common_scaffold.tools.exec_utils.parse_result import parse_result_python


class LocalExecTool(BaseTool):
    """
    Executes Python code inside the current container using subprocess.
    All previous tool results (env) are passed via pickle so complex
    objects (DataFrames, lists of dicts, etc.) survive intact.
    """

    def __init__(self, log_path, name: str, work_dir: Path, timeout: int = 600):
        super().__init__(log_path, name)
        self.logger = logging.getLogger(__name__)
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.artifact_log_path = os.path.join(
            os.path.dirname(str(log_path)), f"{name}_artifacts.jsonl"
        )
        self.logger.info(f"\twork_dir: {self.work_dir}")
        self.logger.info(f"\ttimeout:  {self.timeout}s")
        self.logger.info(f"\tartifact_log: {self.artifact_log_path}")

    # ------------------------------------------------------------------ #
    # BaseTool interface                                                    #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "work_dir": str(self.work_dir),
            "timeout": self.timeout,
            "artifact_log_path": self.artifact_log_path,
        }

    def get_spec(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Execute a Python snippet. All previous tool results are "
                    "available as variables. You must print the final result "
                    "following the required PRINT FORMAT."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": (
                                "Python code to execute in the context of "
                                "already loaded previous tool results."
                            ),
                        }
                    },
                    "required": ["code"],
                },
            },
        }

    def _check_args(self, args: dict) -> dict:
        super()._check_args(args)
        if "code" in args:
            if not isinstance(args["code"], str):
                raise ValueError(
                    f"`code` must be a string, got {type(args['code']).__name__}"
                )
            if "env" not in args:
                raise FatalError("Missing required argument: env")
            if not isinstance(args["env"], dict):
                raise FatalError(
                    f"`env` must be a dict, got {type(args['env']).__name__}"
                )
            return {"code": args["code"].strip(), "env": args["env"]}
        elif "command" in args:
            if not isinstance(args["command"], str):
                raise ValueError(
                    f"`command` must be a string, got {type(args['command']).__name__}"
                )
            return {"command": args["command"].strip()}
        else:
            raise ValueError("Invalid argument: must contain 'code' or 'command'")

    def _exec(self, args: dict):
        super()._exec(args)
        if "code" in args:
            return self._run_code(args["code"], args["env"])
        elif "command" in args:
            return self._run_shell(args["command"])
        else:
            raise FatalError("Invalid argument")

    def clean_up(self) -> None:
        super().clean_up()
        # Nothing persistent to clean up (subprocess exits automatically)

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _run_code(self, code: str, env: dict):
        """
        Run Python code with `env` dict injected as pre-defined variables.
        Uses pickle to pass complex objects (DataFrames, etc.) to the subprocess.
        """
        # Write env to a temp pickle file
        env_file = self.work_dir / "_exec_env.pkl"
        try:
            with open(env_file, "wb") as f:
                pickle.dump(env, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            # If env can't be pickled, fall back to an empty dict
            self.logger.warning(f"Could not pickle env ({e}); running without env vars")
            with open(env_file, "wb") as f:
                pickle.dump({}, f)

        # Write the wrapper script
        wrapper = (
            "import pickle, sys\n"
            f"with open({str(env_file)!r}, 'rb') as _f:\n"
            "    _env = pickle.load(_f)\n"
            "# Expose every env key as a top-level variable\n"
            "globals().update(_env)\n"
            f"{code}\n"
        )
        code_file = self.work_dir / "_exec_code.py"
        code_file.write_text(wrapper, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, str(code_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.work_dir),   # match original ExecTool's working directory
            )
        except subprocess.TimeoutExpired:
            self._log_artifact({"code_len": len(code)}, -1, "TIMEOUT")
            raise TimeoutError(f"Execution timed out after {self.timeout} seconds")

        output = proc.stdout + proc.stderr
        self._log_artifact({"code_len": len(code)}, proc.returncode, output)

        if proc.returncode != 0:
            lines = output.strip().splitlines()
            clean_err = lines[-1] if lines else output
            raise ValueError(
                f"Execution failed with exit code {proc.returncode}\n{clean_err}"
            )

        return parse_result_python(output)

    def _run_shell(self, command: str) -> str:
        """Run a shell command and return combined stdout+stderr."""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            self._log_artifact({"command": command}, -1, "TIMEOUT")
            raise TimeoutError(f"Command timed out after {self.timeout} seconds")

        output = proc.stdout + proc.stderr
        self._log_artifact({"command": command}, proc.returncode, output)

        if proc.returncode != 0:
            raise ValueError(
                f"Command failed with exit code {proc.returncode}\n{output.strip()}"
            )
        return output

    def _log_artifact(self, args: dict, exit_code: int, output: str) -> None:
        entry = {
            "val_args": args,
            "exit_code": exit_code,
            "output": output[:2000],
        }
        try:
            with open(self.artifact_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
