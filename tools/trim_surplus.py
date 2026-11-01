import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "work" / "full"
PILOT_RECORDS = sum(1 for p in (ROOT / "work" / "pilot").glob("canonical-*.jsonl") for _ in p.open(encoding="utf-8"))


def main(target):
    surplus_dir = FULL / "surplus"
    surplus_dir.mkdir(exist_ok=True)
    files = sorted(FULL.glob("canonical-*.jsonl"))
    total = PILOT_RECORDS + sum(1 for p in files for _ in p.open(encoding="utf-8"))
    excess = total - target
    for path in sorted((p for p in files if p.stem.startswith("canonical-a-")), reverse=True):
        if excess <= 0:
            break
        rows = path.read_text(encoding="utf-8").splitlines(keepends=True)
        cut = min(excess, len(rows))
        (surplus_dir / path.name).write_text("".join(rows[len(rows) - cut:]), encoding="utf-8")
        path.write_text("".join(rows[:len(rows) - cut]), encoding="utf-8")
        if cut == len(rows):
            path.unlink()
        excess -= cut
    remaining = PILOT_RECORDS + sum(1 for p in FULL.glob("canonical-*.jsonl") for _ in p.open(encoding="utf-8"))
    print(f"before {total}, after {remaining}")


if __name__ == "__main__":
    main(int(sys.argv[1]))
