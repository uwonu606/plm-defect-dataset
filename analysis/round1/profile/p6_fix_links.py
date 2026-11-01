import sys
from collections import Counter
sys.path.insert(0, "analysis/round1/profile")
from extract import load, extract_refs, extract_versions

recs = load("canonical")
stats = Counter()
by_origin = Counter()
tot_origin = Counter(r["origin"] for r in recs)
for r in recs:
    refs = extract_refs(r["resolution"], r["source_id"])
    has_fix_ref = bool(refs["mr"] or refs["commit"] or refs["review"])
    has_fix_ver = bool(extract_versions(r["resolution"]))
    has_aff_ver = bool(extract_versions(r["location"] + " " + r["problem"]))
    stats["fix_ref_in_resolution"] += has_fix_ref
    stats["version_in_resolution"] += has_fix_ver
    stats["affected_version(location/problem)"] += has_aff_ver
    stats["affected_and_fixed_version"] += has_aff_ver and has_fix_ver
    by_origin[r["origin"]] += has_fix_ref
for k, v in stats.items():
    print(f"{k}: {v} ({100*v/len(recs):.1f}%)")
print("fix_ref by origin: " + ", ".join(f"{o}={by_origin[o]}/{tot_origin[o]} ({100*by_origin[o]/tot_origin[o]:.1f}%)" for o in tot_origin))
