import argparse
import json
import os
import pathlib
import sys

from .catalog import load_catalog
from .errors import RecoveryError
from .executor import FixtureAdapter, execute
from .planner import REALTEST_SERVICE_ORDER, build_plan
from .realtest import (RealtestAdapter, load_realtest_config, realtest_plan_binding,
                       realtest_sizes, scan_real_sources)
from .source_scan import scan_fixture
from .state import StateManager
from .util import atomic_json, read_json
from .validation import validate_usb
from .wizard import RecoveryWizard, menu_help


def _usb_root():
    value = os.environ.get("HP_RECOVERY_USB_ROOT")
    if value:
        return pathlib.Path(value).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


def _roots(args):
    if args.test_root:
        if os.environ.get("HP_RECOVERY_ALLOW_TEST_ROOT") != "1":
            raise RecoveryError("test root requires HP_RECOVERY_ALLOW_TEST_ROOT=1")
        base = pathlib.Path(args.test_root).resolve()
        return base / "state", base / "log"
    return pathlib.Path("/var/lib/hp-server-recovery"), pathlib.Path("/var/log/hp-server-recovery")


def parser():
    p = argparse.ArgumentParser(prog="hp-recovery")
    p.add_argument("--test-root")
    sub = p.add_subparsers(dest="command", required=True)
    menu = sub.add_parser("menu", description=menu_help(), formatter_class=argparse.RawDescriptionHelpFormatter)
    sub.add_parser("validate")
    scan = sub.add_parser("scan"); scan.add_argument("--fixture-root")
    scan.add_argument("--realtest", action="store_true"); scan.add_argument("--realtest-config")
    plan = sub.add_parser("plan")
    plan.add_argument("--fixture-root"); plan.add_argument("--realtest", action="store_true"); plan.add_argument("--realtest-config")
    plan.add_argument("--mode", required=True)
    plan.add_argument("--scope", required=True); plan.add_argument("--service"); plan.add_argument("--snapshot")
    plan.add_argument("--target", required=True); plan.add_argument("--development", action="store_true")
    run = sub.add_parser("execute"); run.add_argument("run_id"); run.add_argument("--fixture-root")
    run.add_argument("--realtest", action="store_true"); run.add_argument("--realtest-config")
    run.add_argument("--confirm", default=""); run.add_argument("--fail-at"); run.add_argument("--abort-at")
    run.add_argument("--secret-fd", type=int)
    resume = sub.add_parser("resume"); resume.add_argument("run_id"); resume.add_argument("--fixture-root")
    resume.add_argument("--realtest", action="store_true"); resume.add_argument("--realtest-config")
    resume.add_argument("--confirm", default=""); resume.add_argument("--fail-at"); resume.add_argument("--abort-at")
    resume.add_argument("--snapshot")
    resume.add_argument("--secret-fd", type=int)
    status = sub.add_parser("status", help="Kurzen Status eines gespeicherten Laufs anzeigen")
    status.add_argument("run_id")
    return p


def _print(value):
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _runtime(args, usb_root):
    fixture = getattr(args, "fixture_root", None)
    real = getattr(args, "realtest", False)
    real_config = getattr(args, "realtest_config", None)
    if real:
        if fixture or not real_config:
            raise RecoveryError("realtest requires --realtest and --realtest-config without --fixture-root")
        config = load_realtest_config(real_config)
        return "ISOLATED_REALTEST", config, scan_real_sources(config, usb_root)
    if real_config or not fixture:
        raise RecoveryError("fixture mode requires --fixture-root; realtest requires explicit --realtest")
    return "FIXTURE", None, scan_fixture(fixture)


def main(argv=None):
    effective = list(sys.argv[1:] if argv is None else argv)
    if not effective:
        effective = ["menu"]
    args = parser().parse_args(effective)
    root = _usb_root()
    try:
        if args.command == "menu":
            state_root, log_root = _roots(args)
            return RecoveryWizard(root, state_root, log_root).run()
        if args.command == "validate":
            _print(validate_usb(root)); return 0
        if args.command == "scan":
            _mode, _config, scan = _runtime(args, root)
            _print(scan); return 0
        state_root, log_root = _roots(args)
        if args.command == "status":
            state = read_json(StateManager(state_root, log_root).path(args.run_id))
            _print({"run_id": state["run_id"], "status": state["status"],
                    "last_completed_step": state.get("resume_point"),
                    "updated_at": state.get("updated_at"),
                    "resume_available": state["status"] in {"PLANNED", "FAILED", "ABORTED", "WAITING_FOR_L3"}})
            return 0
        manager = StateManager(state_root, log_root); manager.lock()
        try:
            if args.command == "plan":
                validate_usb(root)
                runtime_mode, config, scan = _runtime(args, root)
                if runtime_mode == "FIXTURE":
                    sizes_path = pathlib.Path(args.fixture_root) / "sizes.json"
                    sizes = read_json(sizes_path) if sizes_path.is_file() else None
                    target = args.target
                    system_target = None
                else:
                    selected = REALTEST_SERVICE_ORDER if args.scope == "FULL_SERVER" else [args.service]
                    sizes = realtest_sizes(config, scan, args.mode, selected, snapshot_id=args.snapshot)
                    target = config["data_target"]
                    system_target = config["system_target"]
                    if pathlib.Path(args.target).resolve(strict=False) != pathlib.Path(target).resolve(strict=False):
                        raise RecoveryError("realtest --target must exactly match sentinel-bound data_target")
                plan = build_plan(load_catalog(root), scan, mode=args.mode, scope=args.scope,
                                  target=target, service=args.service, snapshot_id=args.snapshot,
                                  sizes=sizes, development=args.development, usb_root=root,
                                  runtime_mode=runtime_mode, system_target=system_target,
                                  realtest_binding=realtest_plan_binding(config, scan) if config else None)
                if runtime_mode == "ISOLATED_REALTEST":
                    plan["isolation"] = scan["isolation"]
                manager.create(plan); _print(plan); return 0
            state = manager.load(args.run_id)
            runtime_mode, config, runtime_scan = _runtime(args, root)
            if state["plan"].get("runtime_mode", "FIXTURE") != runtime_mode:
                raise RecoveryError("runtime mode does not match stored plan")
            if args.command == "resume" and state["status"] == "WAITING_FOR_L3":
                if runtime_mode == "ISOLATED_REALTEST":
                    RealtestAdapter(config, root)._recheck(state["plan"])
                scan = runtime_scan
                snapshots = scan.get("l3", {}).get("snapshots", [])
                chosen_snapshot = args.snapshot if runtime_mode == "ISOLATED_REALTEST" else (
                    snapshots[0]["id"] if len(snapshots) == 1 else None)
                selected_snapshots = [x for x in snapshots if x.get("id") == chosen_snapshot]
                if len(selected_snapshots) != 1:
                    raise RecoveryError("resume requires one explicit validated L3 snapshot")
                old = state["plan"]
                if runtime_mode == "FIXTURE":
                    sizes_path = pathlib.Path(args.fixture_root) / "sizes.json"
                    sizes = read_json(sizes_path) if sizes_path.is_file() else None
                else:
                    sizes = realtest_sizes(config, scan, "L3_ONLY", old["services"], snapshot_id=chosen_snapshot)
                resumed = build_plan(load_catalog(root), scan, mode="L3_ONLY", scope=old["scope"],
                                     service=old.get("service"), target=old["target"], snapshot_id=chosen_snapshot,
                                     sizes=sizes, development=True, usb_root=root, runtime_mode=runtime_mode,
                                     system_target=old.get("system_target"),
                                     realtest_binding=realtest_plan_binding(config, scan) if config else None)
                resumed["run_id"] = old["run_id"]
                retained = [x for x in old["steps"] if x["id"] in state["completed_steps"]]
                remaining = [x for x in resumed["steps"] if x["id"] not in {"preflight.usb", "preflight.storage", "base.prepare", "timers.hold"}]
                resumed["steps"] = retained + remaining
                state["plan"] = resumed
                manager.save(state)
            if getattr(args, "secret_fd", None) is not None and runtime_mode != "ISOLATED_REALTEST":
                raise RecoveryError("secret fd is allowed only for isolated realtest")
            adapter = (FixtureAdapter(args.fixture_root, root) if runtime_mode == "FIXTURE" else
                       RealtestAdapter(config, root, secret_fd=getattr(args, "secret_fd", None)))
            result = execute(manager, state, adapter, confirmation=args.confirm,
                             fail_at=args.fail_at, abort_at=args.abort_at)
            _print({"run_id": result["run_id"], "status": result["status"]}); return 0
        finally:
            manager.close()
    except RecoveryError as exc:
        print(f"{exc.code}:{exc}", file=sys.stderr); return 2
    except Exception as exc:
        print(f"STOP_UNEXPECTED:{type(exc).__name__}", file=sys.stderr); return 3
