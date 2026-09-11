import json
import pathlib
import re

from .errors import SourceError
from .util import tree_fingerprint


STAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}$")
KNOWN_SERVICES = {
    "nextcloud", "immich", "paperless", "jellyfin", "adguard", "npm",
    "analyzer", "snowflake", "storage", "urlaubsplaner", "devicewatchdog",
}


def validate_l2(root, target=None):
    p = pathlib.Path(root).resolve()
    expected = p / "server-backups/mirror/data"
    if not expected.is_dir() or expected.is_symlink():
        raise SourceError("invalid L2 layout")
    if target is not None and expected == pathlib.Path(target).resolve():
        raise SourceError("L2 source equals target")
    return {"kind": "L2", "root": str(expected), "read_only": True}


def scan_l3_roots(roots, fingerprint_func=tree_fingerprint):
    snapshots = []
    for priority, raw_root in enumerate(roots):
        root = pathlib.Path(raw_root)
        if not root.is_dir() or root.is_symlink():
            continue
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or child.is_symlink() or not STAMP.fullmatch(child.name):
                continue
            services = sorted(x.name for x in child.iterdir() if x.is_dir() and x.name in KNOWN_SERVICES)
            if not services:
                continue
            before = child.stat().st_mtime_ns
            fingerprint = fingerprint_func(child)
            after = child.stat().st_mtime_ns
            if before != after:
                raise SourceError(f"L3 changed during scan: {child.name}")
            snapshots.append({"id": child.name, "path": str(child.resolve()), "services": services, "fingerprint": fingerprint, "priority": priority})
    return deduplicate_l3(snapshots)


def deduplicate_l3(snapshots):
    by_id = {}
    conflicts = []
    for item in snapshots:
        prior = by_id.get(item["id"])
        if prior is None or item["priority"] < prior["priority"]:
            if prior and prior["fingerprint"] != item["fingerprint"]:
                conflicts.append(item["id"])
            by_id[item["id"]] = item
        elif prior["fingerprint"] != item["fingerprint"]:
            conflicts.append(item["id"])
    return {"snapshots": [by_id[k] for k in sorted(by_id)], "conflicts": sorted(set(conflicts))}


def scan_fixture(fixture_root):
    root = pathlib.Path(fixture_root).resolve()
    config = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    result = {"l2": None, "l3": {"snapshots": [], "conflicts": []}}
    if config.get("l2_root"):
        result["l2"] = validate_l2(root / config["l2_root"], root / config.get("data_target", "target-data"))
    result["l3"] = scan_l3_roots(root / p for p in config.get("l3_roots", []))
    return result
