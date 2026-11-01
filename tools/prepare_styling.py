import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assign_personas import assign

ROOT = Path(__file__).resolve().parent.parent


def main(work_dir):
    work = ROOT / work_dir
    sequence = Counter()
    personas = Counter()
    for path in sorted(work.glob("canonical-*.jsonl")):
        rows = [json.loads(line) for line in path.open(encoding="utf-8")]
        for row in rows:
            year = (row.get("created") or "0000")[:4]
            sequence[row["equipment"]] += 1
            row["case_code"] = f"DF-{row['equipment']}-{year}-{sequence[row['equipment']]:05d}"
            row["persona"] = assign(row["source_id"], row["equipment"])
            personas[row["persona"]] += 1
        out = work / path.name.replace("canonical-", "coded-")
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(dict(sorted(personas.items())))


if __name__ == "__main__":
    main(sys.argv[1])
