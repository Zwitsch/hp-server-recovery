"""Deutschsprachige, fail-closed Bedienebene der bestehenden Recovery-Engine.

Der Assistent plant oder mutiert nichts selbst. Er verwendet ausschließlich
Validation, Source-Scan, Planner, State, Executor und Reporting der Engine.
Produktive Ausführung bleibt in v0.2.8 bewusst ohne Adapter blockiert.
"""

from __future__ import annotations

import getpass
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .catalog import load_catalog
from .errors import RecoveryError, SafetyError, ValidationError
from .planner import build_plan
from .realtest import (load_realtest_config, realtest_plan_binding,
                       realtest_sizes, scan_real_sources)
from .reporting import build_report
from .source_scan import scan_fixture
from .state import StateManager
from .util import read_json
from .validation import validate_usb


SERVICE_LABELS = {
    "adguard": "AdGuard",
    "analyzer": "Analyzer",
    "immich": "Immich",
    "jellyfin": "Jellyfin",
    "nextcloud": "Nextcloud",
    "npm": "Nginx Proxy Manager",
    "paperless": "Paperless",
    "snowflake": "Snowflake",
    "storage": "Storage",
    "urlaubsplaner": "Urlaubsplaner",
    "devicewatchdog": "DeviceWatchdog",
}
VISIBLE_SERVICES = tuple(SERVICE_LABELS)
APP_SERVICES = {"urlaubsplaner", "devicewatchdog"}
MUTATING_STATUSES = {"PLANNED", "RUNNING", "FAILED", "ABORTED", "WAITING_FOR_L3"}
FINAL_LABELS = {
    "FULL": "Vollständig",
    "PARTIAL": "Teilweise",
    "FAILED": "Fehlgeschlagen",
    "ABORTED": "Abgebrochen",
    "WAITING_FOR_L3": "Wartet auf Level 3",
}


class UserCancelled(Exception):
    pass


class Console:
    """Kleine zeilenorientierte Konsole; absichtlich keine Vollbild-TUI."""

    def __init__(self, input_stream=None, output_stream=None, secret_reader=None):
        self.input = input_stream or sys.stdin
        self.output = output_stream or sys.stdout
        self.secret_reader = secret_reader

    def write(self, text=""):
        print(text, file=self.output, flush=True)

    def ask(self, prompt):
        try:
            self.output.write(prompt)
            self.output.flush()
            line = self.input.readline()
        except KeyboardInterrupt as exc:
            raise UserCancelled from exc
        if line == "":
            raise UserCancelled
        return line.rstrip("\r\n")

    def choose(self, title, choices, *, allow_cancel=True):
        if not choices:
            raise ValidationError("keine sichere Auswahl verfügbar")
        while True:
            self.write("")
            self.write(title)
            for number, (_value, label) in enumerate(choices, 1):
                self.write(f"{number} – {label}")
            if allow_cancel:
                self.write("0 – Zurück / sicher abbrechen")
            answer = self.ask("Auswahl: ").strip()
            if allow_cancel and answer == "0":
                raise UserCancelled
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                return choices[int(answer) - 1][0]
            self.write("Ungültige Auswahl. Es wurde nichts verändert.")

    def secret(self, prompt):
        if self.secret_reader is not None:
            return self.secret_reader(prompt)
        try:
            return getpass.getpass(prompt, stream=self.output)
        except (EOFError, KeyboardInterrupt) as exc:
            raise UserCancelled from exc


@dataclass
class RuntimeContext:
    mode: str
    fixture_root: pathlib.Path | None
    config_path: pathlib.Path | None
    config: dict | None
    scan: dict
    target: pathlib.Path
    system_target: pathlib.Path | None


def _human_bytes(value):
    if value is None:
        return "unbekannt"
    amount = float(value)
    for unit in ("Byte", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.0f} {unit}" if unit == "Byte" else f"{amount:.1f} {unit}"
        amount /= 1024


def _age_from_snapshot(snapshot_id):
    try:
        stamp = datetime.strptime(snapshot_id, "%Y-%m-%d_%H-%M").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return "unbekannt"
    seconds = max(0, int((datetime.now(timezone.utc) - stamp).total_seconds()))
    if seconds < 3600:
        return f"{seconds // 60} Minuten"
    if seconds < 86400:
        return f"{seconds // 3600} Stunden"
    return f"{seconds // 86400} Tage"


def _directory_size(path):
    total = 0
    for base, dirs, names in os.walk(path, followlinks=False):
        dirs[:] = [name for name in dirs if not pathlib.Path(base, name).is_symlink()]
        for name in names:
            item = pathlib.Path(base, name)
            if item.is_symlink() or not item.is_file():
                raise SafetyError("unsicherer Dateityp in Wiederherstellungsquelle")
            total += item.stat().st_size
    return total


def _runtime_from_environment(usb_root):
    fixture = os.environ.get("HP_RECOVERY_WIZARD_FIXTURE_ROOT")
    realtest = os.environ.get("HP_RECOVERY_REALTEST_CONFIG")
    if not realtest:
        for candidate in (pathlib.Path(usb_root) / "config/active-realtest.json",
                          pathlib.Path("/etc/hp-server-recovery/realtest-config.json")):
            if candidate.is_file() and not candidate.is_symlink():
                realtest = str(candidate)
                break
    if fixture and realtest:
        raise ValidationError("Fixture und isolierter Realtest sind gleichzeitig gebunden")
    if fixture:
        root = pathlib.Path(fixture).resolve(strict=True)
        scan = scan_fixture(root)
        cfg = read_json(root / "sources.json")
        return RuntimeContext("FIXTURE", root, None, None, scan,
                              (root / cfg.get("data_target", "target-data")).resolve(strict=False), None)
    if realtest:
        config_path = pathlib.Path(realtest).resolve(strict=True)
        config = load_realtest_config(config_path)
        scan = scan_real_sources(config, usb_root)
        return RuntimeContext("ISOLATED_REALTEST", None, config_path, config, scan,
                              pathlib.Path(config["data_target"]), pathlib.Path(config["system_target"]))
    raise SafetyError(
        "keine isolierte Zielbindung vorhanden; produktive Wiederherstellung ist in v0.2.8 nicht freigegeben"
    )


class RecoveryWizard:
    def __init__(self, usb_root, state_root, log_root, console=None):
        self.usb_root = pathlib.Path(usb_root).resolve()
        self.state_root = pathlib.Path(state_root)
        self.log_root = pathlib.Path(log_root)
        self.console = console or Console()
        self.worker = self.usb_root / "bin/hp-recovery"

    def run(self):
        self._header()
        while True:
            try:
                choice = self.console.choose("Hauptmenü", [
                    ("full", "Gesamten Server wiederherstellen"),
                    ("single", "Einzelnen Dienst oder eine App wiederherstellen"),
                    ("resume", "Unterbrochene Wiederherstellung fortsetzen"),
                    ("check", "Backupquellen und Recovery-Paket nur prüfen"),
                    ("report", "Letzten Recovery-Bericht anzeigen"),
                    ("exit", "Beenden"),
                ], allow_cancel=False)
                if choice == "exit":
                    self.console.write("Recovery-Assistent beendet. Es wurde nichts gestartet.")
                    return 0
                if choice == "check":
                    self.check_only()
                elif choice == "report":
                    self.show_last_report()
                elif choice == "resume":
                    self.resume()
                else:
                    self.restore(scope="FULL_SERVER" if choice == "full" else "SINGLE_SERVICE")
            except UserCancelled:
                self.console.write("Sicher abgebrochen. Vor der Ausführung wurde nichts verändert.")
            except RecoveryError as exc:
                self.console.write(f"STOP: {exc}")
                self.console.write("Details prüfen und den Vorgang erst nach Behebung erneut starten.")

    def _header(self):
        self.console.write("HP Server Recovery")
        self.console.write("==================")
        self.console.write("Geführter Assistent v0.2.8")
        self.console.write("Fixture, isolierter Realtest und Produktion werden strikt getrennt.")
        self.console.write("Bis zur Bestätigung eines Plans kann jederzeit gefahrlos abgebrochen werden.")

    def _context(self):
        return _runtime_from_environment(self.usb_root)

    def check_only(self):
        self.console.write("")
        self.console.write("Paketprüfung läuft (normalerweise unter 1 Minute) …")
        result = validate_usb(self.usb_root)
        self.console.write(f"Recovery-Paket: {result['status']} ({result['manifest_files']} Dateien geprüft)")
        try:
            context = self._context()
        except SafetyError as exc:
            self.console.write(f"Zielumgebung: BLOCKIERT – {exc}")
            self.console.write("Es wurden keine Quellen geöffnet und keine Änderungen ausgeführt.")
            return
        self.console.write("Quellenscan läuft (normalerweise 1–5 Minuten) …")
        self._show_runtime(context)
        self._show_sources(context.scan)
        self.console.write("Prüfung abgeschlossen. Es wurden keine Änderungen ausgeführt.")

    def _show_runtime(self, context):
        label = "Fixture" if context.mode == "FIXTURE" else "ISOLIERTER REALTEST"
        self.console.write(f"Ausführungsart: {label}")
        self.console.write(f"Datenziel: {context.target}")
        if context.system_target:
            self.console.write(f"Systemziel: {context.system_target}")
        identities = context.scan.get("isolation", {}).get("target_devices", {})
        for role in ("system", "data"):
            item = identities.get(role)
            if item:
                self.console.write(
                    f"Zielgerät {role}: {item.get('path')}; Modell {item.get('model')}; "
                    f"UUID {item.get('uuid')}; Größe {_human_bytes(item.get('size'))}; "
                    f"Mountpoint {item.get('mountpoint')}"
                )
        self.console.write("Produktion: NICHT FREIGEGEBEN")

    def _show_sources(self, scan):
        l2 = scan.get("l2")
        if l2:
            size = l2.get("bytes")
            if size is None:
                size = _directory_size(l2["root"])
            self.console.write(f"Level 2 / Backup-HDD: gültig, schreibgeschützt, Größe {_human_bytes(size)}, Pfad {l2['root']}")
        else:
            self.console.write("Level 2: nicht vorhanden")
        snapshots = scan.get("l3", {}).get("snapshots", [])
        if not snapshots:
            self.console.write("Level 3: kein gültiger Snapshot")
        for item in snapshots:
            size = item.get("bytes") if item.get("bytes") is not None else _directory_size(item["path"])
            services = ", ".join(SERVICE_LABELS.get(x, x) for x in item.get("services", []))
            self.console.write(
                f"{item.get('display_name', item.get('source_type', 'Level 3'))}: {item['id']}; Alter {_age_from_snapshot(item['id'])}; "
                f"Größe {_human_bytes(size)}; Manifest/Fingerprint PASS; Dienste {services or 'keine'}"
            )
        if scan.get("l3", {}).get("conflicts"):
            raise ValidationError("mehrdeutige Level-3-Snapshots erkannt")

    def _select_service(self):
        return self.console.choose("Dienst oder App auswählen", [
            (name, SERVICE_LABELS[name]) for name in VISIBLE_SERVICES
        ])

    def _select_restore_case(self, service):
        if service not in APP_SERVICES:
            return "SINGLE_SERVICE"
        choices = [
            ("APP_DATA_ONLY", "Nur App-Daten wiederherstellen"),
            ("APP_FULL", "Vollständige App wiederherstellen"),
        ]
        if service == "urlaubsplaner":
            choices.append(("APP_PREVIOUS", "Vorherigen kompatiblen App-Release verwenden"))
        return self.console.choose("Wiederherstellungsumfang auswählen", choices)

    def _select_mode(self, scan):
        has_l2 = bool(scan.get("l2"))
        has_l3 = bool(scan.get("l3", {}).get("snapshots"))
        choices = []
        if has_l2 and has_l3:
            choices.append(("COMBINED_L2_L3", "Level 2 und Level 3 kombiniert"))
        if has_l2:
            choices.append(("L2_ONLY", "Nur Level 2"))
        if has_l3:
            choices.append(("L3_ONLY", "Nur Level 3"))
        if has_l2 and not has_l3:
            choices.append(("L3_DEFERRED", "Level 2 jetzt, Level 3 später fortsetzen"))
        choices.append(("BASE_ONLY", "Nur Basissystem vorbereiten"))
        return self.console.choose("Sicherungsquelle auswählen", choices)

    def _select_snapshot(self, scan, mode):
        if mode not in {"COMBINED_L2_L3", "L3_ONLY"}:
            return None
        snapshots = scan.get("l3", {}).get("snapshots", [])
        if not snapshots:
            raise ValidationError("kein gültiger Level-3-Snapshot verfügbar")
        return self.console.choose("Level-3-Snapshot bewusst auswählen", [
            (item["id"], f"{item['id']} – Alter {_age_from_snapshot(item['id'])} – "
                         f"{_human_bytes(_directory_size(item['path']))}")
            for item in snapshots
        ])

    def _build_plan(self, context, scope, service, restore_case, mode, snapshot):
        selected_release = None
        if restore_case == "APP_PREVIOUS":
            if context.mode == "FIXTURE":
                contract_path = context.fixture_root / "previous-release.json"
                contract = read_json(contract_path) if contract_path.is_file() else {}
            else:
                contract = context.config.get("app_releases", {}).get(service, {}).get("previous", {})
            if (contract.get("status") != "COMPLETE_COMPATIBLE" or
                    not contract.get("version") or not contract.get("image_id") or
                    contract.get("schema_compatible") is not True):
                raise ValidationError("PREVIOUS-Release ist nicht vollständig und schema-kompatibel gebunden")
            selected_release = {key: contract[key] for key in ("version", "image_id")}
        if context.mode == "FIXTURE":
            size_path = context.fixture_root / "sizes.json"
            sizes = read_json(size_path) if size_path.is_file() else {"system": 6 * 1024 ** 3}
            for name in (list(VISIBLE_SERVICES) if scope == "FULL_SERVER" else [service]):
                if name in sizes:
                    continue
                candidates = []
                if snapshot:
                    candidates.extend(pathlib.Path(item["path"]) / name for item in context.scan["l3"]["snapshots"]
                                      if item["id"] == snapshot)
                if context.scan.get("l2"):
                    candidates.append(pathlib.Path(context.scan["l2"]["root"]) / name)
                found = next((item for item in candidates if item.is_dir() and not item.is_symlink()), None)
                sizes[name] = _directory_size(found) if found else 0
            binding = None
        else:
            selected = list(VISIBLE_SERVICES) if scope == "FULL_SERVER" else [service]
            missing = [name for name in selected if name not in context.config.get("services", {})]
            if missing:
                raise ValidationError(
                    "isolierter Realtestvertrag für diese Auswahl noch nicht gebunden: " + ", ".join(missing)
                )
            sizes = realtest_sizes(context.config, context.scan, mode, selected, snapshot_id=snapshot)
            binding = realtest_plan_binding(context.config, context.scan)
        service_order = list(VISIBLE_SERVICES)
        plan = build_plan(load_catalog(self.usb_root), context.scan, mode=mode, scope=scope,
                          target=context.target, service=service, snapshot_id=snapshot,
                          sizes=sizes, development=True, usb_root=self.usb_root,
                          runtime_mode=context.mode, system_target=context.system_target,
                          realtest_binding=binding, service_order=service_order)
        plan["assistant_restore_case"] = restore_case
        plan["assistant_selected_release"] = selected_release
        target_name = pathlib.Path(context.target).name
        if scope == "FULL_SERVER":
            system_name = pathlib.Path(context.system_target).name if context.system_target else "Fixture-System"
            phrase = f"WIEDERHERSTELLUNG HP-SERVER AUF {system_name} UND {target_name} BESTÄTIGEN"
        else:
            phrase = f"WIEDERHERSTELLUNG {SERVICE_LABELS[service].upper()} AUF {target_name} BESTÄTIGEN"
        plan["confirmation_phrase"] = phrase
        plan["assistant_runtime_estimate"] = self._runtime_estimate(scope, service)
        return plan

    @staticmethod
    def _runtime_estimate(scope, service):
        if scope == "FULL_SERVER":
            return "mehrere Stunden"
        if service in {"immich", "nextcloud", "paperless"}:
            return "abhängig vom Datenvolumen, häufig 30 Minuten bis mehrere Stunden"
        return "ungefähr 10–30 Minuten"

    def _preview(self, plan):
        self.console.write("")
        self.console.write("Wiederherstellungsplan")
        self.console.write("----------------------")
        label = "Gesamter Server" if plan["scope"] == "FULL_SERVER" else SERVICE_LABELS[plan["service"]]
        self.console.write(f"Wiederherstellung: {label}")
        self.console.write(f"Ausführungsart: {plan['runtime_mode']}")
        source = plan.get("l3", {}).get("id") if plan.get("l3") else ("Level 2" if plan.get("l2") else "Basissystem")
        self.console.write(f"Quelle: {plan['mode']} – {source}")
        self.console.write(f"Ziel: {plan['target']}")
        if plan.get("system_target"):
            self.console.write(f"Systemziel: {plan['system_target']}")
        self.console.write("Dienste: " + ", ".join(SERVICE_LABELS.get(x, x) for x in plan["services"]))
        self.console.write(f"Umfang: {plan.get('assistant_restore_case')}")
        if plan.get("service") in APP_SERVICES or plan["scope"] == "FULL_SERVER":
            self.console.write("App-Releases: manifest- und imagegebunden zu prüfen")
            self.console.write("Secrets: verschlüsseltes Paket und Schema vor Verwendung erforderlich")
        self.console.write(f"Datenvolumen: {_human_bytes(plan['estimates'].get('data_required'))}")
        self.console.write(f"Geschätzte Laufzeit: {plan['assistant_runtime_estimate']}")
        self.console.write("Produktive Pfade: nicht freigegeben / isolierte Bindung erforderlich")
        self.console.write("Es wurden noch keine Änderungen ausgeführt.")

    def restore(self, scope):
        self.console.write("Recovery-Paket und Zielbindung werden geprüft …")
        validate_usb(self.usb_root)
        context = self._context()
        self._show_runtime(context)
        self._show_sources(context.scan)
        service = self._select_service() if scope == "SINGLE_SERVICE" else None
        restore_case = self._select_restore_case(service) if service else "FULL_SERVER"
        mode = self._select_mode(context.scan)
        snapshot = self._select_snapshot(context.scan, mode)
        plan = self._build_plan(context, scope, service, restore_case, mode, snapshot)
        self._preview(plan)
        self.console.write("")
        self.console.write("Ab hier beginnt nach korrekter Bestätigung die kontrollierte Ausführung.")
        self.console.write("Exakte Bestätigungsphrase:")
        self.console.write(plan["confirmation_phrase"])
        confirmation = self.console.ask("Phrase exakt eingeben (0 = Abbruch): ")
        if confirmation == "0":
            raise UserCancelled
        if confirmation != plan["confirmation_phrase"]:
            raise ValidationError("Bestätigungsphrase stimmt nicht; keine Ausführung gestartet")
        manager = StateManager(self.state_root, self.log_root)
        manager.lock()
        try:
            manager.create(plan)
        finally:
            manager.close()
        self._execute_worker(context, plan, confirmation, resume=False)

    def _secret_required(self, context, plan):
        return context.mode == "ISOLATED_REALTEST" and bool(context.config.get("secrets", {}).get("required_files"))

    def _execute_worker(self, context, plan, confirmation, *, resume, snapshot=None):
        command = [str(self.worker), "--test-root", str(self.state_root.parent),
                   "resume" if resume else "execute", plan["run_id"]]
        if context.mode == "FIXTURE":
            command.extend(["--fixture-root", str(context.fixture_root)])
        else:
            command.extend(["--realtest", "--realtest-config", str(context.config_path)])
        command.extend(["--confirm", confirmation])
        if snapshot:
            command.extend(["--snapshot", snapshot])
        pass_fds = ()
        read_fd = write_fd = None
        if self._secret_required(context, plan):
            self.console.write("Für diesen Restore wird das Kennwort des verschlüsselten Secret-Pakets benötigt.")
            self.console.write("Das Kennwort wird nicht gespeichert oder protokolliert.")
            secret = self.console.secret("Secret-Kennwort: ")
            if not secret:
                raise ValidationError("leeres Secret-Kennwort abgewiesen")
            read_fd, write_fd = os.pipe()
            os.set_inheritable(read_fd, True)
            os.write(write_fd, secret.encode("utf-8") + b"\n")
            os.close(write_fd); write_fd = None
            command.extend(["--secret-fd", str(read_fd)])
            pass_fds = (read_fd,)
            secret = ""
        log_file = self.log_root / f"{plan['run_id']}.worker.log"
        log_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.console.write(f"Ausführung gestartet. Run-ID: {plan['run_id']}")
        self.console.write(f"Status später: ./bin/hp-recovery status {plan['run_id']}")
        self.console.write("Der Hintergrundprozess läuft unabhängig von der Termius-Sitzung weiter.")
        started = time.monotonic()
        interval = max(0.05, float(os.environ.get("HP_RECOVERY_PROGRESS_INTERVAL", "30")))
        try:
            with open(log_file, "ab", buffering=0) as log:
                os.chmod(log_file, 0o600)
                proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                        close_fds=True, pass_fds=pass_fds, start_new_session=True)
                if read_fd is not None:
                    os.close(read_fd); read_fd = None
                try:
                    while proc.poll() is None:
                        time.sleep(interval)
                        elapsed = int(time.monotonic() - started)
                        self.console.write(f"Läuft: Schritt wird ausgeführt; vergangen {elapsed // 60} min {elapsed % 60} s")
                except KeyboardInterrupt:
                    self.console.write("Kontrollierter Abbruch angefordert; der Run-State bleibt für Resume erhalten.")
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=60)
                rc = proc.wait()
        finally:
            if read_fd is not None:
                os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)
        state = self._load_state(plan["run_id"])
        report = build_report(state)
        self._show_report(report)
        if rc != 0 and state.get("status") not in {"ABORTED", "WAITING_FOR_L3"}:
            raise RecoveryError(f"Recovery-Ausführung fehlgeschlagen (RC {rc})")

    def _state_files(self):
        runs = self.state_root / "runs"
        if not runs.is_dir():
            return []
        return sorted((p for p in runs.glob("run-*/state.json") if p.is_file() and not p.is_symlink()),
                      key=lambda p: p.stat().st_mtime_ns, reverse=True)

    def _load_state(self, run_id):
        manager = StateManager(self.state_root, self.log_root)
        try:
            return manager.load(run_id)
        finally:
            manager.close()

    def resume(self):
        candidates = []
        for path in self._state_files():
            state = read_json(path)
            if state.get("status") in MUTATING_STATUSES:
                plan = state.get("plan", {})
                services = ", ".join(SERVICE_LABELS.get(x, x) for x in plan.get("services", []))
                label = (f"{state['run_id']} – {state.get('status')} – {state.get('created_at')} – "
                         f"{services} – letzter Schritt {state.get('resume_point') or 'keiner'}")
                candidates.append((state, label))
        state = self.console.choose("Fortsetzbare Wiederherstellungen", candidates)
        context = self._context()
        plan = state["plan"]
        if plan.get("runtime_mode") != context.mode:
            raise ValidationError("Ausführungsart des gespeicherten Laufs stimmt nicht mehr")
        snapshot = None
        if state["status"] == "WAITING_FOR_L3":
            self._show_sources(context.scan)
            snapshot = self._select_snapshot(context.scan, "L3_ONLY")
        self._preview(plan)
        phrase = plan["confirmation_phrase"]
        self.console.write("Vor Resume werden Quelle, Ziel, Sentinel und Operationsgeneration erneut geprüft.")
        self.console.write(phrase)
        confirmation = self.console.ask("Phrase exakt eingeben (0 = Abbruch): ")
        if confirmation == "0":
            raise UserCancelled
        if confirmation != phrase:
            raise ValidationError("Bestätigungsphrase stimmt nicht; Resume nicht gestartet")
        self._execute_worker(context, plan, confirmation, resume=True, snapshot=snapshot)

    def show_last_report(self):
        for state_file in self._state_files():
            report_file = state_file.parent / "report.json"
            if report_file.is_file() and not report_file.is_symlink():
                self._show_report(read_json(report_file))
                return
        self.console.write("Kein Recovery-Bericht vorhanden.")

    def _show_report(self, report):
        self.console.write("")
        self.console.write("Recovery-Abschlussbericht")
        self.console.write("--------------------------")
        status = report.get("overall_status", "FAILED")
        self.console.write(f"Status: {status} – {FINAL_LABELS.get(status, status)}")
        self.console.write(f"Run-ID: {report.get('run_id', 'unbekannt')}")
        self.console.write(f"Modus: {report.get('mode', 'unbekannt')}")
        self.console.write(f"Umfang: {report.get('scope', 'unbekannt')}")
        services = report.get("services", {})
        for name, result in sorted(services.items()):
            self.console.write(f"{SERVICE_LABELS.get(name, name)}: {result}")
        if report.get("last_error"):
            self.console.write(f"Fehlerklasse: {report['last_error']}")
        self.console.write("Ausführliche, secret-freie Berichte liegen im geschützten Run-Verzeichnis.")


def menu_help():
    return """HP Server Recovery – geführtes Menü

Aufruf:
  ./START-RECOVERY.sh
  ./bin/hp-recovery menu

Das Menü prüft zuerst das Recovery-Paket und führt anschließend durch Quellen-,
Snapshot-, Dienst-, Ziel- und Planauswahl. Technische Parameter, Run-ID und
Bestätigungsphrase werden automatisch erzeugt beziehungsweise angezeigt.

Ausführungsarten:
  FIXTURE             Nur isolierte synthetische Tests.
  ISOLATED_REALTEST   Nur mit gebundener Realtest-Konfiguration und Sentinel.
  PRODUKTION          In v0.2.8 weiterhin technisch blockiert.

Ohne gebundene isolierte Umgebung sind nur Paketprüfung und Berichte möglich.
Expertenbefehle validate, scan, plan, execute, resume und status bleiben erhalten.
Secrets werden ausschließlich verdeckt abgefragt und nie als Prozessargument,
State-, Log- oder Berichtswert gespeichert.
"""
