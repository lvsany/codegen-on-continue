import os
import time
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from langchain.callbacks.base import BaseCallbackHandler

class AgentMetricsHandler(BaseCallbackHandler):
    """
    通用 callback handler，支持全局 log 文件：
    - 使用 AgentMetricsHandler.set_global_log_file(path) 在程序启动时设置全局文件
    - 若实例化时传入 log_file，会优先使用实例级文件（仍保留兼容性）
    """
    GLOBAL_LOG_FILE: Optional[str] = None

    @classmethod
    def set_global_log_file(cls, path: str):
        cls.GLOBAL_LOG_FILE = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def __init__(self, log_file: Optional[str] = None):
        # 优先使用实例传入的 log_file，否则用全局文件，否则 fallback 到 ./logs/agent_metrics.log
        self.log_file = log_file or self.__class__.GLOBAL_LOG_FILE or "./logs/agent_metrics.log"
        os.makedirs(os.path.dirname(self.log_file) or ".", exist_ok=True)
        self._start_ts = None
        self._start_iso = None
        self._prompts = None
        self._meta: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"AgentMetricsHandler:{self.log_file}")
        if not self._logger.handlers:
            fh = logging.FileHandler(self.log_file, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(fh)
            self._logger.setLevel(logging.INFO)

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        self._start_ts = time.time()
        self._start_iso = datetime.utcnow().isoformat() + "Z"
        self._prompts = prompts
        self._meta = kwargs.get("metadata", kwargs)

    def on_llm_end(self, response: Any, **kwargs) -> None:
        end_ts = time.time()
        end_iso = datetime.utcnow().isoformat() + "Z"
        elapsed = None
        if self._start_ts:
            elapsed = end_ts - self._start_ts

        # 尝试获取输出文本（兼容不同 response 结构）
        output_text = None
        try:
            gens = getattr(response, "generations", None)
            if gens and len(gens) > 0 and len(gens[0]) > 0:
                output_text = getattr(gens[0][0], "text", None) or str(gens[0][0])
            else:
                output_text = str(response)
        except Exception:
            output_text = str(response)

        # 尝试提取 llm_output 中的 token usage（不同实现可能在不同键）
        llm_output = None
        try:
            llm_output = getattr(response, "llm_output", None) or (response.get("llm_output") if isinstance(response, dict) else None)
        except Exception:
            llm_output = None

        def extract_tokens(o):
            if not o or not isinstance(o, dict):
                return None, None, None
            # 常见结构： {"prompt_tokens":..., "completion_tokens":..., "total_tokens":...}
            pt = o.get("prompt_tokens") or o.get("promptTokenCount")
            ct = o.get("completion_tokens") or o.get("completionTokenCount")
            tt = o.get("total_tokens") or o.get("totalTokenCount")
            # 有些工具把 usage 放在嵌套 usage 键
            if not any([pt, ct, tt]) and "token_usage" in o and isinstance(o["token_usage"], dict):
                u = o["token_usage"]
                pt = pt or u.get("prompt_tokens")
                ct = ct or u.get("completion_tokens")
                tt = tt or u.get("total_tokens")
            return pt, ct, tt

        prompt_tokens, completion_tokens, total_tokens = extract_tokens(llm_output)

        record = {
            "timestamp_start": self._start_iso,
            "timestamp_end": end_iso,
            "elapsed_seconds": elapsed,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "meta": self._meta,
            "input_text": ("\n\n".join(self._prompts)) if self._prompts else None,
            "output_text": output_text,
        }

        try:
            self._logger.info(json.dumps(record, ensure_ascii=False))
        except Exception:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")