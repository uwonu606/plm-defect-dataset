import json, re, math, random, collections, sys, os
import multiprocessing as mp

PROFILE = "analysis/round1/profile"
sys.path.insert(0, PROFILE)
import extract as X
from extract import load, repo_of, NF_ALIASES, IFACE_ALIASES, SBI_SERVICE_RE, SBI_PATH_RE, SIGNAL_RE, normalize_signature


def latin_bounded(rx):
    return re.compile(rx.pattern.replace(r"(?![\w])", r"(?![A-Za-z0-9_])").replace(r"(?<![\w.])", r"(?<![A-Za-z0-9_.])"), rx.flags)


VERSION_RE = latin_bounded(X.VERSION_RE)
EXC_RE = latin_bounded(X.EXC_RE)
ASSERT_RE = X.ASSERT_RE
PANIC_RE = X.PANIC_RE


def bounded(alias):
    return r"(?<![A-Za-z0-9_-])" + alias + r"(?![A-Za-z0-9_-])"

OUT = os.path.dirname(os.path.abspath(__file__))
SEED = int(os.environ.get("SEED", "7"))
N_RAN, N_ADJ = int(os.environ.get("N_RAN", "200")), int(os.environ.get("N_ADJ", "100"))
TOPN = 20
MRR_CUT = 100

C = {r["case_code"]: r for r in load("canonical")}
R = {r["case_code"]: r for r in load("records")}
CODES = list(R)

# ---------- tokenizer ----------
VER_TOKEN_RE = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+)+)(?![\w])")


def tok(s):
    s = s.lower()
    out = []
    for v in VER_TOKEN_RE.findall(s):
        parts = v.split(".")
        out.append("ver:" + v)
        out.append("ver:" + ".".join(parts[:2]))
    out += re.findall(r"[a-z0-9_]{2,}", s)
    for run in re.findall(r"[가-힣]+", s):
        out += [run] if len(run) < 2 else [run[i:i + 2] for i in range(len(run) - 1)]
    return out


DOC_FIELDS = ["title", "location", "problem", "cause", "resolution"]
SYMPTOM_FIELDS = ["title", "location", "problem"]


def text_of(rec, fields):
    return "\n".join(rec.get(f) or "" for f in fields)


# ---------- slot surfaces ----------
def alt(pats, flags=0):
    return re.compile("|".join(bounded(p) for p in pats), flags)


EQUIP_PATS = [r"gNB(?:-CU(?:-CP|-UP)?|-DU)?", r"gNodeB", r"ng-eNB", r"eNB", r"eNodeB", r"CU(?:-CP|-UP)?", r"DU",
              r"UE", r"nrUE", r"lteUE", r"O-RU", r"RU", r"Near-RT RIC", r"RIC", r"OAM", r"EMS",
              r"단말", r"기지국", r"코어망?"]
EQUIP_RE = alt(EQUIP_PATS)
EQUIP_CANON = [("gnb", re.compile(r"(?i)gnb|gnodeb")), ("enb", re.compile(r"(?i)enb|enodeb")),
               ("cu", re.compile(r"^CU")), ("du", re.compile(r"^DU")), ("ue", re.compile(r"(?i)ue$|단말")),
               ("ru", re.compile(r"RU")), ("ric", re.compile(r"RIC")), ("oam", re.compile(r"OAM|EMS")),
               ("core", re.compile(r"코어"))]

PROD_PATS = [r"open5gs", r"free5gc", r"magma", r"openairinterface5g", r"openairinterface", r"OAI", r"ocudu",
             r"srsRAN(?:_4G|_Project)?", r"srsENB", r"srsUE", r"srsGNB", r"srsEPC", r"srsCU", r"srsDU",
             r"neutron", r"quantum", r"duranta", r"openshift", r"OSP", r"RHOSP"]
PROD_RE = alt(PROD_PATS, re.I)

CORE_NF = ["AMF", "SMF", "UPF", "NRF", "AUSF", "UDM", "UDR", "PCF", "NSSF", "NEF", "BSF", "SCP", "SEPP",
           "N3IWF", "SMSF", "CHF", "MME", "SGW", "PGW", "SPGW", "HSS", "PCRF", "EPC", "5GC"]
NFIF_ALIASES = {k: v for k, v in NF_ALIASES.items() if k in CORE_NF}
NFIF_ALIASES.update(IFACE_ALIASES)
NFIF_RES = {canon: alt(pats) for canon, pats in NFIF_ALIASES.items()}
NFIF_ANY = re.compile("|".join(bounded(p) for pats in NFIF_ALIASES.values() for p in pats)
                      + "|" + SBI_SERVICE_RE.pattern + "|" + SBI_PATH_RE.pattern)

ERR_KW = re.compile(r"(?i)error|fail|assert|exception|abort|fatal|panic|segfault|sigsegv|timeout|timed out|"
                    r"refused|denied|invalid|cannot|can't|unable|not found|traceback|errno|warn|crash|core dump|"
                    r"no such|unknown|unexpected|mismatch|reject")
BACKTICK_SPAN_RE = re.compile(r"`[^`\n]{1,300}`")


def error_spans(text):
    spans = []
    for m in BACKTICK_SPAN_RE.finditer(text):
        if ERR_KW.search(m.group(0)):
            spans.append((m.start(), m.end()))
    for rx in (EXC_RE, SIGNAL_RE, ASSERT_RE, PANIC_RE):
        for m in rx.finditer(text):
            spans.append((m.start(), m.end()))
    return spans


def regex_spans(rx, text):
    return [(m.start(), m.end()) for m in rx.finditer(text)]


def remove_spans(text, spans):
    if not spans:
        return text
    spans = sorted(spans)
    out, last = [], 0
    for s, e in spans:
        if s < last:
            s = last
        if e <= s:
            continue
        out.append(text[last:s])
        out.append(" ")
        last = e
    out.append(text[last:])
    t = "".join(out)
    t = re.sub(r"\(\s*\)|\[\s*\]|`\s*`", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_version(v):
    v = v.strip().lower()
    m = re.fullmatch(r"v?(\d+)\.(\d+)(?:\..*)?", v)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return re.sub(r"\s+", "", v).removeprefix("stable/")


def versions_in(text):
    return {norm_version(m.group(1)) for m in VERSION_RE.finditer(text)}


def nfif_in(text):
    vals = {canon for canon, rx in NFIF_RES.items() if rx.search(text)}
    vals |= {m.group(1).split("_")[0].lower() for m in SBI_SERVICE_RE.finditer(text)}
    vals |= {m.group(1).split("-")[0].lower() for m in SBI_PATH_RE.finditer(text)}
    return vals


def err_norm(s):
    s = s.strip("`'\" ").lower()
    return normalize_signature(s)


def errors_in(text):
    return {err_norm(text[s:e]) for s, e in error_spans(text)} - {""}


SLOTS = ["equipment", "repo", "version", "nf_if", "error"]


def surface_spans(slot, text):
    if slot == "equipment":
        return regex_spans(EQUIP_RE, text)
    if slot == "repo":
        return regex_spans(PROD_RE, text)
    if slot == "version":
        return regex_spans(VERSION_RE, text)
    if slot == "nf_if":
        return regex_spans(NFIF_ANY, text)
    if slot == "error":
        return error_spans(text)


# ---------- doc slot values (from records, the indexed text) ----------
DOC_VALUES = {}
DOC_NORM_TEXT = {}
for c, r in R.items():
    sym = text_of(r, SYMPTOM_FIELDS)
    full = text_of(r, DOC_FIELDS)
    DOC_VALUES[c] = {
        "equipment": {r["equipment"]},
        "repo": {repo_of(r["source_id"])},
        "version": versions_in(full),
        "nf_if": nfif_in(sym),
        "error": errors_in(full),
    }
    DOC_NORM_TEXT[c] = normalize_signature(full.lower())

# ---------- BM25 ----------
docs = {c: tok(text_of(R[c], DOC_FIELDS)) for c in CODES}
N = len(docs)
avg = sum(map(len, docs.values())) / N
K1, B = 1.2, 0.75
inv = collections.defaultdict(dict)
for c, t in docs.items():
    dl = len(t)
    for w, n in collections.Counter(t).items():
        inv[w][c] = n * (K1 + 1) / (n + K1 * (1 - B + B * dl / avg))
for w, p in inv.items():
    idf = math.log(1 + (N - len(p) + .5) / (len(p) + .5))
    for c in p:
        p[c] *= idf
del docs


def search(q):
    sc = collections.Counter()
    for w in set(tok(q)):
        p = inv.get(w)
        if p:
            for c, v in p.items():
                sc[c] += v
    return [c for c, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))]


def rank_of(ranking, golds, keep=None, exclude=frozenset()):
    r = 0
    for c in ranking:
        if c in exclude or (keep is not None and not keep(c)):
            continue
        r += 1
        if c in golds:
            return r
    return None


def metrics(rank):
    return {"hit5": int(rank is not None and rank <= 5),
            "hit20": int(rank is not None and rank <= 20),
            "rr": (1.0 / rank) if rank is not None and rank <= MRR_CUT else 0.0,
            "rank": rank}


def split_stats(ranking, slot):
    top = ranking[:TOPN]
    w = collections.Counter()
    for c in top:
        vals = DOC_VALUES[c][slot] or {"<none>"}
        for v in vals:
            w[v] += 1.0 / len(vals)
    total = sum(w.values()) or 1.0
    ent = -sum((x / total) * math.log2(x / total) for x in w.values() if x > 0)
    top_val, top_w = w.most_common(1)[0] if w else ("<none>", 0)
    with_value = sum(1 for c in top if DOC_VALUES[c][slot])
    return {"entropy": ent, "max_share": top_w / total, "top_value": top_val,
            "n_values": len(w), "with_value": with_value}


def keep_fn(slot, gold_vals):
    if slot == "error":
        def keep(c):
            t = DOC_NORM_TEXT[c]
            return any(g in t for g in gold_vals)
        return keep
    return lambda c: bool(DOC_VALUES[c][slot] & gold_vals)


def first_sentence(text):
    text = re.sub(r"^\[[^\]]{1,20}\]\s*", "", text.strip())
    parts = re.split(r"(?<=[.다])\s+", text)
    s = parts[0]
    if len(s) < 25 and len(parts) > 1:
        s += " " + parts[1]
    return s


def gold_values(slot, case, removed_text):
    if slot == "equipment":
        return {C[case]["equipment"]}
    if slot == "repo":
        return {repo_of(C[case]["source_id"])}
    if slot == "version":
        return versions_in(removed_text)
    if slot == "nf_if":
        return nfif_in(removed_text)
    if slot == "error":
        return errors_in(removed_text)


def run_query(args):
    case, qtype, q, golds, exclude = args
    golds, exclude = frozenset(golds), frozenset(exclude)
    full_rank_list = search(q)
    base = metrics(rank_of(full_rank_list, golds, None, exclude))
    out = {"case": case, "golds": sorted(golds), "qtype": qtype, "origin": C[case]["origin"], "q": q, "full": base, "slots": {}}
    for slot in SLOTS:
        spans = surface_spans(slot, q)
        present = bool(spans)
        removed_text = " ".join(q[s:e] for s, e in spans)
        q_minus = remove_spans(q, spans) if present else q
        ranking = search(q_minus) if present else full_rank_list
        minus = metrics(rank_of(ranking, golds, None, exclude))
        gv = gold_values(slot, case, removed_text) if (present or slot in ("equipment", "repo")) else set()
        gold_has = bool(gv) and any(keep_fn(slot, gv)(g) for g in golds)
        filt = metrics(rank_of(ranking, golds, keep_fn(slot, gv), exclude)) if gv else None
        split = split_stats([c for c in ranking[:TOPN + len(exclude)] if c not in exclude], slot)
        own_vals = DOC_VALUES[case][slot]
        nat_filt = None
        if not present and own_vals and slot in ("version", "nf_if", "error"):
            nat_filt = metrics(rank_of(ranking, golds, keep_fn(slot, own_vals), exclude))
            nat_soft = metrics(rank_of(search(q + " " + " ".join(sorted(own_vals))), golds, None, exclude))
        else:
            nat_soft = None
        out["slots"][slot] = {"present": present, "q_minus": q_minus, "minus": minus, "gold_vals": sorted(gv),
                              "gold_has_value": gold_has, "filtered": filt, "split": split,
                              "gold_doc_has_slot": bool(own_vals), "nat_filtered": nat_filt, "nat_soft": nat_soft,
                              "query_removed_all": present and not q_minus.strip()}
    return out


MODE = os.environ.get("MODE", "self")
PAIRS = PROFILE + "/out/pairs_all.json"


def neighbors():
    nb = collections.defaultdict(set)
    for kind, a, b in json.load(open(PAIRS)):
        if kind in ("dup", "xref"):
            nb[a].add(b); nb[b].add(a)
    return nb


def sample_cases(pool_filter=lambda c: True):
    rnd = random.Random(SEED)
    expl = [c for c, r in C.items() if r["cause_basis"] == "명시" and pool_filter(c)]
    ran = sorted(c for c in expl if C[c]["origin"] == "ran-core")
    adj = sorted(c for c in expl if C[c]["origin"] != "ran-core")
    return rnd.sample(ran, min(N_RAN, len(ran))) + rnd.sample(adj, min(N_ADJ, len(adj)))


if __name__ == "__main__":
    if MODE == "neighbor":
        nb = neighbors()
        cases = sample_cases(lambda c: c in nb)
        target = {c: (nb[c], {c}) for c in cases}
    else:
        cases = sample_cases()
        target = {c: ({c}, set()) for c in cases}
    jobs = []
    for c in cases:
        g, ex = target[c]
        jobs.append((c, "title", C[c]["title"], g, ex))
        p1 = first_sentence(C[c]["problem"])
        jobs.append((c, "problem1", p1, g, ex))
        jobs.append((c, "short6", " ".join(p1.split()[:6]), g, ex))
    with mp.get_context("fork").Pool(int(os.environ.get("PROCS", "16"))) as pool:
        res = pool.map(run_query, jobs, chunksize=4)
    tag = os.environ.get("TAG", f"{MODE}_s{SEED}_{N_RAN}_{N_ADJ}")
    with open(f"{OUT}/results_{tag}.jsonl", "w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", len(res), f"{OUT}/results_{tag}.jsonl")
