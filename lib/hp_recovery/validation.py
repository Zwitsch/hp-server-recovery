import json
import pathlib
import re

from .catalog import component_map, load_catalog, profile_documents
from .errors import ValidationError
from .manifest import verify_manifest
from .util import ensure_regular


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _walk_component_refs(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "component_id" and isinstance(item, str):
                found.add(item)
            elif key == "component_ids" and isinstance(item, list):
                found.update(x for x in item if isinstance(x, str))
            _walk_component_refs(item, found)
    elif isinstance(value, list):
        for item in value:
            _walk_component_refs(item, found)


def validate_catalog(usb_root):
    catalog = load_catalog(usb_root)
    components = component_map(catalog)
    if len(components) != len(catalog["documents"]["inventory/components.yaml"]["components"]):
        raise ValidationError("duplicate component_id")
    for component_id, component in components.items():
        for dep in component.get("dependencies") or []:
            ref = dep.get("component_id") if isinstance(dep, dict) else dep
            if ref and ref not in components:
                raise ValidationError(f"unknown dependency: {component_id}->{ref}")
        profile = component.get("recovery_profile") or {}
        path = profile.get("path") if isinstance(profile, dict) else profile
        if path not in (None, "UNKNOWN", "NOT_REQUIRED") and path not in catalog["documents"]:
            raise ValidationError(f"missing profile: {component_id}:{path}")
    refs = set()
    for profile in profile_documents(catalog).values():
        _walk_component_refs(profile, refs)
    unknown = sorted(refs - set(components))
    if unknown:
        raise ValidationError(f"unknown profile component references: {unknown}")
    return {"components": len(components), "profile_references": len(refs), "status": "PASS"}


def validate_image_lock(usb_root):
    path = pathlib.Path(usb_root) / "payload/docker/image-lock.json"
    data = json.loads(ensure_regular(path).read_text(encoding="utf-8"))
    contracts = data.get("service_image_contracts")
    if not isinstance(contracts, list) or not contracts:
        raise ValidationError("service image contracts missing")
    seen = set()
    for item in contracts:
        cid = item.get("contract_id")
        if not cid or cid in seen:
            raise ValidationError("duplicate or missing service image contract")
        seen.add(cid)
        compose = item.get("compose_image_or_build") or {}
        expression = compose.get("resolved_image_from_sanitized_env") or compose.get("image_expression")
        build = compose.get("build_context")
        immutable = item.get("immutable_restore_reference")
        if build:
            if not isinstance(immutable, str) or not immutable.startswith("offline-image-archive:"):
                raise ValidationError(f"local build lacks portable archive: {cid}")
        else:
            if not isinstance(expression, str) or expression.endswith(":latest"):
                raise ValidationError(f"mutable effective compose reference: {cid}")
            if not isinstance(immutable, str) or "@sha256:" not in immutable:
                raise ValidationError(f"immutable restore reference missing: {cid}")
            if not DIGEST_RE.fullmatch(immutable.rsplit("@", 1)[1]):
                raise ValidationError(f"immutable restore digest invalid: {cid}")
        offline = item.get("offline_image_archive") or {}
        if offline.get("present") is not True or offline.get("status") != "PASS_VERIFIED_P3_07":
            raise ValidationError(f"offline archive not verified: {cid}")
        digest = offline.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValidationError(f"offline archive checksum invalid: {cid}")
    return {"status": "PASS", "service_contracts": len(contracts)}


REPOSITORY_METADATA = {".gitignore", "README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md"}
REPOSITORY_METADATA_DIRS = {".git", ".github", "docs"}


def _is_repository_metadata(relative_path):
    path = pathlib.PurePosixPath(relative_path)
    return relative_path in REPOSITORY_METADATA or (path.parts and path.parts[0] in REPOSITORY_METADATA_DIRS)


def validate_usb(usb_root):
    root = pathlib.Path(usb_root).resolve()
    manifest = root / "manifests/usb-files.sha256"
    checked = verify_manifest(root, manifest)
    actual = sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                    if p.is_file() and not p.is_symlink() and p != manifest
                    and "__pycache__" not in p.parts and p.suffix != ".pyc"
                    and not _is_repository_metadata(p.relative_to(root).as_posix()))
    if checked != actual:
        raise ValidationError("USB manifest coverage mismatch")
    catalog_result = validate_catalog(root)
    image_result = validate_image_lock(root)
    filen = root / "payload/apt/keys/filen.gpg"
    if not filen.exists() or filen.stat().st_size != 0:
        raise ValidationError("Filen keyring contract changed")
    return {"status": "PASS", "manifest_files": len(checked), "catalog": catalog_result, "images": image_result, "filen_keyring": "EMPTY_REJECTED_AS_KEY"}
