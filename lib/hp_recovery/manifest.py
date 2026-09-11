import pathlib

from .errors import ValidationError
from .util import ensure_regular, sha256_file


def parse_sha256_manifest(path):
    entries = []
    for number, raw in enumerate(ensure_regular(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        if len(raw) < 67 or raw[64:66] not in ("  ", " *"):
            raise ValidationError(f"invalid manifest line {number}")
        digest, rel = raw[:64], raw[66:]
        if any(c not in "0123456789abcdef" for c in digest):
            raise ValidationError(f"invalid digest line {number}")
        p = pathlib.PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or rel in ("", "."):
            raise ValidationError(f"unsafe manifest path line {number}")
        entries.append((digest, rel))
    if [x[1] for x in entries] != sorted(x[1] for x in entries):
        raise ValidationError("manifest not LC_ALL=C path sorted")
    if len({x[1] for x in entries}) != len(entries):
        raise ValidationError("duplicate manifest path")
    return entries


def verify_manifest(root, manifest_path, *, allow_manifest_self=False):
    root = pathlib.Path(root).resolve()
    checked = []
    for digest, rel in parse_sha256_manifest(manifest_path):
        target = (root / rel).resolve(strict=True)
        if root not in target.parents:
            raise ValidationError(f"manifest escape: {rel}")
        ensure_regular(target)
        actual = sha256_file(target)
        if actual != digest:
            raise ValidationError(f"checksum mismatch: {rel}")
        checked.append(rel)
    return checked
