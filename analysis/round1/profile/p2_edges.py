import json
import sys
from collections import Counter, defaultdict
from math import comb
sys.path.insert(0, "analysis/round1/profile")
from extract import load, repo_of

OUT = "analysis/round1/profile/out"
recs = load("canonical")
by_code = {r["case_code"]: r for r in recs}
ents = json.load(open(f"{OUT}/entities_canonical.json"))
by_source = {r["source_id"]: r["case_code"] for r in recs}
N = len(recs)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)

    def components(self):
        comps = defaultdict(list)
        for x in self.parent:
            comps[self.find(x)].append(x)
        return list(comps.values())


def bucket(size):
    for lo, hi, label in [(2, 2, "2"), (3, 5, "3-5"), (6, 10, "6-10"), (11, 50, "11-50"), (51, 200, "51-200"), (201, 10**9, ">200")]:
        if lo <= size <= hi:
            return label


def describe_pairs(name, pairs):
    uf = UnionFind()
    for a, b in pairs:
        uf.union(a, b)
    comps = uf.components()
    sizes = sorted((len(c) for c in comps), reverse=True)
    dist = Counter(bucket(s) for s in sizes)
    connected = sum(sizes)
    print(f"{name}: edges={len(pairs)} connected_records={connected} ({100*connected/N:.1f}%) components={len(comps)} "
          f"largest={sizes[0] if sizes else 0} sizes={dict(sorted(dist.items(), key=lambda kv: ['2','3-5','6-10','11-50','51-200','>200'].index(kv[0])))}")
    return comps


def describe_keyed(name, key_to_records, max_df=None):
    groups = {k: sorted(v) for k, v in key_to_records.items() if len(v) >= 2 and (max_df is None or len(v) <= max_df)}
    edges = sum(comb(len(v), 2) for v in groups.values())
    uf = UnionFind()
    for v in groups.values():
        for x in v[1:]:
            uf.union(v[0], x)
    comps = uf.components()
    sizes = sorted((len(c) for c in comps), reverse=True)
    dist = Counter(bucket(s) for s in sizes)
    connected = sum(sizes)
    label = f"{name}[df<={max_df}]" if max_df else f"{name}[all]"
    print(f"{label}: shared_keys={len(groups)} edges(pairs)={edges} connected_records={connected} ({100*connected/N:.1f}%) "
          f"components={len(comps)} largest={sizes[0] if sizes else 0} "
          f"sizes={dict(sorted(dist.items(), key=lambda kv: ['2','3-5','6-10','11-50','51-200','>200'].index(kv[0])))}")
    return groups, uf


def keyed(category, scope_by_repo=True, codes=None):
    out = defaultdict(set)
    for code, e in ents.items():
        if codes is not None and code not in codes:
            continue
        scope = repo_of(by_code[code]["source_id"]) if scope_by_repo else ""
        for v in e[category]:
            out[(scope, v)].add(code)
    return out


print("# 1. duplicate_of_case")
dup_pairs = [(r["case_code"], r["duplicate_of_case"]) for r in recs if r["duplicate_of_case"]]
dup_any = sum(1 for r in recs if r["duplicate_of"])
print(f"duplicate_of filled={dup_any}, duplicate_of_case resolvable in dataset={len(dup_pairs)}")
describe_pairs("dup", dup_pairs)

print("\n# 2. issue cross-reference (same repo #N -> source_id)")
xref_pairs, dangling, total_refs = [], 0, 0
xref_kinds = Counter()
for code, e in ents.items():
    r = by_code[code]
    repo = repo_of(r["source_id"])
    for num in e["ref_issue"]:
        total_refs += 1
        target = by_source.get(f"{repo}#{num}")
        if target and target != code:
            xref_pairs.append((code, target))
            xref_kinds[repo] += 1
        elif not target:
            dangling += 1
print(f"issue-ref mentions={total_refs}, resolved to another record={len(xref_pairs)}, dangling(not in dataset)={dangling}, self={total_refs-len(xref_pairs)-dangling}")
print(f"resolved by repo={dict(xref_kinds)}")
undirected = {tuple(sorted(p)) for p in xref_pairs}
print(f"undirected xref edges={len(undirected)}; records with outgoing xref={len({a for a,_ in xref_pairs})}")
xref_comps = describe_pairs("xref", list(undirected))
json.dump(sorted(undirected), open(f"{OUT}/xref_pairs.json", "w"))

print("\n# 3. shared PR/MR/review number (same repo) and shared commit")
for cat in ["ref_mr_pr", "ref_commit"]:
    kr = keyed(cat)
    describe_keyed(cat, kr)
    describe_keyed(cat, kr, 10)

print("\n# 4. shared code symbol (scoped by repo)")
for cat in ["func", "file"]:
    kr = keyed(cat)
    describe_keyed(cat, kr)
    describe_keyed(cat, kr, 50)
    describe_keyed(cat, kr, 10)
    top = sorted(((len(v), k) for k, v in kr.items()), reverse=True)[:10]
    print(f"  hubs({cat}): {[(k[1], n) for n, k in top]}")

print("\n# 5. shared error signature (scoped by repo)")
for cat in ["err_specific", "err_generic"]:
    kr = keyed(cat)
    describe_keyed(cat, kr)
    describe_keyed(cat, kr, 50)
    describe_keyed(cat, kr, 10)
    top = sorted(((len(v), k) for k, v in kr.items()), reverse=True)[:8]
    print(f"  hubs({cat}): {[(k[1][:70], n) for n, k in top]}")
print("  err_specific unscoped (cross-repo sharing):")
describe_keyed("err_specific_xrepo", keyed("err_specific", scope_by_repo=False), 50)

print("\n# 6. (NF, interface, cause_class) triple, cross-repo")
triple = defaultdict(set)
eligible = 0
for code, e in ents.items():
    cc = by_code[code]["cause_class"]
    if not cc or not e["nf"] or not e["iface"]:
        continue
    eligible += 1
    for nf in e["nf"]:
        for ifc in e["iface"]:
            triple[(nf, ifc, cc)].add(code)
print(f"records with nf+iface+cause_class={eligible} ({100*eligible/N:.1f}%), distinct triples={len(triple)}")
describe_keyed("triple", triple)
describe_keyed("triple", triple, 50)
describe_keyed("triple", triple, 10)
top = sorted(((len(v), k) for k, v in triple.items()), reverse=True)[:10]
print(f"  hubs(triple): {[(k, n) for n, k in top]}")
sz = Counter(bucket(len(v)) if len(v) >= 2 else "1" for v in triple.values())
print(f"  triple group size distribution: {dict(sz)}")

print("\n# 7. single-entity hubs (records sharing one NF/interface)")
for cat in ["nf", "iface", "neutron"]:
    cnt = Counter(v for e in ents.values() for v in e[cat])
    print(f"  {cat}: " + ", ".join(f"{k}={n}" for k, n in cnt.most_common(12)))
    print(f"  {cat}: pairs implied by top-3 alone = {sum(comb(n,2) for _, n in cnt.most_common(3))}")

print("\n# 8. combined 'specific' graph: dup + xref + mr/pr + commit + func/file/err_specific(df<=10)")
uf = UnionFind()
edge_sources = Counter()
for a, b in dup_pairs:
    uf.union(a, b); edge_sources["dup"] += 1
for a, b in undirected:
    uf.union(a, b); edge_sources["xref"] += 1
for cat in ["ref_mr_pr", "ref_commit", "func", "file", "err_specific"]:
    for k, v in keyed(cat).items():
        if 2 <= len(v) <= 10:
            v = sorted(v)
            for x in v[1:]:
                uf.union(v[0], x)
            edge_sources[cat] += comb(len(v), 2)
comps = uf.components()
sizes = sorted((len(c) for c in comps), reverse=True)
connected = sum(sizes)
print(f"edges by source={dict(edge_sources)}")
print(f"connected={connected} ({100*connected/N:.1f}%), components={len(comps)}, largest={sizes[:5]}, "
      f"dist={dict(Counter(bucket(s) for s in sizes))}")
by_origin = Counter(by_code[x]["origin"] for c in comps for x in c)
tot_origin = Counter(r["origin"] for r in recs)
print("connected by origin: " + ", ".join(f"{o}={by_origin[o]}/{tot_origin[o]} ({100*by_origin[o]/tot_origin[o]:.1f}%)" for o in tot_origin))
by_basis = Counter(by_code[x]["cause_basis"] for c in comps for x in c)
tot_basis = Counter(r["cause_basis"] for r in recs)
print("connected by cause_basis: " + ", ".join(f"{o}={by_basis[o]}/{tot_basis[o]} ({100*by_basis[o]/tot_basis[o]:.1f}%)" for o in tot_basis))

print("\n# 9. edges that bridge 'cause unknown' to 'cause stated' (useful hops)")
bridge = Counter()
pairs_all = [("dup", a, b) for a, b in dup_pairs] + [("xref", a, b) for a, b in undirected]
for cat in ["ref_mr_pr", "ref_commit", "func", "err_specific"]:
    for k, v in keyed(cat).items():
        if 2 <= len(v) <= 10:
            v = sorted(v)
            pairs_all += [(cat, a, b) for i, a in enumerate(v) for b in v[i+1:]]
weak = {"미상", "추론"}
bridging_records = defaultdict(set)
for kind, a, b in pairs_all:
    ba, bb = by_code[a]["cause_basis"], by_code[b]["cause_basis"]
    if (ba in weak and bb == "명시") or (bb in weak and ba == "명시"):
        bridge[kind] += 1
        bridging_records[kind].add(a if ba in weak else b)
print({k: (n, len(bridging_records[k])) for k, n in bridge.items()}, "(pairs, distinct weak-cause records reached)")
all_weak_reached = set().union(*bridging_records.values())
print(f"weak-cause records reachable to a 명시 record in 1 hop: {len(all_weak_reached)} / {tot_basis['미상']+tot_basis['추론']}")
json.dump(pairs_all, open(f"{OUT}/pairs_all.json", "w"))
