# szl-data-core

Sovereign estate data layer for the SZL Holdings / a11oy governed-AI estate.
Pure-stdlib Python on SQLite (WAL): no third-party services, no external dependencies.

Owner directive 2026-11-22: build our own data core to replace the Snowflake
dependency (solo build, green light).

## Doctrine
- GitHub is the source of truth; Hugging Face mirrors.
- Every stored row is receipt-verified: readback-or-it-didn't-happen.
- MEASURED != PASS; fail closed.
- No secrets in code; no third-party runtime.

## What it provides
- DataCore(path): sqlite WAL-backed store with entities + receipts tables.
- upsert_entity(kind, id, attrs) -> receipt with payload_sha256
- verify_entity(kind, id) -> readback verification (fail-closed)
- snapshot_json() -> canonical export with snapshot_sha256
- verify_snapshot(snap) -> tamper detection (SNAPSHOT_SHA_MISMATCH / ENTITY_MISMATCH)
- receipt_stats() -> receipts/verified counts

## Self-test receipt
Executed on device betterwithage, 2026-11-22T23:40Z:
PASS T1 upsert+verify / PASS T2 fail-closed missing / PASS T3 idempotent update /
PASS T4 snapshot verified / PASS T5 tamper detected / PASS T6 receipts counted /
SELFTEST_DONE fails=0

Run it: python -u -B selftest.py

## License
Apache-2.0 (see LICENSE).
