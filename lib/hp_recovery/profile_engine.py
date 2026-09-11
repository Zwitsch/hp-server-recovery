import hashlib
import pathlib
import sqlite3

from .errors import ValidationError
from .util import sha256_file


def sqlite_quick_check(path):
    p = pathlib.Path(path)
    if p.is_symlink() or not p.is_file(): return False
    try:
        with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as db:
            return db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    except sqlite3.Error:
        return False


def paperless_source(mode, l2_available, l3_db):
    valid = bool(l3_db and sqlite_quick_check(l3_db))
    if mode == "COMBINED_L2_L3":
        if valid: return "L3"
        if l2_available: return "L2_FALLBACK"
    if mode == "L3_ONLY" and valid: return "L3"
    return "UNAVAILABLE"


def verify_analyzer_manifest(root, manifest):
    root = pathlib.Path(root).resolve(); path = pathlib.Path(manifest)
    for raw in path.read_text(encoding="utf-8").splitlines():
        digest, rel = raw.split("  ", 1)
        target = (root / rel).resolve(strict=True)
        if root not in target.parents or sha256_file(target) != digest:
            return False
    return True


def require_l3_dump(snapshot, service):
    candidates = sorted((pathlib.Path(snapshot) / service / "db").glob("*.sql"))
    if len(candidates) != 1 or candidates[0].stat().st_size == 0:
        raise ValidationError(f"required L3 dump missing: {service}")
    return candidates[0]


def validate_component_profile_documents(components, profiles):
    known = {x["component_id"] for x in components}
    errors=[]
    for x in components:
        p=x.get("recovery_profile")
        if isinstance(p,dict): p=p.get("path")
        if p not in (None,"UNKNOWN","NOT_REQUIRED") and p not in profiles:
            errors.append(f"missing:{x['component_id']}:{p}")
    if len(known) != len(components): errors.append("duplicate-component-id")
    if errors: raise ValidationError(";".join(errors))
    return True
