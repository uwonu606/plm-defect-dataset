import json
import re
import sys
from collections import Counter, defaultdict
sys.path.insert(0, "analysis/round1/profile")
from extract import load, record_text, CATEGORIES, NF_ALIASES, IFACE_ALIASES

OUT = "analysis/round1/profile/out"
can = {r["case_code"]: r for r in load("canonical")}
rec = {r["case_code"]: r for r in load("records")}
ec = json.load(open(f"{OUT}/entities_canonical.json"))
er = json.load(open(f"{OUT}/entities_records.json"))

print("# 4-1. record coverage (>=1 entity) canonical vs records, and value-level recall/precision")
print(f"{'category':14}{'cov_can':>9}{'cov_rec':>9}{'recall':>9}{'precision':>10}{'lost_vals':>10}{'new_vals':>10}")
for c in CATEGORIES:
    cov_c = sum(1 for k in ec if ec[k][c]) / len(ec)
    cov_r = sum(1 for k in er if er[k][c]) / len(er)
    tp = fn = fp = 0
    for k in ec:
        a, b = set(ec[k][c]), set(er[k][c])
        tp += len(a & b); fn += len(a - b); fp += len(b - a)
    print(f"{c:14}{100*cov_c:8.1f}%{100*cov_r:8.1f}%{100*tp/max(1,tp+fn):8.1f}%{100*tp/max(1,tp+fp):9.1f}%{fn:10}{fp:10}")

print("\n# 4-2. recall by persona (nf+iface+func+file+err_specific+spec values)")
key_cats = ["nf", "iface", "func", "file", "err_specific", "spec", "version", "config_key"]
by_p = defaultdict(lambda: [0, 0])
for k in ec:
    p = can[k]["persona"]
    for c in key_cats:
        a, b = set(ec[k][c]), set(er[k][c])
        by_p[p][0] += len(a & b); by_p[p][1] += len(a)
for p in sorted(by_p):
    tp, tot = by_p[p]
    print(f"{p}: recall={100*tp/max(1,tot):.1f}% (n_vals={tot})")

print("\n# 4-3. which field content was dropped: per-category lost examples")
for c in ["err_specific", "func", "spec_clause", "version"]:
    ex = []
    for k in ec:
        lost = set(ec[k][c]) - set(er[k][c])
        if lost:
            ex.append((k, can[k]["persona"], sorted(lost)[0][:70]))
    print(c, len(ex), ex[:4])

print("\n# 4-4. surface-form variants per canonical NF/interface (case-insensitive liberal match incl. hyphen/space/Korean)")
LIBERAL = {
    "gNB": r"g[- ]?n(?:ode)?[- ]?b|지엔비", "eNB": r"(?<!ng-)e[- ]?n(?:ode)?[- ]?b|이엔비", "AMF": r"amf|에이엠에프", "SMF": r"smf",
    "UPF": r"upf", "MME": r"mme|엠엠이", "SGW": r"s[- ]?gw(?:[- ]?[cu])?|serving gateway", "PGW": r"p[- ]?gw(?:[- ]?[cu])?|pdn gateway",
    "UE": r"ue|단말|user equipment", "NRF": r"nrf", "UDM": r"udm", "AUSF": r"ausf", "PCF": r"pcf", "HSS": r"hss",
    "CU": r"(?:gnb[- ]?)?cu(?:[- ](?:cp|up))?", "DU": r"(?:gnb[- ]?)?du",
    "NGAP": r"ngap|ng[- ]ap", "F1AP": r"f1[- ]?ap", "S1AP": r"s1[- ]?ap", "PFCP": r"pfcp", "GTP-U": r"gtp[- ]?v?1?[- ]?u",
    "SCTP": r"sctp", "NAS": r"nas", "RRC": r"rrc", "PDCP": r"pdcp", "RLC": r"rlc", "Diameter": r"diameter|다이어미터",
}
variants = {}
for canon_name, pat in LIBERAL.items():
    rx = re.compile(r"(?<![A-Za-z0-9_])(?:" + pat + r")(?![A-Za-z0-9_])", re.I)
    forms_c, forms_r = Counter(), Counter()
    for k in can:
        forms_c.update(m.group(0) for m in rx.finditer(record_text(can[k])))
        forms_r.update(m.group(0) for m in rx.finditer(record_text(rec[k])))
    strict_aliases = NF_ALIASES.get(canon_name) or IFACE_ALIASES.get(canon_name) or []
    strict_rx = re.compile("|".join(f"(?:{a})" for a in strict_aliases)) if strict_aliases else None
    missed_r = sum(n for f, n in forms_r.items() if strict_rx and not strict_rx.fullmatch(f))
    variants[canon_name] = (len(forms_c), len(forms_r), sum(forms_r.values()), missed_r)
    top_r = [f for f, _ in forms_r.most_common(10)]
    print(f"{canon_name:9} forms_can={len(forms_c):3} forms_rec={len(forms_rec) if False else len(forms_r):3} "
          f"mentions_rec={sum(forms_r.values()):5} missed_by_strict_rec={missed_r:4} top_rec={top_r}")
tot_forms_c = sum(v[0] for v in variants.values()); tot_forms_r = sum(v[1] for v in variants.values())
tot_m = sum(v[2] for v in variants.values()); tot_miss = sum(v[3] for v in variants.values())
print(f"TOTAL for {len(variants)} entities: forms canonical={tot_forms_c}, records={tot_forms_r}, "
      f"records mentions={tot_m}, missed by strict dict={tot_miss} ({100*tot_miss/tot_m:.1f}%)")

print("\n# 4-5. typo-like variants of identifiers introduced by rewriting (edit distance 1, token absent from canonical record)")


def ed1(a, b):
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1 or any(a[:i] + a[i+1] + a[i] + a[i+2:] == b for i in range(len(a) - 1))
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i+1:] == a for i in range(len(b)))


TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]{2,40}")
typo_records, typo_examples, typo_by_persona = 0, Counter(), Counter()
for k in can:
    ctoks = set(TOK.findall(record_text(can[k])))
    rtoks = set(TOK.findall(record_text(rec[k])))
    new = rtoks - ctoks
    found = False
    for t in new:
        for ct in ctoks:
            if len(ct) >= 4 and ed1(t, ct) and t.lower() != ct.lower():
                typo_examples[(ct, t)] += 1
                found = True
                break
    if found:
        typo_records += 1
        typo_by_persona[can[k]["persona"]] += 1
print(f"records with >=1 edit-distance-1 identifier variant: {typo_records} ({100*typo_records/len(can):.1f}%)")
print(f"by persona: {dict(sorted(typo_by_persona.items()))}")
print(f"examples: {typo_examples.most_common(25)}")
case_only = Counter()
for k in can:
    ctoks = set(TOK.findall(record_text(can[k])))
    rtoks = set(TOK.findall(record_text(rec[k])))
    lc = {t.lower(): t for t in ctoks}
    for t in rtoks - ctoks:
        if t.lower() in lc:
            case_only[(lc[t.lower()], t)] += 1
print(f"case-only variants (records vs canonical): pairs={sum(case_only.values())} distinct={len(case_only)} examples={case_only.most_common(12)}")

print("\n# 4-6. SBI service name vs URI path forms (same service, two spellings) in canonical")
path_to_service = {"nnrf-nfm": "Nnrf_NFManagement", "nnrf-disc": "Nnrf_NFDiscovery", "nudm-sdm": "Nudm_SDM",
                   "nsmf-pdusession": "Nsmf_PDUSession", "namf-comm": "Namf_Communication", "nudm-uecm": "Nudm_UECM",
                   "nudm-ueau": "Nudm_UEAuthentication", "nausf-auth": "Nausf_UEAuthentication", "npcf-am-policy-control": "Npcf_AMPolicyControl",
                   "npcf-smpolicycontrol": "Npcf_SMPolicyControl", "nudr-dr": "Nudr_DataRepository", "nnssf-nsselection": "Nnssf_NSSelection",
                   "namf-evts": "Namf_EventExposure", "nsmf-event-exposure": "Nsmf_EventExposure"}
sbi_counter = Counter(v for e in ec.values() for v in e["sbi_service"])
paths = {k: n for k, n in sbi_counter.items() if not k[0].isupper()}
names = {k: n for k, n in sbi_counter.items() if k[0].isupper()}
print(f"service-name forms={len(names)} ({sum(names.values())} hits), URI-path forms={len(paths)} ({sum(paths.values())} hits)")
both = 0
for k in ec:
    s = set(ec[k]["sbi_service"])
    if any(p in s for p in path_to_service) and not any(path_to_service.get(p) in s for p in s if p in path_to_service):
        both += 1
print(f"records with only URI-path form of a mapped service (would not join a service-name node without mapping): {both}")
