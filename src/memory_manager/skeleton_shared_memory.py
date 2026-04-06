from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import os
import json
import threading
import time
import copy


@dataclass
class SkeletonFile:
    path: str
    skeleton_code: str
    diff: Optional[str] = None
    meta: Dict[str, Any] = None


@dataclass
class Feedback:
    result: Optional[Any] = None
    text: str = ""
    timestamp: Optional[str] = None


@dataclass
class SharedStepSkeletonRecord:
    step: int
    generated_skeleton: Optional[Dict[str, Any]] = None
    feedbacks: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class _SkeletonGlobalSharedStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.store: Dict[str, Dict[int, SharedStepSkeletonRecord]] = {}

    def save_step(self, session_id: str, repo_dir: str, record: SharedStepSkeletonRecord) -> None:
        with self.lock:
            if session_id not in self.store:
                self.store[session_id] = {}
            record.timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.store[session_id][record.step] = record
        try:
            json_dir = os.path.join(repo_dir, "tmp_files")
            os.makedirs(json_dir, exist_ok=True)
            path = os.path.join(json_dir, "skeleton_shared_steps.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def update_step(self, session_id: str, step: int, partial: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
        with self.lock:
            if session_id not in self.store or step not in self.store[session_id]:
                rec = SharedStepSkeletonRecord(step=step, generated_skeleton=None, feedbacks=None)
                self.store.setdefault(session_id, {})[step] = rec
            rec = self.store[session_id][step]
            # merge partial into rec
            if "generated_skeleton" in partial and partial["generated_skeleton"] is not None:
                rec.generated_skeleton = partial["generated_skeleton"]
            if "feedbacks" in partial and partial["feedbacks"] is not None:
                rec.feedbacks = partial["feedbacks"]
            rec.timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # optionally persist
        if repo_dir:
            try:
                json_dir = os.path.join(repo_dir, "tmp_files")
                os.makedirs(json_dir, exist_ok=True)
                path = os.path.join(json_dir, "skeleton_shared_steps.jsonl")
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            except Exception:
                pass

    def load_step(self, session_id: str, step: Optional[int] = None) -> Optional[SharedStepSkeletonRecord]:
        with self.lock:
            if session_id not in self.store:
                return None
            if step is None:
                steps = sorted(self.store[session_id].keys())
                if not steps:
                    return None
                record = self.store[session_id][steps[-1]]
                return copy.deepcopy(record) if record else None
            record = self.store[session_id].get(step)
            return copy.deepcopy(record) if record else None


_GLOBAL = _SkeletonGlobalSharedStore()


def save_skeleton_step(session_id: str, repo_dir: str, record: SharedStepSkeletonRecord) -> None:
    _GLOBAL.save_step(session_id, repo_dir, record)


def update_skeleton_step(session_id: str, step: int, partial: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
    _GLOBAL.update_step(session_id, step, partial, repo_dir=repo_dir)


def load_skeleton_step(session_id: str, step: Optional[int] = None) -> Optional[SharedStepSkeletonRecord]:
    return _GLOBAL.load_step(session_id, step)
