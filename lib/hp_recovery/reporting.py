import json
import pathlib
import re

from .util import atomic_json, utc_now


SENSITIVE = re.compile(r"(?i)(password|passwd|secret|token|private[_-]?key|credential)")


def _safe(value, key=""):
    if SENSITIVE.search(str(key)):
        return "<REDACTED>"
    if isinstance(value, dict):
        return {k: _safe(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v, key) for v in value]
    if isinstance(value, str) and SENSITIVE.search(value):
        return "<REDACTED>"
    return value


def overall_status(state):
    if state["status"] == "WAITING_FOR_L3": return "WAITING_FOR_L3"
    if state["status"] == "ABORTED": return "ABORTED"
    if state["status"] == "FAILED": return "FAILED"
    outcomes = state.get("service_outcomes", state["plan"].get("service_outcomes_planned", {}))
    required = [v for k, v in outcomes.items() if k != "snowflake"]
    return "FULL" if required and all(x == "FULL" for x in required) else "PARTIAL"


def build_report(state, *, created_at=None):
    report = {
        "run_id": state["run_id"], "created_at": created_at or utc_now(), "runtime_status": state["status"],
        "started_at": state.get("execution_started_at"), "ended_at": state.get("execution_ended_at"),
        "overall_status": overall_status(state), "mode": state["plan"]["mode"], "scope": state["plan"]["scope"],
        "runtime_mode": state["plan"].get("runtime_mode"),
        "restore_case": state["plan"].get("assistant_restore_case"),
        "targets": {"system": state["plan"].get("system_target"), "data": state["plan"].get("target")},
        "sources": {"l2": state["plan"].get("l2"), "l3": state["plan"].get("l3")},
        "services": state.get("service_outcomes", state["plan"].get("service_outcomes_planned", {})),
        "completed_steps": state["completed_steps"], "skipped_steps": state.get("skipped_steps", []),
        "open_steps": [x["id"] for x in state["plan"].get("steps", []) if x["id"] not in state["completed_steps"]],
        "resume_instruction": (f"./bin/hp-recovery-resume {state['run_id']}" if state["status"] in
                               {"FAILED", "ABORTED", "WAITING_FOR_L3"} else None),
        "last_error": state.get("last_error"),
        "healthchecks": state.get("compose_identity_evidence", {}),
        "marker_verification": state.get("marker_verification"),
        "storage": state.get("storage_preflight"), "timers": state.get("timers", "HELD"),
        "release_allowed": False, "override_allowed": False,
    }
    return _safe(report)


def render_report_markdown(report):
    lines = [
        "# HP Server Recovery – Abschlussbericht", "", f"Run-ID: {report['run_id']}",
        f"Status: {report['overall_status']}", f"Laufstatus: {report['runtime_status']}",
        f"Ausführungsart: {report.get('runtime_mode')}", f"Modus: {report['mode']}",
        f"Umfang: {report['scope']}", f"Start: {report.get('started_at')}", f"Ende: {report.get('ended_at')}",
        "", "## Dienste", "",
    ]
    lines.extend(f"- {k}: {v}" for k, v in sorted(report["services"].items()))
    if report.get("open_steps"):
        lines.extend(["", "## Offene Schritte", ""])
        lines.extend(f"- {x}" for x in report["open_steps"])
    if report.get("resume_instruction"):
        lines.extend(["", f"Fortsetzung: `{report['resume_instruction']}`"])
    lines.extend(["", "release_allowed=false", "override_allowed=false", ""])
    return "\n".join(lines)


def prepare_report(state, *, created_at=None):
    report = build_report(state, created_at=created_at)
    return report, render_report_markdown(report)


def write_report(state, run_dir, *, prepared=None):
    run_dir = pathlib.Path(run_dir)
    report, markdown = prepared or prepare_report(state)
    atomic_json(run_dir / "report.json", report)
    (run_dir / "report.md").write_text(markdown, encoding="utf-8", newline="\n")
    return report
