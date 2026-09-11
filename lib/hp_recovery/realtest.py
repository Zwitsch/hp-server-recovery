"""Fail-closed real restore adapter for the isolated HP Evidence Intake VM.

This module intentionally contains no hp-server device identity, UUID, secret,
or mutable image default.  Those values must be bound by a signed-off VM
configuration and its sentinel before a target-changing operation is possible.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from .errors import RecoveryError, SafetyError, SourceError, ValidationError
from .compose_isolation import (build_isolated_compose, load_compose_payload,
                                load_dummy_env, prepare_companions, prepare_mount_sources,
                                validate_isolated_compose)
from .planner import storage_preflight
from .source_scan import scan_l3_roots
from .util import atomic_json, ensure_safe_target, metadata_tree_fingerprint, sha256_file, tree_fingerprint


GIB = 1024 ** 3
REALTEST_VERSION = "0.2.8-dev-ASSISTENT"
REALTEST_SCHEMA = "1.0"
KNOWN_SERVICES = {
    "base-system", "adguard", "npm", "nextcloud", "immich", "paperless",
    "jellyfin", "analyzer", "monatsausgaben", "snowflake",
}
DEFAULT_PROTECTED_PREFIXES = (
    "/var/lib/docker",
    "/srv/docker",
)
SECRET_KEY_RE = re.compile(r"(?i)(password|passwd|secret|token|private[_-]?key|credential)")
SENSITIVE_OPTION_RE = re.compile(r"(?i)^--?(?:password|passwd|secret|token|private[-_]?key|credential)(?:=|$)")


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError) as exc:
        raise ValidationError(f"invalid realtest JSON: {path}") from exc


def _require(value, message):
    if not value:
        raise ValidationError(message)
    return value


def _under(path, root):
    path = pathlib.Path(path).resolve(strict=False)
    root = pathlib.Path(root).resolve(strict=False)
    return path == root or root in path.parents


def _reject_productive_path(path, label, protected_prefixes=DEFAULT_PROTECTED_PREFIXES):
    resolved = pathlib.Path(path).resolve(strict=False)
    text = str(resolved)
    if text in {"/", "/home", "/mnt"}:
        raise SafetyError(f"protected {label}: {text}")
    for prefix in protected_prefixes:
        p = pathlib.Path(prefix)
        if resolved == p or p in resolved.parents:
            raise SafetyError(f"productive {label}: {text}")
    return resolved


def _safe_relative(value, label):
    p = pathlib.PurePosixPath(str(value))
    if p.is_absolute() or not p.parts or any(x in {"", ".", ".."} for x in p.parts):
        raise ValidationError(f"unsafe relative {label}")
    return p


def _directory_bytes(root):
    total = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not pathlib.Path(base, d).is_symlink()]
        for name in files:
            path = pathlib.Path(base, name)
            if path.is_symlink():
                raise SourceError(f"source symlink rejected: {path}")
            try:
                total += path.stat().st_size
            except OSError as exc:
                raise SourceError(f"cannot size source file: {path}") from exc
    return total


def _all_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "productive_ips":
                continue
            yield from _all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)
    elif isinstance(value, str):
        yield value


def _marker_texts(markers):
    """Return non-empty textual marker values without persisting them."""
    values = set()
    for marker in markers or ():
        if isinstance(marker, bytes):
            try:
                marker = marker.decode("utf-8")
            except UnicodeDecodeError:
                continue
        marker = str(marker)
        if marker:
            values.add(marker)
    return sorted(values, key=len, reverse=True)


def _redact_marker_substrings(value, markers):
    value = str(value)
    for marker in _marker_texts(markers):
        value = value.replace(marker, "<REDACTED>")
    return value


def _redact_argv(argv, markers=()):
    """Redact secret options, following values, and every known marker substring."""
    redacted = []
    hide_next = False
    for raw in argv:
        value = _redact_marker_substrings(raw, markers)
        if hide_next:
            redacted.append("<REDACTED>")
            hide_next = False
            continue
        if SENSITIVE_OPTION_RE.match(value):
            if "=" in value:
                redacted.append(value.split("=", 1)[0] + "=<REDACTED>")
            else:
                redacted.append(value)
                hide_next = True
            continue
        if "=" in value and SECRET_KEY_RE.search(value.split("=", 1)[0]):
            redacted.append(value.split("=", 1)[0] + "=<REDACTED>")
            continue
        try:
            parsed = urllib.parse.urlsplit(value)
            if parsed.scheme and parsed.hostname and (parsed.username is not None or parsed.password is not None):
                host = parsed.hostname
                if parsed.port is not None:
                    host += f":{parsed.port}"
                redacted.append(urllib.parse.urlunsplit((parsed.scheme, "<REDACTED>@" + host,
                                                         parsed.path, parsed.query, parsed.fragment)))
                continue
        except (ValueError, TypeError):
            pass
        redacted.append("<REDACTED>" if SECRET_KEY_RE.search(value) else value)
    return redacted


class RealPlatform:
    """Small OS boundary; tests replace it with a deterministic fake."""

    def hostname(self):
        return socket.gethostname()

    def run(self, argv, *, input_bytes=None, stdin_path=None, stdout_path=None, env=None, timeout=300):
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise ValidationError("command must be a non-empty argv array")
        try:
            if input_bytes is not None and stdin_path is not None:
                raise ValidationError("input_bytes and stdin_path are mutually exclusive")
            stdin_stream = open(stdin_path, "rb") if stdin_path is not None else None
            stdout_stream = open(stdout_path, "wb") if stdout_path is not None else None
            try:
                return subprocess.run(
                    argv, input=input_bytes, stdin=stdin_stream,
                    stdout=stdout_stream or subprocess.PIPE, stderr=subprocess.PIPE,
                    env=env, timeout=timeout, check=False,
                )
            finally:
                if stdin_stream:
                    stdin_stream.close()
                if stdout_stream:
                    stdout_stream.close()
        except (OSError, subprocess.SubprocessError) as exc:
            raise RecoveryError(f"isolated command unavailable: {pathlib.Path(argv[0]).name}") from exc

    def mount_record(self, path):
        result = self.run(["findmnt", "--json", "--target", str(path), "--output", "SOURCE,TARGET,OPTIONS"])
        if result.returncode != 0:
            raise SafetyError(f"mount identity unavailable: {path}")
        try:
            records = json.loads(result.stdout.decode("utf-8"))["filesystems"]
            record = records[0]
        except (ValueError, KeyError, IndexError, UnicodeDecodeError) as exc:
            raise SafetyError(f"invalid mount identity: {path}") from exc
        options = set(str(record.get("options", "")).split(","))
        return {"source": record.get("source"), "target": record.get("target"), "read_only": "ro" in options}

    def device_record(self, device):
        result = self.run(["lsblk", "--json", "--bytes", "--output",
                           "PATH,NAME,PKNAME,TYPE,MODEL,SERIAL,UUID,SIZE"])
        if result.returncode != 0:
            raise SafetyError(f"device identity unavailable: {device}")
        try:
            roots = json.loads(result.stdout.decode("utf-8"))["blockdevices"]
        except (ValueError, KeyError, IndexError, UnicodeDecodeError) as exc:
            raise SafetyError(f"invalid device identity: {device}") from exc
        flat = []
        def visit(item):
            flat.append(item)
            for child in item.get("children", []) or []:
                visit(child)
        for root in roots:
            visit(root)
        wanted = str(pathlib.Path(device))
        item = next((x for x in flat if x.get("path") == wanted), None)
        if item is None:
            raise SafetyError(f"device identity unavailable: {device}")
        model = item.get("model")
        if not model and item.get("pkname"):
            parent = next((x for x in flat if x.get("name") == item.get("pkname") or
                           x.get("path") == "/dev/" + str(item.get("pkname"))), None)
            model = parent.get("model") if parent else None
        return {"path": item.get("path"), "type": item.get("type"), "model": model,
                "serial": item.get("serial"), "uuid": item.get("uuid"), "size": item.get("size")}

    def free_bytes(self, path):
        return shutil.disk_usage(path).free

    def validate_container_runtime(self, socket_path, target_root, productive_ips):
        socket_path = pathlib.Path(socket_path)
        for item in (socket_path, *socket_path.parents):
            if item.exists() and item.is_symlink():
                raise SafetyError("isolated Docker socket path contains symlink")
        if not socket_path.exists() or not stat.S_ISSOCK(socket_path.stat().st_mode):
            raise SafetyError("isolated Docker socket is unavailable")
        argv = ["docker", "--host", str(socket_path)]
        info = self.run(argv + ["info", "--format", "{{.DockerRootDir}}"])
        if info.returncode != 0:
            raise SafetyError("isolated Docker daemon unavailable")
        docker_root = pathlib.Path(info.stdout.decode("utf-8").strip()).resolve(strict=False)
        if not _under(docker_root, target_root):
            raise SafetyError("Docker data root is outside isolated target")
        ips = self.run(["hostname", "-I"])
        if ips.returncode == 0:
            live = set(ips.stdout.decode("utf-8").split())
            if live & set(productive_ips):
                raise SafetyError("productive IP detected on realtest host")


def load_realtest_config(path):
    path = pathlib.Path(path).resolve(strict=True)
    config = _read_json(path)
    if config.get("schema_version") != REALTEST_SCHEMA:
        raise ValidationError("unsupported realtest configuration schema")
    if config.get("runtime_mode") != "ISOLATED_REALTEST":
        raise ValidationError("configuration is not isolated realtest")
    if config.get("release_allowed") is not False or config.get("override_allowed") is not False:
        raise SafetyError("release or override flag must remain false")
    required_services = KNOWN_SERVICES - {"snowflake"}
    services = config.get("services")
    if not isinstance(services, dict) or not KNOWN_SERVICES <= set(services):
        raise ValidationError("complete realtest service contracts missing")
    for service in sorted(required_services):
        contract = services.get(service) or {}
        if not contract.get("copies") or not contract.get("checks"):
            raise ValidationError(f"empty required realtest contract: {service}")
    for service in sorted(KNOWN_SERVICES):
        contract = services.get(service) or {}
        compose = contract.get("compose")
        if compose:
            expected = set(compose.get("expected_services", []))
            images = set((compose.get("image_bindings") or {}).keys())
            mounts = set((compose.get("mounts") or {}).keys())
            ports = set((compose.get("ports") or {}).keys())
            networks = set((compose.get("service_networks") or {}).keys())
            if not expected or images != expected or mounts != expected or ports != expected or networks != expected:
                raise ValidationError(f"complete Compose isolation contract missing: {service}")
            names = compose.get("container_names") or {}
            project = compose.get("project_name")
            if set(names) != expected or project != f"hp-realtest-{service}":
                raise ValidationError(f"complete Compose identity contract missing: {service}")
            if any(value != f"{project}-{name}" for name, value in names.items()):
                raise ValidationError(f"noncanonical isolated container identity: {service}")
            if not set(compose.get("verify_services", [])) <= expected:
                raise ValidationError(f"invalid Compose verification service set: {service}")
            allowed_networks = set(compose.get("allowed_networks", []))
            if not allowed_networks or any(not set(value) <= allowed_networks
                                           for value in compose["service_networks"].values()):
                raise ValidationError(f"Compose internal network contract missing: {service}")
            if not compose.get("env_secret_rel"):
                raise ValidationError(f"Compose dummy env contract missing: {service}")
    if not config.get("base_system", {}).get("copies"):
        raise ValidationError("base-system copy contracts missing")
    packages = config.get("packages")
    if not isinstance(packages, dict):
        raise ValidationError("package contracts missing")
    required = packages.get("required")
    if not isinstance(required, list) or not required:
        raise ValidationError("required package contracts missing")
    package_name = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
    if any(not isinstance(item, str) or not package_name.fullmatch(item) for item in required):
        raise ValidationError("invalid required package name")
    required_any = packages.get("required_any")
    if not isinstance(required_any, list):
        raise ValidationError("required_any package contracts must be a list")
    for group in required_any:
        if not isinstance(group, list) or not group:
            raise ValidationError("required_any package group must be a nonempty list")
        if any(not isinstance(item, str) or not package_name.fullmatch(item) for item in group):
            raise ValidationError("invalid required_any package name")
    if not config.get("images"):
        raise ValidationError("immutable image contracts missing")
    allowed_source_types = {"LOCAL_L3", "FILEN_DOWNLOADED_L3", "MONTHLY_L3"}
    for source in config.get("sources", {}).get("l3", []):
        if source.get("source_type", "LOCAL_L3") not in allowed_source_types:
            raise ValidationError("unknown Level-3 source type")
    for image in config["images"]:
        kind = image.get("kind", "REGISTRY")
        reference = str(image.get("reference", ""))
        if kind == "REGISTRY" and not re.search(r"@sha256:[0-9a-f]{64}$", reference):
            raise ValidationError("registry image is not RepoDigest-bound")
        if kind == "LOCAL_ARCHIVE" and not re.fullmatch(r"sha256:[0-9a-f]{64}", str(image.get("expected_image_id", ""))):
            raise ValidationError("local image ID contract missing")
        if not re.fullmatch(r"[0-9a-f]{64}", str(image.get("archive_sha256", ""))):
            raise ValidationError("image archive checksum contract missing")
    hold = config.get("timers", {}).get("hold", [])
    if not hold or any(not str(x).endswith(".timer") for x in hold):
        raise ValidationError("timer hold contract missing")
    config["_config_path"] = str(path)
    config["_config_sha256"] = sha256_file(path)
    return config


def realtest_plan_binding(config, scan):
    """Immutable identities that authorize execute and resume."""
    return {
        "config_path": config["_config_path"],
        "config_sha256": config["_config_sha256"],
        "sentinel_path": str(pathlib.Path(config["sentinel_path"]).resolve(strict=True)),
        "sentinel_sha256": sha256_file(config["sentinel_path"]),
        "l2": ({"root": scan["l2"]["root"], "device": scan["l2"]["device"],
                "fingerprint": scan["l2"]["fingerprint"]} if scan.get("l2") else None),
        "l3": [{"id": x["id"], "path": x["path"], "device": x.get("device"), "fingerprint": x["fingerprint"]}
               for x in scan.get("l3", {}).get("snapshots", [])],
        "release_allowed": False,
        "override_allowed": False,
    }


class IsolationGate:
    def __init__(self, config, usb_root, platform=None):
        self.config = config
        self.usb_root = pathlib.Path(usb_root).resolve(strict=False)
        self.platform = platform or RealPlatform()
        self.sentinel = None

    def _validate_device(self, label, binding, sentinel_binding, mount):
        for key in ("device", "uuid", "type", "model", "size"):
            if binding.get(key) in (None, "", "UNKNOWN"):
                raise SafetyError(f"unknown {label} device {key}")
            if binding.get(key) != sentinel_binding.get(key):
                raise SafetyError(f"{label} device not sentinel-bound: {key}")
        if binding.get("virtual") is not True or sentinel_binding.get("virtual") is not True:
            raise SafetyError(f"{label} device is not registered virtual test storage")
        if mount.get("source") != binding["device"]:
            raise SafetyError(f"{label} mount device mismatch")
        actual = self.platform.device_record(binding["device"])
        comparisons = {"path": "device", "uuid": "uuid", "type": "type", "model": "model", "size": "size"}
        for actual_key, binding_key in comparisons.items():
            if str(actual.get(actual_key)) != str(binding.get(binding_key)):
                raise SafetyError(f"{label} live device mismatch: {binding_key}")
        return actual

    def validate(self):
        cfg = self.config
        try:
            sentinel_path = pathlib.Path(_require(cfg.get("sentinel_path"), "sentinel path missing")).resolve(strict=True)
        except FileNotFoundError as exc:
            raise SafetyError("realtest sentinel missing") from exc
        sentinel = _read_json(sentinel_path)
        self.sentinel = sentinel
        expected_sha = _require(cfg.get("sentinel_sha256"), "sentinel sha256 missing")
        if sha256_file(sentinel_path) != expected_sha:
            raise SafetyError("realtest sentinel checksum mismatch")
        if sentinel.get("schema_version") != REALTEST_SCHEMA or sentinel.get("purpose") != "HP_EVIDENCE_INTAKE_REALTEST":
            raise SafetyError("invalid realtest sentinel")
        if sentinel.get("release_allowed") is not False or sentinel.get("override_allowed") is not False:
            raise SafetyError("sentinel release flags invalid")
        host = self.platform.hostname()
        allowed = set(cfg.get("allowed_hostnames", [])) & set(sentinel.get("allowed_hostnames", []))
        forbidden = set(cfg.get("forbidden_hostnames", [])) | set(sentinel.get("forbidden_hostnames", []))
        if not forbidden:
            raise SafetyError("forbidden hostnames missing")
        if host in forbidden or host not in allowed:
            raise SafetyError(f"hostname not allowed for realtest: {host}")

        cfg_prefixes = tuple(cfg.get("protected_prefixes", []))
        sentinel_prefixes = tuple(sentinel.get("protected_prefixes", []))
        if not cfg_prefixes or not sentinel_prefixes:
            raise SafetyError("protected prefixes missing")
        protected_prefixes = tuple(dict.fromkeys(DEFAULT_PROTECTED_PREFIXES + cfg_prefixes + sentinel_prefixes))

        target_root = _reject_productive_path(_require(cfg.get("target_root"), "target root missing"), "target root", protected_prefixes)
        system_target = _reject_productive_path(_require(cfg.get("system_target"), "system target missing"), "system target", protected_prefixes)
        data_target = _reject_productive_path(_require(cfg.get("data_target"), "data target missing"), "data target", protected_prefixes)
        if not _under(system_target, target_root) or not _under(data_target, target_root):
            raise SafetyError("system/data targets must be under target root")
        if system_target == data_target or system_target in data_target.parents or data_target in system_target.parents:
            raise SafetyError("system and data targets must be separate")
        if _under(target_root, self.usb_root) or _under(self.usb_root, target_root):
            raise SafetyError("target and USB root overlap")

        target_bindings = cfg.get("target_devices", {})
        sentinel_bindings = sentinel.get("target_devices", {})
        system_mount = self.platform.mount_record(system_target)
        data_mount = self.platform.mount_record(data_target)
        system_identity = self._validate_device("system", _require(target_bindings.get("system"), "system device binding missing"),
                                                _require(sentinel_bindings.get("system"), "sentinel system device missing"), system_mount)
        data_identity = self._validate_device("data", _require(target_bindings.get("data"), "data device binding missing"),
                                              _require(sentinel_bindings.get("data"), "sentinel data device missing"), data_mount)
        if system_mount["source"] == data_mount["source"]:
            raise SafetyError("system and data target devices are identical")

        sources = cfg.get("sources", {})
        source_devices = set()
        source_paths = []
        for label in ("l2", "l3"):
            for item in sources.get(label, []):
                path = pathlib.Path(_require(item.get("path"), f"{label} source path missing")).resolve(strict=True)
                mount = self.platform.mount_record(path)
                if not mount.get("read_only"):
                    raise SafetyError(f"{label.upper()} source is writable")
                expected_device = _require(item.get("device"), f"{label} source device unknown")
                if mount.get("source") != expected_device:
                    raise SafetyError(f"{label.upper()} source device mismatch")
                source_devices.add(expected_device); source_paths.append(path)
        if not sources.get("l2") and not sources.get("l3"):
            raise SafetyError("no realtest sources configured")
        if source_devices & {system_mount["source"], data_mount["source"]}:
            raise SafetyError("source and target device are identical")
        for source in source_paths:
            if _under(target_root, source) or _under(source, target_root):
                raise SafetyError("source and target paths overlap")

        container = cfg.get("container_runtime", {})
        socket_path = container.get("socket")
        if socket_path in (None, "", "/var/run/docker.sock", "/run/docker.sock"):
            raise SafetyError("isolated Docker socket not configured")
        if not _under(socket_path, target_root):
            raise SafetyError("Docker socket is outside isolated target root")
        if container.get("production_context_connected") is not False:
            raise SafetyError("production container context not explicitly disconnected")
        productive_ips = set(cfg.get("productive_ips", []))
        if any(x in {"127.0.0.1", "::1", "localhost"} for x in productive_ips):
            raise SafetyError("loopback cannot be declared productive")
        for value in _all_strings({"services": cfg.get("services", {}), "base_system": cfg.get("base_system", {})}):
            if any(ip and ip in value for ip in productive_ips):
                raise SafetyError("productive IP present in realtest contract")
        self.platform.validate_container_runtime(socket_path, target_root, productive_ips)
        return {
            "status": "PASS", "hostname": host, "target_root": str(target_root),
            "system_target": str(system_target), "data_target": str(data_target),
            "system_device": system_mount["source"], "data_device": data_mount["source"],
            "target_devices": {
                "system": {**system_identity, "mountpoint": str(system_target)},
                "data": {**data_identity, "mountpoint": str(data_target)},
            },
            "source_devices": sorted(source_devices), "sentinel_sha256": expected_sha,
            "release_allowed": False, "override_allowed": False,
        }


def scan_real_sources(config, usb_root, platform=None):
    platform = platform or RealPlatform()
    isolation = IsolationGate(config, usb_root, platform).validate()
    result = {"l2": None, "l3": {"snapshots": [], "conflicts": []}, "isolation": isolation, "sizes": {}}
    l2_items = config.get("sources", {}).get("l2", [])
    if len(l2_items) > 1:
        raise SourceError("exactly zero or one L2 source is supported")
    if l2_items:
        base = pathlib.Path(l2_items[0]["path"]).resolve(strict=True)
        mirror = base / "server-backups/mirror/data"
        if not mirror.is_dir() or mirror.is_symlink():
            raise SourceError("invalid L2 layout")
        result["l2"] = {"kind": "L2", "root": str(mirror), "mount_root": str(base),
                        "device": l2_items[0]["device"], "read_only": True,
                        "bytes": _directory_bytes(mirror), "fingerprint": metadata_tree_fingerprint(mirror)}
    l3_roots = [x["path"] for x in config.get("sources", {}).get("l3", [])]
    result["l3"] = scan_l3_roots(l3_roots, fingerprint_func=metadata_tree_fingerprint)
    for snapshot in result["l3"]["snapshots"]:
        matches = [x for x in config.get("sources", {}).get("l3", []) if _under(snapshot["path"], x["path"])]
        if len(matches) != 1:
            raise SourceError("L3 snapshot device binding is ambiguous")
        snapshot["device"] = matches[0]["device"]
        snapshot["source_type"] = matches[0].get("source_type", "LOCAL_L3")
        snapshot["display_name"] = matches[0].get("display_name", snapshot["source_type"])
        snapshot["bytes"] = _directory_bytes(snapshot["path"])
    return result


def _selected_snapshot(scan, snapshot_id, *, required):
    snapshots = scan.get("l3", {}).get("snapshots", [])
    if not required:
        return None
    if not snapshot_id:
        raise ValidationError("explicit L3 snapshot selection required")
    selected = [x for x in snapshots if x.get("id") == snapshot_id]
    if len(selected) != 1 or snapshot_id in set(scan.get("l3", {}).get("conflicts", [])):
        raise ValidationError("unknown, ambiguous, or conflicting L3 snapshot selection")
    return selected[0]


def realtest_sizes(config, scan, mode, services, snapshot_id=None):
    """Calculate required bytes from the concrete selected source mappings."""
    system = config.get("system_required_bytes")
    if not isinstance(system, int) or system < 0:
        raise ValidationError("realtest system requirement is UNKNOWN")
    sizes = {"system": system}
    selected_snapshot = _selected_snapshot(scan, snapshot_id,
                                           required=mode in {"COMBINED_L2_L3", "L3_ONLY"})
    for service in services:
        if service == "snowflake":
            sizes[service] = 0
            continue
        contract = config.get("services", {}).get(service)
        if not contract:
            raise ValidationError(f"realtest service contract missing: {service}")
        total = 0
        applicable = 0
        for mapping in contract.get("copies", []):
            if mode not in mapping.get("modes", []):
                continue
            kind = mapping.get("source")
            root = None
            if kind == "L2" and scan.get("l2"):
                root = pathlib.Path(scan["l2"]["root"])
            if kind == "L3" and selected_snapshot:
                root = pathlib.Path(selected_snapshot["path"])
            if root is None:
                if mapping.get("required", True):
                    continue
                applicable += 1
                continue
            source = root.joinpath(*_safe_relative(mapping["source_rel"], "size source").parts)
            if source.is_dir():
                total += _directory_bytes(source); applicable += 1
            elif mapping.get("required", True):
                continue
        if applicable == 0 and contract.get("copy_required", True):
            raise ValidationError(f"realtest required size is UNKNOWN: {service}")
        sizes[service] = total
    return sizes


class RealtestAdapter:
    """Executes only sentinel-authorized operations inside the isolated VM."""

    def __init__(self, config, usb_root, platform=None, secret_fd=None):
        self.config = config
        self.usb_root = pathlib.Path(usb_root).resolve(strict=False)
        self.platform = platform or RealPlatform()
        self.gate = IsolationGate(config, usb_root, self.platform)
        self.isolation = self.gate.validate()
        self.protected_prefixes = tuple(dict.fromkeys(
            DEFAULT_PROTECTED_PREFIXES
            + tuple(config.get("protected_prefixes", []))
            + tuple((self.gate.sentinel or {}).get("protected_prefixes", []))
        ))
        self.system_target = pathlib.Path(self.isolation["system_target"])
        self.data_target = pathlib.Path(self.isolation["data_target"])
        self.target_root = pathlib.Path(self.isolation["target_root"])
        self.command_audit = []
        self._active_compose = {}
        self._database_containers = set()
        self._secret_markers = set()
        self._state_checkpoint = None
        self._audit_sealed = False
        self._sealed_audit = None
        self._secret_fd = secret_fd

    def set_state_checkpoint(self, callback):
        self._state_checkpoint = callback

    def _checkpoint(self):
        if self._state_checkpoint is not None:
            self._state_checkpoint()

    def initialize_marker_verification(self, state):
        """Persist a secret-free verification state before any possible secret use."""
        current = state.get("marker_verification")
        secret_possible = bool(self.config.get("secrets", {}).get("required_files", []))
        secret_possible = secret_possible or bool(state.get("plaintext_secret_dir")) or bool(self._secret_markers)
        if current is None:
            state["marker_verification"] = {
                "status": "PENDING" if secret_possible else "PASS",
                "run_id": state["run_id"],
                "operation_generation": 1 if secret_possible else 0,
                "verified_generation": None if secret_possible else 0,
                "method": "AWAITING_MARKER_SCAN" if secret_possible else "NO_SECRET_MARKERS_CONFIGURED",
                "path_classes": [], "hit_count": 0,
            }
            self._checkpoint()
            return
        if current.get("run_id") != state["run_id"]:
            raise SafetyError("marker verification belongs to another run")
        if secret_possible and current.get("status") == "PASS" and state.get("plaintext_secret_dir"):
            current["operation_generation"] = int(current.get("operation_generation", 0)) + 1
            current.update({"status": "PENDING", "verified_generation": None,
                            "method": "AWAITING_MARKER_SCAN", "path_classes": [], "hit_count": 0})
            self._checkpoint()

    def _note_persistent_operation(self, state, operation):
        verification = state.get("marker_verification")
        if not verification or verification.get("status") == "PASS" and verification.get("method") == "NO_SECRET_MARKERS_CONFIGURED":
            return
        verification["operation_generation"] = int(verification.get("operation_generation", 0)) + 1
        verification.update({"status": "PENDING", "verified_generation": None,
                             "method": "AWAITING_MARKER_SCAN", "path_classes": [], "hit_count": 0,
                             "last_operation_class": operation})
        self._checkpoint()

    def _recheck(self, plan=None):
        current = self.gate.validate()
        if current != self.isolation:
            raise SafetyError("realtest isolation identity changed")
        if plan is not None:
            binding = plan.get("realtest_binding")
            if not binding:
                raise SafetyError("realtest plan identity binding missing")
            current_config_path = str(pathlib.Path(self.config["_config_path"]).resolve(strict=True))
            if binding.get("config_path") != current_config_path or sha256_file(current_config_path) != binding.get("config_sha256"):
                raise SafetyError("realtest configuration changed after planning")
            sentinel_path = str(pathlib.Path(self.config["sentinel_path"]).resolve(strict=True))
            if binding.get("sentinel_path") != sentinel_path or sha256_file(sentinel_path) != binding.get("sentinel_sha256"):
                raise SafetyError("realtest sentinel changed after planning")
            if plan.get("l2"):
                expected = binding.get("l2") or {}
                if (expected.get("root") != plan["l2"].get("root") or
                        metadata_tree_fingerprint(plan["l2"]["root"]) != expected.get("fingerprint")):
                    raise SafetyError("L2 source identity changed after planning")
            if plan.get("l3"):
                expected = [x for x in binding.get("l3", []) if x.get("id") == plan["l3"].get("id")]
                if (len(expected) != 1 or expected[0].get("path") != plan["l3"].get("path") or
                        expected[0].get("device") != plan["l3"].get("device") or
                        metadata_tree_fingerprint(plan["l3"]["path"]) != expected[0].get("fingerprint")):
                    raise SafetyError("L3 source identity changed after planning")

    def _recorded_run(self, argv, *, input_bytes=None, stdin_path=None, stdout_path=None, timeout=300):
        if self._audit_sealed:
            raise SafetyError("command audit is sealed after marker verification boundary")
        forbidden = {"pull", "build", "system", "prune"}
        if pathlib.Path(argv[0]).name == "docker" and any(x in forbidden for x in argv[1:]):
            raise SafetyError("forbidden Docker operation")
        self.command_audit.append(_redact_argv(
            [pathlib.Path(argv[0]).name, *argv[1:]], self._secret_markers
        ))
        result = self.platform.run(argv, input_bytes=input_bytes, stdin_path=stdin_path,
                                   stdout_path=stdout_path, timeout=timeout)
        if result.returncode != 0:
            raise RecoveryError(f"isolated command failed: {pathlib.Path(argv[0]).name}")
        return result

    def _safe_audit_rows(self, rows):
        if not isinstance(rows, list):
            raise SafetyError("invalid command audit structure")
        safe = []
        for row in rows:
            if not isinstance(row, list):
                raise SafetyError("invalid command audit row")
            safe.append(_redact_argv(row, self._secret_markers))
        return safe

    def seal_command_audit(self, state):
        """Freeze the complete, marker-redacted audit before the final scan."""
        stored = state.get("realtest_command_audit", [])
        # During a live run, run() points the state at this exact list.  A fresh
        # resume adapter instead combines the prior persisted audit with only
        # the newly executed reconciliation commands.
        previous = [] if stored is self.command_audit else self._safe_audit_rows(stored)
        current = self._safe_audit_rows(self.command_audit)
        complete = previous + current
        state["realtest_command_audit"] = complete
        self.command_audit = complete
        self._sealed_audit = json.dumps(complete, sort_keys=True, ensure_ascii=False)
        self._audit_sealed = True

    def _assert_sealed_audit(self, state):
        if not self._audit_sealed or self._sealed_audit is None:
            raise SafetyError("complete command audit was not sealed")
        current = json.dumps(state.get("realtest_command_audit"), sort_keys=True, ensure_ascii=False)
        if current != self._sealed_audit:
            raise SafetyError("command audit changed after marker verification boundary")

    def _document_marker_hits(self, *documents):
        markers = {marker for marker in self._secret_markers if marker}
        hits = 0
        for document in documents:
            if isinstance(document, bytes):
                content = document
            elif isinstance(document, str):
                content = document.encode("utf-8")
            else:
                content = json.dumps(document, sort_keys=True, ensure_ascii=False).encode("utf-8")
            hits += sum(1 for marker in markers if marker in content)
        return hits

    def sanitize_persistent_state(self, state):
        """Remove known synthetic marker substrings from data destined for evidence."""
        def scrub(value):
            if isinstance(value, dict):
                return {key: scrub(item) for key, item in value.items()}
            if isinstance(value, list):
                return [scrub(item) for item in value]
            if isinstance(value, str):
                return _redact_marker_substrings(value, self._secret_markers)
            return value

        cleaned = scrub(state)
        state.clear()
        state.update(cleaned)

    def validate_pre_scan_documents(self, state, report, markdown):
        """Reject marker-bearing provisional evidence before any persistent write."""
        self._assert_sealed_audit(state)
        hits = self._document_marker_hits(state, report, markdown)
        if not hits:
            return
        verification = state.get("marker_verification") or {}
        verification.update({"status": "FAILED", "verified_generation": None,
                             "method": "PREWRITE_MARKER_FOUND",
                             "path_classes": ["STATE_REPORT"], "hit_count": hits})
        state["marker_verification"] = verification
        self.sanitize_persistent_state(state)
        raise RecoveryError("synthetic secret marker rejected before evidence write")

    def validate_final_documents(self, state, report, markdown):
        """Gate the exact final in-memory evidence after the recursive scan."""
        self._assert_sealed_audit(state)
        verification = state.get("marker_verification") or {}
        if (verification.get("run_id") != state.get("run_id") or
                verification.get("status") != "PASS" or
                verification.get("verified_generation") != verification.get("operation_generation")):
            raise RecoveryError("final marker verification is not a current PASS")
        hits = self._document_marker_hits(state, report, markdown)
        if hits:
            verification.update({"status": "FAILED", "verified_generation": None,
                                 "method": "FINAL_DOCUMENT_MARKER_FOUND",
                                 "path_classes": ["STATE_REPORT"], "hit_count": hits})
            self.sanitize_persistent_state(state)
            raise RecoveryError("synthetic secret marker rejected in final evidence")

    def _validate_contract_command(self, argv):
        if not isinstance(argv, list) or not argv:
            raise ValidationError("contract command must be argv array")
        allowed = set(self.config.get("allowed_command_basenames", [
            "docker", "psql", "pg_dump", "mysql", "mariadb", "mysqldump", "sqlite3", "systemctl", "true",
        ]))
        if pathlib.Path(argv[0]).name not in allowed:
            raise SafetyError("contract command binary is not allowlisted")
        joined = " ".join(_redact_argv(argv))
        for prefix in self.protected_prefixes:
            if prefix in joined:
                raise SafetyError("contract command contains productive path")
        for ip in self.config.get("productive_ips", []):
            if ip and ip in joined:
                raise SafetyError("contract command contains productive IP")
        if pathlib.Path(argv[0]).name == "docker":
            socket_path = self.config["container_runtime"]["socket"]
            if not ({"--host", socket_path} <= set(argv)):
                raise SafetyError("database Docker command lacks isolated socket")
        if pathlib.Path(argv[0]).name == "systemctl":
            allowed_units = set(self.config.get("allowed_units", []))
            mentioned = {x for x in argv[1:] if x.endswith((".service", ".timer"))}
            if not mentioned or not mentioned <= allowed_units:
                raise SafetyError("systemd command references an unbound unit")

    def _prepare_secrets(self, state):
        contract = self.config.get("secrets", {})
        required = contract.get("required_files", [])
        if not required:
            return
        verification = state.get("marker_verification")
        if not verification or verification.get("status") != "PENDING":
            raise SafetyError("marker verification was not pending before secret use")
        encrypted = pathlib.Path(_require(contract.get("age_package"), "required test secret package missing")).resolve(strict=True)
        if encrypted.stat().st_size == 0 or not _under(encrypted, self.target_root):
            raise SafetyError("test secret package is empty or outside isolated target root")
        passphrase_mode = contract.get("authentication") == "PASSPHRASE_PROMPT"
        if passphrase_mode and self._secret_fd is None:
            raise ValidationError("secret passphrase must be supplied through the protected terminal prompt")
        if not passphrase_mode and self._secret_fd is not None:
            raise SafetyError("secret passphrase and identity contract must not be mixed")
        identity = None
        if not passphrase_mode:
            identity = pathlib.Path(_require(contract.get("age_identity"), "required test age identity missing")).resolve(strict=True)
            if identity.stat().st_size == 0 or not _under(identity, self.target_root):
                raise SafetyError("test identity is empty or outside isolated target root")
        self._cleanup_stale_secret_dirs()
        secret_dir = pathlib.Path(tempfile.mkdtemp(prefix="hp-recovery-secret-", dir=self.target_root))
        os.chmod(secret_dir, 0o700)
        atomic_json(secret_dir / ".hp-recovery-owned.json", {"run_id": state["run_id"], "kind": "PLAINTEXT_SECRET_DIR"})
        state["plaintext_secret_dir"] = str(secret_dir)
        self.config["_plaintext_secret_dir"] = str(secret_dir)
        archive = secret_dir / "package.tar"
        if passphrase_mode:
            passphrase = self._read_secret_fd()
            try:
                result = self.platform.run(["age", "--decrypt", "--passphrase", "-o", str(archive), str(encrypted)],
                                           input_bytes=bytes(passphrase))
            finally:
                for index in range(len(passphrase)):
                    passphrase[index] = 0
        else:
            result = self.platform.run(["age", "--decrypt", "-i", str(identity), "-o", str(archive), str(encrypted)])
        if result.returncode != 0:
            raise RecoveryError("test secret decryption failed")
        with tarfile.open(archive, "r:") as tf:
            for member in tf.getmembers():
                rel = pathlib.PurePosixPath(member.name)
                if rel.is_absolute() or ".." in rel.parts or member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                    raise SafetyError("unsafe test secret archive")
            tf.extractall(secret_dir, filter="data")
        archive.unlink()
        for rel in required:
            path = secret_dir.joinpath(*_safe_relative(rel, "secret file").parts)
            if not path.is_file() or path.stat().st_size == 0:
                raise ValidationError("required test secret missing")
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            for match in re.findall(r"DUMMY[A-Za-z0-9_.:@/+\-=]{3,}", text, flags=re.IGNORECASE):
                self._secret_markers.add(match.encode("utf-8"))
            if path.suffix == ".env" or "/compose/" in f"/{rel}":
                for key, value in load_dummy_env(path).items():
                    if value and len(value) >= 6 and SECRET_KEY_RE.search(key):
                        self._secret_markers.add(value.encode("utf-8"))

    def _read_secret_fd(self):
        fd = self._secret_fd
        self._secret_fd = None
        if not isinstance(fd, int) or fd < 3:
            raise SafetyError("invalid protected secret channel")
        chunks = bytearray()
        try:
            while len(chunks) <= 4096:
                block = os.read(fd, min(1024, 4097 - len(chunks)))
                if not block:
                    break
                chunks.extend(block)
                if b"\n" in block:
                    break
        finally:
            os.close(fd)
        if len(chunks) > 4096 or b"\n" not in chunks:
            for index in range(len(chunks)):
                chunks[index] = 0
            raise ValidationError("invalid secret passphrase channel")
        value = chunks.split(b"\n", 1)[0]
        for index in range(len(chunks)):
            chunks[index] = 0
        if not value or b"\x00" in value or b"\r" in value:
            for index in range(len(value)):
                value[index] = 0
            raise ValidationError("empty or invalid secret passphrase")
        value.extend(b"\n")
        return value

    def _cleanup_stale_secret_dirs(self):
        for path in self.target_root.glob("hp-recovery-secret-*"):
            if path.is_symlink() or not path.is_dir():
                raise SafetyError("unsafe stale secret path")
            marker = path / ".hp-recovery-owned.json"
            if marker.is_symlink() or not marker.is_file():
                raise SafetyError("unbound stale secret directory requires manual inspection")
            data = _read_json(marker)
            if data.get("kind") != "PLAINTEXT_SECRET_DIR" or not re.fullmatch(r"run-[0-9a-f]{16}", str(data.get("run_id", ""))):
                raise SafetyError("invalid stale secret directory marker")
            shutil.rmtree(path)

    def _copy(self, source, target, delete=False, target_root=None):
        source = pathlib.Path(source).resolve(strict=True)
        target = pathlib.Path(target).resolve(strict=False)
        target_root = pathlib.Path(target_root or self.data_target)
        if not _under(target, target_root):
            raise SafetyError("copy target outside declared realtest target")
        before = metadata_tree_fingerprint(source) if source.is_dir() else sha256_file(source)
        target.mkdir(parents=True, exist_ok=True) if source.is_dir() else target.parent.mkdir(parents=True, exist_ok=True)
        argv = ["rsync", "-aHAX", "--numeric-ids", "--protect-args"]
        if delete:
            argv.append("--delete")
        if source.is_dir():
            argv.extend([str(source) + "/", str(target) + "/"])
        else:
            argv.extend([str(source), str(target)])
        self._recorded_run(argv)
        after = metadata_tree_fingerprint(source) if source.is_dir() else sha256_file(source)
        if after != before:
            raise SourceError("source changed during realtest copy")

    def _source_for(self, mapping, plan):
        kind = mapping["source"]
        if kind == "L2":
            if not plan.get("l2"):
                return None
            root = pathlib.Path(plan["l2"]["root"])
        elif kind == "L3":
            if not plan.get("l3"):
                return None
            root = pathlib.Path(plan["l3"]["path"])
        else:
            raise ValidationError("copy source must be L2 or L3")
        rel = _safe_relative(mapping["source_rel"], "source path")
        source = root.joinpath(*rel.parts).resolve(strict=False)
        if not _under(source, root):
            raise SafetyError("copy source escaped source root")
        return source

    def _restore_service(self, service, plan, state):
        contract = _require(self.config.get("services", {}).get(service), f"realtest service contract missing: {service}")
        performed = 0
        for mapping in contract.get("copies", []):
            if plan["mode"] not in mapping.get("modes", []):
                continue
            restore_cases = mapping.get("restore_cases")
            if restore_cases and plan.get("assistant_restore_case") not in restore_cases:
                continue
            source = self._source_for(mapping, plan)
            required = mapping.get("required", True)
            if source is None or not source.exists() or source.is_symlink():
                if required:
                    raise SourceError(f"required service source missing: {service}")
                state.setdefault("service_outcomes", {})[service] = "PARTIAL"
                continue
            target_rel = _safe_relative(mapping["target_rel"], "target path")
            target = self.data_target.joinpath(*target_rel.parts)
            self._copy(source, target, delete=mapping.get("delete", False) is True)
            performed += 1
        if performed == 0 and contract.get("copy_required", True):
            raise SourceError(f"no applicable copy contract: {service}")
        self._database_workflow(service, contract.get("database"), plan, state)
        if plan.get("assistant_restore_case") != "APP_DATA_ONLY":
            self._prepare_compose(service, contract, state)
            self._prepare_unit(service, contract)

    def _database_workflow(self, service, database, plan, state):
        if not database:
            return
        kind = database.get("kind")
        if kind == "SQLITE":
            rel = _safe_relative(database["target_rel"], "SQLite target")
            path = self.data_target.joinpath(*rel.parts)
            try:
                with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
                    result = db.execute("PRAGMA quick_check").fetchone()
                if not result or result[0] != "ok":
                    raise sqlite3.DatabaseError("quick_check")
            except (OSError, sqlite3.DatabaseError):
                policy = database.get("invalid_policy", "UNAVAILABLE")
                state.setdefault("service_outcomes", {})[service] = policy
            return
        if kind not in {"POSTGRESQL", "MARIADB", "MYSQL"}:
            raise ValidationError(f"unknown database workflow: {service}")
        workflow = database.get("workflows", {}).get(plan["mode"])
        if not workflow:
            raise ValidationError(f"database workflow missing for mode: {service}")
        work = self.target_root / "work" / "database" / service / plan["run_id"]
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True, mode=0o700)
        dump = work / ("export.pgsql" if kind == "POSTGRESQL" else "export.sql")
        source_kind = workflow.get("source_kind")
        raw_source = None
        export_started = False
        target_started = False

        def command(name, *, stdin_path=None, stdout_path=None):
            action = (workflow.get("commands") or database.get("commands") or {}).get(name)
            if not isinstance(action, dict) or not isinstance(action.get("argv"), list):
                raise ValidationError(f"database command missing: {service}:{name}")
            values = {
                "{DUMP}": str(dump), "{RAW_SOURCE}": str(raw_source) if raw_source else "",
                "{WORK_DIR}": str(work), "{TARGET_ROOT}": str(self.target_root),
                "{DATA_TARGET}": str(self.data_target),
                "{DOCKER_SOCKET}": self.config["container_runtime"]["socket"],
                "{SECRET_DIR}": str(self.config.get("_plaintext_secret_dir", "")),
            }
            expanded = []
            for raw in action["argv"]:
                value = str(raw)
                for token, replacement in values.items():
                    value = value.replace(token, replacement)
                expanded.append(value)
            if any("{" in x or "}" in x for x in expanded):
                raise ValidationError(f"unresolved database command placeholder: {service}:{name}")
            database_container = None
            if name in {"isolated_start", "initialize_empty"} and "--name" in expanded:
                position = expanded.index("--name") + 1
                if position >= len(expanded):
                    raise ValidationError(f"database container name missing: {service}:{name}")
                database_container = expanded[position]
                labels = ["--label", f"hp.recovery.run_id={plan['run_id']}",
                          "--label", f"hp.recovery.service={service}"]
                expanded[-1:-1] = labels
                self._database_containers.add(database_container)
                state.setdefault("database_cleanup_contracts", {})[database_container] = {
                    "profile": service, "name": database_container,
                    "run_id_label": plan["run_id"], "service_label": service,
                    "cleanup_status": "PENDING_START",
                }
                self._checkpoint()
            self._validate_contract_command(expanded)
            attempts = int(action.get("attempts", 1))
            for attempt in range(attempts):
                try:
                    self._recorded_run(expanded, stdin_path=stdin_path, stdout_path=stdout_path,
                                       timeout=int(action.get("timeout", 300)))
                    if database_container is not None:
                        state["database_cleanup_contracts"][database_container]["cleanup_status"] = "ACTIVE"
                        self._checkpoint()
                    if name in {"isolated_stop", "target_stop"} and expanded:
                        stopped = expanded[-1]
                        contract_state = state.get("database_cleanup_contracts", {}).get(stopped)
                        if contract_state is not None:
                            contract_state["cleanup_status"] = "REMOVED"
                            self._checkpoint()
                    break
                except RecoveryError:
                    if attempt + 1 >= attempts:
                        raise
                    time.sleep(float(action.get("retry_delay", 1)))

        def has_command(name):
            return name in (workflow.get("commands") or database.get("commands") or {})

        try:
            if source_kind == "L2_RAW":
                raw_backup = self._source_for({"source": "L2", "source_rel": workflow["raw_source_rel"]}, plan)
                if raw_backup is None or not raw_backup.is_dir():
                    raise SourceError(f"required L2 raw database missing: {service}")
                raw_source = work / "raw-copy"
                self._copy(raw_backup, raw_source, target_root=self.target_root)
                command("isolated_start")
                export_started = True
                if has_command("wait_export"):
                    command("wait_export")
                command("logical_export", stdout_path=dump)
                if not dump.is_file() or dump.stat().st_size == 0:
                    raise RecoveryError(f"logical database export is empty: {service}")
            elif source_kind == "L3_DUMP":
                dump_glob = workflow.get("dump_glob")
                if not dump_glob:
                    raise ValidationError(f"logical dump glob missing: {service}")
                rel_glob = _safe_relative(dump_glob, "logical dump glob")
                l3_root = pathlib.Path(plan["l3"]["path"])
                candidates = [x for x in l3_root.glob(rel_glob.as_posix())
                              if x.is_file() and not x.is_symlink() and _under(x, l3_root)]
                source_dump = candidates[0] if len(candidates) == 1 else None
                if source_dump is None or not source_dump.is_file() or source_dump.stat().st_size == 0:
                    state.setdefault("service_outcomes", {})[service] = workflow.get("missing_dump_policy", "UNAVAILABLE")
                    raise SourceError(f"required logical dump missing: {service}")
                shutil.copyfile(source_dump, dump)
                os.chmod(dump, 0o600)
            else:
                raise ValidationError(f"database source kind missing: {service}")
            if export_started:
                command("isolated_stop")
                export_started = False
            command("initialize_empty")
            target_started = True
            if has_command("wait_target"):
                command("wait_target")
            command("import_dump", stdin_path=dump)
            command("test_query")
            command("target_stop")
            target_started = False
            state.setdefault("database_workflows", {})[service] = {
                "kind": kind, "source_kind": source_kind, "operations": "PASS",
                "dump_location_class": "TARGET_ROOT_CONTROLLED_WORKDIR",
            }
        finally:
            if export_started:
                try:
                    command("isolated_stop")
                except Exception as exc:
                    state.setdefault("database_cleanup_errors", {})[service] = type(exc).__name__
            if target_started:
                try:
                    command("target_stop")
                except Exception as exc:
                    state.setdefault("database_cleanup_errors", {})[service] = type(exc).__name__
            if work.exists():
                shutil.rmtree(work)

    def _prepare_base_files(self, plan):
        for mapping in self.config.get("base_system", {}).get("copies", []):
            modes = mapping.get("modes", ["BASE_ONLY", "L2_ONLY", "L3_ONLY", "COMBINED_L2_L3", "L3_DEFERRED"])
            if plan["mode"] not in modes:
                continue
            if mapping.get("source") == "USB":
                source = self.usb_root.joinpath(*_safe_relative(mapping["source_rel"], "base source").parts)
            else:
                source = self._source_for(mapping, plan)
            if source is None or not source.exists() or source.is_symlink():
                if mapping.get("required", True):
                    raise SourceError("required base-system source missing")
                continue
            target = self.system_target.joinpath(*_safe_relative(mapping["target_rel"], "base target").parts)
            self._copy(source, target, delete=mapping.get("delete", False) is True, target_root=self.system_target)

    def _prepare_compose(self, service, contract, state):
        compose = contract.get("compose")
        if not compose:
            return
        payload_file = self.usb_root.joinpath(*_safe_relative(compose.get("payload_file", ""), "Compose payload").parts)
        if not payload_file.is_file() or payload_file.is_symlink():
            raise ValidationError(f"Compose payload missing: {service}")
        compose_dir = self.target_root.joinpath(*_safe_relative(compose.get("target_rel", ""), "Compose target").parts).parent
        source_file = compose_dir / "source-compose.yml"
        self._copy(payload_file, source_file, target_root=self.target_root)
        image_bindings = compose.get("image_bindings")
        if not isinstance(image_bindings, dict) or not image_bindings:
            raise ValidationError(f"immutable Compose image bindings missing: {service}")
        allowed_images = {x["reference"] for x in self.config.get("images", [])
                          if service in set(x.get("services", []))}
        if not set(image_bindings.values()) <= allowed_images:
            raise ValidationError(f"Compose image binding outside image lock: {service}")
        secret_root = self.config.get("_plaintext_secret_dir")
        if not secret_root:
            raise ValidationError(f"dummy secret package not prepared for Compose: {service}")
        env_file = pathlib.Path(secret_root).joinpath(*_safe_relative(compose.get("env_secret_rel", ""), "Compose env").parts)
        if not env_file.is_file() or env_file.is_symlink() or not _under(env_file, secret_root):
            raise ValidationError(f"isolated dummy Compose env missing: {service}")
        missing = prepare_companions(compose, self.usb_root, self.target_root)
        if missing:
            policy = compose.get("missing_companion_policy", "STOP")
            if policy == "PARTIAL" and compose.get("start") is False:
                state.setdefault("service_outcomes", {})[service] = "PARTIAL"
                state.setdefault("compose_unavailable", {})[service] = {
                    "reason": "MISSING_CONFIRMED_COMPANION", "missing": missing,
                }
                return
            raise ValidationError(f"required Compose companion missing: {service}")
        prepare_mount_sources(compose, self.target_root, self.data_target)
        payload_document = load_compose_payload(payload_file)
        isolated_document = build_isolated_compose(payload_document, compose, self.target_root, env_file,
                                                    self.data_target)
        validate_isolated_compose(isolated_document, compose, self.target_root, env_file,
                                  self.config.get("productive_ips", []), data_target=self.data_target)
        compose_file = compose_dir / "isolated-compose.json"
        atomic_json(compose_file, isolated_document)
        docker = ["docker", "--host", self.config["container_runtime"]["socket"], "compose",
                  "--project-name", compose["project_name"], "--env-file", str(env_file),
                  "--file", str(compose_file)]
        rendered = self.platform.run(docker + ["config", "--format", "json"])
        if rendered.returncode != 0:
            raise ValidationError(f"isolated Compose render failed: {service}")
        try:
            document = json.loads(rendered.stdout.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValidationError(f"invalid isolated Compose render: {service}") from exc
        validate_isolated_compose(document, compose, self.target_root, env_file,
                                  self.config.get("productive_ips", []), data_target=self.data_target,
                                  env_expanded=True)
        self._recorded_run(docker + ["config", "--quiet"])
        if compose.get("start") is True:
            cleanup_contract = {
                "profile": service,
                "project_name": compose["project_name"],
                "service_ids": list(compose["verify_services"]),
                "containers": {
                    service_id: {
                        "name": compose["container_names"][service_id],
                        "project_label": compose["project_name"],
                        "service_label": service_id,
                    }
                    for service_id in compose["verify_services"]
                },
                "networks": {
                    network_id: {
                        "name": f"{compose['project_name']}_{network_id}",
                        "project_label": compose["project_name"],
                        "network_label": network_id,
                    }
                    for network_id in compose.get("allowed_networks", [])
                },
                "cleanup_status": "PENDING_START",
            }
            state.setdefault("runtime_cleanup_contracts", {})[service] = cleanup_contract
            state.setdefault("compose_projects", {})[service] = {
                "project": compose["project_name"], "services": list(compose["verify_services"]),
                "status": "PENDING_START",
            }
            self._checkpoint()
            self._active_compose[service] = {"argv": docker, "contract": compose}
            self._recorded_run(docker + ["up", "--detach", "--no-build", "--pull", "never"], timeout=900)
            cleanup_contract["cleanup_status"] = "ACTIVE"
            state["compose_projects"][service]["status"] = "STARTED_ISOLATED"
            self._checkpoint()

    def _validate_compose_containers(self, service, state):
        active = self._active_compose.get(service)
        if active is None:
            return
        compose = active["contract"]
        verified = []
        for service_id in compose.get("verify_services", []):
            container_name = compose["container_names"][service_id]
            inspect = self.platform.run([
                "docker", "--host", self.config["container_runtime"]["socket"],
                "inspect", container_name, "--format", "{{json .}}",
            ])
            if inspect.returncode != 0:
                raise RecoveryError(f"isolated Compose container unavailable: {service}:{service_id}")
            try:
                document = json.loads(inspect.stdout.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValidationError(f"invalid isolated container inspection: {service}:{service_id}") from exc
            labels = document.get("Config", {}).get("Labels", {}) or {}
            if labels.get("com.docker.compose.project") != compose["project_name"]:
                raise SafetyError(f"isolated container project mismatch: {service}:{service_id}")
            if labels.get("com.docker.compose.service") != service_id:
                raise SafetyError(f"isolated container service mismatch: {service}:{service_id}")
            actual_name = str(document.get("Name", "")).lstrip("/")
            if actual_name != container_name:
                raise SafetyError(f"isolated container name mismatch: {service}:{service_id}")
            if document.get("Config", {}).get("Image") != compose["image_bindings"][service_id]:
                raise SafetyError(f"isolated container image mismatch: {service}:{service_id}")
            container_state = document.get("State", {}) or {}
            if container_state.get("Running") is not True:
                raise RecoveryError(f"isolated Compose container not running: {service}:{service_id}")
            if service_id in set(compose.get("health_required", [])):
                if (container_state.get("Health") or {}).get("Status") != "healthy":
                    raise RecoveryError(f"isolated Compose container is not healthy: {service}:{service_id}")
            verified.append({"service": service_id, "container": container_name,
                             "image": compose["image_bindings"][service_id], "status": "RUNNING_VERIFIED"})
        state.setdefault("compose_identity_evidence", {})[service] = verified

    def _prepare_unit(self, service, contract):
        unit = contract.get("unit")
        if not unit:
            return
        if unit not in set(self.config.get("allowed_units", [])) or not unit.endswith(".service"):
            raise SafetyError(f"unbound service unit: {service}")
        exists = self.platform.run(["systemctl", "show", unit, "--property=LoadState", "--value"])
        if exists.returncode != 0 or exists.stdout.strip() != b"loaded":
            raise ValidationError(f"unknown service unit: {service}")
        self._recorded_run(["systemctl", "start", unit])

    def _prepare_packages_images(self, state, plan):
        packages = self.config.get("packages", {})
        stable_locale = {"LC_ALL": "C", "LANG": "C"}

        def installed(package):
            result = self.platform.run(
                ["dpkg-query", "-W", "-f=${Status}", package], env=stable_locale
            )
            return result.returncode == 0 and result.stdout == b"install ok installed"

        for package in packages.get("required", []):
            if not installed(package):
                raise ValidationError(f"required package missing: {package}")
        for group in packages.get("required_any", []):
            if not any(installed(package) for package in group):
                raise ValidationError("required package alternative group unsatisfied")
        docker = self.config.get("container_runtime", {})
        docker_argv = ["docker", "--host", docker["socket"]]
        compose = self.platform.run(docker_argv + ["compose", "version"], env=stable_locale)
        if compose.returncode != 0:
            raise ValidationError("Docker Compose v2 capability unavailable")
        for item in packages.get("offline_debs", []):
            try:
                path = pathlib.Path(item.get("path", "")).resolve(strict=True)
            except FileNotFoundError as exc:
                raise ValidationError("offline package missing") from exc
            if not _under(path, self.target_root) or sha256_file(path) != item.get("sha256"):
                raise ValidationError("offline package checksum mismatch")
            self._recorded_run(["dpkg", "--install", str(path)], timeout=600)
        for image in self.config.get("images", []):
            image_services = set(image.get("services", []))
            if image_services and not (image_services & set(plan.get("services", []))):
                continue
            if (plan.get("assistant_restore_case") == "APP_DATA_ONLY" and
                    image_services & {"urlaubsplaner", "devicewatchdog"}):
                continue
            reference = _require(image.get("reference"), "image reference missing")
            kind = image.get("kind", "REGISTRY")
            if kind == "REGISTRY" and not re.search(r"@sha256:[0-9a-f]{64}$", reference):
                raise SafetyError("movable registry image reference rejected")
            expected_id = image.get("expected_image_id")
            inspect = self.platform.run(docker_argv + ["image", "inspect", reference, "--format", "{{.Id}}"])
            if inspect.returncode == 0:
                actual_id = inspect.stdout.decode("utf-8").strip()
                if expected_id and actual_id != expected_id:
                    raise ValidationError("local image identity mismatch")
                continue
            try:
                archive_root = pathlib.Path(_require(self.config.get("image_archive_root"), "image archive root missing")).resolve(strict=True)
                archive = archive_root.joinpath(*_safe_relative(image.get("archive_rel", ""), "image archive").parts).resolve(strict=True)
            except FileNotFoundError as exc:
                if image.get("required", True) is False:
                    continue
                raise ValidationError("required image archive missing") from exc
            if not _under(archive, archive_root) or not archive.is_file() or sha256_file(archive) != image.get("archive_sha256"):
                raise ValidationError("missing or invalid immutable image archive")
            self._recorded_run(docker_argv + ["load", "--input", str(archive)], timeout=900)
            loaded = self.platform.run(docker_argv + ["image", "inspect", reference, "--format", "{{.Id}}"])
            if loaded.returncode != 0:
                raise ValidationError("required image unavailable after offline load")
            actual_id = loaded.stdout.decode("utf-8").strip()
            if expected_id and actual_id != expected_id:
                raise ValidationError("local image identity mismatch after load")
        state["package_image_preflight"] = "PASS"

    def _hold_timers(self, state):
        timers = self.config.get("timers", {})
        held = timers.get("hold", [])
        if not held:
            raise ValidationError("timer hold contract missing")
        for unit in held:
            if not unit.endswith(".timer") or "/" in unit:
                raise ValidationError("invalid timer unit")
            if unit not in set(self.config.get("allowed_units", [])):
                raise SafetyError(f"unbound timer unit: {unit}")
            exists = self.platform.run(["systemctl", "show", unit, "--property=LoadState", "--value"])
            if exists.returncode != 0 or exists.stdout.strip() != b"loaded":
                raise ValidationError(f"unknown timer unit: {unit}")
            self._recorded_run(["systemctl", "disable", "--now", unit])
        state["timers"] = "HELD"

    def _test_service(self, service, state):
        contract = self.config["services"][service]
        failures = []
        container_ready = True
        try:
            self._validate_compose_containers(service, state)
        except RecoveryError:
            container_ready = False
            failures.append("CONTAINER")
        for check in contract.get("checks", []):
            kind = check.get("kind")
            if kind == "PATH":
                rel = _safe_relative(check["target_rel"], "check path")
                path = self.data_target.joinpath(*rel.parts)
                if not path.exists() or path.is_symlink():
                    failures.append("PATH")
                    continue
                current = stat.S_IMODE(path.stat().st_mode)
                if check.get("mode") is not None and current != int(str(check["mode"]), 8):
                    failures.append("MODE")
                if check.get("uid") is not None and path.stat().st_uid != int(check["uid"]):
                    failures.append("UID")
                if check.get("gid") is not None and path.stat().st_gid != int(check["gid"]):
                    failures.append("GID")
                if check.get("acl_required"):
                    if shutil.which("getfacl") is None:
                        failures.append("ACL_TOOL_MISSING")
                    elif self.platform.run(["getfacl", "--absolute-names", str(path)]).returncode != 0:
                        failures.append("ACL")
            elif kind == "COMMAND":
                argv = [str(x).replace("{DOCKER_SOCKET}", self.config["container_runtime"]["socket"])
                        .replace("{TARGET_ROOT}", str(self.target_root))
                        .replace("{DATA_TARGET}", str(self.data_target))
                        for x in check.get("argv", [])]
                self._validate_contract_command(argv)
                result = self.platform.run(argv, timeout=int(check.get("timeout", 60)))
                if result.returncode != 0:
                    failures.append("COMMAND")
            elif kind == "ENDPOINT":
                if not container_ready:
                    failures.append("ENDPOINT")
                    continue
                url = check.get("url", "")
                parsed = urllib.parse.urlparse(url)
                if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                    raise SafetyError("non-loopback endpoint rejected")
                try:
                    with urllib.request.urlopen(url, timeout=float(check.get("timeout", 5))) as response:
                        if response.status not in check.get("status", [200]):
                            failures.append("ENDPOINT")
                except (OSError, urllib.error.URLError):
                    failures.append("ENDPOINT")
            else:
                raise ValidationError(f"unknown service check: {service}")
        if failures:
            state.setdefault("service_outcomes", {})[service] = contract.get("check_failure", "UNAVAILABLE")
            state.setdefault("service_check_failures", {})[service] = sorted(set(failures))
        else:
            state.setdefault("service_outcomes", {}).setdefault(service, contract.get("success_status", "FULL"))

    def _inspect_object(self, argv, description):
        result = self.platform.run(argv + ["--format", "{{json .}}"])
        if result.returncode != 0:
            error = (result.stderr or b"").decode("utf-8", errors="replace").lower()
            if "no such" in error or "not found" in error:
                return None
            raise RecoveryError(f"{description} absence cannot be confirmed")
        try:
            return json.loads(result.stdout.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise RecoveryError(f"{description} absence cannot be confirmed") from exc

    def _cleanup_compose_contracts(self, state):
        docker = ["docker", "--host", self.config["container_runtime"]["socket"]]
        contracts = state.get("runtime_cleanup_contracts", {})
        for profile, contract in sorted(contracts.items()):
            if contract.get("cleanup_status") == "REMOVED":
                continue
            present_containers = []
            present_networks = []
            # Verify every identity before deleting any object from this project.
            for service_id, expected in sorted(contract.get("containers", {}).items()):
                document = self._inspect_object(docker + ["inspect", expected["name"]], "container")
                if document is None:
                    continue
                labels = document.get("Config", {}).get("Labels", {}) or {}
                actual_name = str(document.get("Name", "")).lstrip("/")
                if (actual_name != expected["name"] or
                        labels.get("com.docker.compose.project") != expected["project_label"] or
                        labels.get("com.docker.compose.service") != expected["service_label"]):
                    raise SafetyError("stored cleanup container identity mismatch")
                present_containers.append(expected["name"])
            for network_id, expected in sorted(contract.get("networks", {}).items()):
                document = self._inspect_object(docker + ["network", "inspect", expected["name"]], "network")
                if document is None:
                    continue
                labels = document.get("Labels", {}) or {}
                if (document.get("Name") != expected["name"] or
                        labels.get("com.docker.compose.project") != expected["project_label"] or
                        labels.get("com.docker.compose.network") != expected["network_label"]):
                    raise SafetyError("stored cleanup network identity mismatch")
                present_networks.append(expected["name"])
            for name in present_containers:
                self._recorded_run(docker + ["container", "rm", "--force", name])
            for name in present_networks:
                self._recorded_run(docker + ["network", "rm", name])
            for expected in contract.get("containers", {}).values():
                if self._inspect_object(docker + ["inspect", expected["name"]], "container") is not None:
                    raise RecoveryError("isolated Compose container remained after cleanup")
            for expected in contract.get("networks", {}).values():
                if self._inspect_object(docker + ["network", "inspect", expected["name"]], "network") is not None:
                    raise RecoveryError("isolated Compose network remained after cleanup")
            contract["cleanup_status"] = "REMOVED"
            state.setdefault("compose_projects", {}).setdefault(profile, {})["status"] = "REMOVED"
            self._checkpoint()

    def _cleanup_database_contracts(self, state):
        docker = ["docker", "--host", self.config["container_runtime"]["socket"]]
        contracts = state.get("database_cleanup_contracts", {})
        for name, expected in sorted(contracts.items()):
            if expected.get("cleanup_status") == "REMOVED":
                continue
            document = self._inspect_object(docker + ["inspect", name], "database container")
            if document is not None:
                labels = document.get("Config", {}).get("Labels", {}) or {}
                if (str(document.get("Name", "")).lstrip("/") != name or
                        labels.get("hp.recovery.run_id") != expected["run_id_label"] or
                        labels.get("hp.recovery.service") != expected["service_label"]):
                    raise SafetyError("stored cleanup database identity mismatch")
                self._recorded_run(docker + ["container", "rm", "--force", name])
            if self._inspect_object(docker + ["inspect", name], "database container") is not None:
                raise RecoveryError("isolated database container remained after cleanup")
            expected["cleanup_status"] = "REMOVED"
            self._checkpoint()

    def reconcile_runtime(self, state):
        """Reconcile persisted runtime objects before any completed step is skipped."""
        self._cleanup_compose_contracts(state)
        self._cleanup_database_contracts(state)

    def finalize(self, state):
        """Remove persisted runtime objects before plaintext cleanup/reporting."""
        errors = []
        try:
            self._cleanup_compose_contracts(state)
        except Exception as exc:
            errors.append(f"compose:{type(exc).__name__}")
        try:
            self._cleanup_database_contracts(state)
        except Exception as exc:
            errors.append(f"database:{type(exc).__name__}")
        self._active_compose.clear()
        self.config.pop("_plaintext_secret_dir", None)
        if errors:
            state["cleanup_errors"] = errors
            raise RecoveryError("isolated runtime cleanup failed")

    def verify_runtime_cleanup(self, state):
        """Prove every persisted runtime object absent before PASS/COMPLETED."""
        docker = ["docker", "--host", self.config["container_runtime"]["socket"]]
        for contract in state.get("runtime_cleanup_contracts", {}).values():
            for expected in contract.get("containers", {}).values():
                if self._inspect_object(docker + ["inspect", expected["name"]], "container") is not None:
                    raise RecoveryError("stored Compose container absence is unconfirmed")
            for expected in contract.get("networks", {}).values():
                if self._inspect_object(docker + ["network", "inspect", expected["name"]], "network") is not None:
                    raise RecoveryError("stored Compose network absence is unconfirmed")
        for name in state.get("database_cleanup_contracts", {}):
            if self._inspect_object(docker + ["inspect", name], "database container") is not None:
                raise RecoveryError("stored database container absence is unconfirmed")
        if any(item.get("cleanup_status") != "REMOVED"
               for item in state.get("runtime_cleanup_contracts", {}).values()):
            raise RecoveryError("Compose cleanup contract is not removed")
        if any(item.get("status") != "REMOVED"
               for item in state.get("compose_projects", {}).values()):
            raise RecoveryError("Compose project cleanup is not removed")
        if any(item.get("cleanup_status") != "REMOVED"
               for item in state.get("database_cleanup_contracts", {}).values()):
            raise RecoveryError("database cleanup contract is not removed")
        raw = state.get("plaintext_secret_dir")
        if raw or (raw and pathlib.Path(raw).exists()):
            raise RecoveryError("plaintext secret root cleanup is unconfirmed")

        verification = state.get("marker_verification") or {}
        if (verification.get("run_id") != state.get("run_id") or
                verification.get("status") != "PASS" or
                verification.get("verified_generation") != verification.get("operation_generation")):
            raise RecoveryError("marker verification is not a current PASS")

    def verify_secret_cleanup(self, state, roots):
        """Persist a fail-closed, secret-free marker verification result."""
        verification = state.get("marker_verification")
        if not isinstance(verification, dict) or verification.get("run_id") != state.get("run_id"):
            state["marker_verification"] = {
                "status": "UNKNOWN", "run_id": state.get("run_id"),
                "operation_generation": 0, "verified_generation": None,
                "method": "MARKERS_UNAVAILABLE", "path_classes": [], "hit_count": 0,
            }
            self._checkpoint()
            raise RecoveryError("marker verification state is missing or invalid")
        markers = {marker for marker in self._secret_markers if marker}
        if not markers:
            reusable = (verification.get("status") == "PASS" and
                        verification.get("verified_generation") == verification.get("operation_generation") and
                        verification.get("method") in {"IN_MEMORY_MARKER_SCAN", "NO_SECRET_MARKERS_CONFIGURED"})
            if reusable:
                return
            verification.update({"status": "FAILED", "verified_generation": None,
                                 "method": "MARKERS_UNAVAILABLE", "hit_count": 0})
            self._checkpoint()
            raise RecoveryError("marker verification cannot be reconstructed")
        hit_count = 0
        hit_classes = set()
        scanned_classes = []
        for path_class, root in roots.items():
            scanned_classes.append(path_class)
            path = pathlib.Path(root)
            if not path.exists():
                continue
            files = [path] if path.is_file() else (item for item in path.rglob("*") if item.is_file() and not item.is_symlink())
            for item in files:
                try:
                    content = item.read_bytes()
                except OSError as exc:
                    verification.update({"status": "FAILED", "verified_generation": None,
                                         "method": "SCAN_UNREADABLE", "path_classes": [path_class],
                                         "hit_count": hit_count})
                    self._checkpoint()
                    raise RecoveryError("secret cleanup verification unreadable") from exc
                matches = sum(1 for marker in markers if marker in content)
                if matches:
                    hit_count += matches
                    hit_classes.add(path_class)
        if hit_count:
            verification.update({"status": "FAILED", "verified_generation": None,
                                 "method": "MARKER_FOUND", "path_classes": sorted(hit_classes),
                                 "hit_count": hit_count})
            self._checkpoint()
            raise RecoveryError("synthetic secret marker remained after cleanup")
        verification.update({"status": "PASS",
                             "verified_generation": verification.get("operation_generation"),
                             "method": "IN_MEMORY_MARKER_SCAN", "path_classes": scanned_classes,
                             "hit_count": 0})
        self._checkpoint()

    def _enable_timers(self, plan, state):
        accepted = {name for name, status in state.get("service_outcomes", {}).items() if status == "FULL"}
        bindings = self.config.get("timers", {}).get("enable_after_acceptance", {})
        enabled = []
        for service in plan["services"]:
            if service not in accepted:
                continue
            for unit in bindings.get(service, []):
                if not unit.endswith(".timer") or "/" in unit:
                    raise ValidationError("invalid profile timer")
                if unit not in set(self.config.get("allowed_units", [])):
                    raise SafetyError(f"unbound profile timer: {unit}")
                self._recorded_run(["systemctl", "enable", "--now", unit])
                enabled.append(unit)
        state["timers"] = {"status": "PROFILE_ALLOWED_ONLY", "enabled": sorted(enabled)}

    def run(self, step, plan, state):
        self._recheck(plan)
        op = step["op"]
        if op in {"PREPARE_BASE", "RESTORE_SERVICE", "TEST_SERVICE", "ENABLE_PROFILE_TIMERS"}:
            self._note_persistent_operation(state, op)
        if op == "CHECK_STORAGE":
            result = storage_preflight(plan, system_free=self.platform.free_bytes(self.system_target),
                                       data_free=self.platform.free_bytes(self.data_target), safety_copy_required=0)
            state["storage_preflight"] = result
            if any(x["status"] != "PASS" for x in result.values()):
                raise ValidationError("realtest storage preflight stopped execution")
        elif op == "PREPARE_BASE":
            self.system_target.mkdir(parents=True, exist_ok=True)
            self.data_target.mkdir(parents=True, exist_ok=True)
            self._prepare_secrets(state)
            self._prepare_packages_images(state, plan)
            self._prepare_base_files(plan)
        elif op == "HOLD_TIMERS":
            self._hold_timers(state)
        elif op == "RESTORE_SERVICE":
            self._restore_service(step["service"], plan, state)
        elif op == "TEST_SERVICE":
            self._test_service(step["service"], state)
        elif op == "OPTIONAL_SERVICE":
            state.setdefault("service_outcomes", {})["snowflake"] = "SKIPPED_OPTIONAL"
        elif op == "ENABLE_PROFILE_TIMERS":
            self._enable_timers(plan, state)
        elif op in {"VALIDATE_USB", "REPORT", "WAIT_FOR_L3"}:
            pass
        else:
            raise RecoveryError(f"unsupported realtest operation: {op}")
        state["realtest_command_audit"] = self.command_audit
