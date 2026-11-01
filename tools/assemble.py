import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK_DIRS = [ROOT / "work" / "pilot", ROOT / "work" / "full"]
OUT = ROOT / "dataset"

FIELDS = [
    "case_code", "record_type", "title", "equipment", "location", "problem", "cause", "cause_basis",
    "cause_class", "resolution", "origin", "duplicate_of", "duplicate_of_case", "persona",
    "source_id", "source_url", "source_license", "created",
]
EDITABLE = {"title", "location", "problem", "cause", "resolution"}
RECORD_TYPES = {"결함", "CI·빌드", "기능 요청"}
EQUIPMENT = {"RAN-CU", "RAN-DU", "UE", "CORE", "OAM", "PLATFORM"}
CAUSE_BASIS = {"명시", "추론", "미상", "해당 없음"}


def load_pairs():
    pairs = []
    for work in WORK_DIRS:
        for coded_path in sorted(work.glob("coded-*.jsonl")):
            styled_path = work / coded_path.name.replace("coded-", "styled-")
            canonical = [json.loads(line) for line in coded_path.open(encoding="utf-8")]
            styled = {row["case_code"]: row for row in map(json.loads, styled_path.open(encoding="utf-8"))}
            for row in canonical:
                pairs.append((row, styled[row["case_code"]]))
    return pairs


def check_pair(canonical, styled):
    for key in canonical:
        if key not in EDITABLE and canonical[key] != styled.get(key):
            raise ValueError(f"{canonical['case_code']}: {key} changed in styled version")
    if canonical["record_type"] not in RECORD_TYPES or canonical["equipment"] not in EQUIPMENT or canonical["cause_basis"] not in CAUSE_BASIS:
        raise ValueError(f"{canonical['case_code']}: enum value out of schema")


def renumber(pairs):
    sequence = Counter()
    pairs.sort(key=lambda pair: (pair[0].get("created") or "", pair[0]["source_id"]))
    case_by_source = {}
    for canonical, styled in pairs:
        year = (canonical.get("created") or "0000")[:4]
        sequence[canonical["equipment"]] += 1
        code = f"DF-{canonical['equipment']}-{year}-{sequence[canonical['equipment']]:05d}"
        case_by_source[canonical["source_id"]] = code
        for row in (canonical, styled):
            row["case_code"] = code
            row.setdefault("duplicate_of", "")
    for canonical, styled in pairs:
        target = case_by_source.get(canonical["duplicate_of"], "")
        canonical["duplicate_of_case"] = styled["duplicate_of_case"] = target


def write(rows, stem):
    with (OUT / f"{stem}.jsonl").open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps({k: row.get(k, "") for k in FIELDS}, ensure_ascii=False) + "\n")
    with (OUT / f"{stem}.csv").open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: row.get(k, "") for k in FIELDS} for row in rows)


def main():
    pairs = load_pairs()
    for canonical, styled in pairs:
        check_pair(canonical, styled)
    sources = Counter(canonical["source_id"] for canonical, _ in pairs)
    duplicated = [s for s, n in sources.items() if n > 1]
    if duplicated:
        raise ValueError(f"source_id appears more than once: {duplicated[:5]}")
    renumber(pairs)
    OUT.mkdir(exist_ok=True)
    write([styled for _, styled in pairs], "records")
    write([canonical for canonical, _ in pairs], "canonical")
    stats = {
        "records": len(pairs),
        "record_type": Counter(c["record_type"] for c, _ in pairs),
        "equipment": Counter(c["equipment"] for c, _ in pairs),
        "cause_basis": Counter(c["cause_basis"] for c, _ in pairs),
        "origin": Counter(c["origin"] for c, _ in pairs),
        "duplicates_in_dataset": sum(1 for c, _ in pairs if c["duplicate_of_case"]),
        "persona": Counter(c["persona"] for c, _ in pairs),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
