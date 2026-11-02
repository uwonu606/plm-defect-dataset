"""분류 체계(taxonomy/*.json)로 정본 레코드 표본을 Haiku에 두 번(pass A·B) 라벨링하고 일치도·분포를 낸다.

    python3 -I taxonomy/label.py --dry-run
    python3 -I taxonomy/label.py --sample-size 450 --version v3 --out /tmp/plm-taxonomy-v3

같은 --seed·--sample-size면 같은 표본을 뽑는다(450건·seed 20261103이 v2 실측 표본이다).
Haiku 호출은 sim/llm.py의 ask를 쓰고 sim/runs/llm_cache에 캐시된다.
"""
import argparse
import collections
import json
import random
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TAXONOMY_DIR = REPO / "taxonomy"
sys.path.insert(0, str(REPO / "sim"))
from llm import ask, parse_json  # noqa: E402

AXES = ("problem", "cause", "resolution")
SPECIALS = ("_none", "_na", "_other")
MAX_WORKERS = 6
BATCH = 10
MIN_PER_STRATUM = 3


def load_records():
    with open(REPO / "dataset" / "canonical.jsonl") as f:
        return [json.loads(line) for line in f]


def stratified_sample(records, size, seed):
    strata = collections.defaultdict(list)
    for r in records:
        strata[(r["record_type"], r["origin"], r["equipment"])].append(r)
    keys = sorted(strata)
    total = len(records)
    quota = {k: max(MIN_PER_STRATUM, size * len(strata[k]) // total) for k in keys}
    remainders = sorted(keys, key=lambda k: -(size * len(strata[k]) / total - size * len(strata[k]) // total))
    i = 0
    while sum(quota.values()) < size:
        quota[remainders[i % len(remainders)]] += 1
        i += 1
    while sum(quota.values()) > size:
        biggest = max(keys, key=lambda k: quota[k])
        quota[biggest] -= 1
    rng = random.Random(seed)
    picked = []
    for k in keys:
        picked.extend(rng.sample(strata[k], quota[k]))
    return picked, {"|".join(k): quota[k] for k in keys if quota[k]}


class Taxonomy:
    def __init__(self, axis, path):
        data = json.loads(Path(path).read_text())
        self.axis = axis
        self.path = str(path)
        self.version = data.get("version", "")
        self.root = data["scheme"]
        self.label_rule = data.get("label_rule", "")
        self.nodes = {c["id"]: c for c in data["concepts"]}
        self.special_nodes = {s["id"]: s for s in data["special_codes"]}
        self.children = collections.defaultdict(list)
        for n in self.nodes.values():
            self.children[n["broader"]].append(n["id"])
        self.leaves = [i for i in self.nodes if not self.children.get(i)]

    def valid(self, node_id):
        return node_id in self.nodes or node_id in SPECIALS

    def ancestors(self, node_id):
        chain = [node_id]
        while chain[-1] in self.nodes and self.nodes[chain[-1]]["broader"] != self.root["id"]:
            chain.append(self.nodes[chain[-1]]["broader"])
        return chain

    def l1(self, node_id):
        return self.ancestors(node_id)[-1] if node_id in self.nodes else node_id

    def depth(self, node_id):
        return len(self.ancestors(node_id)) if node_id in self.nodes else 0

    def prompt_block(self):
        root = self.root
        lines = [f"### 축 {self.axis} (루트 {root['id']}: {root['pref_label']['ko']})",
                 f"정의: {root['definition']}", f"판정: {root['include']}", f"제외: {root['exclude']}", ""]
        for node_id in sorted(self.nodes, key=lambda i: self.ancestors(i)[::-1]):
            n = self.nodes[node_id]
            indent = "  " * (self.depth(node_id) - 1)
            label = n["pref_label"]
            lines.append(f"{indent}- {node_id} [{label['ko']} / {label['en']}] 정의: {n['definition']} | "
                         f"포함: {n['include']} | 제외: {n['exclude']}")
        lines.append("")
        lines.append(f"{self.axis} 특수 코드(트리 밖):")
        for code in SPECIALS:
            s = self.special_nodes[code]
            lines.append(f"- {code}: {s['definition']} | 포함: {s['include']} | 제외: {s['exclude']}")
        return "\n".join(lines)


def system_prompt(taxonomies):
    head = (
        "너는 통신 장비 조직의 결함·요청 기록을 분류 체계에 따라 라벨링한다. 축은 problem(관찰된 현상·증상), "
        "cause(근본 원인), resolution(조치·종결 방식) 세 개이고 서로 독립이다. 장비군·NF·프로토콜·제품·버전·모듈 같은 "
        "'어디서'는 라벨에 넣지 않는다.\n"
        "규칙:\n"
        "1. 레코드마다 축별로 primary 1개(필수)와 secondary 0~1개를 단다. secondary가 없으면 null.\n"
        "2. 가능한 한 가장 깊은 노드 id를 쓴다. 하위를 가를 근거가 없거나 맞는 자식이 없으면 그 부모(중간) 노드 id를 쓴다. 축 루트 id(p, c, r)는 쓰지 않는다.\n"
        "3. 트리에 맞지 않으면 특수 코드 _none(정보 없음), _na(해당 없음), _other(맞는 노드 없음) 중 하나를 쓴다.\n"
        "4. 아래 목록에 있는 id만 쓴다. 새 id를 만들지 않는다.\n"
        "5. 출력은 JSON 배열 하나뿐이다. 설명을 붙이지 않는다. 형식: "
        '[{"case_code": "...", "problem": {"primary": "...", "secondary": null}, '
        '"cause": {"primary": "...", "secondary": null}, "resolution": {"primary": "...", "secondary": null}}]\n\n'
    )
    return head + "\n\n".join(t.prompt_block() for t in taxonomies.values())


def record_block(r):
    def field(v):
        return v.strip() if v and v.strip() else "(비어 있음)"
    return (f"## {r['case_code']}\n유형: {r['record_type']}\n제목: {field(r['title'])}\n"
            f"problem: {field(r['problem'])}\ncause: {field(r['cause'])}\nresolution: {field(r['resolution'])}")


def user_prompt(batch):
    return (f"아래 레코드 {len(batch)}건을 라벨링하라. 입력 순서대로 {len(batch)}개 원소의 JSON 배열로 답하라.\n\n"
            + "\n\n".join(record_block(r) for r in batch))


def clean_label(taxonomy, value):
    if not isinstance(value, dict):
        return None
    primary = value.get("primary")
    secondary = value.get("secondary")
    if not isinstance(primary, str) or not taxonomy.valid(primary.strip()):
        return None
    secondary = secondary.strip() if isinstance(secondary, str) and taxonomy.valid(secondary.strip()) else None
    if secondary == primary.strip():
        secondary = None
    return {"primary": primary.strip(), "secondary": secondary}


def run_batch(system, taxonomies, batch):
    try:
        out = ask(user_prompt(batch), system, model="haiku")
        items = parse_json(out["text"])
    except Exception as exc:  # noqa: BLE001
        return {}, {"error": str(exc)[:200]}
    if isinstance(items, dict):
        items = items.get("labels") or items.get("records") or [items]
    wanted = {r["case_code"] for r in batch}
    labels = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or item.get("case_code") not in wanted:
            continue
        labels[item["case_code"]] = {ax: clean_label(taxonomies[ax], item.get(ax)) for ax in AXES}
    return labels, {"cost_usd": out.get("cost_usd", 0), "seconds": out.get("seconds", 0),
                    "input_tokens": out.get("input_tokens", 0), "output_tokens": out.get("output_tokens", 0)}


def code_incomplete(axes):
    return not axes or any(not axes.get(ax) for ax in AXES)


def run_pass(records, seed, system, taxonomies, workers):
    order = list(records)
    random.Random(seed).shuffle(order)
    batches = [order[i:i + BATCH] for i in range(0, len(order), BATCH)]
    labels, usage = {}, []

    def collect(results):
        for got, meta in results:
            usage.append(meta)
            for code, axes in got.items():
                prev = labels.get(code, {})
                labels[code] = {ax: axes.get(ax) or prev.get(ax) for ax in AXES}

    with ThreadPoolExecutor(workers) as pool:
        collect(pool.map(lambda b: run_batch(system, taxonomies, b), batches))
        for retry_size in (5, 1):
            missing = [r for r in order if code_incomplete(labels.get(r["case_code"]))]
            if not missing:
                break
            retry = [missing[i:i + retry_size] for i in range(0, len(missing), retry_size)]
            collect(pool.map(lambda b: run_batch(system, taxonomies, b), retry))
    final = {}
    for r in order:
        got = labels.get(r["case_code"]) or {}
        final[r["case_code"]] = {ax: got.get(ax) or {"primary": "_invalid", "secondary": None} for ax in AXES}
    return final, usage, [sorted(x["case_code"] for x in b) for b in batches]


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0


def diverge_pair(t, a, b):
    if a not in t.nodes or b not in t.nodes:
        return tuple(sorted((t.l1(a), t.l1(b)))), "특수·L1"
    chain_a, chain_b = t.ancestors(a)[::-1], t.ancestors(b)[::-1]
    i = 0
    while i < min(len(chain_a), len(chain_b)) and chain_a[i] == chain_b[i]:
        i += 1
    if i == len(chain_a) or i == len(chain_b):
        return tuple(sorted((a, b))), "부모-자식"
    return tuple(sorted((chain_a[i], chain_b[i]))), f"형제(L{i + 1})"


def axis_stats(t, sample, la, lb):
    n = len(sample)
    codes = [r["case_code"] for r in sample]
    pa = {c: la[c][t.axis]["primary"] for c in codes}
    pb = {c: lb[c][t.axis]["primary"] for c in codes}
    pooled = collections.Counter(list(pa.values()) + list(pb.values()))
    judged = sum(v for k, v in pooled.items() if k in t.nodes)

    def share(count, denom=2 * n):
        return round(count / denom, 4) if denom else None

    node_rows = {}
    for node_id in t.nodes:
        subtree = sum(v for k, v in pooled.items() if k in t.nodes and node_id in t.ancestors(k))
        node_rows[node_id] = {"label_ko": t.nodes[node_id]["pref_label"]["ko"], "depth": t.depth(node_id),
                              "leaf": node_id in t.leaves, "assigned": pooled.get(node_id, 0),
                              "subtree_share_all": share(subtree), "subtree_share_judged": share(subtree, judged)}
    l1_pairs = [(t.l1(pa[c]), t.l1(pb[c])) for c in codes]
    exact_pairs = [(pa[c], pb[c]) for c in codes]
    compatible = sum(a == b or (a in t.nodes and b in t.nodes and (a in t.ancestors(b) or b in t.ancestors(a)))
                     for a, b in exact_pairs)
    confusions = collections.defaultdict(list)
    for c in codes:
        if pa[c] != pb[c]:
            confusions[diverge_pair(t, pa[c], pb[c])].append(c)
    ranked = sorted(confusions.items(), key=lambda kv: -len(kv[1]))
    leaf_share = {lf: share(pooled.get(lf, 0), judged) for lf in t.leaves}
    rtype = {r["case_code"]: r["record_type"] for r in sample}
    by_type = {}
    for rt in sorted(set(rtype.values())):
        cs = [c for c in codes if rtype[c] == rt]
        cnt = collections.Counter(t.l1(pa[c]) for c in cs) + collections.Counter(t.l1(pb[c]) for c in cs)
        by_type[rt] = {"n": len(cs), "l1_share": {k: round(v / (2 * len(cs)), 4) for k, v in cnt.most_common()}}
    intermediate = sum(v for k, v in pooled.items() if k in t.nodes and k not in t.leaves)
    return {
        "taxonomy": t.path,
        "agreement": {"n": n, "l1_agree": round(sum(a == b for a, b in l1_pairs) / n, 4),
                      "exact_agree": round(sum(a == b for a, b in exact_pairs) / n, 4),
                      "hierarchy_compatible_agree": round(compatible / n, 4),
                      "kappa_l1": kappa(l1_pairs), "kappa_exact": kappa(exact_pairs)},
        "l1_share_all": {k: share(v) for k, v in collections.Counter(t.l1(v) for v in list(pa.values()) + list(pb.values())).most_common()},
        "special_share": {s: share(pooled.get(s, 0)) for s in SPECIALS},
        "invalid_share": share(pooled.get("_invalid", 0)),
        "intermediate_share_judged": share(intermediate, judged),
        "secondary_used_share": round(sum(bool(la[c][t.axis]["secondary"]) + bool(lb[c][t.axis]["secondary"]) for c in codes) / (2 * n), 4),
        "small_leaves_lt2pct_judged": {k: v for k, v in sorted(leaf_share.items(), key=lambda kv: kv[1] or 0) if v is not None and v < 0.02},
        "large_leaves_gt25pct_judged": {k: v for k, v in leaf_share.items() if v is not None and v > 0.25},
        "top_confusions": [{"pair": list(p), "relation": rel, "count": len(cs), "examples": cs[:3]} for (p, rel), cs in ranked[:10]],
        "by_record_type": by_type,
        "nodes": node_rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default="v3", help="출력에 적을 분류 체계 버전 이름")
    ap.add_argument("--taxonomy-dir", default=str(TAXONOMY_DIR), help="problem.json·cause.json·resolution.json이 있는 폴더")
    ap.add_argument("--sample-size", type=int, default=450)
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--out", default=None, help="출력 폴더(기본: 임시 폴더 아래 plm-taxonomy-<version>)")
    ap.add_argument("--dry-run", action="store_true", help="표본과 system prompt만 만들고 Haiku를 부르지 않는다")
    args = ap.parse_args()
    workers = max(1, min(args.workers, MAX_WORKERS))
    out_dir = Path(args.out or Path(tempfile.gettempdir()) / f"plm-taxonomy-{args.version}")
    out_dir.mkdir(parents=True, exist_ok=True)

    taxonomies = {ax: Taxonomy(ax, Path(args.taxonomy_dir) / f"{ax}.json") for ax in AXES}
    sample, quota = stratified_sample(load_records(), args.sample_size, args.seed)
    system = system_prompt(taxonomies)
    (out_dir / "sample.json").write_text(json.dumps({"seed": args.seed, "quota": quota, "case_codes": [r["case_code"] for r in sample]},
                                                    ensure_ascii=False, indent=1))
    (out_dir / "system_prompt.txt").write_text(system)
    if args.dry_run:
        print(json.dumps({"out": str(out_dir), "sample": len(sample), "strata": len(quota),
                          "system_prompt_chars": len(system),
                          "concepts": {ax: len(t.nodes) for ax, t in taxonomies.items()}}, ensure_ascii=False))
        return

    passes = {"A": run_pass(sample, args.seed + 1, system, taxonomies, workers),
              "B": run_pass(sample, args.seed + 2, system, taxonomies, workers)}
    with open(out_dir / "labels.jsonl", "w") as f:
        for name, (labels, _, _) in passes.items():
            for r in sample:
                row = {"case_code": r["case_code"], "pass": name, "taxonomy": args.version}
                row.update(labels[r["case_code"]])
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    la, lb = passes["A"][0], passes["B"][0]
    usage = passes["A"][1] + passes["B"][1]
    stats = {
        "version": args.version,
        "sample": {"n": len(sample), "seed": args.seed, "strata": quota,
                   "record_type": dict(collections.Counter(r["record_type"] for r in sample))},
        "run": {"calls": len(usage), "errors": [u for u in usage if "error" in u],
                "cost_usd": round(sum(u.get("cost_usd", 0) for u in usage), 4),
                "shared_batches_AB": len({tuple(s) for s in passes["A"][2]} & {tuple(s) for s in passes["B"][2]}),
                "system_prompt_chars": len(system)},
        "axes": {ax: axis_stats(taxonomies[ax], sample, la, lb) for ax in AXES},
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps({"out": str(out_dir), "run": stats["run"],
                      "agreement": {ax: stats["axes"][ax]["agreement"] for ax in AXES}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
