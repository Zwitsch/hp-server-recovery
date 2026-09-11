import fcntl
import pathlib

from . import ALLOWED_STATES
from .errors import StateError
from .util import atomic_json, read_json, utc_now


TRANSITIONS = {
    "PLANNED": {"RUNNING", "ABORTED"},
    "RUNNING": {"WAITING_FOR_L3", "FAILED", "ABORTED", "COMPLETED"},
    "WAITING_FOR_L3": {"RUNNING", "ABORTED", "FAILED"},
    "FAILED": {"RUNNING", "ABORTED"},
    "ABORTED": {"RUNNING", "FAILED"},
    "COMPLETED": set(),
}


class StateManager:
    def __init__(self, state_root, log_root):
        self.state_root = pathlib.Path(state_root)
        self.log_root = pathlib.Path(log_root)
        self.runs = self.state_root / "runs"
        self.runs.mkdir(parents=True, exist_ok=True)
        self.log_root.mkdir(parents=True, exist_ok=True)
        self._lock_stream = None

    def lock(self):
        lock = self.state_root / "recovery.lock"
        self._lock_stream = open(lock, "a+", encoding="utf-8")
        try:
            fcntl.flock(self._lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise StateError("another recovery run is active") from exc

    def close(self):
        if self._lock_stream:
            fcntl.flock(self._lock_stream, fcntl.LOCK_UN)
            self._lock_stream.close(); self._lock_stream = None

    def create(self, plan):
        state = {"run_id": plan["run_id"], "status": "PLANNED", "created_at": utc_now(), "updated_at": utc_now(),
                 "plan": plan, "completed_steps": [], "confirmations": [], "last_error": None, "resume_point": None,
                 "release_allowed": False, "override_allowed": False}
        atomic_json(self.path(plan["run_id"]), state)
        return state

    def path(self, run_id):
        if not run_id.startswith("run-") or "/" in run_id or ".." in run_id:
            raise StateError("invalid run id")
        return self.runs / run_id / "state.json"

    def load(self, run_id):
        return read_json(self.path(run_id))

    def save(self, state, *, touch=True):
        if state["status"] not in ALLOWED_STATES:
            raise StateError("invalid state")
        if touch:
            state["updated_at"] = utc_now()
        atomic_json(self.path(state["run_id"]), state)

    def transition(self, state, target, *, persist=True):
        if target not in TRANSITIONS.get(state["status"], set()):
            raise StateError(f"invalid transition {state['status']}->{target}")
        state["status"] = target
        if persist:
            self.save(state)

    def complete_step(self, state, step_id):
        if step_id not in state["completed_steps"]:
            state["completed_steps"].append(step_id)
        state["resume_point"] = step_id; self.save(state)
