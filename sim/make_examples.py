import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as e

SYSTEMS = ("bm25_only", "dag_regex", "dag_llm_front", "llm_loop", "llm_planner")
PER_TYPE = 1


def load(name):
    return {r["qid"]: r for r in map(json.loads, open(HERE / "results" / f"{name}.jsonl", encoding="utf-8"))}


def describe_trace(name, out):
    steps = []
    for t in out.get("trace", []):
        if "tool" in t:
            args = t.get("args") or {k: v for k, v in t.items() if k != "tool"}
            steps.append(f"{t['tool']}({json.dumps(args, ensure_ascii=False)[:90]})")
        elif "front" in t:
            steps.append(f"LLM 전처리(query={json.dumps(t['front'].get('query', ''), ensure_ascii=False)[:70]}, in_scope={t['front'].get('in_scope')})")
        elif "intents" in t:
            steps.append(f"slots={json.dumps({k: v for k, v in t['slots'].items() if v}, ensure_ascii=False)} intents={t['intents']}")
    return " → ".join(steps) or "-"


def main():
    items = [json.loads(line) for line in open(HERE / "testset.jsonl", encoding="utf-8")]
    results = {name: load(name) for name in SYSTEMS}
    picked, seen = [], {}
    for it in items:
        if it["split"] == "test" and it["type"] != "clarify" and seen.get(it["type"], 0) < PER_TYPE:
            picked.append(it)
            seen[it["type"]] = seen.get(it["type"], 0) + 1
    lines = ["# 시뮬레이션 예시", "",
             "test split에서 유형마다 첫 문항을 골라 다섯 구성의 실행 경로와 답을 나란히 둔다. 생성은 `python3 -I sim/make_examples.py`.", ""]
    for it in picked:
        gold = it.get("gold_cases") or []
        lines += [f"## {it['qid']}", "", "```text", it["question"], "```", ""]
        expect = []
        if gold:
            expect.append("정답 case: " + ", ".join(f"`{g}`" for g in gold))
        if "gold_status" in it:
            expect.append(f"정답 수정 상태: `{it['gold_status']}`")
        if "gold_count" in it:
            expect.append(f"정답 건수: {it['gold_count']}")
        if it["type"] == "unanswerable":
            expect.append("정답: 기권(데이터에 없음)")
        lines += ["- " + x for x in expect] + ["", "| 시스템 | 실행 경로 | 답 | LLM 호출 |", "|---|---|---|---|"]
        for name in SYSTEMS:
            out = results[name][it["qid"]]
            answer = []
            if out.get("abstain"):
                answer.append("기권")
            if out.get("cases"):
                marks = [f"**{c}**" if c in gold else c for c in out["cases"][:3]]
                answer.append("상위 3: " + ", ".join(marks))
            if out.get("fix_status"):
                answer.append(f"status={out['fix_status']}")
            if out.get("count") is not None:
                answer.append(f"count={out['count']}")
            lines.append(f"| {name} | {describe_trace(name, out)} | {'; '.join(answer) or '-'} | {out.get('llm_calls', 0)} |")
        lines.append("")
    (HERE / "examples.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", HERE / "examples.md")


if __name__ == "__main__":
    main()
