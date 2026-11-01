import collections
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as e
from llm import ask, parse_json

OUT = Path(__file__).resolve().parent / "testset.jsonl"
SYSTEM = "You write evaluation questions for a Korean telecom defect search system. Reply with JSON only."

STYLE = """규칙:
- 현장 엔지니어가 사내 결함 검색 에이전트에 묻는 한국어 질문 1~2문장. 구어체여도 된다.
- 제목을 그대로 옮기지 말고 현상을 자기 말로 쓴다. case_code는 쓰지 않는다.
- NF·모듈·프로토콜 이름(AMF, PFCP, RRC 등)은 자연스럽게 써도 된다. 로그 문구는 넣더라도 짧게 하나만.
- 원인은 질문에 쓰지 않는다."""

TYPE_RULES = {
    "single": "현상을 설명하고 비슷한 과거 사례를 찾는 질문. {product_rule}",
    "multihop": "현상을 설명하고 원인이 뭔지, 원인이 밝혀진 비슷한 사례가 있는지 묻는다. {product_rule}",
    "fix": "현상을 설명하고 이게 고쳐졌는지, 패치나 수정 버전이 있는지 묻는다. {product_rule}",
    "composite": "현상을 설명하고 원인과 패치 여부를 한 질문에 함께 묻는다. {product_rule}",
    "clarify": "현상만 설명하고 비슷한 사례를 묻는다. 제품·저장소 이름(open5gs, magma, free5gc, OAI, OCUDU, srsRAN, neutron 등)과 SW 버전은 절대 쓰지 않는다.",
}
WITH_PRODUCT = "제품 이름 '{product}'를 질문에 자연스럽게 넣는다."
NO_PRODUCT = "제품·저장소 이름은 쓰지 않는다."


def dup_partners(code, canonical):
    out = {code}
    for r in canonical.values():
        if r["duplicate_of_case"] == code:
            out.add(r["case_code"])
    if canonical[code]["duplicate_of_case"]:
        out.add(canonical[code]["duplicate_of_case"])
    return sorted(out)


def pick(rng, pool, n):
    pool = sorted(pool, key=lambda r: r["case_code"])
    return rng.sample(pool, min(n, len(pool)))


def seeds(rng, c):
    can = c.canonical
    defects = [r for r in can.values() if r["record_type"] == "결함"]
    explicit = [r for r in defects if r["cause_basis"] == "명시"]
    ran = [r for r in explicit if r["origin"] == "ran-core"]
    adj = [r for r in explicit if r["origin"] == "adjacent-network"]
    used = set()

    def take(pool, n):
        chosen = pick(rng, [r for r in pool if r["case_code"] not in used], n)
        used.update(r["case_code"] for r in chosen)
        return chosen

    items = []
    for i, r in enumerate(take(ran, 24) + take(adj, 16)):
        items.append({"type": "single", "seed": r["case_code"], "with_product": i % 2 == 0,
                      "gold_cases": dup_partners(r["case_code"], can)})

    weak = []
    for r in defects:
        if r["cause_basis"] not in ("추론", "미상"):
            continue
        neighbors = sorted({o for rel, o in c.relations.get(r["case_code"], [])
                            if rel in ("duplicate", "xref") and can[o]["cause_basis"] == "명시"})
        if neighbors:
            weak.append((r, neighbors))
    weak.sort(key=lambda x: x[0]["case_code"])
    for r, neighbors in rng.sample(weak, 30):
        used.add(r["case_code"])
        items.append({"type": "multihop", "seed": r["case_code"], "with_product": True, "gold_cases": neighbors})

    by_status = collections.defaultdict(list)
    for r in defects:
        by_status[e.fix_status_of(r["resolution"])].append(r)
    quota = {"fixed_in_version": 7, "fix_ref_only": 7, "wont_fix": 6, "not_backported": 4, "workaround_only": 3, "unknown": 3}
    for status, n in quota.items():
        for r in take(by_status[status], n):
            items.append({"type": "fix", "seed": r["case_code"], "with_product": True,
                          "gold_cases": dup_partners(r["case_code"], can), "gold_status": status})
    quota_d = {"fixed_in_version": 6, "fix_ref_only": 8, "wont_fix": 5, "not_backported": 2, "workaround_only": 2, "unknown": 2}
    for status, n in quota_d.items():
        pool = [r for r in by_status[status] if r["cause_basis"] == "명시"]
        for r in take(pool, n):
            items.append({"type": "composite", "seed": r["case_code"], "with_product": True,
                          "gold_cases": dup_partners(r["case_code"], can), "gold_status": status})

    log_pool = []
    for r in explicit + [x for x in defects if x["cause_basis"] != "명시"]:
        logs = [m for m in re.findall(r"`([^`]{24,160})`", r["problem"])
                if re.search(r"error|fail|assert|exception|fatal|panic|refused|timeout|invalid|abort|segmentation", m, re.I)]
        if logs and r["case_code"] not in used:
            log_pool.append((r, logs[0]))
    log_pool.sort(key=lambda x: x[0]["case_code"])
    for r, log in rng.sample(log_pool, 30):
        used.add(r["case_code"])
        stamp = f"[2026-10-{rng.randint(10, 28)} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}.{rng.randint(0, 999):03d}]"
        question = f"현장에서 아래 로그가 반복해서 찍힙니다. 비슷한 사례와 원인 있으면 알려 주세요.\n{stamp} {log}"
        items.append({"type": "logpaste", "seed": r["case_code"], "question": question,
                      "gold_cases": dup_partners(r["case_code"], can)})

    clarify_pool = [r for r in explicit if r["case_code"] not in used and r["origin"] == "ran-core"]
    for r in take(clarify_pool, 35) + take([x for x in adj if x["case_code"] not in used], 15):
        items.append({"type": "clarify", "seed": r["case_code"], "with_product": False,
                      "gold_cases": dup_partners(r["case_code"], can),
                      "slots": {"product": e.product_of(r), "equipment": r["equipment"]}})

    items += aggregate_items(rng, c)
    return items


def aggregate_items(rng, c):
    combos = []
    for _ in range(400):
        f = {"equipment": rng.choice(e.EQUIPMENTS + [None]), "record_type": rng.choice(e.RECORD_TYPES + [None]),
             "year": rng.choice([None, *range(2015, 2027)]), "product": rng.choice([None, None, *e.PRODUCTS]),
             "cause_class": rng.choice([None, None, *e.CAUSE_CLASSES])}
        f = {k: v for k, v in f.items() if v is not None}
        if len(f) < 2:
            continue
        n = sum(1 for r in c.canonical.values() if c.matches(r, f))
        if n >= 3 and f not in [x for x, _ in combos]:
            combos.append((f, n))
        if len(combos) == 20:
            break
    items = []
    for f, n in combos:
        parts = []
        if "year" in f:
            parts.append(f"{f['year']}년에 등록된")
        if "product" in f:
            parts.append(f"{f['product']}")
        if "equipment" in f:
            parts.append(f"{f['equipment']} 장비")
        noun = {"결함": "결함", "CI·빌드": "CI·빌드 이슈", "기능 요청": "기능 요청"}.get(f.get("record_type"), "레코드")
        tail = f" 중 원인 분류가 '{f['cause_class']}'인 것" if "cause_class" in f else ""
        items.append({"type": "aggregate", "question": f"{' '.join(parts)} {noun}{tail}은 몇 건이야?",
                      "gold_count": n, "gold_filters": f})
    return items


def write_questions(items, c):
    jobs = collections.defaultdict(list)
    for it in items:
        if "question" not in it:
            jobs[it["type"]].append(it)
    batches = []
    for kind, group in jobs.items():
        for i in range(0, len(group), 10):
            batches.append((kind, group[i:i + 10]))

    def run(batch):
        kind, group = batch
        lines = []
        for it in group:
            r = c.canonical[it["seed"]]
            rule = TYPE_RULES[kind].format(product_rule=(WITH_PRODUCT.format(product=e.product_of(r))
                                                         if it.get("with_product") else NO_PRODUCT))
            lines.append(json.dumps({"id": it["seed"], "rule": rule, "title": r["title"], "location": r["location"],
                                     "problem": r["problem"][:500]}, ensure_ascii=False))
        prompt = (STYLE + "\n\n아래 레코드마다 rule에 맞는 질문을 하나씩 쓴다. 출력은 "
                  '[{"id": ..., "question": ...}] JSON 배열 하나.\n\n' + "\n".join(lines))
        reply = parse_json(ask(prompt, SYSTEM)["text"])
        return {x["id"]: x["question"] for x in reply}

    with ThreadPoolExecutor(6) as pool:
        written = {}
        for result in pool.map(run, batches):
            written.update(result)
    for it in items:
        if "question" not in it:
            it["question"] = written.get(it["seed"], "")
    return [it for it in items if it["question"]]


def unanswerable_items(c):
    prompt = ("오픈소스 5G/LTE(open5gs, free5GC, magma, OAI, srsRAN, OCUDU)와 OpenStack Neutron 이슈 트래커에는 없을 법한, "
              "상용 벤더 장비·현장 운용 문제를 묻는 현장 엔지니어 질문 40개를 한국어로 쓴다. 예: 특정 벤더 RU의 VSWR 알람, "
              "광중계기 온도, 상용 EMS 화면 오류, 전원 장치, 안테나 틸트. 각 질문에 그 질문만의 고유 명사·용어 2~3개를 key_terms로 붙인다. "
              '출력: [{"question": ..., "key_terms": [...]}] JSON 배열 하나.')
    reply = parse_json(ask(prompt, SYSTEM)["text"])
    corpus_text = " ".join(" ".join(r[f] for f in e.SEARCH_FIELDS) for r in c.records).lower()
    items = []
    for x in reply:
        if all(t.lower() not in corpus_text for t in x.get("key_terms", [])):
            items.append({"type": "unanswerable", "question": x["question"], "key_terms": x["key_terms"], "gold_cases": []})
    return items[:20]


def main():
    rng = random.Random(20261102)
    c = e.corpus()
    items = write_questions(seeds(rng, c), c) + unanswerable_items(c)
    counters = collections.Counter()
    for it in items:
        it["split"] = "dev" if counters[it["type"]] % 5 < 2 else "test"
        counters[it["type"]] += 1
        it["qid"] = f"{it['type']}-{counters[it['type']]:03d}"
    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(dict(counters), "→", OUT)


if __name__ == "__main__":
    main()
