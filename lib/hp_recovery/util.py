import hashlib
import json
import os
import pathlib
import stat
import tempfile
from datetime import datetime, timezone

from .errors import SafetyError


PROTECTED_TARGETS = {"/", "/home", "/mnt"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(chunk)
            if not block:
                return h.hexdigest()
            h.update(block)


def canonical(path, strict=True):
    return pathlib.Path(path).resolve(strict=strict)


def ensure_regular(path):
    p = pathlib.Path(path)
    if p.is_symlink() or not p.is_file():
        raise SafetyError(f"not a regular file: {p}")
    return p


def ensure_safe_target(path, *, usb_root=None, source_roots=()):
    raw = os.path.abspath(os.fspath(path))
    if raw in PROTECTED_TARGETS or raw == "":
        raise SafetyError(f"protected target: {raw}")
    p = pathlib.Path(raw)
    for item in [p, *p.parents]:
        if item.exists() and item.is_symlink():
            raise SafetyError(f"symlink target component: {item}")
    resolved = p.resolve(strict=False)
    roots = [pathlib.Path(x).resolve(strict=False) for x in source_roots]
    if usb_root is not None:
        roots.append(pathlib.Path(usb_root).resolve(strict=False))
    for root in roots:
        if resolved == root or root in resolved.parents or resolved in root.parents:
            raise SafetyError(f"source/target overlap: {resolved} and {root}")
    return resolved


def atomic_json(path, value, mode=0o600):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def tree_fingerprint(root):
    root = pathlib.Path(root)
    h = hashlib.sha256()
    for p in sorted((x for x in root.rglob("*") if x.is_file()), key=lambda x: x.as_posix()):
        rel = p.relative_to(root).as_posix().encode()
        h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        h.update(bytes.fromhex(sha256_file(p)))
    return h.hexdigest()


def metadata_tree_fingerprint(root):
    """Fingerprint names, contents, ownership, modes and nanosecond mtimes."""
    root = pathlib.Path(root)
    h = hashlib.sha256()
    for p in sorted(root.rglob("*"), key=lambda x: os.fsencode(x.relative_to(root).as_posix())):
        if p.is_symlink():
            raise SafetyError(f"source symlink rejected: {p}")
        st = p.stat()
        rel = os.fsencode(p.relative_to(root).as_posix())
        kind = b"d" if p.is_dir() else b"f" if p.is_file() else b"x"
        if kind == b"x":
            raise SafetyError(f"special source member rejected: {p}")
        h.update(kind); h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        for value in (stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid, st.st_mtime_ns, st.st_size):
            h.update(int(value).to_bytes(16, "big", signed=False))
        if p.is_file():
            h.update(bytes.fromhex(sha256_file(p)))
    return h.hexdigest()
