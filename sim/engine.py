import collections
import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRODUCT_OF_SOURCE = {
    "open5gs/open5gs": "open5gs",
    "magma/magma": "magma",
    "free5gc/free5gc": "free5gc",
    "oai/openairinterface5g": "oai",
    "duranta-project/openairinterface5g": "oai",
    "ocudu/ocudu": "ocudu",
    "srsran/srsRAN_4G": "srsran",
    "srsran/srsRAN_Project": "srsran",
    "launchpad:neutron": "neutron",
    "rhbz": "redhat",
}
PRODUCTS = sorted(set(PRODUCT_OF_SOURCE.values()))
EQUIPMENTS = ["RAN-CU", "RAN-DU", "UE", "CORE", "OAM", "PLATFORM"]
CAUSE_CLASSES = ["프로토콜 처리", "상태 관리", "입력 검증", "자원 관리", "동시성", "규격 미준수", "연동",
                 "설정", "성능·타이밍", "플랫폼", "빌드·의존성", "테스트", "구현 오류", "결함 아님"]
RECORD_TYPES = ["결함", "CI·빌드", "기능 요청"]
SEARCH_FIELDS = ("title", "title", "location", "problem", "cause", "resolution")


def product_of(record):
    return PRODUCT_OF_SOURCE[record["source_id"].split("#")[0]]


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


TOKEN = re.compile(r"[a-z0-9_]+|[가-힣]+")


def tokenize(text):
    out = []
    for tok in TOKEN.findall(text.lower()):
        if "가" <= tok[0] <= "힣" and len(tok) > 2:
            out.extend(tok[i:i + 2] for i in range(len(tok) - 1))
        else:
            out.append(tok)
    return out


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.postings = collections.defaultdict(list)
        self.lengths = []
        for i, doc in enumerate(docs):
            counts = collections.Counter(tokenize(doc))
            self.lengths.append(sum(counts.values()))
            for term, tf in counts.items():
                self.postings[term].append((i, tf))
        self.avg_length = sum(self.lengths) / len(self.lengths)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def scores(self, query):
        acc = collections.defaultdict(float)
        for term in sorted(set(tokenize(query))):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in self.postings[term]:
                norm = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_length)
                acc[i] += idf * tf * (self.k1 + 1) / norm
        return acc


IDENT_PATTERNS = [
    re.compile(r"`([^`]{6,160})`"),
    re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{3,})\(\)"),
    re.compile(r"\b((?:[\w.-]+/)+[\w.-]+\.(?:c|cc|cpp|h|hpp|py|go|rs|yaml|yml|conf))\b"),
]
LOG_LINE_NOISE = re.compile(r"^\s*(\[[^\]]*\]\s*|\d{4}-\d\d-\d\d[T ][\d:.,]+\s*|\d\d:\d\d:\d\d[.\d]*\s*)+")


def identifiers(text):
    found = set()
    for pattern in IDENT_PATTERNS:
        for value in pattern.findall(text):
            value = value.strip().lower()
            if len(value) >= 6 and not re.fullmatch(r"[\d.v]+", value):
                found.add(value)
    return found


class Corpus:
    def __init__(self):
        self.records = load_jsonl(ROOT / "dataset" / "records.jsonl")
        self.canonical = {r["case_code"]: r for r in load_jsonl(ROOT / "dataset" / "canonical.jsonl")}
        self.by_code = {r["case_code"]: r for r in self.records}
        self.codes = [r["case_code"] for r in self.records]
        self.index_of = {c: i for i, c in enumerate(self.codes)}
        self.bm25 = BM25([" ".join(r[f] for f in SEARCH_FIELDS) for r in self.records])
        self.ident_postings = collections.defaultdict(set)
        for r in self.records:
            text = " ".join(r[f] for f in ("title", "location", "problem", "cause"))
            for value in identifiers(text):
                self.ident_postings[value].add(r["case_code"])
        self.relations = self._load_relations()

    def _load_relations(self):
        pairs = json.load(open(ROOT / "analysis" / "round1" / "profile" / "out" / "pairs_all.json"))
        rel = collections.defaultdict(list)
        names = {"dup": "duplicate", "xref": "xref", "ref_mr_pr": "same_fix", "ref_commit": "same_fix"}
        for kind, a, b in pairs:
            if kind in names:
                rel[a].append((names[kind], b))
                rel[b].append((names[kind], a))
        return rel

    def matches(self, record, filters):
        for key, value in (filters or {}).items():
            if value in (None, "", []):
                continue
            if key == "product" and product_of(record) != value:
                return False
            if key == "equipment" and record["equipment"] != value:
                return False
            if key == "record_type" and record["record_type"] != value:
                return False
            if key == "cause_class" and record["cause_class"] != value:
                return False
            if key == "year" and record["created"][:4] != str(value):
                return False
        return True


@lru_cache(maxsize=1)
def corpus():
    return Corpus()


def summarize(record, snippet=110):
    return {
        "case_code": record["case_code"],
        "title": record["title"][:120],
        "equipment": record["equipment"],
        "product": product_of(record),
        "cause_basis": record["cause_basis"],
        "cause": record["cause"][:snippet],
    }


RETRIEVER = os.environ.get("SIM_RETRIEVER", "bm25")
RETRIEVERS = ("bm25", "hybrid", "rerank")
FUSION_DEPTH = 100
RERANK_DEPTH = 30


def results_dir():
    base = Path(__file__).resolve().parent / "results"
    return base if RETRIEVER == "bm25" else base / RETRIEVER


def boost_factor(record, boost):
    factor = 1.0
    for key, value in (boost or {}).items():
        if value and ((key == "product" and product_of(record) == value) or record.get(key) == value):
            factor *= 1.15
    return factor


def bm25_ranked(query, filters, boost):
    c = corpus()
    hits = []
    for i, score in c.bm25.scores(query).items():
        record = c.records[i]
        if c.matches(record, filters):
            hits.append((score * boost_factor(record, boost), record["case_code"], i))
    hits.sort(reverse=True)
    return hits


@lru_cache(maxsize=1)
def dense_matrix():
    import dense
    return dense.corpus_matrix(corpus().records)


def dense_ranked(query, filters):
    import dense
    c = corpus()
    sims = dense.similarities(dense_matrix(), query)
    order = sims.argsort()[::-1]
    hits = []
    for i in order:
        if c.matches(c.records[i], filters):
            hits.append(int(i))
            if len(hits) == FUSION_DEPTH:
                break
    return hits, sims


def search(query, filters=None, k=10, boost=None):
    bm = bm25_ranked(query, filters, boost)
    if RETRIEVER == "bm25":
        return [{"case_code": code, "score": round(score, 2)} for score, code, _ in bm[:k]]
    import dense
    c = corpus()
    dense_hits, sims = dense_ranked(query, filters)
    fused = collections.defaultdict(float)
    for rank, (_, _, i) in enumerate(bm[:FUSION_DEPTH]):
        fused[i] += 1 / (60 + rank)
    for rank, i in enumerate(dense_hits):
        fused[i] += 1 / (60 + rank)
    ranked = sorted(fused, key=lambda i: (-fused[i] * boost_factor(c.records[i], boost), c.codes[i]))
    if RETRIEVER == "hybrid":
        return [{"case_code": c.codes[i], "score": round(float(sims[i]), 4)} for i in ranked[:k]]
    candidates = ranked[:max(RERANK_DEPTH, k)]
    scores = dense.rerank_scores(query, [c.codes[i] for i in candidates], [dense.doc_text(c.records[i]) for i in candidates])
    reranked = sorted(zip(candidates, scores), key=lambda x: (-x[1] * boost_factor(c.records[x[0]], boost), c.codes[x[0]]))
    return [{"case_code": c.codes[i], "score": round(s, 4)} for i, s in reranked[:k]]


def find_by_identifier(text, max_df=10):
    c = corpus()
    lines = [LOG_LINE_NOISE.sub("", line).strip().lower() for line in text.splitlines()]
    probe = "\n".join(lines) + "\n" + text.lower()
    hits = collections.Counter()
    for value in sorted(identifiers(text) | {v for v in c.ident_postings if len(v) >= 12 and v in probe}):
        codes = c.ident_postings.get(value, ())
        if 0 < len(codes) <= max_df:
            for code in sorted(codes):
                hits[code] += len(value)
    ranked = sorted(hits.items(), key=lambda x: (-x[1], x[0]))[:10]
    return [{"case_code": code, "matched": weight} for code, weight in ranked]


def get_case(case_code):
    record = corpus().by_code.get(case_code)
    if not record:
        return {"error": f"unknown case_code {case_code}"}
    return {k: record[k] for k in ("case_code", "title", "equipment", "location", "problem", "cause",
                                   "cause_basis", "cause_class", "resolution", "created")} | {"product": product_of(record)}


def expand_related(case_code, relations=("duplicate", "xref")):
    c = corpus()
    out = []
    for relation, other in c.relations.get(case_code, []):
        if relation in relations and other in c.by_code:
            out.append({"relation": relation, **summarize(c.by_code[other])})
    return out


FIX_RULES = [
    ("wont_fix", re.compile(r"won'?t ?fix|고치지 않|수정하지 않기로|결함이 아니|정상 동작", re.I)),
    ("not_backported", re.compile(r"반영(하지 않|할 계획이 없|되지 않|안 ?됨)|백포트(하지|되지|안)|backport(ed)? (is )?not|not backport", re.I)),
    ("fixed_in_version", re.compile(r"(\bv?\d+\.\d+(\.\d+)?\b|\d+\.\d+\.\d+\.\d+b\d)[^.]{0,40}(에서|에|부터)[^.]{0,20}(고쳤|수정|반영|해결|들어갔|포함)|(고쳤|수정|반영|해결)[^.]{0,60}\bv?\d+\.\d+(\.\d+)?\b(에|부터|에서)", re.I)),
    ("fix_ref_only", re.compile(r"\b(PR|MR)\s*[#!]?\d+|pull/\d+|merge_requests/\d+|review \d{4,}|commit [0-9a-f]{7,}|\b[0-9a-f]{8,40}\b", re.I)),
    ("workaround_only", re.compile(r"우회|workaround", re.I)),
]
FIX_STATUSES = [name for name, _ in FIX_RULES] + ["unknown"]


def fix_status_of(resolution):
    for name, pattern in FIX_RULES:
        if pattern.search(resolution):
            return name
    return "unknown"


def trace_fix(case_code):
    record = corpus().by_code.get(case_code)
    if not record:
        return {"error": f"unknown case_code {case_code}"}
    return {"case_code": case_code, "status": fix_status_of(record["resolution"]), "evidence": record["resolution"][:200]}


def aggregate(filters):
    c = corpus()
    rows = [r for r in c.records if c.matches(r, filters)]
    excluded = sum(1 for r in rows if not r["cause_class"]) if not filters.get("cause_class") else 0
    return {"count": len(rows), "filters": {k: v for k, v in filters.items() if v}, "cause_class_empty": excluded}


TOOLS = {
    "search": lambda a: [summarize(corpus().by_code[h["case_code"]]) | {"score": h["score"]}
                         for h in search(a.get("query", ""), a.get("filters"), int(a.get("k", 8)))],
    "find_by_identifier": lambda a: [summarize(corpus().by_code[h["case_code"]]) for h in find_by_identifier(a.get("text", ""))],
    "get_case": lambda a: get_case(a.get("case_code", "")),
    "expand_related": lambda a: expand_related(a.get("case_code", "")),
    "trace_fix": lambda a: trace_fix(a.get("case_code", "")),
    "aggregate": lambda a: aggregate(a.get("filters") or {}),
}

TOOL_DOC = """도구(JSON args):
- search {"query": str, "filters": {"product"?, "equipment"?, "year"?, "record_type"?, "cause_class"?}, "k"?: int} → 유사 결함 목록(case_code, title, cause_basis, cause 앞부분, score)
- find_by_identifier {"text": str} → 로그 문구·함수명·파일 경로가 정확히 일치하는 결함
- get_case {"case_code": str} → 레코드 전체(problem, cause, resolution 포함)
- expand_related {"case_code": str} → 중복·교차참조로 이어진 결함(원인이 명시된 이웃 찾기에 쓴다)
- trace_fix {"case_code": str} → 수정 상태 status ∈ fixed_in_version | not_backported | wont_fix | fix_ref_only | workaround_only | unknown
- aggregate {"filters": {"product"?, "equipment"?, "year"?, "record_type"?, "cause_class"?}} → 조건에 맞는 레코드 수
filters 값: product ∈ """ + ", ".join(PRODUCTS) + "; equipment ∈ " + ", ".join(EQUIPMENTS) + \
    "; record_type ∈ " + ", ".join(RECORD_TYPES) + "; cause_class ∈ " + ", ".join(CAUSE_CLASSES) + "; year는 4자리 숫자"


def call_tool(name, args):
    if name not in TOOLS:
        return {"error": f"unknown tool {name}"}
    try:
        return TOOLS[name](args or {})
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
