import json
import re
import sys
from collections import Counter
sys.path.insert(0, "analysis/round1/profile")
from extract import load, record_text

OUT = "analysis/round1/profile/out"
can = {r["case_code"]: r for r in load("canonical")}
rec = {r["case_code"]: r for r in load("records")}
ec = json.load(open(f"{OUT}/entities_canonical.json"))

IMPL_ALIASES = {
    "gNB": [r"nr-softmodem", r"srsgnb", r"gnb_cu_cp", r"srsGNB", r"OAI gNB", r"gnb\.conf"],
    "UE": [r"nr-uesoftmodem", r"lte-uesoftmodem", r"srsue", r"srsUE", r"UERANSIM", r"nr-ue", r"단말"],
    "eNB": [r"lte-softmodem", r"srsenb", r"srsENB", r"기지국"],
    "MME": [r"open5gs-mmed", r"mmed", r"nextepc-mmed", r"oai-mme", r"magma_mme"],
    "AMF": [r"open5gs-amfd", r"amfd"], "SMF": [r"open5gs-smfd", r"smfd"], "UPF": [r"open5gs-upfd", r"upfd", r"gtp5g"],
    "SPGW/SGW/PGW": [r"spgw_u", r"spgw-u", r"open5gs-sgwcd", r"open5gs-sgwud", r"sgwcd", r"pgwd", r"srsepc", r"srsEPC"],
    "HSS": [r"open5gs-hssd", r"hssd", r"subscriberdb"],
    "magma AGW (MME+SPGW 기능 분산)": [r"sessiond", r"mobilityd", r"pipelined", r"sctpd", r"AGW", r"agw", r"FeG", r"feg", r"orc8r"],
    "core 일반어": [r"코어망?", r"core network", r"EPC", r"5GC"],
}
print("# implementation/product names that denote an NF (entity linking needed)")
tot_new = 0
for nf, pats in IMPL_ALIASES.items():
    rx = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(pats) + r")(?![A-Za-z0-9_])")
    hits_c = [k for k in can if rx.search(record_text(can[k]))]
    forms = Counter(m.group(0) for k in hits_c for m in rx.finditer(record_text(can[k])))
    target = nf.split("/")[0]
    only_impl = [k for k in hits_c if target in ("gNB", "UE", "eNB", "MME", "AMF", "SMF", "UPF", "HSS") and target not in ec[k]["nf"]]
    tot_new += len(only_impl)
    print(f"{nf:32} records={len(hits_c):5} distinct_forms={len(forms):3} records_without_canonical_token={len(only_impl):4} top={forms.most_common(6)}")
print(f"records that gain an NF only through impl-name aliases (single-NF targets): {tot_new}")

print("\n# record-level NF coverage: strict case-sensitive vs liberal (case-insensitive + impl names), canonical and records")
LIB = re.compile(r"(?<![A-Za-z0-9_])(?:amf|smf|upf|nrf|ausf|udm|udr|pcf|nssf|mme|s-?gw(?:-?[cu])?|p-?gw(?:-?[cu])?|spgw|hss|g-?nb|gnodeb|e-?nb|enodeb|ue|cu(?:-cp|-up)?|du|"
                 + "|".join(p for v in IMPL_ALIASES.values() for p in v) + r")(?![A-Za-z0-9_])", re.I)
for name, corpus in [("canonical", can), ("records", rec)]:
    cov = sum(1 for k in corpus if LIB.search(record_text(corpus[k])))
    by_origin = Counter(corpus[k]["origin"] for k in corpus if LIB.search(record_text(corpus[k])))
    print(f"{name}: liberal NF coverage={100*cov/len(corpus):.1f}% by origin={dict(by_origin)}")

print("\n# known persona typos in English identifiers (docs/personas.md: handvoer, recieve) and Korean colloquial NF terms")
for w in ["handvoer", "recieve", "recieved", "seesion", "sesion", "regsitration", "attatch", "죽음", "튐", "먹통", "기지국", "단말"]:
    c = sum(record_text(can[k]).count(w) for k in can)
    r = sum(record_text(rec[k]).count(w) for k in rec)
    print(f"{w}: canonical={c} records={r}")
