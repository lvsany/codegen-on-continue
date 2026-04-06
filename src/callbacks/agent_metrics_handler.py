import json
import time
import uuid
import os
from typing import Any, Dict, List, Optional, Set

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class AgentMetricsHandler(BaseCallbackHandler):
    """
    Per-invoke metrics logger for LangChain agents.

    - One JSON line per agent.invoke()
    - Records aggregated token usage
    - Records per-LLM-call details in execution order
    - Attributes tool calls to the LLM call that triggered them
    """

    GLOBAL_LOG_FILE: Optional[str] = None

    @classmethod
    def set_global_log_file(cls, path: str):
        cls.GLOBAL_LOG_FILE = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def __init__(self, log_path: Optional[str] = None):
        # Store provided explicit path; if None, resolve at write-time from class GLOBAL_LOG_FILE.
        self.log_path = log_path
        # Only create dir now if an explicit log_path provided
        if self.log_path:
            os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        self._reset()

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------

    def _reset(self):
        # invoke scope
        self.invoke_id: Optional[str] = None
        self.start_time: Optional[float] = None

        # aggregated tokens
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0

        # counters
        self.llm_calls: int = 0
        self.tool_calls: int = 0

        # metadata
        self.model_names: List[str] = []
        self.tools_used: List[str] = []

        # per-LLM-call execution trace
        self.llm_call_details: List[Dict[str, Any]] = []

        # pointer to current LLM call
        self._current_llm_call: Optional[Dict[str, Any]] = None

    def _finalize_and_log(self):
        if self.invoke_id is None or self.start_time is None:
            return

        record = {
            "invoke_id": self.invoke_id,
            "latency": time.time() - self.start_time,

            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,

            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,

            "model_names": list(self.model_names),
            "tools_used": list(self.tools_used),

            "llm_call_trace": self.llm_call_details,
        }

        # Resolve effective log path at write time so callers can change GLOBAL_LOG_FILE dynamically.
        effective_path = self.log_path or self.__class__.GLOBAL_LOG_FILE or "./logs/agent_metrics.log"
        os.makedirs(os.path.dirname(effective_path) or ".", exist_ok=True)
        with open(effective_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._reset()

    # ------------------------------------------------------------------
    # LangChain callbacks
    # ------------------------------------------------------------------

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ):
        # ONLY treat root chain as one invoke
        if parent_run_id is None and self.invoke_id is None:
            self.invoke_id = str(run_id)
            self.start_time = time.time()

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ):
        # ONLY finalize on root chain end
        if parent_run_id is None and str(run_id) == self.invoke_id:
            self._finalize_and_log()

    # ---------------- LLM ----------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        run_id: uuid.UUID,
        **kwargs: Any,
    ):
        self.llm_calls += 1

        model_name = (
            serialized.get("kwargs", {}).get("model")
            or serialized.get("id", [None])[-1]
        )

        if model_name:
            # `model_name` can be a string or an iterable of names.
            # Use append for single strings to avoid splitting into characters;
            # extend when it's a list/tuple.
            if isinstance(model_name, (list, tuple)):
                self.model_names.extend(model_name)
            else:
                self.model_names.append(model_name)

        llm_call = {
            "index": len(self.llm_call_details),
            "model": model_name,
            "prompt_tokens": 0,
            "prompt": prompts, 
            "outputs": [],  
            "completion_tokens": 0,
            "total_tokens": 0
        }

        self.llm_call_details.append(llm_call)
        self._current_llm_call = llm_call

    def on_llm_end(
        self,
        response: LLMResult,
        run_id: uuid.UUID,
        **kwargs: Any,
    ):
        if not self._current_llm_call:
            return
        
        outputs = []
        for gen_list in response.generations:
            for gen in gen_list:
                if hasattr(gen, "text") and gen.text is not None:
                    outputs.append(gen.text)
                elif hasattr(gen, "message"):
                    outputs.append(gen.message.content)

        self._current_llm_call["outputs"] = outputs

        usage = response.llm_output.get("token_usage") if response.llm_output else None
        if not usage:
            return

        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", 0)

        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += total

        self._current_llm_call["prompt_tokens"] = prompt
        self._current_llm_call["completion_tokens"] = completion
        self._current_llm_call["total_tokens"] = total

        self._current_llm_call = None

    # ---------------- Tool ----------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        run_id: uuid.UUID,
        **kwargs: Any,
    ):
        self.tool_calls += 1

        tool_name = serialized.get("name")
        if tool_name:
            # `tool_name` is often a string; append to avoid character splitting.
            if isinstance(tool_name, (list, tuple)):
                self.tools_used.extend(tool_name)
            else:
                self.tools_used.append(tool_name)

