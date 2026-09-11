import contextlib
import io
import json
import os
import pathlib
import pty
import select
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from hp_recovery.errors import SafetyError, ValidationError
from hp_recovery.reporting import build_report
from hp_recovery.realtest import RealtestAdapter
from hp_recovery.state import StateManager
from hp_recovery.util import atomic_json, read_json
from hp_recovery.wizard import (APP_SERVICES, Console, RecoveryWizard,
                                UserCancelled, VISIBLE_SERVICES,
                                _runtime_from_environment, menu_help)


class ScriptConsole(Console):
    def __init__(self, text="", secret_value="DUMMY_TEST_PASSPHRASE"):
        self.buffer = io.StringIO()
        super().__init__(io.StringIO(text), self.buffer, lambda _prompt: secret_value)

    @property
    def text(self):
        return self.buffer.getvalue()


class WizardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hp-wizard-v028-")
        self.base = pathlib.Path(self.temp.name)
        self.fixture = self.base / "fixture"
        l2 = self.fixture / "l2/server-backups/mirror/data"
        snap = self.fixture / "l3/2026-09-07_02-38"
        l2.mkdir(parents=True); snap.mkdir(parents=True)
        for service in VISIBLE_SERVICES:
            for root in (l2, snap):
                path = root / service
                path.mkdir()
                (path / "fixture.txt").write_text(service + "\n", encoding="utf-8")
        atomic_json(self.fixture / "sources.json", {
            "l2_root": "l2", "l3_roots": ["l3"], "data_target": "target-data"
        })
        atomic_json(self.fixture / "sizes.json", {
            "system": 1024,
            **{service: 1024 for service in VISIBLE_SERVICES},
        })
        self.state = self.base / "runtime/state"
        self.log = self.base / "runtime/log"
        self.old_env = dict(os.environ)
        os.environ["HP_RECOVERY_WIZARD_FIXTURE_ROOT"] = str(self.fixture)
        os.environ["HP_RECOVERY_ALLOW_TEST_ROOT"] = "1"
        os.environ["HP_RECOVERY_PROGRESS_INTERVAL"] = "0.05"

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.old_env)
        self.temp.cleanup()

    def wizard(self, console=None):
        return RecoveryWizard(ROOT, self.state, self.log, console or ScriptConsole("6\n"))

    def test_W01_help_is_human_and_nonempty(self):
        text = menu_help()
        self.assertIn("geführtes Menü", text)
        self.assertIn("PRODUKTION", text)

    def test_W02_menu_exit_without_mutation(self):
        console = ScriptConsole("6\n")
        self.assertEqual(self.wizard(console).run(), 0)
        self.assertIn("nichts gestartet", console.text)
        self.assertFalse(self.state.exists())

    def test_W03_invalid_input_repeats(self):
        console = ScriptConsole("x\n99\n6\n")
        self.wizard(console).run()
        self.assertEqual(console.text.count("Ungültige Auswahl"), 2)

    def test_W04_eof_aborts_without_mutation(self):
        console = ScriptConsole("")
        with self.assertRaises(UserCancelled):
            console.choose("Test", [("x", "X")], allow_cancel=False)
        self.assertFalse(self.state.exists())

    def test_W05_ctrl_c_is_safe(self):
        class Interrupting(io.StringIO):
            def readline(self, *args, **kwargs):
                raise KeyboardInterrupt
        console = Console(Interrupting(), io.StringIO())
        with self.assertRaises(UserCancelled):
            console.ask("Auswahl: ")

    def test_W06_all_main_menu_entries_are_rendered(self):
        console = ScriptConsole("6\n")
        self.wizard(console).run()
        for text in ("Gesamten Server", "Einzelnen Dienst", "fortsetzen", "nur prüfen", "Letzten Recovery-Bericht"):
            self.assertIn(text, console.text)

    def test_W07_all_required_services_visible_and_monatsausgaben_hidden(self):
        console = ScriptConsole("0\n")
        with self.assertRaises(UserCancelled):
            self.wizard(console)._select_service()
        for label in ("AdGuard", "Analyzer", "Immich", "Jellyfin", "Nextcloud", "Nginx Proxy Manager",
                      "Paperless", "Snowflake", "Storage", "Urlaubsplaner", "DeviceWatchdog"):
            self.assertIn(label, console.text)
        self.assertNotIn("Monatsausgaben", console.text)

    def test_W08_app_restore_cases(self):
        for service in APP_SERVICES:
            console = ScriptConsole("1\n")
            self.assertEqual(RecoveryWizard(ROOT, self.state, self.log, console)._select_restore_case(service), "APP_DATA_ONLY")

    def test_W09_previous_requires_complete_compatible_contract(self):
        context = _runtime_from_environment(ROOT)
        with self.assertRaises(ValidationError):
            self.wizard()._build_plan(context, "SINGLE_SERVICE", "urlaubsplaner", "APP_PREVIOUS",
                                      "COMBINED_L2_L3", "2026-09-07_02-38")

    def test_W10_source_scan_shows_l2_l3_size_and_services(self):
        console = ScriptConsole()
        context = _runtime_from_environment(ROOT)
        self.wizard(console)._show_sources(context.scan)
        self.assertIn("Backup-HDD", console.text)
        self.assertIn("2026-09-07_02-38", console.text)
        self.assertIn("Urlaubsplaner", console.text)

    def test_W11_zero_l3_offers_deferred_not_l3_only(self):
        atomic_json(self.fixture / "sources.json", {"l2_root": "l2", "l3_roots": [], "data_target": "target-data"})
        console = ScriptConsole("3\n")
        mode = self.wizard(console)._select_mode(_runtime_from_environment(ROOT).scan)
        self.assertEqual(mode, "BASE_ONLY")
        self.assertIn("Level 3 später", console.text)
        self.assertNotIn("Nur Level 3\n", console.text)

    def test_W12_multiple_snapshots_require_explicit_selection(self):
        second = self.fixture / "l3/2026-09-06_02-38/nextcloud"
        second.mkdir(parents=True); (second / "x").write_text("x")
        context = _runtime_from_environment(ROOT)
        console = ScriptConsole("2\n")
        selected = self.wizard(console)._select_snapshot(context.scan, "L3_ONLY")
        self.assertEqual(selected, "2026-09-07_02-38")
        self.assertEqual(console.text.count("2026-09-"), 2)

    def test_W13_plan_preview_is_human_and_says_no_changes(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "urlaubsplaner", "APP_FULL",
                                         "COMBINED_L2_L3", "2026-09-07_02-38")
        console = ScriptConsole()
        self.wizard(console)._preview(plan)
        for text in ("Wiederherstellungsplan", "Urlaubsplaner", "Geschätzte Laufzeit", "noch keine Änderungen"):
            self.assertIn(text, console.text)

    def test_W14_confirmation_phrase_is_specific(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        self.assertRegex(plan["confirmation_phrase"], r"^WIEDERHERSTELLUNG ADGUARD AUF .+ BESTÄTIGEN$")
        self.assertNotEqual(plan["confirmation_phrase"].lower(), "ja")

    def test_W15_wrong_confirmation_creates_no_state_or_target(self):
        console = ScriptConsole("1\n1\n1\nfalsch\n")
        with self.assertRaises(ValidationError):
            self.wizard(console).restore("SINGLE_SERVICE")
        self.assertFalse(self.state.exists())
        self.assertFalse((self.fixture / "target-data").exists())

    def test_W16_fixture_execution_and_reports(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        manager = StateManager(self.state, self.log); manager.create(plan); manager.close()
        console = ScriptConsole()
        self.wizard(console)._execute_worker(context, plan, plan["confirmation_phrase"], resume=False)
        run = self.state / "runs" / plan["run_id"]
        self.assertEqual(read_json(run / "state.json")["status"], "COMPLETED")
        self.assertTrue((run / "report.json").is_file())
        self.assertTrue((run / "report.md").is_file())
        self.assertIn("FULL", console.text)

    def test_W17_full_server_fixture_plan_excludes_monatsausgaben(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "FULL_SERVER", None, "FULL_SERVER",
                                         "COMBINED_L2_L3", "2026-09-07_02-38")
        self.assertEqual(plan["services"], list(VISIBLE_SERVICES))
        self.assertNotIn("monatsausgaben", plan["services"])

    def test_W18_no_binding_blocks_restore_but_check_package_remains(self):
        os.environ.pop("HP_RECOVERY_WIZARD_FIXTURE_ROOT")
        with self.assertRaises(SafetyError):
            _runtime_from_environment(ROOT)

    def test_W19_protected_production_target_rejected(self):
        from hp_recovery.util import ensure_safe_target
        for path in ("/", "/home", "/mnt"):
            with self.assertRaises(SafetyError):
                ensure_safe_target(path)

    def test_W20_report_has_resume_and_no_secret(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        state = StateManager(self.state, self.log).create(plan)
        state["status"] = "FAILED"; state["last_error"] = "DUMMY"; state["password"] = "NEVER"
        report = build_report(state)
        data = json.dumps(report)
        self.assertIn("hp-recovery-resume", data)
        self.assertNotIn("NEVER", data)

    def test_W21_last_report_is_bounded_and_without_pager(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        manager = StateManager(self.state, self.log); state = manager.create(plan); manager.close()
        run = self.state / "runs" / plan["run_id"]
        atomic_json(run / "report.json", build_report(state))
        console = ScriptConsole()
        self.wizard(console).show_last_report()
        self.assertLess(len(console.text.splitlines()), 40)
        self.assertNotIn("less", console.text)

    def test_W22_status_command_is_noninteractive(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        StateManager(self.state, self.log).create(plan)
        result = subprocess.run([str(ROOT / "bin/hp-recovery"), "--test-root", str(self.state.parent),
                                 "status", plan["run_id"]], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PLANNED")

    def test_W23_secret_prompt_uses_hidden_reader(self):
        seen = []
        console = Console(io.StringIO(), io.StringIO(), lambda prompt: seen.append(prompt) or "DUMMY")
        self.assertEqual(console.secret("Secret-Kennwort: "), "DUMMY")
        self.assertEqual(seen, ["Secret-Kennwort: "])
        self.assertNotIn("DUMMY", console.output.getvalue())

    def test_W24_no_ansi_sequences_in_menu(self):
        console = ScriptConsole("6\n")
        self.wizard(console).run()
        self.assertNotIn("\x1b", console.text)

    def test_W25_help_cli_passes(self):
        result = subprocess.run([str(ROOT / "bin/hp-recovery"), "menu", "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("geführtes Menü", result.stdout)

    def test_W26_no_argument_opens_menu_in_pseudotty(self):
        pid, fd = pty.fork()
        if pid == 0:
            os.execv(str(ROOT / "bin/hp-recovery"), [str(ROOT / "bin/hp-recovery")])
        output = bytearray()
        try:
            deadline = time.time() + 5
            sent = False
            while time.time() < deadline:
                ready, _, _ = select.select([fd], [], [], 0.2)
                if ready:
                    try:
                        chunk = os.read(fd, 4096)
                    except OSError:
                        break
                    output.extend(chunk)
                    if b"Auswahl:" in output and not sent:
                        os.write(fd, b"6\n"); sent = True
                done, status = os.waitpid(pid, os.WNOHANG)
                if done:
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                    break
            else:
                self.fail("Pseudo-TTY menu timed out")
        finally:
            with contextlib.suppress(OSError):
                os.close(fd)
        text = output.decode("utf-8", errors="replace")
        self.assertIn("HP Server Recovery", text)
        self.assertIn("Hauptmenü", text)

    def test_W27_fixture_scan_and_plan_do_not_write_target(self):
        context = _runtime_from_environment(ROOT)
        before = sorted(x.relative_to(self.fixture).as_posix() for x in self.fixture.rglob("*"))
        self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                  "L3_ONLY", "2026-09-07_02-38")
        after = sorted(x.relative_to(self.fixture).as_posix() for x in self.fixture.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse((self.fixture / "target-data").exists())

    def test_W28_console_output_is_bounded(self):
        console = ScriptConsole("6\n")
        self.wizard(console).run()
        self.assertLess(len(console.text.splitlines()), 30)

    def test_W29_runtime_classes_are_visibly_separated(self):
        help_text = menu_help()
        for label in ("FIXTURE", "ISOLATED_REALTEST", "PRODUKTION"):
            self.assertIn(label, help_text)

    def test_W30_worker_command_never_places_secret_value_in_argv(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        manager = StateManager(self.state, self.log); manager.create(plan); manager.close()
        captured = []
        popen_options = {}
        class FakeProc:
            pid = 12345
            def __init__(self, argv, **kwargs):
                captured.extend(argv); popen_options.update(kwargs); self.calls = 0
            def poll(self): self.calls += 1; return 0
            def wait(self, timeout=None): return 0
        completed = read_json(self.state / "runs" / plan["run_id"] / "state.json")
        completed["status"] = "COMPLETED"; completed["service_outcomes"] = {"adguard": "FULL"}
        atomic_json(self.state / "runs" / plan["run_id"] / "state.json", completed)
        with mock.patch("hp_recovery.wizard.subprocess.Popen", FakeProc):
            self.wizard(ScriptConsole(secret_value="TOPSECRET"))._execute_worker(
                context, plan, plan["confirmation_phrase"], resume=False)
        self.assertNotIn("TOPSECRET", " ".join(captured))
        self.assertTrue(popen_options["start_new_session"])

    def test_W31_secret_fd_is_consumed_once(self):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"DUMMY_PASSPHRASE\n"); os.close(write_fd)
        adapter = object.__new__(RealtestAdapter)
        adapter._secret_fd = read_fd
        value = adapter._read_secret_fd()
        self.assertEqual(value, bytearray(b"DUMMY_PASSPHRASE\n"))
        self.assertIsNone(adapter._secret_fd)

    def test_W32_secret_fd_rejects_empty_value(self):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"\n"); os.close(write_fd)
        adapter = object.__new__(RealtestAdapter)
        adapter._secret_fd = read_fd
        with self.assertRaises(ValidationError):
            adapter._read_secret_fd()

    def test_W33_resume_selects_run_without_manual_id_and_skips_completed(self):
        context = _runtime_from_environment(ROOT)
        plan = self.wizard()._build_plan(context, "SINGLE_SERVICE", "adguard", "SINGLE_SERVICE",
                                         "L3_ONLY", "2026-09-07_02-38")
        manager = StateManager(self.state, self.log); state = manager.create(plan)
        state["status"] = "FAILED"; state["completed_steps"] = ["preflight.usb"]
        state["resume_point"] = "preflight.usb"; manager.save(state); manager.close()
        console = ScriptConsole("1\n" + plan["confirmation_phrase"] + "\n")
        self.wizard(console).resume()
        final = read_json(self.state / "runs" / plan["run_id"] / "state.json")
        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["completed_steps"].count("preflight.usb"), 1)
        self.assertIn(plan["run_id"], console.text)

    def test_W34_all_report_end_states_have_labels(self):
        from hp_recovery.wizard import FINAL_LABELS
        self.assertEqual(set(FINAL_LABELS), {"FULL", "PARTIAL", "FAILED", "ABORTED", "WAITING_FOR_L3"})

    def test_W35_scan_plan_preserve_release_identity(self):
        release = ROOT / "payload/app-releases/urlaubsplaner/0.0.0-test/release.json"
        before = (release.read_bytes(), release.stat().st_mtime_ns)
        context = _runtime_from_environment(ROOT)
        self.wizard()._build_plan(context, "SINGLE_SERVICE", "urlaubsplaner", "APP_DATA_ONLY",
                                  "L3_ONLY", "2026-09-07_02-38")
        self.assertEqual((release.read_bytes(), release.stat().st_mtime_ns), before)

    def test_W36_main_check_selection_returns_to_menu(self):
        console = ScriptConsole("4\n6\n")
        self.wizard(console).run()
        self.assertIn("Prüfung abgeschlossen", console.text)

    def test_W37_main_report_selection_returns_to_menu(self):
        console = ScriptConsole("5\n6\n")
        self.wizard(console).run()
        self.assertIn("Kein Recovery-Bericht", console.text)

    def test_W38_main_full_selection_can_cancel_before_plan(self):
        console = ScriptConsole("1\n0\n6\n")
        self.wizard(console).run()
        self.assertIn("Sicher abgebrochen", console.text)
        self.assertFalse((self.fixture / "target-data").exists())

    def test_W39_main_single_selection_can_cancel_before_service(self):
        console = ScriptConsole("2\n0\n6\n")
        self.wizard(console).run()
        self.assertIn("Sicher abgebrochen", console.text)
        self.assertFalse((self.fixture / "target-data").exists())

    def test_W40_main_resume_without_runs_stops_safely(self):
        console = ScriptConsole("3\n6\n")
        self.wizard(console).run()
        self.assertIn("STOP: keine sichere Auswahl verfügbar", console.text)

    def test_W41_owned_stale_secret_directory_is_cleaned(self):
        target = self.base / "isolated-target"; target.mkdir()
        stale = target / "hp-recovery-secret-stale"; stale.mkdir(mode=0o700)
        atomic_json(stale / ".hp-recovery-owned.json",
                    {"run_id": "run-0123456789abcdef", "kind": "PLAINTEXT_SECRET_DIR"})
        (stale / "DUMMY").write_text("DUMMY_TEST_VALUE")
        adapter = object.__new__(RealtestAdapter); adapter.target_root = target
        adapter._cleanup_stale_secret_dirs()
        self.assertFalse(stale.exists())

    def test_W42_foreign_stale_secret_directory_blocks_cleanup(self):
        target = self.base / "isolated-target"; target.mkdir()
        stale = target / "hp-recovery-secret-foreign"; stale.mkdir(mode=0o700)
        adapter = object.__new__(RealtestAdapter); adapter.target_root = target
        with self.assertRaises(SafetyError):
            adapter._cleanup_stale_secret_dirs()
        self.assertTrue(stale.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
