import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from hp_recovery.catalog import load_catalog
from hp_recovery.compose_isolation import (build_isolated_compose, load_compose_payload,
                                           prepare_companions, validate_isolated_compose)
from hp_recovery.errors import ConfirmationError, RecoveryError, SafetyError, SourceError, ValidationError
from hp_recovery.executor import execute
from hp_recovery.planner import build_plan
from hp_recovery.realtest import (IsolationGate, RealPlatform, RealtestAdapter, _redact_argv,
                                  load_realtest_config, realtest_plan_binding,
                                  realtest_sizes, scan_real_sources)
from hp_recovery.state import StateManager
from hp_recovery.util import atomic_json, sha256_file


GIB = 1024 ** 3
SERVICES = ("nextcloud", "immich", "paperless", "jellyfin", "adguard", "npm", "analyzer", "monatsausgaben")


class FakePlatform:
    def __init__(self, case):
        self.case = case
        self.host = "hp-evidence-intake"
        self.l2_ro = True
        self.l3_ro = True
        self.same_targets = False
        self.source_target_same = False
        self.image_present = True
        self.installed_packages = None
        self.compose_v2_available = True
        self.calls = []
        self.io_calls = []
        self.fail_token = None

    def hostname(self): return self.host

    def mount_record(self, path):
        p = pathlib.Path(path).resolve(strict=False)
        if p == self.case.system:
            return {"source": "/dev/vda1", "target": str(p), "read_only": False}
        if p == self.case.data:
            return {"source": "/dev/vda1" if self.same_targets else "/dev/vdb1", "target": str(p), "read_only": False}
        if p == self.case.l2:
            device = "/dev/vda1" if self.source_target_same else "/dev/vdc1"
            return {"source": device, "target": str(p), "read_only": self.l2_ro}
        if p == self.case.l3:
            return {"source": "/dev/vdd1", "target": str(p), "read_only": self.l3_ro}
        raise SafetyError(f"unexpected fake mount: {p}")

    def device_record(self, device):
        records = {
            "/dev/vda1": {"path": "/dev/vda1", "type": "part", "model": "VBOX_SYSTEM", "serial": "SYS", "uuid": "SYS-UUID", "size": 40 * GIB},
            "/dev/vdb1": {"path": "/dev/vdb1", "type": "part", "model": "VBOX_DATA", "serial": "DATA", "uuid": "DATA-UUID", "size": 80 * GIB},
        }
        if device not in records: raise SafetyError("unknown fake device")
        return records[device]

    def free_bytes(self, path): return 100 * GIB

    def validate_container_runtime(self, socket_path, target_root, productive_ips): return None

    def run(self, argv, *, input_bytes=None, stdin_path=None, stdout_path=None, env=None, timeout=300):
        self.calls.append(list(argv))
        self.io_calls.append({"argv": list(argv), "stdin_path": str(stdin_path) if stdin_path else None,
                              "stdout_path": str(stdout_path) if stdout_path else None,
                              "env": dict(env or {})})
        if self.fail_token and self.fail_token in argv:
            return subprocess.CompletedProcess(argv, 1, b"", b"synthetic")
        if stdout_path and argv[0] != "rsync":
            pathlib.Path(stdout_path).write_bytes(b"SYNTHETIC_LOGICAL_DUMP\n")
            return subprocess.CompletedProcess(argv, 0, None, b"")
        if argv[0] == "rsync":
            return subprocess.run(argv, input=input_bytes,
                                  stdin=open(stdin_path, "rb") if stdin_path else None,
                                  stdout=open(stdout_path, "wb") if stdout_path else subprocess.PIPE,
                                  stderr=subprocess.PIPE, check=False)
        if argv[0] == "systemctl" and argv[1] == "show":
            return subprocess.CompletedProcess(argv, 0, b"loaded\n", b"")
        if argv[0] == "docker" and "inspect" in argv:
            return subprocess.CompletedProcess(argv, 0 if self.image_present else 1,
                                               b"sha256:" + b"1" * 64 + b"\n", b"")
        if argv[0] == "docker" and "load" in argv:
            self.image_present = True
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        if argv[0] == "dpkg-query":
            installed = self.installed_packages is None or argv[-1] in self.installed_packages
            return subprocess.CompletedProcess(argv, 0 if installed else 1,
                                               b"install ok installed" if installed else b"", b"")
        if argv[0] == "docker" and argv[-2:] == ["compose", "version"]:
            return subprocess.CompletedProcess(argv, 0 if self.compose_v2_available else 1,
                                               b"Docker Compose version v2\n" if self.compose_v2_available else b"", b"")
        if argv[0] == "age":
            return subprocess.CompletedProcess(argv, 1, b"", b"disabled in unit test")
        return subprocess.CompletedProcess(argv, 0, b"", b"")


class ComposePlatform(FakePlatform):
    """In-memory Docker boundary with exact Compose/container identities."""
    def __init__(self, case):
        super().__init__(case)
        self.containers = {}
        self.foreign_containers = {"adguardhome": {"project": "production", "service": "adguardhome"}}
        self.project_override = None
        self.image_override = None
        self.running_override = None
        self.health_override = None
        self.fail_up = False
        self.fail_down = False
        self.fail_network_cleanup = False
        self.networks = {}
        self.up_observer = None

    def activate(self, contract):
        for service_id in contract["verify_services"]:
            self.containers[contract["container_names"][service_id]] = {
                "project": self.project_override or contract["project_name"], "service": service_id,
                "image": self.image_override or contract["image_bindings"][service_id],
                "running": True if self.running_override is None else self.running_override,
                "health": self.health_override or "healthy",
            }
        for network_id in contract.get("allowed_networks", []):
            self.networks[f"{contract['project_name']}_{network_id}"] = {
                "project": contract["project_name"], "network": network_id,
            }

    def run(self, argv, **kwargs):
        self.calls.append(list(argv)); self.io_calls.append({"argv": list(argv), "stdin_path": None, "stdout_path": None})
        if self.fail_token and self.fail_token in argv:
            return subprocess.CompletedProcess(argv, 1, b"", b"synthetic")
        if kwargs.get("stdout_path"):
            pathlib.Path(kwargs["stdout_path"]).write_bytes(b"SYNTHETIC_LOGICAL_DUMP\n")
            return subprocess.CompletedProcess(argv, 0, None, b"")
        if argv and argv[0] == "rsync":
            return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if argv and argv[0] == "docker" and "compose" in argv:
            compose_file = pathlib.Path(argv[argv.index("--file") + 1])
            document = json.loads(compose_file.read_text(encoding="utf-8"))
            if "config" in argv:
                return subprocess.CompletedProcess(argv, 0, json.dumps(document).encode(), b"")
            if "up" in argv:
                if self.up_observer is not None:
                    self.up_observer()
                if self.fail_up:
                    return subprocess.CompletedProcess(argv, 1, b"", b"DUMMY_FAILURE_DETAIL")
                contract = self.case._contract_by_project[document["name"]]
                self.activate(contract)
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            if "down" in argv:
                if self.fail_down:
                    return subprocess.CompletedProcess(argv, 1, b"", b"DUMMY_CLEANUP_DETAIL")
                project = document["name"]
                self.containers = {name: item for name, item in self.containers.items() if item["project"] != project}
                return subprocess.CompletedProcess(argv, 0, b"", b"")
        if argv and argv[0] == "docker" and "run" in argv and "--name" in argv:
            labels = {}
            for index, token in enumerate(argv):
                if token == "--label" and index + 1 < len(argv) and "=" in argv[index + 1]:
                    key, value = argv[index + 1].split("=", 1); labels[key] = value
            self.containers[argv[argv.index("--name") + 1]] = {"project": "database", "service": "database",
                                                                "image": argv[-1], "running": True,
                                                                "health": "healthy", "labels": labels}
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        if argv and argv[0] == "docker" and "container" in argv and "rm" in argv:
            if self.fail_down and argv[-1].startswith("hp-realtest-"):
                return subprocess.CompletedProcess(argv, 1, b"", b"DUMMY_CLEANUP_DETAIL")
            self.containers.pop(argv[-1], None)
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        if argv and argv[0] == "docker" and "network" in argv and "rm" in argv:
            if self.fail_down or self.fail_network_cleanup:
                return subprocess.CompletedProcess(argv, 1, b"", b"DUMMY_CLEANUP_DETAIL")
            self.networks.pop(argv[-1], None)
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        if argv and argv[0] == "docker" and "network" in argv and "inspect" in argv:
            name = argv[argv.index("inspect") + 1]
            item = self.networks.get(name)
            if item is None:
                return subprocess.CompletedProcess(argv, 1, b"", b"Error: No such network")
            value = {"Name": name, "Labels": {"com.docker.compose.project": item["project"],
                                                "com.docker.compose.network": item["network"]}}
            return subprocess.CompletedProcess(argv, 0, json.dumps(value).encode(), b"")
        if argv and argv[0] == "docker" and "inspect" in argv:
            name = argv[argv.index("inspect") + 1]
            item = self.containers.get(name)
            if item is None:
                return subprocess.CompletedProcess(argv, 1, b"", b"Error: No such object")
            if "--format" not in argv:
                return subprocess.CompletedProcess(argv, 0, b"[]", b"")
            labels = {"com.docker.compose.project": item["project"],
                      "com.docker.compose.service": item["service"]}
            labels.update(item.get("labels", {}))
            value = {"Name": "/" + name, "Config": {"Image": item["image"], "Labels": labels},
                "State": {"Running": item["running"], "Health": {"Status": item["health"]}}}
            return subprocess.CompletedProcess(argv, 0, json.dumps(value).encode(), b"")
        if argv and argv[0] == "systemctl" and argv[1] == "show":
            return subprocess.CompletedProcess(argv, 0, b"loaded\n", b"")
        return subprocess.CompletedProcess(argv, 0, b"", b"")


class RealtestModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hp-realtest-")
        self.root = pathlib.Path(self.tmp.name)
        self.target = self.root / "isolated-target"
        self.system = self.target / "system"
        self.data = self.target / "data"
        self.system.mkdir(parents=True); self.data.mkdir()
        self.l2 = self.root / "l2-ro"; self.l3 = self.root / "l3-ro"
        l2data = self.l2 / "server-backups/mirror/data"; l2data.mkdir(parents=True)
        snap = self.l3 / "2026-08-12_12-00"; snap.mkdir(parents=True)
        for service in SERVICES:
            for base in (l2data, snap):
                d = base / service; d.mkdir()
                (d / "payload.txt").write_text(service + "\n", encoding="utf-8")
                os.chmod(d / "payload.txt", 0o640)
        self.sentinel = self.root / "REALTEST-SENTINEL.json"
        self.sentinel_data = {
            "schema_version": "1.0", "purpose": "HP_EVIDENCE_INTAKE_REALTEST",
            "allowed_hostnames": ["hp-evidence-intake"],
            "forbidden_hostnames": ["production-host"],
            "protected_prefixes": ["/srv/production-data", "/srv/production-backup"],
            "release_allowed": False, "override_allowed": False,
            "target_devices": {
                "system": {"device": "/dev/vda1", "uuid": "SYS-UUID", "type": "part", "model": "VBOX_SYSTEM", "size": 40 * GIB, "virtual": True},
                "data": {"device": "/dev/vdb1", "uuid": "DATA-UUID", "type": "part", "model": "VBOX_DATA", "size": 80 * GIB, "virtual": True},
            },
        }
        atomic_json(self.sentinel, self.sentinel_data)
        self.config_path = self.root / "realtest.json"
        services = {}
        for service in SERVICES:
            services[service] = {
                "copy_required": True, "success_status": "FULL", "check_failure": "UNAVAILABLE",
                "copies": [
                    {"source": "L2", "source_rel": service, "target_rel": service, "modes": ["L2_ONLY", "COMBINED_L2_L3"], "required": True},
                    {"source": "L3", "source_rel": service, "target_rel": service, "modes": ["L3_ONLY"], "required": True},
                ],
                "checks": [{"kind": "PATH", "target_rel": service}],
            }
        services["base-system"] = {"copy_required": False, "copies": [{"source": "USB", "source_rel": "tests/fixtures/base/config", "target_rel": "config", "modes": ["L2_ONLY"], "required": True}], "checks": [{"kind": "PATH", "target_rel": "config"}]}
        services["snowflake"] = {"copy_required": False, "copies": [{"source": "L2", "source_rel": "snowflake", "target_rel": "snowflake", "modes": ["L2_ONLY"], "required": False}], "checks": [{"kind": "COMMAND", "argv": ["true"]}]}
        self.config = {
            "schema_version": "1.0", "runtime_mode": "ISOLATED_REALTEST",
            "release_allowed": False, "override_allowed": False,
            "sentinel_path": str(self.sentinel), "sentinel_sha256": sha256_file(self.sentinel),
            "allowed_hostnames": ["hp-evidence-intake"],
            "forbidden_hostnames": ["production-host"],
            "protected_prefixes": ["/srv/production-data", "/srv/production-backup"],
            "target_root": str(self.target), "system_target": str(self.system), "data_target": str(self.data),
            "target_devices": self.sentinel_data["target_devices"],
            "sources": {"l2": [{"path": str(self.l2), "device": "/dev/vdc1"}],
                        "l3": [{"path": str(self.l3), "device": "/dev/vdd1"}]},
            "container_runtime": {"socket": str(self.target / "run/docker.sock"), "production_context_connected": False},
            "productive_ips": ["192.0.2.10"], "system_required_bytes": GIB,
            "image_archive_root": str(self.target),
            "base_system": {"copies": [{"source": "USB", "source_rel": "tests/fixtures/base/config", "target_rel": "config", "required": True}]},
            "packages": {"required": ["rsync"],
                         "required_any": [["docker-compose-v2", "docker-compose-plugin"]]},
            "images": [{"services": ["adguard"], "kind": "REGISTRY",
                        "reference": "example.invalid/test@sha256:" + "2" * 64,
                        "archive_rel": "missing.tar", "archive_sha256": "3" * 64,
                        "expected_image_id": "sha256:" + "1" * 64}], "services": services,
            "allowed_units": ["backup_level2.timer", "backup_level3.timer", "hp-server-analyzer-biweekly.timer", "adguard-test.timer", "budget-test.timer"],
            "timers": {"hold": ["backup_level2.timer", "backup_level3.timer", "hp-server-analyzer-biweekly.timer"],
                       "enable_after_acceptance": {"adguard": ["adguard-test.timer"], "monatsausgaben": ["budget-test.timer"]}},
            "secrets": {"required_files": []},
        }
        self.write_config()
        self.platform = FakePlatform(self)
        self.catalog = load_catalog(ROOT)
        self.manager = StateManager(self.root / "state", self.root / "log")

    def tearDown(self):
        self.manager.close(); self.tmp.cleanup()

    def write_config(self): atomic_json(self.config_path, self.config)

    def loaded(self):
        self.write_config(); return load_realtest_config(self.config_path)

    def scan(self): return scan_real_sources(self.loaded(), ROOT, self.platform)

    def plan(self, service="adguard", mode="L2_ONLY"):
        config = self.loaded(); scan = scan_real_sources(config, ROOT, self.platform)
        snapshot = scan["l3"]["snapshots"][0]["id"] if mode in {"L3_ONLY", "COMBINED_L2_L3"} else None
        sizes = realtest_sizes(config, scan, mode, [service], snapshot_id=snapshot)
        return build_plan(self.catalog, scan, mode=mode, scope="SINGLE_SERVICE", service=service,
                          target=self.data, snapshot_id=snapshot, sizes=sizes, development=True, usb_root=ROOT,
                          runtime_mode="ISOLATED_REALTEST", system_target=self.system,
                          realtest_binding=realtest_plan_binding(config, scan))

    def adapter(self): return RealtestAdapter(self.loaded(), ROOT, self.platform)

    def test_R01_without_sentinel_stops(self):
        self.config["sentinel_path"] = str(self.root / "missing")
        with self.assertRaises(SafetyError): IsolationGate(self.loaded(), ROOT, self.platform).validate()

    def test_R02_hp_server_hostname_stops(self):
        self.platform.host = "hp-server"
        with self.assertRaises(SafetyError): self.scan()

    def test_R03_writable_l2_stops(self):
        self.platform.l2_ro = False
        with self.assertRaises(SafetyError): self.scan()

    def test_R04_writable_l3_stops(self):
        self.platform.l3_ro = False
        with self.assertRaises(SafetyError): self.scan()

    def test_R05_source_and_target_device_same_stops(self):
        self.platform.source_target_same = True
        self.config["sources"]["l2"][0]["device"] = "/dev/vda1"
        with self.assertRaises(SafetyError): self.scan()

    def test_R06_system_and_data_target_same_stops(self):
        self.platform.same_targets = True
        self.config["target_devices"]["data"] = dict(self.config["target_devices"]["system"])
        self.sentinel_data["target_devices"]["data"] = dict(self.sentinel_data["target_devices"]["system"])
        atomic_json(self.sentinel, self.sentinel_data); self.config["sentinel_sha256"] = sha256_file(self.sentinel)
        with self.assertRaises(SafetyError): self.scan()

    def test_R07_unknown_device_identity_stops(self):
        self.config["target_devices"]["data"]["uuid"] = "UNKNOWN"
        with self.assertRaises(SafetyError): self.scan()

    def test_R08_wrong_phrase_changes_nothing(self):
        marker = self.data / "unchanged"; marker.write_bytes(b"same")
        plan = self.plan(); state = self.manager.create(plan)
        before = marker.read_bytes()
        with self.assertRaises(ConfirmationError): execute(self.manager, state, self.adapter(), confirmation="WRONG")
        self.assertEqual(marker.read_bytes(), before)
        self.assertFalse((self.data / "adguard").exists())

    def test_R09_productive_path_stops(self):
        self.config["data_target"] = "/mnt/data"
        with self.assertRaises(SafetyError): self.scan()

    def test_R10_missing_image_stops(self):
        self.platform.image_present = False
        self.config["images"] = [{"reference": "example.invalid/test@sha256:" + "1" * 64,
                                  "archive": str(self.root / "missing.tar"), "archive_sha256": "2" * 64}]
        adapter = self.adapter(); plan = self.plan(); state = self.manager.create(plan)
        with self.assertRaises(ValidationError): execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])

    def test_R11_missing_required_secret_stops(self):
        self.config["secrets"] = {"required_files": ["dummy.env"], "age_package": str(self.target / "missing.age"),
                                  "age_identity": str(self.target / "missing.key")}
        adapter = self.adapter(); plan = self.plan(); state = self.manager.create(plan)
        with self.assertRaises((ValidationError, FileNotFoundError, RecoveryError)):
            execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])

    def test_R12_abort_cleans_secret_and_writes_report(self):
        plan = self.plan(); state = self.manager.create(plan)
        secret = self.target / "hp-recovery-secret-test"; secret.mkdir(); (secret / "value").write_text("DUMMY_ONLY")
        state["plaintext_secret_dir"] = str(secret); self.manager.save(state)
        adapter = self.adapter(); adapter._secret_markers.add(b"DUMMY_ONLY")
        result = execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"], abort_at="restore.adguard")
        self.assertEqual(result["status"], "ABORTED"); self.assertFalse(secret.exists())
        self.assertTrue((self.manager.path(plan["run_id"]).parent / "report.json").is_file())

    def test_R13_resume_does_not_repeat_restore(self):
        plan = self.plan(); state = self.manager.create(plan)
        with self.assertRaises(RecoveryError):
            execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"], fail_at="test.adguard")
        first = sum(1 for x in self.platform.calls if x and x[0] == "rsync")
        failed = self.manager.load(plan["run_id"])
        done = execute(self.manager, failed, self.adapter(), confirmation=plan["confirmation_phrase"])
        second = sum(1 for x in self.platform.calls if x and x[0] == "rsync")
        self.assertEqual(done["status"], "COMPLETED"); self.assertEqual(first, second)

    def test_R14_single_service_preserves_foreign_data(self):
        foreign = self.data / "nextcloud-existing"; foreign.mkdir(); (foreign / "x").write_bytes(b"FOREIGN")
        os.chmod(foreign / "x", 0o610); os.utime(foreign / "x", ns=(1700000000000000000, 1700000000000000000))
        from hp_recovery.util import metadata_tree_fingerprint
        before = metadata_tree_fingerprint(foreign)
        plan = self.plan("adguard"); state = self.manager.create(plan)
        execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual(metadata_tree_fingerprint(foreign), before)

    def test_R15_invalid_sqlite_becomes_unavailable(self):
        db = self.l2 / "server-backups/mirror/data/monatsausgaben/expenses.db"; db.write_bytes(b"not sqlite")
        self.config["services"]["monatsausgaben"]["database"] = {"kind": "SQLITE", "target_rel": "monatsausgaben/expenses.db", "invalid_policy": "UNAVAILABLE"}
        plan = self.plan("monatsausgaben"); state = self.manager.create(plan)
        done = execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual(done["service_outcomes"]["monatsausgaben"], "UNAVAILABLE")

    def test_R16_missing_l3_dump_is_unavailable_and_reported(self):
        service = self.config["services"]["nextcloud"]
        service["database"] = {"kind": "MARIADB", "workflows": {"L3_ONLY": {
            "source_kind": "L3_DUMP", "dump_glob": "nextcloud/missing*.sql",
            "missing_dump_policy": "UNAVAILABLE"}}, "commands": {
                "initialize_empty": {"argv": ["true"]}, "import_dump": {"argv": ["true"]},
                "test_query": {"argv": ["true"]}, "target_stop": {"argv": ["true"]}}}
        plan = self.plan("nextcloud", "L3_ONLY"); state = self.manager.create(plan)
        with self.assertRaises(SourceError): execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
        failed = self.manager.load(plan["run_id"])
        self.assertEqual(failed["service_outcomes"]["nextcloud"], "UNAVAILABLE")
        self.assertTrue((self.manager.path(plan["run_id"]).parent / "report.json").is_file())

    def test_R17_timers_enabled_only_for_full_service(self):
        plan = self.plan("adguard"); state = self.manager.create(plan)
        done = execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual(done["timers"]["enabled"], ["adguard-test.timer"])
        self.assertFalse(any("budget-test.timer" in x for x in self.platform.calls))

    def test_R18_report_and_audit_do_not_contain_secret_value(self):
        adapter = self.adapter(); adapter._recorded_run(["true", "--password=DUMMY_TEST_SECRET"])
        plan = self.plan(); state = self.manager.create(plan)
        done = execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        report = (self.manager.path(plan["run_id"]).parent / "report.json").read_text()
        self.assertNotIn("DUMMY_TEST_SECRET", report)
        self.assertNotIn("DUMMY_TEST_SECRET", json.dumps(done.get("realtest_command_audit")))

    def test_R19_real_copy_occurs_only_in_temporary_target(self):
        plan = self.plan(); state = self.manager.create(plan)
        execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual((self.data / "adguard/payload.txt").read_text(), "adguard\n")
        self.assertTrue(str((self.data / "adguard").resolve()).startswith(str(self.root.resolve())))

    def test_R20_uid_gid_mode_and_acl_contract_boundary(self):
        source = self.l2 / "server-backups/mirror/data/adguard/payload.txt"
        plan = self.plan(); state = self.manager.create(plan)
        execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
        target = self.data / "adguard/payload.txt"
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), stat.S_IMODE(source.stat().st_mode))
        self.assertEqual((target.stat().st_uid, target.stat().st_gid), (source.stat().st_uid, source.stat().st_gid))
        rsync = next(x for x in self.platform.calls if x and x[0] == "rsync")
        self.assertIn("-aHAX", rsync); self.assertIn("--numeric-ids", rsync)

    def test_R21_productive_ip_in_contract_stops_before_change(self):
        self.config["services"]["adguard"]["checks"].append(
            {"kind": "ENDPOINT", "url": "http://192.0.2.10:3000/"})
        with self.assertRaises(SafetyError): self.scan()
        self.assertFalse((self.data / "adguard").exists())

    def test_R22_realtest_switch_is_explicitly_required(self):
        result = subprocess.run(
            [str(ROOT / "bin/hp-recovery"), "scan", "--realtest-config", str(self.config_path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("explicit --realtest", result.stderr)

    def test_R23_bound_template_has_every_service_contract(self):
        template = json.loads((ROOT / "config/realtest-config.template.json").read_text(encoding="utf-8"))
        expected = {"base-system", "adguard", "npm", "nextcloud", "immich", "paperless", "jellyfin", "analyzer", "monatsausgaben", "snowflake"}
        self.assertEqual(set(template["services"]), expected)
        for name, contract in template["services"].items():
            self.assertTrue(contract["copies"], name)
            self.assertTrue(contract["checks"], name)
            if name not in {"base-system"}:
                self.assertTrue(contract["compose"]["image_bindings"], name)
        self.assertTrue(template["base_system"]["copies"])
        self.assertTrue(template["images"])
        self.assertTrue(template["packages"]["required"])

    def test_R24_empty_required_contract_stops_at_validation(self):
        self.config["services"]["adguard"]["copies"] = []
        self.write_config()
        with self.assertRaises(ValidationError): load_realtest_config(self.config_path)

    def test_R25_config_changed_after_plan_stops(self):
        plan = self.plan()
        self.config["services"]["adguard"]["checks"].append({"kind": "PATH", "target_rel": "changed"})
        self.write_config()
        with self.assertRaises(SafetyError): self.adapter()._recheck(plan)

    def test_R26_config_changed_before_resume_stops(self):
        plan = self.plan(); state = self.manager.create(plan)
        with self.assertRaises(RecoveryError):
            execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"], fail_at="test.adguard")
        marker = self.data / "resume-marker"; marker.write_bytes(b"UNCHANGED")
        self.config["packages"]["required"].append("jq"); self.write_config()
        with self.assertRaises(SafetyError):
            execute(self.manager, self.manager.load(plan["run_id"]), self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual(marker.read_bytes(), b"UNCHANGED")

    def test_R27_three_snapshots_explicit_selection_sizes_combined_and_l3(self):
        self.config["services"]["adguard"]["copies"][0]["modes"] = ["L2_ONLY"]
        self.config["services"]["adguard"]["copies"][1]["modes"] = ["L3_ONLY", "COMBINED_L2_L3"]
        for stamp, payload in (("2026-08-12_13-00", b"xx"), ("2026-08-12_14-00", b"yyyyy")):
            d = self.l3 / stamp / "adguard"; d.mkdir(parents=True); (d / "payload.txt").write_bytes(payload)
        config = self.loaded(); scan = scan_real_sources(config, ROOT, self.platform)
        self.assertEqual(len(scan["l3"]["snapshots"]), 3)
        selected = "2026-08-12_14-00"
        self.assertEqual(realtest_sizes(config, scan, "L3_ONLY", ["adguard"], snapshot_id=selected)["adguard"], 5)
        self.assertEqual(realtest_sizes(config, scan, "COMBINED_L2_L3", ["adguard"], snapshot_id=selected)["adguard"], 5)

    def test_R28_nonselected_snapshot_is_untouched(self):
        untouched = self.l3 / "2026-08-12_13-00" / "adguard"; untouched.mkdir(parents=True); (untouched / "x").write_bytes(b"NOCHANGE")
        from hp_recovery.util import metadata_tree_fingerprint
        before = metadata_tree_fingerprint(untouched)
        config = self.loaded(); scan = scan_real_sources(config, ROOT, self.platform)
        realtest_sizes(config, scan, "L3_ONLY", ["adguard"], snapshot_id="2026-08-12_12-00")
        self.assertEqual(metadata_tree_fingerprint(untouched), before)

    def _raw_db_contract(self):
        return {"kind": "POSTGRESQL", "workflows": {"L2_ONLY": {"source_kind": "L2_RAW", "raw_source_rel": "immich_pgdata"}}, "commands": {
            "isolated_start": {"argv": ["true", "isolated_start"]}, "logical_export": {"argv": ["true", "logical_export"]},
            "isolated_stop": {"argv": ["true", "isolated_stop"]}, "initialize_empty": {"argv": ["true", "initialize_empty"]},
            "import_dump": {"argv": ["true", "import_dump"]}, "test_query": {"argv": ["true", "test_query"]},
            "target_stop": {"argv": ["true", "target_stop"]}}}

    def test_R29_l2_raw_export_and_import_bind_same_target_root_dump(self):
        raw = self.l2 / "server-backups/mirror/data/immich_pgdata"; raw.mkdir(); (raw / "PG_VERSION").write_text("14\n")
        plan = self.plan("immich", "L2_ONLY"); adapter = self.adapter(); adapter.config["_plaintext_secret_dir"] = str(self.target)
        adapter._database_workflow("immich", self._raw_db_contract(), plan, {})
        export = next(x for x in self.platform.io_calls if "logical_export" in x["argv"])
        imported = next(x for x in self.platform.io_calls if "import_dump" in x["argv"])
        self.assertTrue(export["stdout_path"].startswith(str(self.target)))
        self.assertEqual(imported["stdin_path"], export["stdout_path"])
        self.assertFalse(export["stdout_path"].startswith(str(self.l2)))

    def test_R30_export_instance_stops_on_export_failure(self):
        raw = self.l2 / "server-backups/mirror/data/immich_pgdata"; raw.mkdir(); (raw / "PG_VERSION").write_text("14\n")
        plan = self.plan("immich", "L2_ONLY"); adapter = self.adapter(); adapter.config["_plaintext_secret_dir"] = str(self.target)
        self.platform.fail_token = "logical_export"
        with self.assertRaises(RecoveryError): adapter._database_workflow("immich", self._raw_db_contract(), plan, {})
        self.assertTrue(any("isolated_stop" in x for x in self.platform.calls))

    def test_R31_secret_following_argument_and_urls_are_redacted_everywhere(self):
        values = ["CorrectHorseBatteryStaple", "AnotherDummyValue", "UrlDummyValue"]
        serial = json.dumps(_redact_argv(["mysql", "--password", values[0], "DB_PASSWORD=" + values[1], "mysql://user:" + values[2] + "@localhost/db"]))
        for value in values: self.assertNotIn(value, serial)
        adapter = self.adapter(); adapter._recorded_run(["true", "--password", values[0]])
        plan = self.plan(); state = self.manager.create(plan); state["realtest_command_audit"] = adapter.command_audit; self.manager.save(state)
        from hp_recovery.reporting import write_report
        write_report(state, self.manager.path(plan["run_id"]).parent)
        combined = self.manager.path(plan["run_id"]).read_text() + (self.manager.path(plan["run_id"]).parent / "report.json").read_text()
        self.assertNotIn(values[0], combined)

    def test_R32_movable_nonlatest_image_tag_stops(self):
        self.config["images"][0]["reference"] = "example.invalid/test:v1.2.3"; self.write_config()
        with self.assertRaises(ValidationError): load_realtest_config(self.config_path)

    def test_R33_local_image_wrong_id_after_load_stops(self):
        archive = self.target / "local.tar"; archive.write_bytes(b"OFFLINE"); self.platform.image_present = False
        self.config["images"] = [{"services": ["adguard"], "kind": "LOCAL_ARCHIVE", "reference": "local:test",
                                  "archive_rel": "local.tar", "archive_sha256": sha256_file(archive),
                                  "expected_image_id": "sha256:" + "9" * 64}]
        plan = self.plan(); state = self.manager.create(plan)
        with self.assertRaises(ValidationError): execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])

    def test_R34_partition_uses_parent_virtualbox_model(self):
        class LsblkPlatform(RealPlatform):
            def run(self, argv, **kwargs):
                value = {"blockdevices": [{"path":"/dev/vda","name":"vda","pkname":None,"type":"disk","model":"VBOX HARDDISK","serial":"D","uuid":None,"size":100,
                                            "children":[{"path":"/dev/vda1","name":"vda1","pkname":"vda","type":"part","model":None,"serial":None,"uuid":"U","size":90}]}]}
                return subprocess.CompletedProcess(argv, 0, json.dumps(value).encode(), b"")
        self.assertEqual(LsblkPlatform().device_record("/dev/vda1"), {"path":"/dev/vda1","type":"part","model":"VBOX HARDDISK","serial":None,"uuid":"U","size":90})

    def _dummy_compose_env(self):
        path = self.root / "dummy-compose.env"
        values = {
            "TZ": "Europe/Berlin", "ADGUARD_TAG": "DUMMY", "NPM_VERSION": "DUMMY",
            "NPM_HTTP_PORT": "80", "NPM_UI_PORT": "81", "NPM_HTTPS_PORT": "443",
            "NPM_DATA": str(self.target / "data/npm/data"),
            "NPM_LETSENCRYPT": str(self.target / "data/npm/letsencrypt"),
            "MARIADB_VERSION": "DUMMY", "NEXTCLOUD_VERSION": "DUMMY", "NC_HTTP_PORT": "8092",
            "NC_DB_DATA": str(self.target / "data/nextcloud_db_data"),
            "NC_CORE": str(self.target / "data/nextcloud_core"), "NC_DATA": str(self.target / "data/nextcloud"),
            "MYSQL_ROOT_PASSWORD": "DUMMY_ROOT", "MYSQL_PASSWORD": "DUMMY_PASSWORD",
            "MYSQL_DATABASE": "nextcloud", "MYSQL_USER": "nextcloud",
            "IMMICH_VERSION": "DUMMY", "UPLOAD_LOCATION": str(self.target / "data/immich"),
            "DB_DATA_LOCATION": str(self.target / "data/immich_pgdata"), "DB_PASSWORD": "DUMMY_DB",
            "DB_USERNAME": "dummy", "DB_DATABASE_NAME": "immich", "DB_HOSTNAME": "database",
            "REDIS_HOSTNAME": "redis", "JF_CONFIG": str(self.target / "data/jellyfin/config"),
            "JF_CACHE": str(self.target / "data/jellyfin/cache"), "JELLYFIN_TAG": "DUMMY",
            "PAPERLESS_IMAGE": "DUMMY", "PAPERLESS_TAG": "DUMMY", "APP_PASSWORD": "DUMMY_APP",
            "SESSION_SECRET": "DUMMY_SESSION", "DATABASE_PATH": "/data/expenses.db", "COOKIE_SECURE": "false",
        }
        path.write_text("".join(f"{key}={value}\n" for key, value in sorted(values.items())), encoding="utf-8")
        return path

    def _isolated_compose(self, service):
        template = json.loads((ROOT / "config/realtest-config.template.json").read_text(encoding="utf-8"))
        contract = template["services"][service]["compose"]
        payload = load_compose_payload(ROOT / contract["payload_file"])
        env_file = self._dummy_compose_env()
        document = build_isolated_compose(payload, contract, self.target, env_file)
        return contract, env_file, document

    def test_R35_every_actual_payload_structurally_renders_and_validates(self):
        for service in ("adguard", "npm", "nextcloud", "immich", "paperless", "jellyfin", "analyzer", "monatsausgaben", "snowflake"):
            with self.subTest(service=service):
                contract, env_file, document = self._isolated_compose(service)
                self.assertTrue(validate_isolated_compose(document, contract, self.target, env_file, ["192.0.2.10"]))

    def test_R36_all_rendered_bind_sources_are_under_target_root(self):
        for service in ("adguard", "npm", "nextcloud", "immich", "paperless", "jellyfin", "monatsausgaben"):
            contract, _, document = self._isolated_compose(service)
            for definition in document["services"].values():
                for volume in definition.get("volumes", []):
                    pathlib.Path(volume["source"]).relative_to(self.target)
            self.assertEqual(set(document["services"]), set(contract["expected_services"]))

    def test_R37_adguard_production_mounts_are_fully_replaced(self):
        _, _, document = self._isolated_compose("adguard")
        mounts = document["services"]["adguardhome"]["volumes"]
        self.assertEqual({x["target"] for x in mounts}, {"/opt/adguardhome/work", "/opt/adguardhome/conf"})
        self.assertNotIn("/mnt/data/adguard", json.dumps(mounts))

    def test_R38_paperless_production_mounts_are_fully_replaced(self):
        _, _, document = self._isolated_compose("paperless")
        targets = {x["target"] for x in document["services"]["paperless"]["volumes"]}
        self.assertEqual(targets, {"/usr/src/paperless/consume", "/usr/src/paperless/data", "/usr/src/paperless/export", "/usr/src/paperless/media"})

    def test_R39_jellyfin_media_mounts_and_host_network_are_replaced(self):
        _, _, document = self._isolated_compose("jellyfin")
        service = document["services"]["jellyfin"]
        self.assertNotIn("network_mode", service); self.assertNotIn("devices", service)
        self.assertEqual(len(service["volumes"]), 7)
        self.assertEqual(service["ports"][0]["host_ip"], "127.0.0.1")

    def test_R40_monatsausgaben_mount_and_build_are_replaced(self):
        _, _, document = self._isolated_compose("monatsausgaben")
        service = document["services"]["monatsausgaben"]
        self.assertNotIn("build", service)
        self.assertEqual(service["volumes"][0]["target"], "/data")

    def test_R41_immich_model_cache_and_localtime_are_controlled(self):
        _, _, document = self._isolated_compose("immich")
        model = document["services"]["immich-machine-learning"]["volumes"][0]
        localtime = next(x for x in document["services"]["immich-server"]["volumes"] if x["target"] == "/etc/localtime")
        self.assertTrue(model["source"].startswith(str(self.target)))
        self.assertTrue(localtime["source"].startswith(str(self.target))); self.assertTrue(localtime["read_only"])

    def test_R42_nextcloud_and_npm_variables_resolve_only_under_target(self):
        for service in ("nextcloud", "npm"):
            _, _, document = self._isolated_compose(service)
            for definition in document["services"].values():
                for volume in definition.get("volumes", []):
                    self.assertTrue(volume["source"].startswith(str(self.target)))
                    self.assertNotIn("/mnt/data", volume["source"])

    def _port_rejection(self, host_ip):
        contract, env_file, document = self._isolated_compose("adguard")
        document["services"]["adguardhome"]["ports"][0]["host_ip"] = host_ip
        with self.assertRaises(SafetyError):
            validate_isolated_compose(document, contract, self.target, env_file, ["192.0.2.10"])

    def test_R43_productive_ip_in_port_mapping_stops(self): self._port_rejection("192.0.2.10")

    def test_R44_wildcard_ipv4_port_mapping_stops(self): self._port_rejection("0.0.0.0")

    def test_R45_other_non_loopback_port_mapping_stops(self): self._port_rejection("198.51.100.20")

    def test_R46_unexpected_additional_bind_mount_stops(self):
        contract, env_file, document = self._isolated_compose("paperless")
        document["services"]["paperless"]["volumes"].append(
            {"type": "bind", "source": str(self.target / "extra"), "target": "/unexpected", "read_only": False})
        with self.assertRaises(SafetyError):
            validate_isolated_compose(document, contract, self.target, env_file, [])

    def test_R47_missing_dummy_env_stops_before_render(self):
        template = json.loads((ROOT / "config/realtest-config.template.json").read_text(encoding="utf-8"))
        contract = template["services"]["nextcloud"]["compose"]
        payload = load_compose_payload(ROOT / contract["payload_file"])
        with self.assertRaises(ValidationError):
            build_isolated_compose(payload, contract, self.target, self.root / "absent.env")

    def test_R48_compose_internal_productive_env_file_stops(self):
        contract, env_file, document = self._isolated_compose("paperless")
        document["services"]["paperless"]["env_file"] = ["/srv/production-data/paperless/.env"]
        with self.assertRaises(SafetyError):
            validate_isolated_compose(document, contract, self.target, env_file, [])

    def test_R49_missing_analyzer_portal_is_partial_and_never_started(self):
        template = json.loads((ROOT / "config/realtest-config.template.json").read_text(encoding="utf-8"))
        contract = template["services"]["analyzer"]["compose"]
        missing = prepare_companions(contract, ROOT, self.target)
        self.assertIn("tests/fixtures/companions/analyzer/portal", missing)
        self.assertEqual(contract["missing_companion_policy"], "PARTIAL")
        self.assertIs(contract["start"], False)
        self.assertTrue((self.target / "work/compose/analyzer/companions/nginx.conf").is_file())

    def test_R50_external_network_contract_stops(self):
        contract, env_file, document = self._isolated_compose("nextcloud")
        document["networks"]["realtest"]["external"] = True
        with self.assertRaises(SafetyError):
            validate_isolated_compose(document, contract, self.target, env_file, [])

    def test_R51_rendered_service_with_wrong_image_stops(self):
        contract, env_file, document = self._isolated_compose("immich")
        document["services"]["redis"]["image"] = "redis:movable"
        with self.assertRaises(SafetyError):
            validate_isolated_compose(document, contract, self.target, env_file, [])

    def test_R52_actual_payload_service_mismatch_stops(self):
        contract, env_file, _ = self._isolated_compose("adguard")
        payload = load_compose_payload(ROOT / contract["payload_file"])
        payload["services"]["unexpected"] = {"image": "invalid"}
        with self.assertRaises(ValidationError):
            build_isolated_compose(payload, contract, self.target, env_file)

    def _identity_contract(self, service):
        template = json.loads((ROOT / "config/realtest-config.template.json").read_text(encoding="utf-8"))
        return template["services"][service]["compose"]

    def _assert_exact_identity(self, service, primary):
        platform = ComposePlatform(self); self.platform = platform
        contract = self._identity_contract(service)
        self._contract_by_project = {contract["project_name"]: contract}
        platform.activate(contract)
        adapter = self.adapter(); adapter._active_compose[service] = {"argv": ["docker"], "contract": contract}
        state = {}
        adapter._validate_compose_containers(service, state)
        expected = contract["container_names"][primary]
        self.assertTrue(any("inspect" in call and expected in call for call in platform.calls))
        self.assertEqual(state["compose_identity_evidence"][service][0]["status"], "RUNNING_VERIFIED")

    def test_R53_adguard_exact_isolated_identity_is_checked(self): self._assert_exact_identity("adguard", "adguardhome")

    def test_R54_npm_exact_isolated_identity_is_checked(self): self._assert_exact_identity("npm", "npm")

    def test_R55_nextcloud_app_exact_isolated_identity_is_checked(self): self._assert_exact_identity("nextcloud", "app")

    def test_R56_immich_server_exact_isolated_identity_is_checked(self): self._assert_exact_identity("immich", "immich-server")

    def test_R57_paperless_exact_isolated_identity_is_checked(self): self._assert_exact_identity("paperless", "paperless")

    def test_R58_jellyfin_exact_isolated_identity_is_checked(self): self._assert_exact_identity("jellyfin", "jellyfin")

    def test_R59_monatsausgaben_exact_isolated_identity_is_checked(self): self._assert_exact_identity("monatsausgaben", "monatsausgaben")

    def test_R60_foreign_same_named_container_cannot_satisfy_check(self):
        platform = ComposePlatform(self); self.platform = platform
        contract = self._identity_contract("adguard"); self._contract_by_project = {contract["project_name"]: contract}
        adapter = self.adapter(); adapter._active_compose["adguard"] = {"argv": ["docker"], "contract": contract}
        with self.assertRaises(RecoveryError): adapter._validate_compose_containers("adguard", {})
        self.assertIn("adguardhome", platform.foreign_containers)

    def test_R61_wrong_compose_project_membership_stops(self):
        platform = ComposePlatform(self); platform.project_override = "production"; self.platform = platform
        contract = self._identity_contract("npm"); platform.activate(contract)
        adapter = self.adapter(); adapter._active_compose["npm"] = {"argv": ["docker"], "contract": contract}
        with self.assertRaises(SafetyError): adapter._validate_compose_containers("npm", {})

    def test_R62_wrong_running_immutable_image_stops(self):
        platform = ComposePlatform(self); platform.image_override = "example.invalid/wrong@sha256:" + "9" * 64; self.platform = platform
        contract = self._identity_contract("immich"); platform.activate(contract)
        adapter = self.adapter(); adapter._active_compose["immich"] = {"argv": ["docker"], "contract": contract}
        with self.assertRaises(SafetyError): adapter._validate_compose_containers("immich", {})

    def test_R63_isolated_container_not_running_is_unavailable(self):
        platform = ComposePlatform(self); platform.running_override = False; self.platform = platform
        contract = self._identity_contract("paperless"); platform.activate(contract)
        adapter = self.adapter(); adapter._active_compose["paperless"] = {"argv": ["docker"], "contract": contract}
        state = {}
        adapter._test_service("paperless", state)
        self.assertEqual(state["service_outcomes"]["paperless"], "UNAVAILABLE")
        self.assertIn("CONTAINER", state["service_check_failures"]["paperless"])

    def test_R64_persisted_isolated_compose_has_no_dummy_password(self):
        contract = self._identity_contract("nextcloud")
        payload = load_compose_payload(ROOT / contract["payload_file"])
        env_file = self._dummy_compose_env(); marker = "DUMMY_ROOT"
        document = build_isolated_compose(payload, contract, self.target, env_file)
        persisted = self.root / "isolated-compose.json"; atomic_json(persisted, document)
        text = persisted.read_text(encoding="utf-8")
        self.assertNotIn(marker, text); self.assertIn("${MYSQL_ROOT_PASSWORD}", text)

    def test_R65_persisted_healthcheck_retains_reference_not_secret(self):
        contract = self._identity_contract("nextcloud")
        payload = load_compose_payload(ROOT / contract["payload_file"]); env_file = self._dummy_compose_env()
        document = build_isolated_compose(payload, contract, self.target, env_file)
        health = json.dumps(document["services"]["db"]["healthcheck"])
        self.assertIn("${MYSQL_PASSWORD}", health); self.assertNotIn("DUMMY_PASSWORD", health)

    class _Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return False

    def _compose_execution(self, *, abort=False, fail_up=False, fail_down=False, leak_marker=False):
        platform = ComposePlatform(self); platform.fail_up = fail_up; platform.fail_down = fail_down; self.platform = platform
        contract = self._identity_contract("adguard"); self._contract_by_project = {contract["project_name"]: contract}
        self.config["services"]["adguard"]["compose"] = contract
        self.config["services"]["adguard"]["checks"].append(
            {"kind": "ENDPOINT", "url": "http://127.0.0.1:3000/", "status": [200]})
        reference = contract["image_bindings"]["adguardhome"]
        self.config["images"] = [{"services": ["adguard"], "kind": "REGISTRY", "reference": reference,
                                  "archive_rel": "missing.tar", "archive_sha256": "3" * 64,
                                  "expected_image_id": "sha256:" + "1" * 64}]
        self.write_config(); plan = self.plan("adguard")
        plan["steps"] = [step for step in plan["steps"] if step["op"] in {"RESTORE_SERVICE", "TEST_SERVICE"}]
        state = self.manager.create(plan)
        secret_dir = self.target / "hp-recovery-secret-e2e"; (secret_dir / "compose").mkdir(parents=True)
        marker = "DUMMY_FULL_FLOW_MARKER_8347"
        (secret_dir / "compose/adguard.env").write_text(f"DUMMY_PASSWORD={marker}\nADGUARD_TAG=DUMMY\n", encoding="utf-8")
        state["plaintext_secret_dir"] = str(secret_dir); self.manager.save(state)
        adapter = self.adapter(); adapter.config["_plaintext_secret_dir"] = str(secret_dir)
        adapter._secret_markers.add(marker.encode())
        leak_file = self.target / "work/persistent-marker.txt"
        if leak_marker:
            leak_file.parent.mkdir(parents=True, exist_ok=True)
            leak_file.write_text(marker + "\n", encoding="utf-8")
        with mock.patch("hp_recovery.realtest.urllib.request.urlopen", return_value=self._Response()):
            if fail_up or fail_down:
                with self.assertRaises(RecoveryError):
                    execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
            else:
                execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"],
                        abort_at="test.adguard" if abort else None)
        return marker, plan, platform, secret_dir

    def test_R66_state_audit_reports_errors_and_compose_are_secret_free(self):
        marker, plan, _, _ = self._compose_execution()
        run_dir = self.manager.path(plan["run_id"]).parent
        for path in [self.manager.path(plan["run_id"]), run_dir / "report.json", run_dir / "report.md",
                     self.target / "work/compose/adguard/isolated-compose.json"]:
            self.assertNotIn(marker, path.read_text(encoding="utf-8"))

    def test_R67_success_removes_secret_files_and_compose_containers(self):
        _, plan, platform, secret_dir = self._compose_execution()
        self.assertFalse(secret_dir.exists()); self.assertFalse(platform.containers)
        self.assertEqual(self.manager.load(plan["run_id"])["status"], "COMPLETED")

    def test_R68_user_abort_removes_secret_files_and_compose_containers(self):
        _, plan, platform, secret_dir = self._compose_execution(abort=True)
        self.assertFalse(secret_dir.exists()); self.assertFalse(platform.containers)
        self.assertEqual(self.manager.load(plan["run_id"])["status"], "ABORTED")

    def test_R69_compose_failure_removes_secret_files_and_runtime_objects(self):
        marker, plan, platform, secret_dir = self._compose_execution(fail_up=True)
        self.assertFalse(secret_dir.exists()); self.assertFalse(platform.containers)
        combined = self.manager.path(plan["run_id"]).read_text() + (self.manager.path(plan["run_id"]).parent / "report.json").read_text()
        self.assertNotIn(marker, combined); self.assertNotIn("DUMMY_FAILURE_DETAIL", combined)

    def test_R70_database_failure_removes_export_and_target_containers(self):
        platform = ComposePlatform(self); platform.fail_token = "import_dump"; self.platform = platform
        raw = self.l2 / "server-backups/mirror/data/immich_pgdata"; raw.mkdir(); (raw / "PG_VERSION").write_text("14\n")
        docker = ["docker", "--host", self.config["container_runtime"]["socket"]]
        contract = {"kind": "POSTGRESQL", "workflows": {"L2_ONLY": {"source_kind": "L2_RAW", "raw_source_rel": "immich_pgdata"}}, "commands": {
            "isolated_start": {"argv": docker + ["run", "--name", "hp-realtest-db-export", "image"]},
            "logical_export": {"argv": ["true", "logical_export"]},
            "isolated_stop": {"argv": docker + ["container", "rm", "--force", "hp-realtest-db-export"]},
            "initialize_empty": {"argv": docker + ["run", "--name", "hp-realtest-db-target", "image"]},
            "import_dump": {"argv": ["true", "import_dump"]}, "test_query": {"argv": ["true", "test_query"]},
            "target_stop": {"argv": docker + ["container", "rm", "--force", "hp-realtest-db-target"]}}}
        adapter = self.adapter(); adapter.config["_plaintext_secret_dir"] = str(self.target)
        with self.assertRaises(RecoveryError): adapter._database_workflow("immich", contract, self.plan("immich"), {})
        self.assertFalse(platform.containers)

    def test_R71_completed_flow_leaves_no_dummy_secret_container(self):
        _, _, platform, _ = self._compose_execution()
        self.assertEqual(platform.containers, {})

    def test_R72_failed_container_cleanup_prevents_full(self):
        _, plan, platform, secret_dir = self._compose_execution(fail_down=True)
        state = self.manager.load(plan["run_id"])
        self.assertEqual(state["status"], "FAILED"); self.assertEqual(state["last_error"], "CLEANUP_FAILED")
        self.assertTrue(platform.containers); self.assertFalse(secret_dir.exists())

    def test_R73_analyzer_without_portal_is_partial_and_not_started(self):
        contract = self._identity_contract("analyzer")
        self.assertFalse(contract["start"]); self.assertEqual(contract["missing_companion_policy"], "PARTIAL")
        self.assertFalse((ROOT / "tests/fixtures/companions/analyzer/portal").exists())

    def test_R74_full_compose_identity_endpoint_cleanup_secret_flow(self):
        marker, plan, platform, secret_dir = self._compose_execution()
        state = self.manager.load(plan["run_id"]); run_dir = self.manager.path(plan["run_id"]).parent
        self.assertEqual(state["status"], "COMPLETED"); self.assertEqual(state["runtime_cleanup"], "PASS")
        self.assertEqual(state["compose_projects"]["adguard"]["status"], "REMOVED")
        self.assertFalse(secret_dir.exists()); self.assertFalse(platform.containers)
        for root in (self.target, run_dir, self.manager.log_root):
            for path in root.rglob("*"):
                if path.is_file(): self.assertNotIn(marker.encode(), path.read_bytes())

    def test_R75_cleanup_failure_resume_with_remaining_container_never_completes(self):
        _, plan, platform, _ = self._compose_execution(fail_down=True)
        failed = self.manager.load(plan["run_id"])
        with self.assertRaises(RecoveryError):
            execute(self.manager, failed, self.adapter(), confirmation=plan["confirmation_phrase"])
        resumed = self.manager.load(plan["run_id"])
        self.assertEqual(resumed["status"], "FAILED")
        self.assertEqual(resumed["last_error"], "CLEANUP_FAILED")
        self.assertNotEqual(resumed.get("runtime_cleanup"), "PASS")
        self.assertTrue(platform.containers)

    def test_R76_later_successful_resume_removes_persisted_project_then_completes(self):
        _, plan, platform, _ = self._compose_execution(fail_down=True)
        platform.fail_down = False
        failed = self.manager.load(plan["run_id"])
        done = execute(self.manager, failed, self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual(done["status"], "COMPLETED")
        self.assertEqual(done["runtime_cleanup"], "PASS")
        self.assertIsNone(done["last_error"])
        self.assertFalse(platform.containers); self.assertFalse(platform.networks)
        self.assertEqual(done["runtime_cleanup_contracts"]["adguard"]["cleanup_status"], "REMOVED")
        self.assertTrue(any(item["error"] == "CLEANUP_FAILED" for item in done["error_history"]))

    def test_R77_repeated_cleanup_failure_remains_failed(self):
        _, plan, _, _ = self._compose_execution(fail_down=True)
        for _ in range(2):
            failed = self.manager.load(plan["run_id"])
            with self.assertRaises(RecoveryError):
                execute(self.manager, failed, self.adapter(), confirmation=plan["confirmation_phrase"])
            current = self.manager.load(plan["run_id"])
            self.assertEqual(current["status"], "FAILED")
            self.assertEqual(current["last_error"], "CLEANUP_FAILED")

    def test_R78_foreign_container_at_expected_name_is_not_removed(self):
        _, plan, platform, _ = self._compose_execution(fail_down=True)
        platform.fail_down = False
        expected = "hp-realtest-adguard-adguardhome"
        platform.containers[expected]["project"] = "production"
        removes_before = sum(1 for call in platform.calls if "container" in call and "rm" in call)
        with self.assertRaises(RecoveryError):
            execute(self.manager, self.manager.load(plan["run_id"]), self.adapter(),
                    confirmation=plan["confirmation_phrase"])
        removes_after = sum(1 for call in platform.calls if "container" in call and "rm" in call)
        state = self.manager.load(plan["run_id"])
        self.assertIn(expected, platform.containers)
        self.assertEqual(removes_after, removes_before)
        self.assertEqual(state["status"], "FAILED")
        self.assertEqual(state["last_error"], "CLEANUP_FAILED")

    def test_R79_runtime_cleanup_pass_impossible_with_remaining_network(self):
        platform = ComposePlatform(self); platform.fail_network_cleanup = True; self.platform = platform
        contract = self._identity_contract("adguard"); self._contract_by_project = {contract["project_name"]: contract}
        self.config["services"]["adguard"]["compose"] = contract
        reference = contract["image_bindings"]["adguardhome"]
        self.config["images"] = [{"services": ["adguard"], "kind": "REGISTRY", "reference": reference,
                                  "archive_rel": "missing.tar", "archive_sha256": "3" * 64,
                                  "expected_image_id": "sha256:" + "1" * 64}]
        self.write_config(); plan = self.plan("adguard")
        plan["steps"] = [step for step in plan["steps"] if step["op"] == "RESTORE_SERVICE"]
        state = self.manager.create(plan)
        secret_dir = self.target / "hp-recovery-secret-network"; (secret_dir / "compose").mkdir(parents=True)
        (secret_dir / "compose/adguard.env").write_text("ADGUARD_TAG=DUMMY\n", encoding="utf-8")
        state["plaintext_secret_dir"] = str(secret_dir); self.manager.save(state)
        adapter = self.adapter(); adapter.config["_plaintext_secret_dir"] = str(secret_dir)
        with self.assertRaises(RecoveryError):
            execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        failed = self.manager.load(plan["run_id"])
        self.assertTrue(platform.networks)
        self.assertEqual(failed["status"], "FAILED")
        self.assertNotEqual(failed.get("runtime_cleanup"), "PASS")

    def test_R80_completed_state_has_no_active_cleanup_error(self):
        _, plan, _, _ = self._compose_execution()
        state = self.manager.load(plan["run_id"])
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["runtime_cleanup"], "PASS")
        self.assertIsNone(state["last_error"])
        self.assertNotIn("cleanup_errors", state)
        self.assertNotIn("cleanup_error_count", state)

    def test_R81_secret_free_cleanup_contract_is_persisted_before_up(self):
        platform = ComposePlatform(self); self.platform = platform
        contract = self._identity_contract("adguard"); self._contract_by_project = {contract["project_name"]: contract}
        self.config["services"]["adguard"]["compose"] = contract
        reference = contract["image_bindings"]["adguardhome"]
        self.config["images"] = [{"services": ["adguard"], "kind": "REGISTRY", "reference": reference,
                                  "archive_rel": "missing.tar", "archive_sha256": "3" * 64,
                                  "expected_image_id": "sha256:" + "1" * 64}]
        self.write_config(); plan = self.plan("adguard")
        plan["steps"] = [step for step in plan["steps"] if step["op"] == "RESTORE_SERVICE"]
        state = self.manager.create(plan)
        secret_dir = self.target / "hp-recovery-secret-contract"; (secret_dir / "compose").mkdir(parents=True)
        marker = "DUMMY_CONTRACT_SECRET_9182"
        (secret_dir / "compose/adguard.env").write_text(f"PASSWORD={marker}\nADGUARD_TAG=DUMMY\n", encoding="utf-8")
        state["plaintext_secret_dir"] = str(secret_dir); self.manager.save(state)
        observed = []
        platform.up_observer = lambda: observed.append(self.manager.load(plan["run_id"])["runtime_cleanup_contracts"]["adguard"])
        adapter = self.adapter(); adapter.config["_plaintext_secret_dir"] = str(secret_dir)
        adapter._secret_markers.add(marker.encode())
        execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        self.assertEqual(len(observed), 1)
        saved = observed[0]
        self.assertEqual(saved["cleanup_status"], "PENDING_START")
        self.assertEqual(saved["project_name"], "hp-realtest-adguard")
        self.assertEqual(saved["service_ids"], ["adguardhome"])
        self.assertNotIn(marker, json.dumps(saved))
        self.assertNotIn("argv", json.dumps(saved).lower())

    def test_R82_marker_failure_survives_fresh_resume_and_blocks_completed(self):
        marker, plan, platform, _ = self._compose_execution(fail_down=True, leak_marker=True)
        marker_file = self.target / "work/persistent-marker.txt"
        first = self.manager.load(plan["run_id"])
        self.assertEqual(first["marker_verification"]["status"], "FAILED")
        self.assertTrue(marker_file.is_file()); self.assertIn(marker, marker_file.read_text())
        platform.fail_down = False
        with self.assertRaises(RecoveryError):
            execute(self.manager, first, self.adapter(), confirmation=plan["confirmation_phrase"])
        resumed = self.manager.load(plan["run_id"])
        self.assertEqual(resumed["status"], "FAILED")
        self.assertEqual(resumed["last_error"], "CLEANUP_FAILED")
        self.assertEqual(resumed["runtime_cleanup"], "FAILED")
        self.assertEqual(resumed["marker_verification"]["status"], "FAILED")
        self.assertTrue(marker_file.is_file()); self.assertIn(marker, marker_file.read_text())

    def test_R83_empty_fresh_adapter_cannot_replace_stored_marker_failure(self):
        _, plan, platform, _ = self._compose_execution(fail_down=True, leak_marker=True)
        platform.fail_down = False
        state = self.manager.load(plan["run_id"])
        adapter = self.adapter()
        self.assertFalse(adapter._secret_markers)
        with self.assertRaises(RecoveryError):
            execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        self.assertEqual(self.manager.load(plan["run_id"])["marker_verification"]["status"], "FAILED")

    def test_R84_pending_or_unknown_marker_status_prevents_cleanup_pass(self):
        for status in ("PENDING", "UNKNOWN"):
            plan = self.plan(); state = self.manager.create(plan)
            state["plan"]["steps"] = []
            state["marker_verification"] = {"status": status, "run_id": state["run_id"],
                                             "operation_generation": 1, "verified_generation": None,
                                             "method": "AWAITING_MARKER_SCAN", "path_classes": [], "hit_count": 0}
            self.manager.save(state)
            with self.assertRaises(RecoveryError):
                execute(self.manager, state, self.adapter(), confirmation=plan["confirmation_phrase"])
            failed = self.manager.load(plan["run_id"])
            self.assertEqual(failed["status"], "FAILED")
            self.assertNotEqual(failed.get("runtime_cleanup"), "PASS")

    def test_R85_prior_marker_pass_allows_pure_cleanup_resume_without_new_operations(self):
        _, plan, platform, _ = self._compose_execution(fail_down=True)
        failed = self.manager.load(plan["run_id"])
        verification = dict(failed["marker_verification"])
        self.assertEqual(verification["status"], "PASS")
        platform.fail_down = False
        done = execute(self.manager, failed, self.adapter(), confirmation=plan["confirmation_phrase"])
        self.assertEqual(done["status"], "COMPLETED")
        self.assertEqual(done["marker_verification"]["status"], "PASS")
        self.assertEqual(done["marker_verification"]["verified_generation"],
                         done["marker_verification"]["operation_generation"])
        self.assertEqual(done["marker_verification"]["operation_generation"],
                         verification["operation_generation"])

    def test_R86_marker_failure_evidence_is_secret_free_everywhere(self):
        marker, plan, _, _ = self._compose_execution(fail_down=True, leak_marker=True)
        marker_file = self.target / "work/persistent-marker.txt"
        marker_file.unlink()
        state_path = self.manager.path(plan["run_id"]); run_dir = state_path.parent
        state = json.loads(state_path.read_text())
        evidence = json.dumps({"state": state, "report": json.loads((run_dir / "report.json").read_text())})
        self.assertNotIn(marker, evidence)
        self.assertEqual(state["marker_verification"]["status"], "FAILED")
        self.assertGreater(state["marker_verification"]["hit_count"], 0)
        self.assertTrue(state["marker_verification"]["path_classes"])

    def test_R87_completed_state_has_explicit_current_marker_pass(self):
        _, plan, _, _ = self._compose_execution()
        state = self.manager.load(plan["run_id"]); verification = state["marker_verification"]
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["run_id"], state["run_id"])
        self.assertEqual(verification["verified_generation"], verification["operation_generation"])

    def test_R88_known_marker_as_free_positional_argument_is_redacted(self):
        marker = "DUMMY_POSITIONAL_MARKER_8347"
        adapter = self.adapter(); adapter._secret_markers.add(marker.encode())
        adapter._recorded_run(["true", marker])
        self.assertEqual(adapter.command_audit[-1], ["true", "<REDACTED>"])
        self.assertNotIn(marker, json.dumps(adapter.command_audit))

    def test_R89_known_marker_substrings_and_embedded_values_are_redacted(self):
        marker = "DUMMY_SUBSTRING_MARKER_8347"
        adapter = self.adapter(); adapter._secret_markers.add(marker.encode())
        adapter._recorded_run(["true", f"prefix-{marker}-suffix", f"--value={marker}"])
        self.assertEqual(adapter.command_audit[-1],
                         ["true", "prefix-<REDACTED>-suffix", "--value=<REDACTED>"])
        self.assertNotIn(marker, json.dumps(adapter.command_audit))

    def test_R90_complete_audit_is_persisted_before_final_marker_scan(self):
        marker = "DUMMY_AUDIT_ORDER_MARKER_8347"
        adapter = self.adapter(); adapter._secret_markers.add(marker.encode())
        adapter._recorded_run(["true", marker])
        plan = self.plan(); plan["steps"] = []; state = self.manager.create(plan)
        observed = []
        original_verify = adapter.verify_secret_cleanup

        def observe_then_verify(current, roots):
            persisted = self.manager.load(plan["run_id"])
            observed.append(persisted.get("realtest_command_audit"))
            return original_verify(current, roots)

        adapter.verify_secret_cleanup = observe_then_verify
        done = execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        self.assertEqual(done["status"], "COMPLETED")
        self.assertEqual(observed, [[["true", "<REDACTED>"]]])
        self.assertNotIn(marker, json.dumps(observed))

    def test_R91_intentionally_unredacted_audit_marker_blocks_completed_and_pass(self):
        marker = "DUMMY_UNREDACTED_AUDIT_MARKER_8347"
        adapter = self.adapter(); adapter._secret_markers.add(marker.encode())
        plan = self.plan(); plan["steps"] = []; state = self.manager.create(plan)
        original_seal = adapter.seal_command_audit

        def inject_after_seal(current):
            original_seal(current)
            current["realtest_command_audit"].append(["true", marker])
            adapter._sealed_audit = json.dumps(current["realtest_command_audit"],
                                                sort_keys=True, ensure_ascii=False)

        adapter.seal_command_audit = inject_after_seal
        with self.assertRaises(RecoveryError):
            execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        failed = self.manager.load(plan["run_id"]); run_dir = self.manager.path(plan["run_id"]).parent
        self.assertEqual(failed["status"], "FAILED")
        self.assertEqual(failed["last_error"], "CLEANUP_FAILED")
        self.assertEqual(failed["runtime_cleanup"], "FAILED")
        self.assertEqual(failed["marker_verification"]["status"], "FAILED")
        evidence = "\n".join((run_dir / name).read_text(encoding="utf-8")
                             for name in ("state.json", "report.json", "report.md"))
        self.assertNotIn(marker, evidence)

    def test_R92_final_state_reports_and_log_are_marker_free(self):
        marker = "DUMMY_FINAL_EVIDENCE_MARKER_8347"
        adapter = self.adapter(); adapter._secret_markers.add(marker.encode())
        adapter._recorded_run(["true", marker, f"prefix-{marker}-suffix"])
        plan = self.plan(); plan["steps"] = []; state = self.manager.create(plan)
        log_path = self.manager.log_root / "realtest.log"
        log_path.write_text("secret-free runtime log\n", encoding="utf-8")
        done = execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        self.assertEqual(done["status"], "COMPLETED")
        run_dir = self.manager.path(plan["run_id"]).parent
        for path in (run_dir / "state.json", run_dir / "report.json", run_dir / "report.md", log_path):
            self.assertNotIn(marker, path.read_text(encoding="utf-8"))

    def test_R93_no_unchecked_audit_data_can_be_added_after_marker_scan(self):
        marker = "DUMMY_AUDIT_SEAL_MARKER_8347"
        late_value = "UNSCANNED_AUDIT_VALUE"
        adapter = self.adapter(); adapter._secret_markers.add(marker.encode())
        adapter._recorded_run(["true", marker])
        plan = self.plan(); plan["steps"] = []; state = self.manager.create(plan)
        original_runtime_verify = adapter.verify_runtime_cleanup
        attempted = []

        def attempt_late_audit(current):
            attempted.append(True)
            with self.assertRaises(SafetyError):
                adapter._recorded_run(["true", late_value])
            return original_runtime_verify(current)

        adapter.verify_runtime_cleanup = attempt_late_audit
        done = execute(self.manager, state, adapter, confirmation=plan["confirmation_phrase"])
        self.assertEqual(attempted, [True])
        self.assertEqual(done["status"], "COMPLETED")
        self.assertNotIn(late_value, json.dumps(done["realtest_command_audit"]))

    def _run_package_gate(self):
        self.adapter()._prepare_packages_images({}, {"services": ["adguard"]})

    def test_R94_only_docker_compose_v2_package_passes(self):
        self.platform.installed_packages = {"rsync", "docker-compose-v2"}
        self._run_package_gate()

    def test_R95_only_docker_compose_plugin_package_passes(self):
        self.platform.installed_packages = {"rsync", "docker-compose-plugin"}
        self._run_package_gate()

    def test_R96_both_compose_package_alternatives_pass(self):
        self.platform.installed_packages = {"rsync", "docker-compose-v2", "docker-compose-plugin"}
        self._run_package_gate()

    def test_R97_missing_compose_package_alternatives_stop(self):
        self.platform.installed_packages = {"rsync"}
        with self.assertRaises(ValidationError):
            self._run_package_gate()

    def test_R98_empty_required_any_group_stops_at_config_load(self):
        self.config["packages"]["required_any"] = [[]]
        with self.assertRaises(ValidationError):
            self.loaded()

    def test_R99_nonarray_required_any_stops_at_config_load(self):
        self.config["packages"]["required_any"] = "docker-compose-v2"
        with self.assertRaises(ValidationError):
            self.loaded()

    def test_R100_empty_package_name_stops_at_config_load(self):
        self.config["packages"]["required_any"] = [[""]]
        with self.assertRaises(ValidationError):
            self.loaded()

    def test_R101_package_present_but_compose_v2_capability_failure_stops(self):
        self.platform.installed_packages = {"rsync", "docker-compose-v2"}
        self.platform.compose_v2_available = False
        with self.assertRaises(ValidationError):
            self._run_package_gate()

    def test_R102_legacy_docker_compose_command_is_never_an_alternative(self):
        self.platform.installed_packages = {"rsync"}
        self.platform.compose_v2_available = False
        with self.assertRaises(ValidationError):
            self._run_package_gate()
        self.assertFalse(any(call and call[0] == "docker-compose" for call in self.platform.calls))

    def test_R103_missing_exact_required_package_still_stops(self):
        self.platform.installed_packages = {"docker-compose-v2"}
        with self.assertRaises(ValidationError):
            self._run_package_gate()

    def test_R104_package_checks_use_stable_locale(self):
        self.platform.installed_packages = {"rsync", "docker-compose-v2"}
        self._run_package_gate()
        relevant = [item for item in self.platform.io_calls
                    if item["argv"][0] == "dpkg-query" or item["argv"][-2:] == ["compose", "version"]]
        self.assertTrue(relevant)
        self.assertTrue(all(item["env"] == {"LC_ALL": "C", "LANG": "C"} for item in relevant))

    def test_R105_compose_capability_is_bound_to_isolated_socket(self):
        self.platform.installed_packages = {"rsync", "docker-compose-v2"}
        self._run_package_gate()
        calls = [item["argv"] for item in self.platform.io_calls
                 if item["argv"][-2:] == ["compose", "version"]]
        self.assertEqual(calls, [["docker", "--host", str(self.target / "run/docker.sock"),
                                  "compose", "version"]])

    def test_R106_template_declares_native_compose_alternatives(self):
        template = json.loads((ROOT / "config/realtest-config.template.json").read_text(encoding="utf-8"))
        self.assertNotIn("docker-compose-plugin", template["packages"]["required"])
        self.assertEqual(template["packages"]["required_any"],
                         [["docker-compose-v2", "docker-compose-plugin"]])


if __name__ == "__main__": unittest.main(verbosity=2)
