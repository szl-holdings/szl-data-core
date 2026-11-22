"""szl-data-core self-test: proves the layer works on-device, fail closed, receipts verified."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datacore import DataCore

fails = 0
def check(name, cond):
    global fails
    if not cond: fails += 1
    print(("PASS " if cond else "FAIL ") + name)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest.db")
if os.path.exists(path): os.remove(path)
dc = DataCore(path)

r1 = dc.upsert_entity("hf_repo", "SZLHOLDINGS/szl-kernels", {"license": "apache-2.0", "card": True})
v1 = dc.verify_entity("hf_repo", "SZLHOLDINGS/szl-kernels")
check("T1 upsert+verify", v1["verified"] is True)

v2 = dc.verify_entity("hf_repo", "SZLHOLDINGS/does-not-exist")
check("T2 fail-closed missing", v2["verified"] is False and v2["reason"] == "MISSING")

r3 = dc.upsert_entity("hf_repo", "SZLHOLDINGS/szl-kernels", {"license": "apache-2.0", "card": True, "topics": 2})
v3 = dc.verify_entity("hf_repo", "SZLHOLDINGS/szl-kernels")
check("T3 idempotent update", v3["verified"] is True and v3["payload_sha256"] != r1["payload_sha256"])

snap = dc.snapshot_json()
v4 = dc.verify_snapshot(snap)
check("T4 snapshot verified", v4["verified"] is True and v4["entities"] >= 1)

tampered = json.loads(json.dumps(snap))
tampered["entities"][0]["attrs"]["license"] = "tampered"
v5 = dc.verify_snapshot(tampered)
check("T5 tamper detected", v5["verified"] is False)

st = dc.receipt_stats()
check("T6 receipts counted", st["receipts"] == 2 and st["verified"] >= 1)

print("SELFTEST_DONE fails=" + str(fails))
sys.exit(1 if fails else 0)
