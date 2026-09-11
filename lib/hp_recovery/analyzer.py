def analyze(runtime, components, profiles, backup, registered_release=None, usb_present=True):
    inventory = {x["component_id"]: x for x in components}
    findings = []
    for item in runtime.get("services", []):
        cid = item.get("component_id")
        if cid not in inventory:
            findings.append({"type": "UNINVENTORIED_SERVICE", "actual": item.get("name"), "action": "REPORT_ONLY"})
            continue
        expected = inventory[cid]
        if item.get("image") and item.get("image") != expected.get("image"):
            findings.append({"type": "IMAGE_MISMATCH", "component_id": cid, "expected": expected.get("image"), "actual": item.get("image"), "action": "REPORT_ONLY"})
        for mount in item.get("persistent_mounts", []):
            if mount not in backup.get("mapped_paths", []):
                findings.append({"type": "UNCOVERED_PERSISTENT_MOUNT", "component_id": cid, "actual": mount, "action": "REPORT_ONLY"})
    for cid, comp in inventory.items():
        profile = comp.get("recovery_profile") or {}
        path = profile.get("path") if isinstance(profile, dict) else profile
        if comp.get("status") == "ACTIVE" and path in (None, "UNKNOWN"):
            findings.append({"type": "MISSING_RECOVERY_PROFILE", "component_id": cid, "action": "REPORT_ONLY"})
        if comp.get("status") in ("DEPRECATED", "REMOVED"):
            findings.append({"type": "HISTORICAL_COMPONENT", "component_id": cid, "action": "REPORT_ONLY_NO_DELETE"})
        if path not in (None, "UNKNOWN", "NOT_REQUIRED") and path not in profiles:
            findings.append({"type": "PROFILE_REFERENCE_MISSING", "component_id": cid, "expected": path, "action": "REPORT_ONLY"})
        l3 = comp.get("backup_level3") or {}
        if isinstance(l3, dict) and l3.get("status") == "REQUIRED" and cid not in backup.get("l3_present", []):
            findings.append({"type": "L3_NOT_COVERED", "component_id": cid, "coverage": "NOT_COVERED", "action": "REPORT_ONLY"})
    for orphan in runtime.get("orphans", []):
        findings.append({"type": "ORPHAN_CANDIDATE", "actual": orphan, "action": "REPORT_ONLY_NO_DELETE"})
    release_status = evaluate_release(registered_release, runtime.get("production_version"))
    return {"findings": findings, "release_status": release_status, "usb_required": False, "usb_present": usb_present, "mutations": 0}


def evaluate_release(registered, production_version):
    if registered is None:
        return "OUTDATED_INCOMPLETE"
    if registered.get("production_version") == production_version:
        return "CURRENT"
    return registered.get("compatibility_if_outdated", "INCOMPATIBLE")
