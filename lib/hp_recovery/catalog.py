import pathlib

from .errors import ValidationError
from .util import read_json, sha256_file


def load_catalog(usb_root):
    root = pathlib.Path(usb_root).resolve()
    catalog = read_json(root / "runtime-data/catalog.json")
    for item in catalog.get("sources", []):
        path = root / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise ValidationError(f"YAML/runtime binding mismatch: {item['path']}")
    return catalog


def component_map(catalog):
    data = catalog["documents"]["inventory/components.yaml"]
    return {x["component_id"]: x for x in data["components"]}


def profile_documents(catalog):
    return {k: v for k, v in catalog["documents"].items() if k.startswith("profiles/")}
