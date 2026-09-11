import pathlib
import uuid

from .catalog import component_map
from .errors import ValidationError
from .util import ensure_safe_target, utc_now


MODES = {"COMBINED_L2_L3", "L2_ONLY", "L3_ONLY", "L3_DEFERRED", "BASE_ONLY"}
SCOPES = {"FULL_SERVER", "SINGLE_SERVICE"}
SERVICE_ORDER = ["nextcloud", "immich", "paperless", "jellyfin", "adguard", "npm", "analyzer", "snowflake"]
REALTEST_SERVICE_ORDER = ["nextcloud", "immich", "paperless", "jellyfin", "adguard", "npm", "analyzer", "monatsausgaben", "snowflake"]
SERVICE_RULES = {
    "nextcloud": {"combined": ["L2_BASE_WITH_RAW_DB_EXCLUDED", "L3_CORE_EXTERNAL_AND_SQL_SAME_SNAPSHOT", "NEW_EMPTY_DB_IMPORT"], "l2_only": ["ISOLATED_RAW_DB_EXPORT", "NEW_EMPTY_DB_IMPORT"], "l3_only": ["L3_CORE_EXTERNAL_AND_SQL_SAME_SNAPSHOT"]},
    "immich": {"combined": ["L2_MEDIA", "L3_SQL_NEW_EMPTY_DB", "EXCLUDE_L2_RAW_DB"], "l2_only": ["L2_MEDIA", "ISOLATED_RAW_DB_EXPORT", "NEW_EMPTY_DB_IMPORT"], "l3_only": ["L3_SQL", "PARTIAL_NO_MEDIA"]},
    "paperless": {"combined": ["L2_BASE", "L3_DATA_MEDIA_ONLY_IF_SQLITE_QUICK_CHECK"], "l2_only": ["L2_ONLY"], "l3_only": ["L3_DATA_MEDIA_SQLITE_QUICK_CHECK"]},
    "jellyfin": {"combined": ["L2_MEDIA", "L3_CONFIG", "GENERATE_CACHE_TRANSCODE"], "l2_only": ["L2_MEDIA_AND_CONFIG"], "l3_only": ["L3_CONFIG", "CONFIG_ONLY_NO_MEDIA"]},
    "adguard": {"combined": ["L3_CONF_AND_WORK_SAME_SNAPSHOT"], "l2_only": ["L2_COMPLETE"], "l3_only": ["L3_CONF_AND_WORK"]},
    "npm": {"combined": ["L3_DATA_AND_LETSENCRYPT_IF_SQLITE_VALID"], "l2_only": ["L2_COMPLETE"], "l3_only": ["L3_DATA_AND_LETSENCRYPT_SAME_SNAPSHOT"]},
    "analyzer": {"combined": ["L3_ARCHIVE_ONLY_IF_SHA256_VALID"], "l2_only": ["L2_IF_PRESENT"], "l3_only": ["L3_ARCHIVE_ONLY_IF_SHA256_VALID"]},
    "monatsausgaben": {"combined": ["PROFILE_BOUND_SQLITE_AND_APPLICATION_DATA"], "l2_only": ["L2_PROFILE_BOUND_SQLITE_AND_APPLICATION_DATA"], "l3_only": ["L3_PROFILE_BOUND_SQLITE_AND_APPLICATION_DATA"]},
    "snowflake": {"combined": ["OPTIONAL"], "l2_only": ["OPTIONAL"], "l3_only": ["OPTIONAL"]},
    "storage": {"combined": ["SENTINEL_BOUND_STORAGE_LAYOUT"], "l2_only": ["SENTINEL_BOUND_STORAGE_LAYOUT"], "l3_only": ["SENTINEL_BOUND_STORAGE_LAYOUT"]},
    "urlaubsplaner": {"combined": ["VERIFIED_APP_BACKUP_AND_RELEASE_TUPLE"], "l2_only": ["VERIFIED_APP_BACKUP"], "l3_only": ["VERIFIED_APP_BACKUP_AND_RELEASE_TUPLE"]},
    "devicewatchdog": {"combined": ["VERIFIED_CONFIG_EXPORT_AND_RELEASE_TUPLE"], "l2_only": ["VERIFIED_CONFIG_EXPORT"], "l3_only": ["VERIFIED_CONFIG_EXPORT_AND_RELEASE_TUPLE"]},
}


def _source_requirements(mode, scan):
    has_l2 = bool(scan.get("l2"))
    has_l3 = bool(scan.get("l3", {}).get("snapshots"))
    conflicts = scan.get("l3", {}).get("conflicts", [])
    if conflicts and mode in {"COMBINED_L2_L3", "L3_ONLY"}:
        raise ValidationError(f"L3 snapshot conflict: {conflicts}")
    if mode == "COMBINED_L2_L3" and not (has_l2 and has_l3):
        raise ValidationError("Combined requires L2 and L3")
    if mode == "L2_ONLY" and not has_l2:
        raise ValidationError("L2_ONLY requires L2")
    if mode == "L3_ONLY" and not has_l3:
        raise ValidationError("L3_ONLY requires L3")
    if mode == "L3_DEFERRED" and has_l3:
        raise ValidationError("L3_DEFERRED requires absent L3")


def _selected_services(scope, service, service_order):
    if scope == "FULL_SERVER":
        return service_order.copy()
    if service not in service_order:
        raise ValidationError("invalid single service")
    return [service]


def _classify(service, mode):
    if service == "snowflake":
        return "SKIPPED_OPTIONAL"
    if mode == "BASE_ONLY" or mode == "L3_DEFERRED":
        return "SKIPPED"
    if mode == "L3_ONLY" and service == "immich":
        return "PARTIAL"
    if mode == "L3_ONLY" and service == "jellyfin":
        return "CONFIG_ONLY"
    return "FULL"


def _estimate(sizes, services, mode, scope):
    sizes = sizes or {}
    system = sizes.get("system")
    if system is None:
        system = 6 * 1024**3
    data = 0
    unknown = []
    if mode not in {"BASE_ONLY", "L3_DEFERRED"}:
        for service in services:
            value = sizes.get(service)
            if value is None:
                unknown.append(service)
            else:
                data += int(value)
    return {
        "system_required": system,
        "system_reserve": max(system // 10, 5 * 1024**3),
        "data_required": data if not unknown else None,
        "data_reserve": max(data // 10, 10 * 1024**3) if not unknown else None,
        "unknown_services": unknown,
        "scope": scope,
    }


def build_plan(catalog, scan, *, mode, scope, target, service=None, snapshot_id=None, sizes=None, development=False, usb_root=None,
               runtime_mode="FIXTURE", system_target=None, realtest_binding=None, service_order=None):
    if mode not in MODES or scope not in SCOPES:
        raise ValidationError("invalid mode or scope")
    _source_requirements(mode, scan)
    effective_service_order = service_order or (REALTEST_SERVICE_ORDER if runtime_mode == "ISOLATED_REALTEST" else SERVICE_ORDER)
    services = _selected_services(scope, service, effective_service_order)
    source_roots = []
    if scan.get("l2"):
        source_roots.append(scan["l2"]["root"])
    source_roots.extend(x["path"] for x in scan.get("l3", {}).get("snapshots", []))
    safe_target = ensure_safe_target(target, usb_root=usb_root, source_roots=source_roots)
    snapshots = scan.get("l3", {}).get("snapshots", [])
    selected_snapshot = None
    if mode in {"COMBINED_L2_L3", "L3_ONLY"}:
        candidates = [x for x in snapshots if snapshot_id in (None, x["id"])]
        if len(candidates) != 1:
            raise ValidationError("exactly one L3 snapshot must be selected")
        selected_snapshot = candidates[0]
    components = component_map(catalog)
    blockers = []
    for cid, comp in components.items():
        if comp.get("status") == "ACTIVE":
            profile = comp.get("recovery_profile") or {}
            p = profile.get("path") if isinstance(profile, dict) else profile
            if p == "UNKNOWN":
                blockers.append(f"UNKNOWN_PROFILE:{cid}")
            if comp.get("integration_state") == "PENDING_INTEGRATION":
                blockers.append(f"PENDING_INTEGRATION:{cid}")
    if blockers and not development:
        raise ValidationError("production plan blocked by inventory integration state")
    estimates = _estimate(sizes, services, mode, scope)
    if estimates["unknown_services"] and mode not in {"BASE_ONLY", "L3_DEFERRED"}:
        raise ValidationError(f"storage requirement unknown: {estimates['unknown_services']}")
    steps = [
        {"id": "preflight.usb", "op": "VALIDATE_USB", "repeatable": True, "destructive": False},
        {"id": "preflight.storage", "op": "CHECK_STORAGE", "repeatable": True, "destructive": False},
        {"id": "timers.hold", "op": "HOLD_TIMERS", "repeatable": True, "destructive": False},
        {"id": "base.prepare", "op": "PREPARE_BASE", "repeatable": False, "destructive": True},
    ]
    if mode == "L3_DEFERRED":
        steps.append({"id": "wait.l3", "op": "WAIT_FOR_L3", "repeatable": True, "destructive": False})
    elif mode != "BASE_ONLY":
        for name in services:
            if name == "snowflake":
                steps.append({"id": "service.snowflake", "op": "OPTIONAL_SERVICE", "service": name, "repeatable": True, "destructive": False})
            else:
                rule_key = {"COMBINED_L2_L3": "combined", "L2_ONLY": "l2_only", "L3_ONLY": "l3_only"}[mode]
                steps.append({"id": f"restore.{name}", "op": "RESTORE_SERVICE", "service": name,
                              "rules": SERVICE_RULES[name][rule_key], "l3_snapshot_id": selected_snapshot["id"] if selected_snapshot else None,
                              "repeatable": False, "destructive": True,
                              "failure_policy": "CONTINUE_PARTIAL" if name == "analyzer" else "STOP"})
                steps.append({"id": f"test.{name}", "op": "TEST_SERVICE", "service": name, "repeatable": True, "destructive": False})
        steps.append({"id": "timers.enable", "op": "ENABLE_PROFILE_TIMERS", "repeatable": False, "destructive": True})
    steps.append({"id": "report.final", "op": "REPORT", "repeatable": True, "destructive": False})
    confirmation = f"RESTORE {service}" if scope == "SINGLE_SERVICE" else "RESTORE /mnt/data"
    if runtime_mode == "ISOLATED_REALTEST":
        confirmation = f"REALTEST RESTORE {service}" if scope == "SINGLE_SERVICE" else "REALTEST RESTORE HP-EVIDENCE-INTAKE"
    plan = {
        "schema_version": "1.0", "run_id": f"run-{uuid.uuid4().hex[:16]}", "created_at": utc_now(),
        "mode": mode, "scope": scope, "service": service, "services": services,
        "target": str(safe_target), "system_target": str(system_target) if system_target else None,
        "runtime_mode": runtime_mode, "l2": scan.get("l2"), "l3": selected_snapshot,
        "estimates": estimates, "development_inventory_blockers": blockers,
        "service_outcomes_planned": {x: _classify(x, mode) for x in services},
        "confirmation_phrase": confirmation,
        "steps": steps, "status": "PLANNED", "release_allowed": False, "override_allowed": False,
    }
    if runtime_mode == "ISOLATED_REALTEST":
        if not realtest_binding:
            raise ValidationError("realtest identity binding missing")
        plan["realtest_binding"] = realtest_binding
    return plan


def storage_preflight(plan, *, system_free, data_free, safety_copy_required=0):
    e = plan["estimates"]
    if e["system_required"] is None or e["data_required"] is None:
        raise ValidationError("required storage unknown")
    system_need = e["system_required"] + e["system_reserve"]
    data_need = e["data_required"] + e["data_reserve"] + safety_copy_required
    return {
        "system": {"free": system_free, "required_with_reserve": system_need, "status": "PASS" if system_free >= system_need else "STOP"},
        "data": {"free": data_free, "required_with_reserve": data_need, "status": "PASS" if data_free >= data_need else "STOP"},
    }
