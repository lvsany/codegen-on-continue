from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import os
import json
import threading
import time
import copy


@dataclass
class CodeFile:
    path: str
    code: str
    diff: Optional[str] = None
    meta: Dict[str, Any] = None


@dataclass
class TestResult:
    passed: int
    total: int
    error: bool
    output: str
    test_status: str
    timestamp: Optional[str] = None


@dataclass
class Feedback:
    result: Optional[List[Dict[str, Any]]] = None
    text: str = ""
    timestamp: Optional[str] = None


@dataclass
class Experience:
    kind: str
    scenario: str
    experience: Dict[str, Any]
    step: int


@dataclass
class SharedStepCodeRecord:
    step: int
    generated_code: List[Dict[str, Any]]
    ssat: List[Dict[str, Any]]
    diff_code: List[Dict[str, Any]] = None
    test_result: Optional[Dict[str, Any]] = None
    feedbacks: Optional[Dict[str, Any]] = None
    experiences: List[Dict[str, Any]] = None
    timestramp: Optional[str] = None


class _CodeGlobalSharedStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.store: Dict[str, Dict[int, SharedStepCodeRecord]] = {}
        # repo-level experiences: key by repo_name
        self.repo_experiences: Dict[str, List[Dict[str, Any]]] = {}

    def save_step(self, session_id: str, repo_dir: str, record: SharedStepCodeRecord) -> None:
        with self.lock:
            if session_id not in self.store:
                self.store[session_id] = {}
            record.timestramp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.store[session_id][record.step] = record
        # persist to repo_dir/tmp_files/shared_step_{step}.json
        try:
            json_dir = os.path.join(repo_dir, "tmp_files")
            os.makedirs(json_dir, exist_ok=True)
            path = os.path.join(json_dir, "code_shared_steps.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _append_repo_experience(self, repo_name: str, experience: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
        with self.lock:
            if repo_name not in self.repo_experiences:
                self.repo_experiences[repo_name] = []
            self.repo_experiences[repo_name].append(experience)
        # persist to repo_dir/tmp_files/repo_experiences.jsonl
        if repo_dir:
            try:
                json_dir = os.path.join(repo_dir, "tmp_files")
                os.makedirs(json_dir, exist_ok=True)
                path = os.path.join(json_dir, "repo_experiences.jsonl")
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(experience, ensure_ascii=False) + "\n")
            except Exception:
                pass

    def update_step(self, session_id: str, step: int, partial: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
        with self.lock:
            if session_id not in self.store or step not in self.store[session_id]:
                # create minimal record
                rec = SharedStepCodeRecord(step=step, generated_code=[], test_result=None, feedbacks=None, experiences=[])
                self.store.setdefault(session_id, {})[step] = rec
            rec = self.store[session_id][step]
            # merge partial into rec
            if "generated_code" in partial and partial["generated_code"] is not None:
                rec.generated_code = partial["generated_code"]
            if "diff_code" in partial and partial["diff_code"] is not None:
                rec.generated_code = partial["diff_code"]
            if "test_result" in partial:
                rec.test_result = partial["test_result"]
            if "feedbacks" in partial and partial["feedbacks"] is not None:
                rec.feedbacks = partial["feedbacks"]
            if "ssat" in partial and partial["ssat"] is not None:
                rec.ssat = partial["ssat"]
            if "experiences" in partial and partial["experiences"] is not None:
                rec.experiences = (rec.experiences or []) + partial["experiences"]
                # also append to repo-level experiences if we can infer repo_name
                try:
                    # session_id convention: code_shared_{repo_name}
                    if session_id.startswith("code_shared_"):
                        repo_name = session_id[len("code_shared_"):]
                        for exp in partial["experiences"]:
                            self._append_repo_experience(repo_name, exp, repo_dir=repo_dir)
                except Exception:
                    pass
            rec.timestramp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # optionally persist
        if repo_dir:
            try:
                json_dir = os.path.join(repo_dir, "tmp_files")
                os.makedirs(json_dir, exist_ok=True)
                path = os.path.join(json_dir, "code_shared_steps.jsonl")
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            except Exception:
                pass

    def load_step(self, session_id: str, step: Optional[int] = None) -> Optional[SharedStepCodeRecord]:
        with self.lock:
            if session_id not in self.store:
                return None
            if step is None:
                # return latest
                steps = sorted(self.store[session_id].keys())
                if not steps:
                    return None
                record = self.store[session_id][steps[-1]]
                return copy.deepcopy(record) if record else None
            record = self.store[session_id].get(step)
            return copy.deepcopy(record) if record else None
        
    def get_best_generated_code(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        with self.lock:
            if session_id not in self.store:
                return None

            best_record = None
            best_passed = -1

            for rec in self.store[session_id].values():
                if not rec.test_result:
                    continue
                passed = rec.test_result.get("passed")
                if passed is None:
                    continue
                if passed >= best_passed:
                    best_passed = passed
                    best_record = rec

            return copy.deepcopy(best_record.generated_code) if best_record else None

            


_GLOBAL = _CodeGlobalSharedStore()


def save_code_step(session_id: str, repo_dir: str, record: SharedStepCodeRecord) -> None:
    _GLOBAL.save_step(session_id, repo_dir, record)


def update_code_step(session_id: str, step: int, partial: Dict[str, Any], repo_dir: Optional[str] = None) -> None:
    _GLOBAL.update_step(session_id, step, partial, repo_dir=repo_dir)


def load_code_step(session_id: str, step: Optional[int] = None) -> Optional[SharedStepCodeRecord]:
    return _GLOBAL.load_step(session_id, step)


def append_experience(session_id: str, step: int, experience: dict, repo_dir: Optional[str] = None) -> None:
    update_code_step(session_id, step, {"experiences": [experience]}, repo_dir=repo_dir)


def load_repo_experiences(repo_name: str) -> List[Dict[str, Any]]:
    with _GLOBAL.lock:
        return list(_GLOBAL.repo_experiences.get(repo_name, []))


def clear_repo_experiences(repo_name: str, repo_dir: Optional[str] = None) -> None:
    with _GLOBAL.lock:
        _GLOBAL.repo_experiences[repo_name] = []
    # optionally clear persisted file
    if repo_dir:
        try:
            json_dir = os.path.join(repo_dir, "tmp_files")
            path = os.path.join(json_dir, "repo_experiences.jsonl")
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

def load_best_generated_code(session_id: str) -> Optional[List[Dict[str, Any]]]:
    return _GLOBAL.get_best_generated_code(session_id)

