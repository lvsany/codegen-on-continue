import threading
from typing import Any, Dict, Optional

_lock = threading.RLock()
_GLOBAL_STATE: Dict[str, Any] = {}

def set_global_state(state: Dict[str, Any]) -> None:
    """Replace the global state with a copy of `state`.

    Agents and tools should use the getter helpers to read values.
    """
    with _lock:
        _GLOBAL_STATE.clear()
        if state:
            _GLOBAL_STATE.update(state)

def update_global_state(updates: Dict[str, Any]) -> None:
    """Merge `updates` into the global state."""
    with _lock:
        _GLOBAL_STATE.update(updates)

def get_global_state() -> Dict[str, Any]:
    """Return a shallow copy of the global state."""
    with _lock:
        return dict(_GLOBAL_STATE)

def get_state_value(key: str, default: Optional[Any] = None) -> Any:
    """Get a single value from the global state."""
    with _lock:
        return _GLOBAL_STATE.get(key, default)
