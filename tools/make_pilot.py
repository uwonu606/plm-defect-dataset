import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "work" / "candidates.jsonl"
PILOT_DIR = ROOT / "work" / "pilot"
QUOTA = {"ran-core": 400, "adjacent-network": 100}
BATCH_SIZE = 50


def source_of(record):
    return record["source_id"].rsplit("#", 1)[0]


def evenly(rows, count):
    if count >= len(rows):
        return rows
    step = len(rows) / count
    return [rows[int(i * step)] for i in range(count)]


def stratified(rows, count):
    by_source = defaultdict(list)
    for row in rows:
        by_source[source_of(row)].append(row)
    picked = []
    for source, items in sorted(by_source.items()):
        share = max(1, round(count * len(items) / len(rows)))
        picked.extend(evenly(items, share))
    return evenly(picked, count)


def main():
    rows = [json.loads(line) for line in CANDIDATES.open(encoding="utf-8")]
    pilot = []
    for tier, count in QUOTA.items():
        pilot.extend(stratified([r for r in rows if r["tier"] == tier], count))
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    for index in range(0, len(pilot), BATCH_SIZE):
        batch = pilot[index:index + BATCH_SIZE]
        path = PILOT_DIR / f"batch-{index // BATCH_SIZE:02d}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in batch), encoding="utf-8")
    counts = defaultdict(int)
    for row in pilot:
        counts[source_of(row)] += 1
    print(len(pilot), dict(counts))


if __name__ == "__main__":
    main()
