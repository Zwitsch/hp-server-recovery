"""Structured, fail-closed Compose isolation for the P3-11 real test."""
from __future__ import annotations

import copy
import pathlib
import re
import shutil

from .errors import SafetyError, ValidationError
from .util import metadata_tree_fingerprint, sha256_file

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by the VM dependency gate
    raise ValidationError("python3-yaml is required for structured Compose isolation") from exc


_ENV_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_INTERPOLATION = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:-|-)([^}]*))?\}")
_SAFE_SERVICE_KEYS = {
    "command", "depends_on", "environment", "healthcheck", "logging", "read_only",
    "restart", "security_opt", "stop_grace_period", "tmpfs",
}
_LOOPBACKS = {"127.0.0.1", "::1"}


def load_compose_payload(path):
    """Load an actual payload as YAML data, never by textual replacement."""
    path = pathlib.Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValidationError("Compose payload is missing or not a regular file")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValidationError("Compose payload is not valid structured YAML") from exc
    if not isinstance(document, dict) or not isinstance(document.get("services"), dict):
        raise ValidationError("Compose payload has no service map")
    return document


def load_dummy_env(path):
    """Read a controlled Compose environment without shell evaluation."""
    path = pathlib.Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValidationError("isolated dummy Compose env missing")
    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValidationError("isolated dummy Compose env is unreadable") from exc
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export ") or "=" not in line:
            raise ValidationError(f"invalid dummy Compose env line: {number}")
        key, value = line.split("=", 1)
        if not _ENV_KEY.fullmatch(key):
            raise ValidationError(f"invalid dummy Compose env key: {number}")
        values[key] = value
    return values


def _required_env_keys(value):
    """Return interpolation keys without expanding or retaining their values."""
    if isinstance(value, str):
        return {match.group(1) for match in _INTERPOLATION.finditer(value)}
    if isinstance(value, list):
        return set().union(*(_required_env_keys(item) for item in value), set())
    if isinstance(value, dict):
        return set().union(*(_required_env_keys(item) for item in value.values()), set())
    return set()


def _under(path, root):
    try:
        pathlib.Path(path).resolve(strict=False).relative_to(pathlib.Path(root).resolve(strict=False))
        return True
    except ValueError:
        return False


def _target_source(target_root, rel, data_target=None):
    rel_path = pathlib.PurePosixPath(str(rel))
    if rel_path.is_absolute() or ".." in rel_path.parts or str(rel_path) in {"", "."}:
        raise ValidationError("invalid isolated Compose source_rel")
    if rel_path.parts[0] == "data":
        base = pathlib.Path(data_target) if data_target is not None else pathlib.Path(target_root) / "data"
        path = base.joinpath(*rel_path.parts[1:]).resolve(strict=False)
    else:
        path = pathlib.Path(target_root).joinpath(*rel_path.parts).resolve(strict=False)
    if not _under(path, target_root):
        raise SafetyError("isolated Compose source escaped target_root")
    return path


def prepare_companions(contract, usb_root, target_root):
    """Copy only confirmed companion artifacts and report absent ones."""
    usb_root = pathlib.Path(usb_root).resolve(strict=False)
    target_root = pathlib.Path(target_root).resolve(strict=False)
    missing = []
    for item in contract.get("companions", []):
        source_rel = pathlib.PurePosixPath(str(item.get("payload_rel", "")))
        if source_rel.is_absolute() or ".." in source_rel.parts:
            raise ValidationError("invalid Compose companion payload path")
        source = usb_root.joinpath(*source_rel.parts).resolve(strict=False)
        target = _target_source(target_root, item.get("target_rel", ""))
        if not _under(source, usb_root) or not source.exists() or source.is_symlink():
            if item.get("required", True):
                missing.append(str(source_rel))
            continue
        expected_type = item.get("type", "file")
        if (expected_type == "file" and not source.is_file()) or (expected_type == "directory" and not source.is_dir()):
            raise ValidationError("Compose companion type mismatch")
        expected_sha = item.get("sha256")
        if expected_sha:
            actual = sha256_file(source) if source.is_file() else metadata_tree_fingerprint(source)
            if actual != expected_sha:
                raise ValidationError("Compose companion identity mismatch")
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target, symlinks=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
    return missing


def prepare_mount_sources(contract, target_root, data_target=None):
    """Create declared isolated sources; copy only the allowlisted localtime file."""
    for service_mounts in contract.get("mounts", {}).values():
        for mount in service_mounts:
            source = _target_source(target_root, mount.get("source_rel", ""), data_target)
            source_type = mount.get("source_type", "directory")
            if source_type == "directory":
                source.mkdir(parents=True, exist_ok=True)
            elif source_type == "localtime_copy":
                system_localtime = pathlib.Path("/etc/localtime").resolve(strict=True)
                if not system_localtime.is_file():
                    raise ValidationError("controlled /etc/localtime source unavailable")
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(system_localtime, source)
            elif source_type == "companion":
                if not source.exists() or source.is_symlink():
                    raise ValidationError("required Compose companion is absent")
            else:
                raise ValidationError("unknown isolated Compose source type")


def build_isolated_compose(payload, contract, target_root, dummy_env, data_target=None):
    """Construct a complete isolated Compose document from structured data."""
    expected = set(contract.get("expected_services", []))
    actual = set(payload.get("services", {}))
    if not expected or actual != expected:
        raise ValidationError("actual Compose service set differs from isolation contract")
    image_bindings = contract.get("image_bindings", {})
    if set(image_bindings) != expected:
        raise ValidationError("Compose image bindings do not cover exact service set")
    env_keys = set(load_dummy_env(dummy_env))
    isolated_services = {}
    for name in sorted(expected):
        original = payload["services"][name]
        if not isinstance(original, dict):
            raise ValidationError("invalid Compose service definition")
        definition = {key: copy.deepcopy(original[key])
                      for key in _SAFE_SERVICE_KEYS if key in original}
        required_keys = _required_env_keys(definition)
        if not required_keys <= env_keys:
            raise ValidationError("dummy Compose env does not cover payload variables")
        definition["container_name"] = contract["container_names"][name]
        definition["image"] = image_bindings[name]
        definition["pull_policy"] = "never"
        mounts = []
        for mount in contract.get("mounts", {}).get(name, []):
            mounts.append({
                "type": "bind",
                "source": str(_target_source(target_root, mount["source_rel"], data_target)),
                "target": mount["target"],
                "read_only": bool(mount.get("read_only", False)),
            })
        if mounts:
            definition["volumes"] = mounts
        ports = []
        for port in contract.get("ports", {}).get(name, []):
            ports.append({
                "target": int(port["target"]), "published": str(port["published"]),
                "host_ip": port["host_ip"], "protocol": port.get("protocol", "tcp"),
                "mode": "host",
            })
        if ports:
            definition["ports"] = ports
        if name in set(contract.get("env_file_services", [])):
            definition["env_file"] = [str(pathlib.Path(dummy_env).resolve(strict=False))]
        service_networks = contract.get("service_networks", {}).get(name, [])
        if service_networks:
            definition["networks"] = list(service_networks)
        isolated_services[name] = definition
    networks = {name: {"internal": True, "name": f"{contract['project_name']}_{name}"}
                for name in contract.get("allowed_networks", [])}
    return {"name": contract["project_name"], "services": isolated_services, "networks": networks}


def _rendered_mounts(definition):
    mounts = []
    for volume in definition.get("volumes", []) or []:
        if not isinstance(volume, dict) or volume.get("type") != "bind":
            raise SafetyError("unexpected non-bind Compose volume")
        mounts.append(volume)
    return mounts


def validate_isolated_compose(document, contract, target_root, dummy_env, productive_ips, *,
                              data_target=None, env_expanded=False):
    """Validate Docker-rendered JSON or the structurally equivalent fallback."""
    services = document.get("services")
    expected = set(contract.get("expected_services", []))
    if not isinstance(services, dict) or set(services) != expected:
        raise SafetyError("rendered Compose contains unexpected services")
    dummy_env = str(pathlib.Path(dummy_env).resolve(strict=False))
    allowed_networks = set(contract.get("allowed_networks", []))
    top_networks = document.get("networks", {}) or {}
    if set(top_networks) != allowed_networks:
        raise SafetyError("rendered Compose network set differs from contract")
    for name, network in top_networks.items():
        if not isinstance(network, dict) or network.get("external") is True or network.get("internal") is not True:
            raise SafetyError(f"Compose network is not isolated: {name}")
        if network.get("name") not in (None, f"{contract['project_name']}_{name}"):
            raise SafetyError(f"Compose network identity differs from contract: {name}")
    for name, definition in services.items():
        if definition.get("container_name") != contract["container_names"][name]:
            raise SafetyError("rendered Compose container identity differs from contract")
        if definition.get("image") != contract["image_bindings"][name]:
            raise SafetyError("rendered Compose image differs from immutable contract")
        if definition.get("build") not in (None, {}):
            raise SafetyError("rendered Compose build is forbidden")
        if definition.get("network_mode"):
            raise SafetyError("Compose network_mode is forbidden")
        if definition.get("devices"):
            raise SafetyError("Compose device passthrough is forbidden")
        actual_networks = definition.get("networks", {}) or {}
        actual_networks = set(actual_networks if isinstance(actual_networks, list) else actual_networks.keys())
        if actual_networks != set(contract.get("service_networks", {}).get(name, [])):
            raise SafetyError("rendered Compose service network differs from contract")
        expected_mounts = {item["target"]: item for item in contract.get("mounts", {}).get(name, [])}
        actual_mounts = _rendered_mounts(definition)
        if {item.get("target") for item in actual_mounts} != set(expected_mounts):
            raise SafetyError("rendered Compose mount targets differ from contract")
        for mount in actual_mounts:
            source = pathlib.Path(str(mount.get("source", ""))).resolve(strict=False)
            if not _under(source, target_root):
                raise SafetyError("Compose bind mount outside isolated target")
            expected_source = _target_source(target_root, expected_mounts[mount["target"]]["source_rel"], data_target)
            if source != expected_source:
                raise SafetyError("rendered Compose mount source differs from contract")
            if bool(mount.get("read_only", False)) != bool(expected_mounts[mount["target"]].get("read_only", False)):
                raise SafetyError("rendered Compose mount mode differs from contract")
        expected_ports = {(str(p["host_ip"]), str(p["published"]), int(p["target"]), p.get("protocol", "tcp"))
                          for p in contract.get("ports", {}).get(name, [])}
        actual_ports = set()
        for port in definition.get("ports", []) or []:
            if not isinstance(port, dict):
                raise SafetyError("non-structured Compose port rejected")
            host_ip = str(port.get("host_ip", ""))
            if host_ip not in _LOOPBACKS:
                raise SafetyError("published Compose port is not loopback-bound")
            actual_ports.add((host_ip, str(port.get("published")), int(port.get("target")), port.get("protocol", "tcp")))
        if actual_ports != expected_ports:
            raise SafetyError("rendered Compose ports differ from contract")
        env_files = definition.get("env_file", []) or []
        if isinstance(env_files, str):
            env_files = [env_files]
        normalized_env = []
        for item in env_files:
            normalized_env.append(str(item.get("path")) if isinstance(item, dict) else str(item))
        expected_env = [dummy_env] if name in set(contract.get("env_file_services", [])) else []
        if normalized_env != expected_env and not (env_expanded and not normalized_env):
            raise SafetyError("rendered Compose env_file is not the controlled dummy file")
    serialized = repr(document)
    for ip in productive_ips:
        if ip and str(ip) in serialized:
            raise SafetyError("productive IP remains in rendered Compose document")
    return True
