import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from hp_recovery.analyzer import analyze
from hp_recovery.catalog import load_catalog
from hp_recovery.errors import ConfirmationError, StateError, ValidationError
from hp_recovery.executor import FixtureAdapter, execute
from hp_recovery.planner import build_plan, storage_preflight
from hp_recovery.profile_engine import paperless_source, require_l3_dump, validate_component_profile_documents, verify_analyzer_manifest
from hp_recovery.release import evaluate_registered_release
from hp_recovery.source_scan import scan_fixture
from hp_recovery.state import StateManager
from hp_recovery.util import atomic_json, sha256_file
from hp_recovery.validation import validate_catalog


GIB = 1024**3


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hp-recovery-fixture-")
        self.f = pathlib.Path(self.tmp.name)
        (self.f / "l2/server-backups/mirror/data").mkdir(parents=True)
        self.l3a = self.f / "l3a/2026-08-01_01-00"; self.l3a.mkdir(parents=True)
        for s in ("nextcloud","immich","paperless","jellyfin","adguard","npm","analyzer"):
            (self.l3a / s).mkdir(); (self.l3a / s / "fixture.txt").write_text(s+"\n")
        self.write_sources(l2=True, l3=["l3a"])
        atomic_json(self.f / "sizes.json", {"system": GIB, **{s: 1024 for s in ("nextcloud","immich","paperless","jellyfin","adguard","npm","analyzer","snowflake")}})
        self.catalog=load_catalog(ROOT)
        self.manager=StateManager(self.f/"state",self.f/"log")

    def tearDown(self): self.manager.close(); self.tmp.cleanup()
    def write_sources(self,l2=False,l3=()):
        atomic_json(self.f/"sources.json", {"l2_root":"l2" if l2 else None,"l3_roots":list(l3),"data_target":"target-data"})
    def scan(self): return scan_fixture(self.f)
    def plan(self,mode="COMBINED_L2_L3",scope="FULL_SERVER",service=None,scan=None,sizes=None):
        return build_plan(self.catalog,scan or self.scan(),mode=mode,scope=scope,service=service,target=self.f/"target-data",sizes=sizes or json.loads((self.f/"sizes.json").read_text()),development=True,usb_root=ROOT)
    def run_plan(self,p,**kw):
        state=self.manager.create(p); return execute(self.manager,state,FixtureAdapter(self.f,ROOT),confirmation=p["confirmation_phrase"],**kw)

    def test_T01_start_without_old_ssd_or_data(self):
        self.write_sources()
        result=subprocess.run([str(ROOT/"bin/hp-recovery"),"menu"],cwd=self.f,text=True,
                              input="6\n",capture_output=True,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("HP Server Recovery", result.stdout)
        self.assertIn("Recovery-Assistent beendet", result.stdout)
        self.assertEqual(self.plan("BASE_ONLY",scan=self.scan())["status"],"PLANNED")
    def test_T02_l2_only(self): self.assertEqual(self.run_plan(self.plan("L2_ONLY"))["status"],"COMPLETED")
    def test_T03_l3_only_partial(self):
        self.write_sources(l3=["l3a"]); p=self.plan("L3_ONLY",scan=self.scan()); self.assertEqual(p["service_outcomes_planned"]["immich"],"PARTIAL")
    def test_T04_combined_merge_plan(self):
        step=next(x for x in self.plan()["steps"] if x["id"]=="restore.nextcloud")
        self.assertIn("L3_CORE_EXTERNAL_AND_SQL_SAME_SNAPSHOT",step["rules"])
    def test_T05_three_l3_snapshots(self):
        for i in (2,3):
            p=self.f/f"l3a/2026-08-0{i}_01-00/nextcloud"; p.mkdir(parents=True); (p/"x").write_text(str(i))
        self.assertEqual(len(self.scan()["l3"]["snapshots"]),3)
    def test_T06_identical_l3_deduplicated(self):
        import shutil; shutil.copytree(self.l3a,self.f/"l3b/2026-08-01_01-00"); self.write_sources(True,["l3a","l3b"]); self.assertEqual(len(self.scan()["l3"]["snapshots"]),1)
    def test_T07_different_same_name_conflict(self):
        import shutil; shutil.copytree(self.l3a,self.f/"l3b/2026-08-01_01-00"); (self.f/"l3b/2026-08-01_01-00/nextcloud/x").write_text("different")
        self.write_sources(True,["l3a","l3b"]); self.assertTrue(self.scan()["l3"]["conflicts"])
    def test_T08_l3_deferred_resume_state(self):
        self.write_sources(); p=self.plan("L3_DEFERRED",scan=self.scan()); s=self.run_plan(p); self.assertEqual(s["status"],"WAITING_FOR_L3")
        self.write_sources(l3=["l3a"])
        resumed=self.plan("L3_ONLY",scan=self.scan()); resumed["run_id"]=p["run_id"]
        retained=[x for x in p["steps"] if x["id"] in s["completed_steps"]]
        resumed["steps"]=retained+[x for x in resumed["steps"] if x["id"] not in {"preflight.usb","preflight.storage","base.prepare","timers.hold"}]
        s["plan"]=resumed; self.manager.save(s)
        done=execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation=resumed["confirmation_phrase"])
        self.assertEqual(done["status"],"COMPLETED")
    def test_T09_system_space_stop(self):
        p=self.plan(); s=self.manager.create(p)
        with self.assertRaises(ValidationError): execute(self.manager,s,FixtureAdapter(self.f,ROOT,system_free=1,data_free=99*GIB),confirmation=p["confirmation_phrase"])
        self.assertFalse((self.f/"target-data").exists())
    def test_T10_wrong_phrase_no_target_change(self):
        p=self.plan(); s=self.manager.create(p)
        with self.assertRaises(ConfirmationError): execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation="WRONG")
        self.assertFalse((self.f/"target-data").exists())
    def test_T11_bad_analyzer_sha_isolated(self):
        a=self.f/"a"; a.mkdir(); (a/"x").write_text("x"); (self.f/"a.sha").write_text("0"*64+"  x\n"); self.assertFalse(verify_analyzer_manifest(a,self.f/"a.sha"))
        p=self.plan(); s=self.manager.create(p)
        done=execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation=p["confirmation_phrase"],fail_at="restore.analyzer")
        self.assertEqual(done["status"],"COMPLETED")
        self.assertEqual(done["service_outcomes"]["analyzer"],"FAILED_OPTIONAL")
        self.assertIn("service.snowflake",done["completed_steps"])
    def test_T12_invalid_paperless_sqlite_falls_back(self):
        p=self.f/"bad.db"; p.write_bytes(b"bad"); self.assertEqual(paperless_source("COMBINED_L2_L3",True,p),"L2_FALLBACK")
    def test_T13_missing_l3_dump_unavailable(self):
        with self.assertRaises(ValidationError): require_l3_dump(self.l3a,"immich")
    def test_T14_missing_snowflake_optional(self): self.assertEqual(self.plan()["service_outcomes_planned"]["snowflake"],"SKIPPED_OPTIONAL")
    def test_T15_copy_failure_report_and_resume(self):
        p=self.plan(); s=self.manager.create(p)
        with self.assertRaises(Exception): execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation=p["confirmation_phrase"],fail_at="restore.immich")
        failed=self.manager.load(p["run_id"])
        self.assertEqual(failed["status"],"FAILED")
        self.assertIn("restore.nextcloud",failed["completed_steps"])
        self.assertTrue((self.manager.path(p["run_id"]).parent/"report.json").is_file())
        done=execute(self.manager,failed,FixtureAdapter(self.f,ROOT),confirmation=p["confirmation_phrase"])
        self.assertEqual(done["status"],"COMPLETED")
        self.assertEqual(done["completed_steps"].count("restore.nextcloud"),1)
    def test_T16_import_failure_requires_new_confirmation(self):
        p=self.plan(); s=self.manager.create(p)
        with self.assertRaises(Exception): execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation=p["confirmation_phrase"],fail_at="restore.immich")
        failed=self.manager.load(p["run_id"])
        self.assertFalse((self.f/"target-data/immich").exists())
        with self.assertRaises(ConfirmationError):
            execute(self.manager,failed,FixtureAdapter(self.f,ROOT),confirmation="")
        self.assertFalse((self.f/"target-data/immich").exists())
    def test_T17_single_service_isolated(self):
        self.run_plan(self.plan(scope="SINGLE_SERVICE",service="adguard")); self.assertTrue((self.f/"target-data/adguard").exists()); self.assertFalse((self.f/"target-data/nextcloud").exists())
    def test_T18_combined_fixture_sequence_only(self):
        s=self.run_plan(self.plan()); self.assertEqual(s["status"],"COMPLETED")
    def test_T19_abort_secret_cleanup_report(self):
        p=self.plan(); s=self.manager.create(p); secret=self.f/"hp-recovery-secret-dummy"; secret.mkdir(); (secret/"DUMMY").write_text("DUMMY_TEST_ONLY_VALUE")
        s["plaintext_secret_dir"]=str(secret); self.manager.save(s); execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation=p["confirmation_phrase"],abort_at="restore.nextcloud")
        self.assertFalse(secret.exists()); self.assertTrue((self.manager.path(p["run_id"]).parent/"report.json").exists())
    def test_T20_completed_resume_no_replay(self):
        s=self.run_plan(self.plan());
        with self.assertRaises(StateError): execute(self.manager,s,FixtureAdapter(self.f,ROOT),confirmation=s["plan"]["confirmation_phrase"])
    def test_T21_data_space_stop(self):
        p=self.plan(); s=self.manager.create(p)
        with self.assertRaises(ValidationError): execute(self.manager,s,FixtureAdapter(self.f,ROOT,system_free=99*GIB,data_free=1),confirmation=p["confirmation_phrase"])
        self.assertFalse((self.f/"target-data").exists())
    def test_T22_both_space_pass(self):
        p=self.plan(); s=self.run_plan(p)
        self.assertTrue(all(x["status"]=="PASS" for x in s["storage_preflight"].values()))
    def test_T23_single_service_less_space(self):
        full=self.plan()["estimates"]["data_required"]; single=self.plan(scope="SINGLE_SERVICE",service="adguard")["estimates"]["data_required"]; self.assertLess(single,full)
    def test_T24_safety_buffer_stop(self):
        p=self.plan(); s=self.manager.create(p)
        with self.assertRaises(ValidationError): execute(self.manager,s,FixtureAdapter(self.f,ROOT,system_free=99*GIB,data_free=10*GIB,safety_copy_required=20*GIB),confirmation=p["confirmation_phrase"])
        self.assertFalse((self.f/"target-data").exists())
    def test_T25_unknown_required_space_stops(self):
        with self.assertRaises(ValidationError): self.plan(sizes={"system":GIB})
    def test_T26_uninventoried_container(self): self.assertEqual(analyze({"services":[{"name":"new"}]},[],{},{} )["findings"][0]["type"],"UNINVENTORIED_SERVICE")
    def test_T27_uncovered_persistent_mount(self):
        c=[{"component_id":"x","status":"ACTIVE","image":"i","recovery_profile":{"path":"p"}}]; f=analyze({"services":[{"component_id":"x","image":"i","persistent_mounts":["/x"]}]},c,{"p":{}},{"mapped_paths":[]})["findings"]; self.assertTrue(any(x["type"]=="UNCOVERED_PERSISTENT_MOUNT" for x in f))
    def test_T28_missing_recovery_profile(self):
        c=[{"component_id":"x","status":"ACTIVE","recovery_profile":{"path":"UNKNOWN"}}]; self.assertTrue(any(x["type"]=="MISSING_RECOVERY_PROFILE" for x in analyze({"services":[]},c,{}, {})["findings"]))
    def test_T29_image_mismatch_records_both(self):
        c=[{"component_id":"x","status":"ACTIVE","image":"expected","recovery_profile":{"path":"p"}}]; f=analyze({"services":[{"component_id":"x","image":"actual"}]},c,{"p":{}}, {})["findings"][0]; self.assertEqual((f["expected"],f["actual"]),("expected","actual"))
    def test_T30_deprecated_report_no_delete(self):
        f=analyze({"services":[]},[{"component_id":"x","status":"DEPRECATED"}],{}, {})["findings"][0]; self.assertEqual(f["action"],"REPORT_ONLY_NO_DELETE")
    def test_T31_l3_profile_without_backup(self):
        c=[{"component_id":"x","status":"ACTIVE","recovery_profile":{"path":"p"},"backup_level3":{"status":"REQUIRED"}}]; self.assertTrue(any(x["type"]=="L3_NOT_COVERED" for x in analyze({"services":[]},c,{"p":{}},{})["findings"]))
    def test_T32_component_profile_conflict_fails(self):
        with self.assertRaises(ValidationError): validate_component_profile_documents([{"component_id":"x","recovery_profile":{"path":"missing"}}],{})
    def test_T33_outdated_release_classification(self):
        p=self.f/"release.json"; atomic_json(p,{"production_version":"1","compatibility_if_outdated":"OUTDATED_COMPATIBLE"}); self.assertEqual(evaluate_registered_release(p,"2")["status"],"OUTDATED_COMPATIBLE")
    def test_T34_no_usb_uses_registered_status(self):
        p=self.f/"release.json"; atomic_json(p,{"production_version":"1","compatibility_if_outdated":"OUTDATED_INCOMPLETE"})
        self.assertFalse((self.f/"recovery-usb").exists())
        result=evaluate_registered_release(p,"2")
        self.assertEqual(result["status"],"OUTDATED_INCOMPLETE")
        self.assertFalse(result["usb_required"])
    def test_T35_orphan_report_only(self):
        f=analyze({"services":[],"orphans":["unit.old"]},[],{}, {})["findings"][0]; self.assertEqual(f["action"],"REPORT_ONLY_NO_DELETE")


if __name__ == "__main__": unittest.main(verbosity=2)
