import pathlib

from .analyzer import evaluate_release
from .errors import ValidationError
from .util import read_json


def evaluate_registered_release(path, production_version):
    p = pathlib.Path(path)
    if not p.is_file() or p.is_symlink():
        raise ValidationError("registered release status missing")
    data = read_json(p)
    return {"status": evaluate_release(data, production_version), "source": "LOCAL_REGISTERED_STATUS", "usb_required": False}
