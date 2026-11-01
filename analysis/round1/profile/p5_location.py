import re
import sys
from collections import Counter, defaultdict
sys.path.insert(0, "analysis/round1/profile")
from extract import load, VERSION_RE, IFACE_RE, NF_RE, extract_dict, BACKTICK_RE

SEP = re.compile(r"\s/\s")
VERSIONISH = re.compile(VERSION_RE.pattern + r"|commit|master|main\b|develop|branch|release|[0-9a-f]{7,40}|\bRel|빌드|build|UBSAN|ASAN|nightly|최신|latest|trunk|@", re.I)
PROTO_EXTRA = re.compile(r"API|REST|HTTP|RPC|NETCONF|YANG|IE\b|message|메시지|절차|procedure|interface|인터페이스|Request|Response|Indication|Command|N[a-z]{2,5}_\w+|/n[a-z]+-[a-z-]+", re.I)


def split_location(loc):
    masked = BACKTICK_RE.sub(lambda m: "`" + m.group(1).replace("/", "∕") + "`", loc)
    return [p.strip() for p in SEP.split(masked)]


def analyse(name, recs):
    seg_counts = Counter()
    groups = defaultdict(lambda: Counter())
    for r in recs:
        parts = split_location(r["location"])
        n = len(parts)
        seg_counts[min(n, 5)] += 1
        g = groups[r["origin"]], groups[r["equipment"]], groups["ALL"]
        third_version = n >= 3 and bool(VERSIONISH.search(parts[-1]))
        second_proto = n >= 2 and (bool(extract_dict(parts[1], IFACE_RE)) or bool(PROTO_EXTRA.search(parts[1])))
        any_version = bool(VERSION_RE.search(r["location"])) or bool(re.search(r"commit|[0-9a-f]{7,40}", r["location"]))
        for c in g:
            c["n"] += 1
            c["seg3"] += n == 3
            c["seg>=3"] += n >= 3
            c["last_is_version(seg>=3)"] += third_version
            c["seg2_proto"] += second_proto
            c["strict3(3seg,2nd proto,last ver)"] += n == 3 and second_proto and third_version
            c["any_version_in_location"] += any_version
            c["first_has_nf"] += bool(extract_dict(parts[0], NF_RE))
    print(f"## {name}: segment count distribution (split on ' / ' outside backticks): "
          + ", ".join(f"{k if k<5 else '5+'}seg={v} ({100*v/len(recs):.1f}%)" for k, v in sorted(seg_counts.items())))
    keys = ["seg3", "seg>=3", "last_is_version(seg>=3)", "seg2_proto", "strict3(3seg,2nd proto,last ver)", "any_version_in_location", "first_has_nf"]
    cols = ["ALL", "ran-core", "adjacent-network", "PLATFORM", "CORE", "RAN-DU", "OAM", "UE", "RAN-CU"]
    print("metric".ljust(34) + "".join(f"{c[:12]:>13}" for c in cols))
    for k in keys:
        print(k.ljust(34) + "".join(f"{100*groups[c][k]/groups[c]['n']:12.1f}%" for c in cols))


can = load("canonical")
rec = load("records")
analyse("canonical", can)
same = sum(1 for a, b in zip(can, rec) if a["location"] == b["location"])
print(f"\nrecords.location identical to canonical: {same}/{len(can)} ({100*same/len(can):.1f}%)")
analyse("records", rec)
import random
random.seed(4)
print("\nexamples of non-3-segment locations:")
for r in random.sample([r for r in can if len(split_location(r["location"])) != 3], 8):
    print("  ", r["location"][:140])
