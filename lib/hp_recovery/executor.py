import copy
import os
import pathlib
import shutil
import signal

from .errors import ConfirmationError, RecoveryError, StateError, ValidationError
from .planner import storage_preflight
from .reporting import prepare_report, write_report
from .util import ensure_safe_target, utc_now


class FixtureAdapter:
    """Bounded adapter that can mutate only a declared isolated fixture root."""
    def __init__(self, fixture_root, usb_root, *, system_free=None, data_free=None,
                 safety_copy_required=0):
        self.fixture_root = pathlib.Path(fixture_root).resolve()
        self.usb_root = pathlib.Path(usb_root).resolve()
        if not self.fixture_root.is_dir() or self.fixture_root == pathlib.Path("/"):
            raise RecoveryError("invalid fixture root")
        self.target = self.fixture_root / "target-data"
        ensure_safe_target(self.target, usb_root=self.usb_root)
        self.system_free = 1 << 60 if system_free is None else system_free
        self.data_free = 1 << 60 if data_free is None else data_free
        self.safety_copy_required = safety_copy_required

    def run(self, step, plan, state):
        op = step["op"]
        if op == "CHECK_STORAGE":
            result = storage_preflight(
                plan,
                system_free=self.system_free,
                data_free=self.data_free,
                safety_copy_required=self.safety_copy_required,
            )
            state["storage_preflight"] = result
            if any(item["status"] != "PASS" for item in result.values()):
                raise ValidationError("isolated storage preflight stopped execution")
        elif op == "PREPARE_BASE":
            self.target.mkdir(parents=True, exist_ok=True)
        elif op == "HOLD_TIMERS":
            state["timers"] = "HELD"
        elif op == "RESTORE_SERVICE":
            service = step["service"]
            dest = self.target / service
            dest.mkdir(parents=True, exist_ok=True)
            (dest / ".fixture-restored").write_text(f"{service}\n", encoding="utf-8", newline="\n")
        elif op == "TEST_SERVICE":
            service = step["service"]
            if not (self.target / service / ".fixture-restored").is_file():
                raise RecoveryError(f"fixture service test failed: {service}")
        elif op == "OPTIONAL_SERVICE":
            state.setdefault("service_outcomes", {})["snowflake"] = "SKIPPED_OPTIONAL"
        elif op == "ENABLE_PROFILE_TIMERS":
            state["timers"] = "PROFILE_ALLOWED_ONLY"
        elif op in {"VALIDATE_USB", "REPORT", "WAIT_FOR_L3"}:
            pass
        else:
            raise RecoveryError(f"unsupported operation: {op}")


def _cleanup_secrets(state):
    raw = state.pop("plaintext_secret_dir", None)
    if raw:
        p = pathlib.Path(raw)
        if p.exists() and p.is_dir() and "hp-recovery-secret-" in p.name:
            shutil.rmtree(p)
        if p.exists():
            raise RecoveryError("plaintext secret cleanup failed")


def execute(state_manager, state, adapter, *, confirmation, fail_at=None, abort_at=None):
    plan = state["plan"]
    destructive = any(x["destructive"] for x in plan["steps"])
    if destructive and confirmation != plan["confirmation_phrase"]:
        raise ConfirmationError("exact confirmation phrase required")
    if state["status"] == "COMPLETED":
        raise StateError("completed run cannot be re-executed")
    checkpoint = getattr(adapter, "set_state_checkpoint", None)
    if checkpoint is not None:
        checkpoint(lambda: state_manager.save(state))
    state.setdefault("execution_started_at", utc_now())
    state_manager.transition(state, "RUNNING")
    state["runtime_cleanup"] = "PENDING"
    state["confirmations"].append({"phrase_matched": True, "scope": plan["scope"]})
    initialize_marker = getattr(adapter, "initialize_marker_verification", None)
    if initialize_marker is not None:
        initialize_marker(state)
    previous_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda _signum, _frame: (_ for _ in ()).throw(KeyboardInterrupt()))
    completed_normally = False
    try:
        reconcile = getattr(adapter, "reconcile_runtime", None)
        if reconcile is not None:
            try:
                reconcile(state)
            except Exception:
                state["last_error"] = "CLEANUP_FAILED"
                raise
        for step in plan["steps"]:
            if step["id"] in state["completed_steps"]:
                # A resume must never replay a completed step.  This is most
                # important for non-repeatable/destructive operations.
                continue
            if abort_at == step["id"]:
                state_manager.transition(state, "ABORTED")
                break
            if fail_at == step["id"]:
                if step.get("failure_policy") == "CONTINUE_PARTIAL":
                    state.setdefault("service_outcomes", {})[step["service"]] = "FAILED_OPTIONAL"
                    state.setdefault("nonfatal_errors", []).append(step["id"])
                    state_manager.complete_step(state, step["id"])
                    continue
                raise RecoveryError(f"synthetic failure at {step['id']}")
            if (step["op"] == "TEST_SERVICE" and
                    state.get("service_outcomes", {}).get(step["service"]) == "FAILED_OPTIONAL"):
                state.setdefault("skipped_steps", []).append(step["id"])
                state_manager.complete_step(state, step["id"])
                continue
            adapter.run(step, plan, state)
            state_manager.complete_step(state, step["id"])
            if step["op"] == "WAIT_FOR_L3":
                state_manager.transition(state, "WAITING_FOR_L3")
                break
        else:
            outcomes = dict(plan["service_outcomes_planned"])
            outcomes.update(state.get("service_outcomes", {}))
            state["service_outcomes"] = outcomes
            completed_normally = True
    except KeyboardInterrupt:
        state["last_error"] = "USER_ABORT"
        state_manager.transition(state, "ABORTED")
    except Exception as exc:
        if state.get("last_error") != "CLEANUP_FAILED":
            state["last_error"] = type(exc).__name__
        state_manager.transition(state, "FAILED")
        raise
    finally:
        cleanup_errors = []
        try:
            try:
                finalize = getattr(adapter, "finalize", None)
                if finalize is not None:
                    finalize(state)
            except Exception as exc:
                cleanup_errors.append(exc)
            try:
                _cleanup_secrets(state)
            except Exception as exc:
                cleanup_errors.append(exc)

            # The complete command audit is copied, marker-redacted and sealed
            # before any final marker scan.  No recorded command may run after
            # this boundary.
            audit_ready = True
            try:
                seal_audit = getattr(adapter, "seal_command_audit", None)
                if seal_audit is not None:
                    seal_audit(state)
                elif hasattr(adapter, "command_audit"):
                    state["realtest_command_audit"] = copy.deepcopy(adapter.command_audit)
            except Exception as exc:
                audit_ready = False
                cleanup_errors.append(exc)
                verification = state.get("marker_verification")
                if isinstance(verification, dict):
                    verification.update({"status": "FAILED", "verified_generation": None,
                                         "method": "AUDIT_SEAL_FAILED",
                                         "path_classes": ["STATE_REPORT"], "hit_count": 0})

            run_dir = state_manager.path(state["run_id"]).parent
            pre_scan_ready = False
            if audit_ready:
                try:
                    state["updated_at"] = utc_now()
                    provisional = prepare_report(state)
                    validate_pre_scan = getattr(adapter, "validate_pre_scan_documents", None)
                    if validate_pre_scan is not None:
                        validate_pre_scan(state, *provisional)
                    state_manager.save(state, touch=False)
                    write_report(state, run_dir, prepared=provisional)
                    pre_scan_ready = True
                except Exception as exc:
                    cleanup_errors.append(exc)

            if pre_scan_ready:
                try:
                    verify = getattr(adapter, "verify_secret_cleanup", None)
                    if verify is not None:
                        verify(state, {
                            "TARGET": getattr(adapter, "target_root", state_manager.state_root),
                            "STATE_REPORT": run_dir,
                            "LOG": state_manager.log_root,
                        })
                except Exception as exc:
                    cleanup_errors.append(exc)

            try:
                verify_runtime = getattr(adapter, "verify_runtime_cleanup", None)
                if verify_runtime is not None:
                    verify_runtime(state)
            except Exception as exc:
                cleanup_errors.append(exc)

            candidate = copy.deepcopy(state)
            if cleanup_errors:
                candidate["cleanup_error_count"] = len(cleanup_errors)
                candidate["last_error"] = "CLEANUP_FAILED"
                candidate["runtime_cleanup"] = "FAILED"
                candidate["status"] = "FAILED"
            else:
                candidate["runtime_cleanup"] = "PASS"
                if completed_normally:
                    if candidate.get("last_error"):
                        candidate.setdefault("error_history", []).append({
                            "error": candidate["last_error"],
                            "resolution": "RUNTIME_CLEANUP_CONFIRMED",
                        })
                    candidate["last_error"] = None
                    candidate.pop("cleanup_errors", None)
                    candidate.pop("cleanup_error_count", None)
                    state_manager.transition(candidate, "COMPLETED", persist=False)

            candidate["updated_at"] = utc_now()
            if candidate.get("status") != "WAITING_FOR_L3":
                candidate["execution_ended_at"] = candidate["updated_at"]
            prepared = prepare_report(candidate)
            validate_final = getattr(adapter, "validate_final_documents", None)
            if not cleanup_errors and validate_final is not None:
                try:
                    validate_final(candidate, *prepared)
                except Exception as exc:
                    cleanup_errors.append(exc)
                    candidate = copy.deepcopy(state)
                    candidate["cleanup_error_count"] = len(cleanup_errors)
                    candidate["last_error"] = "CLEANUP_FAILED"
                    candidate["runtime_cleanup"] = "FAILED"
                    candidate["status"] = "FAILED"
                    sanitizer = getattr(adapter, "sanitize_persistent_state", None)
                    if sanitizer is not None:
                        sanitizer(candidate)
                    candidate["updated_at"] = utc_now()
                    prepared = prepare_report(candidate)
            elif cleanup_errors:
                sanitizer = getattr(adapter, "sanitize_persistent_state", None)
                if sanitizer is not None:
                    sanitizer(candidate)
                candidate["updated_at"] = utc_now()
                prepared = prepare_report(candidate)

            state.clear()
            state.update(candidate)
            state_manager.save(state, touch=False)
            write_report(state, run_dir, prepared=prepared)
        finally:
            signal.signal(signal.SIGTERM, previous_term)
        if cleanup_errors:
            raise RecoveryError("isolated cleanup verification failed") from cleanup_errors[0]
    return state
