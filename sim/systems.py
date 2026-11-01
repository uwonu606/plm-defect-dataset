import json
import re
import time

import engine as e
from llm import ask, parse_json

PRODUCT_WORDS = {
    "open5gs": r"open5gs|nextepc", "magma": r"magma|\bagw\b|orc8r", "free5gc": r"free5gc",
    "oai": r"\boai\b|openairinterface|nr-?softmodem|lte-softmodem|nrue", "ocudu": r"ocudu",
    "srsran": r"srsran|srsue|srsenb|srsgnb|srsepc", "neutron": r"neutron|\bml2\b|ovs agent|l3 ?agent|openstack",
    "redhat": r"red ?hat|openshift|\bocp\b",
}
EQUIPMENT_HINTS = {
    "CORE": r"\b(amf|smf|upf|nrf|udm|udr|ausf|pcf|nssf|mme|sgw|pgw|hss|pcrf|sbi|pfcp|gtp)\b",
    "RAN-CU": r"\b(cu-?cp|cu-?up|rrc|pdcp|ngap|f1ap|e1ap|s1ap|x2ap|xnap)\b",
    "RAN-DU": r"\b(phy|mac|rlc|scheduler|fronthaul|ldpc|harq|prach|pusch|pdsch|du)\b|스케줄러",
    "UE": r"\b(ue|nrue|srsue)\b|단말",
    "OAM": r"\b(netconf|yang|o1|ems|oam)\b",
}
INTENTS = {
    "aggregate": r"몇 ?건|건수|몇 ?개|통계",
    "fix": r"패치|고쳐|고친|수정(된|됐|버전|본|사항)|fix|반영|백포트|어느 버전",
    "cause": r"원인|왜|이유|root ?cause",
}


def normalize(question):
    q = question.lower()
    slots = {"product": next((p for p, pat in PRODUCT_WORDS.items() if re.search(pat, q)), None),
             "equipment": next((eq for eq in e.EQUIPMENTS if re.search(rf"(?<![\w-]){re.escape(eq.lower())}(?![\w-])", q)), None),
             "year": (m.group(1) if (m := re.search(r"(20\d\d)년", q)) else None),
             "record_type": next((t for t in ("CI·빌드", "기능 요청", "결함") if t.lower() in q), None),
             "cause_class": next((cc for cc in e.CAUSE_CLASSES if cc in question), None)}
    hint = next((eq for eq, pat in EQUIPMENT_HINTS.items() if re.search(pat, q)), None)
    intents = {name for name, pat in INTENTS.items() if re.search(pat, q, re.I)}
    return slots, hint, intents


def rrf(*ranked_lists, weights=None):
    score = {}
    for n, ranked in enumerate(ranked_lists):
        w = (weights or [1] * len(ranked_lists))[n]
        for rank, code in enumerate(ranked):
            score[code] = score.get(code, 0) + w / (60 + rank)
    return [code for code, _ in sorted(score.items(), key=lambda x: -x[1])]


def code_abstain(question, tau):
    hits = e.search(question, k=1)
    return not e.find_by_identifier(question) and (not hits or hits[0]["score"] < tau)


def bm25_only(item, tau):
    hits = e.search(item["question"], k=10)
    top = hits[0]["score"] if hits else 0
    return {"cases": [h["case_code"] for h in hits], "fix_status": None, "count": None,
            "abstain": top < tau, "llm_calls": 0, "trace": [{"tool": "search", "top": top}]}


def fixed_dag(item, tau, normalize_fn=normalize):
    question = item["question"]
    slots, hint, intents = normalize_fn(question)
    trace = [{"slots": slots, "hint": hint, "intents": sorted(intents)}]
    if "aggregate" in intents:
        filters = {k: v for k, v in slots.items() if v}
        result = e.aggregate(filters)
        trace.append({"tool": "aggregate", "args": filters, "count": result["count"]})
        return {"cases": [], "fix_status": None, "count": result["count"], "abstain": False, "llm_calls": 0, "trace": trace}
    hard = {"product": slots["product"]} if slots["product"] else {}
    id_hits = [h["case_code"] for h in e.find_by_identifier(question)]
    bm = e.search(question, filters=hard, k=50, boost={"equipment": hint})
    top = bm[0]["score"] if bm else 0
    cases = rrf([h["case_code"] for h in bm], id_hits, weights=[1, 2])
    trace.append({"tool": "find_by_identifier", "n": len(id_hits)})
    trace.append({"tool": "search", "filters": hard, "top": top})
    abstain = not id_hits and top < tau
    if "cause" in intents:
        expanded = []
        for code in cases[:5]:
            expanded.append(code)
            if e.corpus().by_code[code]["cause_basis"] in ("추론", "미상"):
                neighbors = [n["case_code"] for n in e.expand_related(code) if n["cause_basis"] == "명시"]
                expanded += neighbors
                trace.append({"tool": "expand_related", "seed": code, "added": neighbors})
        cases = list(dict.fromkeys(expanded + cases))
    fix_status = None
    if "fix" in intents and cases:
        fix_status = e.trace_fix(cases[0])["status"]
        trace.append({"tool": "trace_fix", "case": cases[0], "status": fix_status})
    return {"cases": cases[:10], "fix_status": fix_status, "count": None, "abstain": abstain, "llm_calls": 0, "trace": trace}


LOOP_SYSTEM = """너는 통신 장비 결함 검색 에이전트다. 사용자의 질문에 답하려고 도구를 부른다.
매 응답은 JSON 하나만 출력한다.
- 도구 호출: {"tool": 이름, "args": {...}}
- 마침: {"final": {"cases": [관련 높은 순 case_code 최대 10개], "fix_status": status 문자열 또는 null, "count": 정수 또는 null, "abstain": true/false}}
규칙: 도구는 최대 6번 부른다. 데이터에 관련 사례가 없으면 abstain=true. 원인을 물으면 원인이 명시(cause_basis=명시)된 사례를 앞에 둔다.
수정 여부를 물으면 trace_fix의 status를 그대로 쓴다. 건수를 물으면 aggregate의 count를 그대로 쓴다. 질문에 없는 값을 지어내 필터로 넣지 않는다.
""" + e.TOOL_DOC


def clip(value, limit=2400):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…(생략)"


def llm_loop(item, tau, model="haiku", max_tools=6):
    history, trace, calls, spent = [], [], 0, 0.0
    final = None
    for step in range(max_tools + 1):
        force = step == max_tools
        prompt = f"질문: {item['question']}\n\n" + "\n".join(history) + \
                 ("\n\n도구 한도에 닿았다. 지금 final JSON을 출력한다." if force else "\n\n다음 JSON을 출력한다.")
        reply = ask(prompt, LOOP_SYSTEM, model=model)
        calls += 1
        spent += reply["seconds"]
        try:
            action = parse_json(reply["text"])
        except ValueError:
            history.append(f"[{step + 1}] 응답이 JSON이 아니었다: {reply['text'][:100]}")
            trace.append({"error": "not json"})
            continue
        if "final" in action or force:
            final = action.get("final", action)
            break
        result = e.call_tool(action.get("tool"), action.get("args"))
        trace.append({"tool": action.get("tool"), "args": action.get("args")})
        history.append(f"[{step + 1}] 호출 {clip(action, 400)}\n결과 {clip(result)}")
    final = final or {}
    cases = [c for c in final.get("cases") or [] if isinstance(c, str)]
    return {"cases": cases[:10], "fix_status": final.get("fix_status"), "count": final.get("count"),
            "abstain": bool(final.get("abstain")), "llm_calls": calls, "llm_seconds": round(spent, 1), "trace": trace}


PLAN_SYSTEM = """너는 통신 장비 결함 검색 에이전트의 planner다. 질문을 보고 실행 계획을 JSON 하나로 세운다. 도구 결과는 보지 못한다.
형식: {"steps": [{"id": "s1", "tool": 이름, "args": {...}}, ...], "answer": {"cases": [case 목록을 낼 단계 id들], "fix_status": 단계 id 또는 null, "count": 단계 id 또는 null}}
- 단계는 최대 5개. args 값에 "$s1.top"(s1 결과 1위 case_code) 또는 "$s1.top3"(1~3위 각각에 같은 단계를 펼침)을 쓸 수 있다.
- 로그나 함수명이 있으면 find_by_identifier를 함께 쓴다. 원인을 물으면 expand_related로 원인이 명시된 이웃을 찾는다.
- 수정 여부는 trace_fix, 건수는 aggregate. 질문에 없는 값을 지어내 필터로 넣지 않는다.
""" + e.TOOL_DOC


def resolve(value, results):
    if isinstance(value, str) and (m := re.fullmatch(r"\$(s\d+)\.top(\d*)", value.strip())):
        ranked = case_list(results.get(m.group(1)))
        return ranked[:int(m.group(2) or 1)]
    return None


def case_list(result):
    if isinstance(result, list):
        return [r["case_code"] for r in result if isinstance(r, dict) and "case_code" in r]
    return []


def llm_planner(item, tau, model="haiku"):
    reply = ask(f"질문: {item['question']}", PLAN_SYSTEM, model=model)
    trace, results, statuses = [], {}, {}
    try:
        plan = parse_json(reply["text"])
        steps = plan.get("steps", [])[:5]
    except (ValueError, AttributeError):
        return {"cases": [], "fix_status": None, "count": None, "abstain": True, "llm_calls": 1,
                "llm_seconds": reply["seconds"], "trace": [{"error": "plan not json"}]}
    for step in steps:
        args = dict(step.get("args") or {})
        fanout = None
        for key, value in list(args.items()):
            refs = resolve(value, results)
            if refs is not None:
                fanout = (key, refs[:3])
        if fanout:
            key, refs = fanout
            merged = []
            for ref in refs:
                out = e.call_tool(step.get("tool"), {**args, key: ref})
                merged.extend(out if isinstance(out, list) else [out])
            result = merged
        else:
            result = e.call_tool(step.get("tool"), args)
        results[step.get("id")] = result
        trace.append({"tool": step.get("tool"), "args": step.get("args"), "n": len(result) if isinstance(result, list) else 1})
    answer = plan.get("answer") or {}
    case_ids = answer.get("cases") or []
    case_ids = case_ids if isinstance(case_ids, list) else [case_ids]
    cases = rrf(*[case_list(results.get(i)) for i in case_ids]) if case_ids else []
    fix = results.get(answer.get("fix_status"))
    fix = fix[0] if isinstance(fix, list) and fix else fix
    count = results.get(answer.get("count"))
    abstain = not count and code_abstain(item["question"], tau)
    return {"cases": cases[:10], "fix_status": fix.get("status") if isinstance(fix, dict) else None,
            "count": count.get("count") if isinstance(count, dict) else None, "abstain": abstain,
            "llm_calls": 1, "llm_seconds": reply["seconds"], "trace": trace, "plan": plan}


SLOT_SYSTEM = "You classify Korean telecom defect questions. Reply with JSON only."


def llm_slot_batch(items, model="haiku"):
    lines = "\n".join(json.dumps({"qid": it["qid"], "question": it["question"]}, ensure_ascii=False) for it in items)
    prompt = ("질문마다 의도와 slot을 뽑는다. intents ⊆ [\"cause\", \"fix\", \"aggregate\"] (유사 사례 검색만이면 빈 목록). "
              f"product ∈ {e.PRODUCTS} 또는 null(질문에 제품 이름이 직접 나올 때만). equipment ∈ {e.EQUIPMENTS} 또는 null(질문에 장비군이 직접 나올 때만). "
              "year: 질문에 나온 4자리 연도 또는 null. record_type ∈ [결함, CI·빌드, 기능 요청] 또는 null. cause_class: 질문에 나온 원인 분류 이름 또는 null.\n"
              '출력: [{"qid":..., "intents": [...], "product":..., "equipment":..., "year":..., "record_type":..., "cause_class":...}]\n\n' + lines)
    reply = ask(prompt, SLOT_SYSTEM, model=model)
    return {x["qid"]: x for x in parse_json(reply["text"])}, reply["seconds"]


def llm_normalizer(table):
    def normalize_fn(question):
        row = table[question]
        slots = {k: (str(row.get(k)) if row.get(k) else None) for k in ("product", "equipment", "year", "record_type", "cause_class")}
        _, hint, _ = normalize(question)
        return slots, hint, set(row.get("intents") or [])
    return normalize_fn


FRONT_SYSTEM = "You preprocess Korean telecom defect questions for a search pipeline. Reply with JSON only."


def llm_front(question, model="haiku"):
    prompt = ("질문을 검색 파이프라인 입력으로 바꾼다. 데이터는 오픈소스 5G/LTE(open5gs, free5GC, magma, OAI, srsRAN, OCUDU)와 "
              "OpenStack Neutron·Red Hat 이슈 트래커의 결함 기록이다.\n"
              "- query: 검색용 키워드 문자열(한국어·영어 기술어 섞어 20단어 이내, 핵심 현상·모듈·메시지 이름)\n"
              "- intents ⊆ [\"cause\", \"fix\", \"aggregate\"]. cause=원인을 묻는다, fix=패치·수정 여부나 버전을 묻는다, "
              "aggregate=레코드 건수·통계를 묻는다(\"몇 건\"). 로그가 반복된다는 말이나 사례 찾기는 aggregate가 아니다\n"
              f"- product ∈ {e.PRODUCTS} 또는 null(질문에 직접 나올 때만), equipment ∈ {e.EQUIPMENTS} 또는 null(직접 나올 때만), "
              "year: 건수를 물으며 \"2020년\"처럼 연도를 조건으로 말할 때만(로그 타임스탬프는 아니다), record_type, cause_class: 질문에 직접 나올 때만, 아니면 null\n"
              "- in_scope: 이 데이터에 비슷한 기록이 있을 법하면 true, 상용 벤더 장비·현장 운용처럼 범위 밖이면 false\n"
              f'출력: {{"query":..., "intents": [...], "product":..., "equipment":..., "year":..., "record_type":..., "cause_class":..., "in_scope": true}}\n\n질문: {question}')
    reply = ask(prompt, FRONT_SYSTEM, model=model)
    return parse_json(reply["text"]), reply["seconds"]


def dag_llm_front(item, tau):
    front, seconds = llm_front(item["question"])
    slots = {k: (str(front.get(k)) if front.get(k) else None) for k in ("product", "equipment", "year", "record_type", "cause_class")}
    _, hint, _ = normalize(item["question"])
    intents = set(front.get("intents") or [])
    rewritten = {**item, "question": item["question"] + "\n" + str(front.get("query", ""))}
    out = fixed_dag(rewritten, tau=0, normalize_fn=lambda q: (slots, hint, intents))
    out["abstain"] = front.get("in_scope") is False
    out["llm_calls"], out["llm_seconds"] = 1, seconds
    out["trace"].insert(0, {"front": front})
    return out


def timed(fn, *args, **kwargs):
    started = time.monotonic()
    out = fn(*args, **kwargs)
    out["seconds"] = round(time.monotonic() - started, 2)
    return out
