import json, sys, random, collections, statistics

PATH = sys.argv[1]
ROWS = [json.loads(l) for l in open(PATH, encoding="utf-8")]
SLOTS = ["equipment", "repo", "version", "nf_if", "error"]
QTYPES = ["title", "problem1", "short6"]
TAUS = [0.5, 0.7, 0.9]
ENTS = [1.0, 2.0, 3.0]
METADATA_SLOTS = {"equipment", "repo"}
rnd = random.Random(0)


def m(x, key):
    return x[key] if x else 0


def fmt(x):
    return f"{x:.3f}"


def boot_ci(diffs, n=2000):
    if not diffs:
        return (0, 0)
    means = []
    for _ in range(n):
        s = [diffs[rnd.randrange(len(diffs))] for _ in diffs]
        means.append(sum(s) / len(s))
    means.sort()
    return means[int(.025 * n)], means[int(.975 * n)]


def population(rows, slot):
    if slot in METADATA_SLOTS:
        return rows
    return [r for r in rows if r["slots"][slot]["present"]]


RECOVERY = "filter"


def outcome(r, slot, asked, recovery=None):
    recovery = recovery or RECOVERY
    s = r["slots"][slot]
    if not asked:
        return s["minus"]
    if recovery == "soft" and slot not in METADATA_SLOTS:
        return r["full"]
    return s["filtered"] if s["filtered"] is not None else s["minus"]


def report_baseline(rows):
    print("## 1. 기준선 (slot 제거 전)")
    print("qtype | n | Hit@5 | Hit@20 | MRR@100")
    for qt in QTYPES:
        rs = [r for r in rows if r["qtype"] == qt]
        print(qt, len(rs), fmt(sum(r["full"]["hit5"] for r in rs) / len(rs)),
              fmt(sum(r["full"]["hit20"] for r in rs) / len(rs)), fmt(sum(r["full"]["rr"] for r in rs) / len(rs)), sep=" | ")
    print()


def report_removal(rows):
    print("## 2. slot 하나를 지웠을 때 (해당 slot이 질의에 있던 경우만; equipment·repo는 질의에 없어도 '말 안 함'으로 전체 포함)")
    print("qtype | slot | n(질의에 있던 수/전체) | Hit@5 full→minus→filter | MRR full→minus→filter | 순위 나빠진 비율 | top20 엔트로피 중앙값 | top20 최다값 비율 중앙값 | 정답이 필터에서 빠짐")
    for qt in QTYPES:
        rs_all = [r for r in rows if r["qtype"] == qt]
        for slot in SLOTS:
            rs = population(rs_all, slot)
            present = sum(r["slots"][slot]["present"] for r in rs_all)
            if not rs:
                continue
            n = len(rs)
            h_full = sum(r["full"]["hit5"] for r in rs) / n
            h_minus = sum(r["slots"][slot]["minus"]["hit5"] for r in rs) / n
            h_filt = sum(m(r["slots"][slot]["filtered"], "hit5") for r in rs) / n
            mr_full = sum(r["full"]["rr"] for r in rs) / n
            mr_minus = sum(r["slots"][slot]["minus"]["rr"] for r in rs) / n
            mr_filt = sum(m(r["slots"][slot]["filtered"], "rr") for r in rs) / n
            worse = sum(1 for r in rs if (r["slots"][slot]["minus"]["rank"] or 10**9) > (r["full"]["rank"] or 10**9)) / n
            ent = statistics.median(r["slots"][slot]["split"]["entropy"] for r in rs)
            ms = statistics.median(r["slots"][slot]["split"]["max_share"] for r in rs)
            lost = sum(1 for r in rs if not r["slots"][slot]["gold_has_value"]) / n
            print(qt, slot, f"{present}/{len(rs_all)}", f"{fmt(h_full)}→{fmt(h_minus)}→{fmt(h_filt)}",
                  f"{fmt(mr_full)}→{fmt(mr_minus)}→{fmt(mr_filt)}", fmt(worse), f"{ent:.2f}", f"{ms:.2f}", fmt(lost), sep=" | ")
    print()


def policy_rows(rs, slot, rule):
    asks = [rule(r["slots"][slot]["split"]) for r in rs]
    n = len(rs)
    never = [r["slots"][slot]["minus"] for r in rs]
    always = [outcome(r, slot, True) for r in rs]
    pol = [outcome(r, slot, a) for r, a in zip(rs, asks)]
    h = lambda xs: sum(x["hit5"] for x in xs) / n
    mr = lambda xs: sum(x["rr"] for x in xs) / n
    asked_idx = [i for i, a in enumerate(asks) if a]
    useful = sum(1 for i in asked_idx if always[i]["hit5"] > never[i]["hit5"])
    harmful = sum(1 for i in asked_idx if always[i]["hit5"] < never[i]["hit5"])
    missed = sum(1 for i, a in enumerate(asks) if not a and always[i]["hit5"] > never[i]["hit5"])
    return {"ask_rate": len(asked_idx) / n, "never_h": h(never), "pol_h": h(pol), "always_h": h(always),
            "never_mrr": mr(never), "pol_mrr": mr(pol), "always_mrr": mr(always),
            "useful": useful, "harmful": harmful, "asked": len(asked_idx), "missed": missed, "n": n}


def report_policy(rows):
    print("## 3. '상위 20건이 slot 값으로 갈릴 때만 묻는다' 규칙의 trade-off")
    print("규칙 A: top20 최다값 비율 < τ 이면 묻는다. 규칙 B: top20 엔트로피(bit) > H 이면 묻는다. 물은 뒤 회복 방식:", RECOVERY)
    print("qtype | slot | 규칙 | 되질문 비율 | Hit@5 안 물음→규칙→항상 물음 | MRR 안 물음→규칙→항상 물음 | 물어서 Hit@5 회복(건/물은 건) | 물어서 Hit@5 잃음 | 안 물어서 놓친 회복(건)")
    for qt in QTYPES:
        rs_all = [r for r in rows if r["qtype"] == qt]
        for slot in SLOTS:
            rs = population(rs_all, slot)
            if not rs:
                continue
            rules = [(f"share<{t}", (lambda t: lambda sp: sp["max_share"] < t)(t)) for t in TAUS]
            rules += [(f"H>{e}", (lambda e: lambda sp: sp["entropy"] > e)(e)) for e in ENTS]
            for name, rule in rules:
                p = policy_rows(rs, slot, rule)
                print(qt, slot, name, fmt(p["ask_rate"]),
                      f"{fmt(p['never_h'])}→{fmt(p['pol_h'])}→{fmt(p['always_h'])}",
                      f"{fmt(p['never_mrr'])}→{fmt(p['pol_mrr'])}→{fmt(p['always_mrr'])}",
                      f"{p['useful']}/{p['asked']}", p["harmful"], p["missed"], sep=" | ")
    print()


def report_ranking(rows, tau=0.7):
    print(f"## 4. 어떤 slot을 묻는 게 값이 큰가 (규칙 share<{tau}, 질의 100건당 / 되질문 100번당 Hit@5 순증, 95% bootstrap CI)")
    print("qtype | slot | 질의 100건당 되질문 | 질의 100건당 Hit@5 순증 [CI] | 되질문 100번당 Hit@5 순증 | 질의 100건당 MRR 순증")
    for qt in QTYPES:
        rs_all = [r for r in rows if r["qtype"] == qt]
        n_all = len(rs_all)
        out = []
        for slot in SLOTS:
            diffs, mrr_d, asks = [], [], 0
            pop = {id(r) for r in population(rs_all, slot)}
            for r in rs_all:
                if id(r) not in pop:
                    diffs.append(0); mrr_d.append(0); continue
                s = r["slots"][slot]
                a = s["split"]["max_share"] < tau
                asks += a
                after = outcome(r, slot, a)
                diffs.append(after["hit5"] - s["minus"]["hit5"])
                mrr_d.append(after["rr"] - s["minus"]["rr"])
            lo, hi = boot_ci(diffs)
            gain = sum(diffs) / n_all
            out.append((gain, slot, asks / n_all, lo, hi, (sum(diffs) / asks if asks else 0), sum(mrr_d) / n_all))
        for gain, slot, ar, lo, hi, per_ask, mrr in sorted(out, reverse=True):
            print(qt, slot, f"{100*ar:.1f}", f"{100*gain:+.1f} [{100*lo:+.1f}, {100*hi:+.1f}]", f"{100*per_ask:+.1f}", f"{100*mrr:+.1f}", sep=" | ")
    print()


def natural_after(r, slot, base, assume):
    s = r["slots"][slot]
    if slot in METADATA_SLOTS:
        return s["filtered"]
    key = "nat_soft" if RECOVERY == "soft" else "nat_filtered"
    if s[key]:
        return s[key]
    if RECOVERY != "soft" and assume == "pess":
        return {"hit5": 0, "rr": 0.0, "rank": None}
    return base


def report_natural(rows):
    print("## 5. 자연 질의(지우지 않은 원래 질의)에서: 빠진 slot 중 top20 최다값 비율이 가장 낮은 하나만 묻기")
    print("빠진 slot = 질의 표면에 없는 slot. 답 = 질의를 만든 레코드(records)의 그 slot 값. 그 레코드에 값이 없으면 시뮬레이션할 답이 없다:")
    print("  opt = '모름'으로 보고 결과 그대로, pess = 사용자가 레코드에 없는 값을 대서 hard filter가 정답을 뺀다고 봄(filter 방식에만 해당)")
    for qt in QTYPES:
        rs = [r for r in rows if r["qtype"] == qt]
        n = len(rs)
        print(f"### {qt} (n={n})")
        miss = collections.Counter(); answerable = collections.Counter()
        for r in rs:
            for slot in SLOTS:
                s = r["slots"][slot]
                if not s["present"]:
                    miss[slot] += 1
                    answerable[slot] += s["gold_doc_has_slot"]
        print("slot | 질의에 빠진 비율 | 빠진 것 중 질의 레코드에 값이 있는 비율(답을 시뮬레이션할 수 있는 비율)")
        for slot in SLOTS:
            print(slot, fmt(miss[slot] / n), fmt(answerable[slot] / max(1, miss[slot])), sep=" | ")
        print("후보 slot | 규칙 | 가정 | 되질문 비율 | 고른 slot 분포 | Hit@5 안 물음→물음 | MRR 안 물음→물음 | Hit@5 회복/잃음(건)")
        for cand_name, cand_slots in [("전체 5개", SLOTS), ("equipment·repo만", ["equipment", "repo"]), ("repo만", ["repo"])]:
            for tau in TAUS:
                for assume in (["opt", "pess"] if RECOVERY != "soft" and cand_slots == SLOTS else ["opt"]):
                    asks, chosen = 0, collections.Counter()
                    h0 = h1 = m0 = m1 = 0.0
                    rec = lost = 0
                    for r in rs:
                        base = r["full"]
                        cands = [(r["slots"][sl]["split"]["max_share"], sl) for sl in cand_slots
                                 if not r["slots"][sl]["present"] and r["slots"][sl]["split"]["max_share"] < tau]
                        after = base
                        if cands:
                            _, slot = min(cands)
                            asks += 1; chosen[slot] += 1
                            after = natural_after(r, slot, base, assume)
                            rec += after["hit5"] > base["hit5"]
                            lost += after["hit5"] < base["hit5"]
                        h0 += base["hit5"]; h1 += after["hit5"]; m0 += base["rr"]; m1 += after["rr"]
                    print(cand_name, f"share<{tau}", assume, fmt(asks / n), dict(chosen.most_common()),
                          f"{fmt(h0/n)}→{fmt(h1/n)}", f"{fmt(m0/n)}→{fmt(m1/n)}", f"{rec}/{lost}", sep=" | ")
        print()


def report_by_origin(rows, tau=0.7):
    print(f"## 6. origin별 (share<{tau}, problem1·short6)")
    print("qtype | origin | slot | n | 되질문 비율 | Hit@5 안 물음→규칙→항상 물음")
    for qt in ["problem1", "short6"]:
        for org in ["ran-core", "adjacent-network"]:
            rs_all = [r for r in rows if r["qtype"] == qt and r["origin"] == org]
            for slot in SLOTS:
                rs = population(rs_all, slot)
                if not rs:
                    continue
                p = policy_rows(rs, slot, lambda sp: sp["max_share"] < tau)
                print(qt, org, slot, p["n"], fmt(p["ask_rate"]), f"{fmt(p['never_h'])}→{fmt(p['pol_h'])}→{fmt(p['always_h'])}", sep=" | ")
    print()


RECOVERY = sys.argv[2] if len(sys.argv) > 2 else "filter"
print("source:", PATH, "rows:", len(ROWS), "| 물은 뒤 회복 방식:", RECOVERY,
      "(filter=정답 slot 값으로 hard filter, soft=값을 질의 텍스트에 되돌려 넣음; equipment·repo는 항상 filter)")
report_baseline(ROWS)
report_removal(ROWS)
report_policy(ROWS)
report_ranking(ROWS)
report_natural(ROWS)
report_by_origin(ROWS)
