"""szl-data-core v0: pure-stdlib estate data layer (Snowflake replacement, owner-directed 2026-11-22).
Doctrine: GitHub is the source of truth; every stored row is receipt-verified (readback-or-it-didnt-happen);
MEASURED != PASS; fail closed; no third-party services required.
"""
import hashlib, json, os, sqlite3, time

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def sha256_str(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

class DataCore:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self._schema()

    def _schema(self):
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS entities(kind TEXT NOT NULL, id TEXT NOT NULL, attrs TEXT, PRIMARY KEY(kind,id));"
            "CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY, subject_kind TEXT, subject_id TEXT, event TEXT, payload_sha256 TEXT, verified INTEGER NOT NULL DEFAULT 0, created_at TEXT);"
            "CREATE INDEX IF NOT EXISTS ix_receipts_subject ON receipts(subject_kind, subject_id);")
        self.db.commit()

    def upsert_entity(self, kind, ident, attrs):
        payload = json.dumps({"kind": kind, "id": ident, "attrs": attrs}, sort_keys=True)
        psha = sha256_str(payload)
        self.db.execute("INSERT INTO entities(kind,id,attrs) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET attrs=excluded.attrs", (kind, ident, payload))
        cur = self.db.execute("INSERT INTO receipts(subject_kind,subject_id,event,payload_sha256,verified,created_at) VALUES(?,?,?,?,0,?)", (kind, ident, "upsert_entity", psha, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        self.db.commit()
        return {"rid": cur.lastrowid, "payload_sha256": psha}

    def verify_entity(self, kind, ident):
        row = self.db.execute("SELECT attrs FROM entities WHERE kind=? AND id=?", (kind, ident)).fetchone()
        if row is None:
            return {"verified": False, "reason": "MISSING"}
        psha = sha256_str(row[0])
        ok = (json.loads(row[0]).get("id") == ident)
        self.db.execute("UPDATE receipts SET verified=1 WHERE subject_kind=? AND subject_id=? AND event='upsert_entity' AND payload_sha256=?", (kind, ident, psha))
        self.db.commit()
        return {"verified": ok, "payload_sha256": psha}

    def snapshot_json(self, kind=None):
        if kind:
            rows = self.db.execute("SELECT kind,id,attrs FROM entities WHERE kind=? ORDER BY id", (kind,)).fetchall()
        else:
            rows = self.db.execute("SELECT kind,id,attrs FROM entities ORDER BY kind,id").fetchall()
        snap = {"schema": "szl.datacore.snapshot/v1", "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "entities": [json.loads(r[2]) for r in rows]}
        snap["snapshot_sha256"] = sha256_str(json.dumps(snap["entities"], sort_keys=True))
        return snap

    def verify_snapshot(self, snap):
        claimed = snap.get("snapshot_sha256")
        actual = sha256_str(json.dumps(snap["entities"], sort_keys=True))
        if claimed != actual:
            return {"verified": False, "reason": "SNAPSHOT_SHA_MISMATCH", "claimed": claimed, "actual": actual}
        for e in snap["entities"]:
            row = self.db.execute("SELECT attrs FROM entities WHERE kind=? AND id=?", (e["kind"], e["id"])).fetchone()
            if row is None or sha256_str(row[0]) != sha256_str(json.dumps(e, sort_keys=True)):
                return {"verified": False, "reason": "ENTITY_MISMATCH", "entity": e.get("id")}
        return {"verified": True, "entities": len(snap["entities"])}

    def receipt_stats(self):
        total = self.db.execute("SELECT COUNT(*), SUM(verified) FROM receipts").fetchone()
        return {"receipts": total[0] or 0, "verified": total[1] or 0}
