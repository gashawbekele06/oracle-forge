"""
Oracle Forge Agent
==================
Extended DataAgent with:
  - Three-layer context injection (schema / domain KB / corrections)
  - Self-correcting execution with diagnostic retry
  - Structured trace logging for the evaluation harness
  - Automatic corrections-log updates on failure

This class wraps the DataAgentBench common_scaffold DataAgent and adds the
Oracle Forge engineering layers on top of it.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Allow import from DataAgentBench directory (mounted at /dab in Docker,
# or resolved relative to this file locally)
_DAB_ROOT = Path(os.getenv("DAB_ROOT", str(Path(__file__).parent.parent / "DataAgentBench")))
if str(_DAB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DAB_ROOT))

from common_scaffold.DataAgent import DataAgent  # type: ignore
from context_manager import ContextManager


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Oracle Agent
# ---------------------------------------------------------------------------

class OracleAgent:
    """
    Production-grade data analytics agent.

    Wraps DataAgent with the three-layer context system, self-correction loop,
    and structured trace logging required by the Oracle Forge challenge spec.
    """

    def __init__(
        self,
        dataset: str,
        query_id: str | int,
        deployment_name: str = "claude-opus-4-6",
        max_iterations: int = 100,
        max_retries: int = 2,
        dab_root: str | Path | None = None,
        kb_root: str | Path | None = None,
        results_root: str | Path | None = None,
        use_hints: bool = True,
    ):
        self.dataset = dataset
        self.query_id = str(query_id)
        self.deployment_name = deployment_name
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.use_hints = use_hints

        # Resolve paths
        self.dab_root = Path(dab_root or _DAB_ROOT)
        self.kb_root = Path(kb_root or (Path(__file__).parent.parent / "kb"))
        self.results_root = Path(results_root or (Path(__file__).parent.parent / "results"))

        # Context manager (3-layer KB injection)
        self.ctx = ContextManager(kb_root=self.kb_root, dab_root=self.dab_root)

        # Locate DAB query directory
        self.query_dir = self._resolve_query_dir()

        # Load 3-layer context
        self.context_addendum = self.ctx.build(
            dataset=self.dataset,
            use_hints=self.use_hints,
        )

        # Load base db_description (Layer 1 without the KB layers — DAB uses this field)
        db_desc_path = self.query_dir.parent / "db_description.txt"
        self.db_description = db_desc_path.read_text(encoding="utf-8").strip() if db_desc_path.exists() else ""
        if use_hints:
            hint_path = self.query_dir.parent / "db_description_withhint.txt"
            if hint_path.exists():
                self.db_description += "\n\n" + hint_path.read_text(encoding="utf-8").strip()

        # Append KB layers 2 & 3 to db_description (passed into DataAgent system prompt)
        self.db_description += "\n\n" + self.ctx.build(
            dataset=self.dataset,
            use_hints=False,  # already included above
        )

        # Locate db_config
        self.db_config_path = str(self.query_dir.parent / "db_config.yaml")

        # Trace log storage
        self.trace: dict = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """
        Execute the agent with self-correction loop.

        Returns a structured result dict:
        {
            "dataset": ..., "query_id": ..., "answer": ...,
            "terminate_reason": ..., "llm_calls": ...,
            "retries": ..., "duration_s": ..., "success": bool,
            "trace_path": ...
        }
        """
        run_start = time.time()
        attempt = 0
        last_error: str = ""
        final_answer: str = ""
        terminate_reason: str = ""
        llm_calls: int = 0

        root_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        while attempt <= self.max_retries:
            attempt += 1
            logger.info(f"[OracleAgent] {self.dataset}/q{self.query_id} attempt {attempt}/{self.max_retries+1}")

            try:
                agent = DataAgent(
                    query_dir=self.query_dir,
                    db_description=self.db_description,
                    db_config_path=self.db_config_path,
                    deployment_name=self.deployment_name,
                    exec_python_timeout=600,
                    max_iterations=self.max_iterations,
                    root_name=f"{root_name}_attempt{attempt}",
                )
                answer = agent.run()
                terminate_reason = agent.terminate_reason
                llm_calls += agent.llm_call_count

                if answer and terminate_reason == "return_answer":
                    final_answer = answer
                    break

                # Empty or bad termination — retry with correction hint
                last_error = f"terminate_reason={terminate_reason}, answer='{answer[:100] if answer else ''}'"
                logger.warning(f"[OracleAgent] Bad result on attempt {attempt}: {last_error}")

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.error(f"[OracleAgent] Exception on attempt {attempt}: {last_error}")

            if attempt <= self.max_retries:
                # Inject correction context into next attempt
                self.db_description += (
                    f"\n\n[SELF-CORRECTION HINT - Attempt {attempt} failed: {last_error}. "
                    "Recheck database names, join key formats, and query syntax. "
                    "Use list_db to confirm available tables before querying.]"
                )
                logger.info("[OracleAgent] Retrying with correction hint...")

        duration = time.time() - run_start
        success = bool(final_answer) and terminate_reason == "return_answer"

        # Log correction if failed
        if not success and last_error:
            try:
                q_text_path = self.query_dir / "query.txt"
                q_text = q_text_path.read_text(encoding="utf-8").strip() if q_text_path.exists() else "unknown"
                self.ctx.append_correction(
                    dataset=self.dataset,
                    query_id=self.query_id,
                    query_text=q_text,
                    what_went_wrong=last_error,
                    correct_approach="[To be filled by team after manual diagnosis]",
                )
            except Exception:
                pass

        result = {
            "dataset": self.dataset,
            "query_id": self.query_id,
            "answer": final_answer,
            "terminate_reason": terminate_reason,
            "llm_calls": llm_calls,
            "retries": attempt - 1,
            "duration_s": round(duration, 2),
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }

        # Save trace
        trace_path = self._save_trace(result, root_name)
        result["trace_path"] = str(trace_path)

        self.trace = result
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_query_dir(self) -> Path:
        """Find the DAB query directory for this dataset/query_id."""
        # DAB naming conventions vary (uppercase / lowercase)
        candidates = [
            self.dab_root / f"query_{self.dataset}" / f"query{self.query_id}",
            self.dab_root / f"query_{self.dataset.upper()}" / f"query{self.query_id}",
            self.dab_root / f"query_{self.dataset.lower()}" / f"query{self.query_id}",
        ]
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError(
            f"Could not find query dir for dataset='{self.dataset}' query_id='{self.query_id}'. "
            f"Tried: {candidates}"
        )

    def _save_trace(self, result: dict, root_name: str) -> Path:
        trace_dir = self.results_root / "traces" / self.dataset
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f"q{self.query_id}_{root_name}.json"
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        return trace_path
