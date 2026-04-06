from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import os
import json
import threading
import time
import copy


@dataclass
class SSAT:
    content: Optional[Any] = None
    diff: Optional[str] = None


@dataclass
class Feedback:
    result: Optional[Any] = None
    text: str = ""
    timestamp: Optional[str] = None


@dataclass
class SharedStepArchRecord:
    step: int
    ssat: Optional[Dict[str, Any]] = None
    feedbacks: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class _ArchGlobalSharedStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.store: Dict[str, Dict[str, SharedStepArchRecord]] = {}

    def save_step(self, session_id: str, repo_dir: str, record: SharedStepArchRecord) -> None:
        with self.lock:
            if session_id not in self.store:
                self.store[session_id] = {}
            record.timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.store[session_id][record.step] = record
        try:
            json_dir = os.path.join(repo_dir, "tmp_files")
            os.makedirs(json_dir, exist_ok=True)
            path = os.path.join(json_dir, "arch_shared_steps.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def update_step(self, session_id: str, step: int, partial: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
        with self.lock:
            if session_id not in self.store or step not in self.store[session_id]:
                rec = SharedStepArchRecord(step=step, ssat=None, feedbacks=None)
                self.store.setdefault(session_id, {})[step] = rec
            rec = self.store[session_id][step]
            # merge partial into rec
            if "ssat" in partial and partial["ssat"] is not None:
                rec.ssat = partial["ssat"]
            if "feedbacks" in partial and partial["feedbacks"] is not None:
                rec.feedbacks = partial["feedbacks"]
            rec.timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # optionally persist
        if repo_dir:
            try:
                json_dir = os.path.join(repo_dir, "tmp_files")
                os.makedirs(json_dir, exist_ok=True)
                path = os.path.join(json_dir, "arch_shared_steps.jsonl")
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            except Exception:
                pass

    def load_step(self, session_id: str, step: Optional[str] = None) -> Optional[SharedStepArchRecord]:
        with self.lock:
            if session_id not in self.store:
                return None
            if step is not None:
                record = self.store[session_id].get(step)
                return copy.deepcopy(record) if record else None
            records = list(self.store[session_id].values())
            if not records:
                return None
            records = [r for r in records if r.timestamp is not None]
            if not records:
                return None
            latest = max(records, key=lambda r: r.timestamp)
            return copy.deepcopy(latest)

_GLOBAL = _ArchGlobalSharedStore()


def save_arch_step(session_id: str, repo_dir: str, record: SharedStepArchRecord) -> None:
    _GLOBAL.save_step(session_id, repo_dir, record)


def update_arch_step(session_id: str, step: int, partial: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
    _GLOBAL.update_step(session_id, step, partial, repo_dir=repo_dir)


def load_arch_step(session_id: str, step: Optional[int] = None) -> Optional[SharedStepArchRecord]:
    return _GLOBAL.load_step(session_id, step)
