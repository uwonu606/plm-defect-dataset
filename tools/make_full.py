import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "work" / "candidates.jsonl"
PILOT_DIR = ROOT / "work" / "pilot"
FULL_DIR = ROOT / "work" / "full"
MAGMA_SOURCE = "magma/magma"
MAGMA_CAP = 2000
BATCH_SIZE = 50
INTERLEAVE_STRIDE = 7


def source_of(record):
    return record["source_id"].rsplit("#", 1)[0]


def evenly(rows, count):
    if count >= len(rows):
        return rows
    step = len(rows) / count
    return [rows[int(i * step)] for i in range(count)]


def interleaved(rows):
    return [row for offset in range(INTERLEAVE_STRIDE) for row in rows[offset::INTERLEAVE_STRIDE]]


def write_batches(rows, prefix):
    for index in range(0, len(rows), BATCH_SIZE):
        path = FULL_DIR / f"batch-{prefix}-{index // BATCH_SIZE:03d}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows[index:index + BATCH_SIZE]), encoding="utf-8")
    return (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE


def main():
    pilot_ids = {json.loads(line)["source_id"] for path in PILOT_DIR.glob("batch-*.jsonl") for line in path.open(encoding="utf-8")}
    rows = [json.loads(line) for line in CANDIDATES.open(encoding="utf-8")]
    ran_core = [r for r in rows if r["tier"] == "ran-core"]
    magma_all = [r for r in ran_core if source_of(r) == MAGMA_SOURCE]
    pilot_magma = sum(1 for r in magma_all if r["source_id"] in pilot_ids)
    magma_kept = evenly([r for r in magma_all if r["source_id"] not in pilot_ids], MAGMA_CAP - pilot_magma)
    ran_core_new = [r for r in ran_core if source_of(r) != MAGMA_SOURCE and r["source_id"] not in pilot_ids] + magma_kept
    adjacent_new = interleaved([r for r in rows if r["tier"] == "adjacent-network" and r["source_id"] not in pilot_ids])

    FULL_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "ran_core_candidates": len(ran_core_new),
        "ran_core_batches": write_batches(ran_core_new, "r"),
        "adjacent_candidates": len(adjacent_new),
        "adjacent_batches": write_batches(adjacent_new, "a"),
        "magma_dropped_by_cap": len(magma_all) - pilot_magma - len(magma_kept),
    }
    (FULL_DIR / "plan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
