"""openllm-kit 절차서로 결함 레코드를 축마다 2단계(대분류 → 하위)로 라벨링하고, 응답을 코드로 검증한다.

백엔드:
  openai  OpenAI 호환 chat completions(DeepSeek API, vLLM, llama.cpp server 등). --base-url, --model, --api-key-env.
  claude  Claude Code CLI(`claude -p`)로 같은 절차를 시험한다. sim/llm.py를 쓴다.
"""
import argparse
import collections
import hashlib
import json
import os
import random
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
REPO = KIT.parent
CLASSIFY = KIT / "classify"
AXES = ("problem", "cause", "resolution")
CODE_RULES = {"cause": lambda r: ("_na", "record_type") if r["record_type"] == "기능 요청" else None}


def squash(text):
    return re.sub(r"\s+", " ", text or "").strip().strip("\"'`").strip()


class OpenAIBackend:
    def __init__(self, base_url, model, api_key_env, extra_body, cache_dir, max_tokens, schema_mode):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model, self.key = model, os.environ.get(api_key_env, "")
        self.extra, self.cache, self.max_tokens, self.schema_mode = extra_body, cache_dir, max_tokens, schema_mode
        self.cache.mkdir(parents=True, exist_ok=True)

    def __call__(self, system, user, schema):
        body = {"model": self.model, "temperature": 0, "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], **self.extra}
        if self.schema_mode == "json_schema":
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "labels", "schema": schema, "strict": True}}
        elif self.schema_mode == "vllm":
            body["guided_json"] = schema
        key = hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())["text"]
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read())
        text = data["choices"][0]["message"].get("content") or ""
        path.write_text(json.dumps({"text": text, "usage": data.get("usage")}, ensure_ascii=False))
        return text


class ClaudeBackend:
    def __init__(self, model):
        sys.path.insert(0, str(REPO / "sim"))
        from llm import ask
        self.ask, self.model = ask, model

    def __call__(self, system, user, schema):
        return self.ask(user, system, model=self.model)["text"]


def parse_results(text):
    start = text.find("{")
    if start < 0:
        return []
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return []
    return value.get("results", []) if isinstance(value, dict) else []


def record_lines(records, fields):
    return "\n".join(json.dumps({"id": r["case_code"], **{f: r[f] for f in fields}}, ensure_ascii=False) for r in records)


def ask_stage(backend, system, schema, records, fields, allowed, needs_stop):
    by_id = {r["case_code"]: r for r in records}
    got = {}
    for item in parse_results(backend(system, record_lines(records, fields), schema)):
        rid = item.get("id")
        if rid not in by_id or rid in got:
            continue
        source = squash(" ".join(by_id[rid][f] for f in fields))
        evidence = squash(item.get("evidence", ""))
        got[rid] = {"label": item.get("label"), "stop": item.get("stop"), "evidence": item.get("evidence", ""),
                    "label_ok": item.get("label") in allowed,
                    "evidence_ok": bool(evidence) and evidence in source,
                    "stop_ok": (not needs_stop) or isinstance(item.get("stop"), int)}
    return got


def run_stage(backend, system, schema, records, fields, allowed, needs_stop, batch, pool):
    batches = [records[i:i + batch] for i in range(0, len(records), batch)]
    results = {}
    for part in pool.map(lambda b: ask_stage(backend, system, schema, b, fields, allowed, needs_stop), batches):
        results.update(part)
    retry = [r for r in records if r["case_code"] not in results or not results[r["case_code"]]["label_ok"]]
    for part in pool.map(lambda r: ask_stage(backend, system, schema, [r], fields, allowed, needs_stop), retry):
        for rid, value in part.items():
            if rid not in results or not results[rid]["label_ok"]:
                results[rid] = {**value, "retried": True}
    return results


def label_axis(backend, axis, records, batch, pool, manifest, common, classify_dir):
    meta = manifest["axes"][axis]
    fields = meta["evidence_fields"]
    out, todo = {}, []
    for r in records:
        rule = CODE_RULES.get(axis, lambda _: None)(r)
        if rule:
            out[r["case_code"]] = {"l1": rule[0], "label": rule[0], "stop": -1, "evidence": r[rule[1]],
                                   "by": "code", "valid": True, "evidence_ok": True}
        else:
            todo.append(r)
    system1 = common + "\n\n" + (classify_dir / axis / meta["l1_doc"]).read_text()
    schema1 = json.loads((classify_dir / axis / "1-l1.schema.json").read_text())
    first = run_stage(backend, system1, schema1, todo, fields, set(meta["l1_labels"]), True, batch, pool)
    groups = collections.defaultdict(list)
    for r in todo:
        res = first.get(r["case_code"])
        if not res or not res["label_ok"]:
            out[r["case_code"]] = {"l1": None, "label": None, "by": "model", "valid": False, "evidence_ok": False}
            continue
        out[r["case_code"]] = {"l1": res["label"], "label": res["label"], "stop": res["stop"], "evidence": res["evidence"],
                               "by": "model", "valid": res["stop_ok"], "evidence_ok": res["evidence_ok"]}
        if res["label"] in meta["stage2"]:
            groups[res["label"]].append(r)
    for l1, group in groups.items():
        stage = meta["stage2"][l1]
        system2 = common + "\n\n" + (classify_dir / axis / stage["doc"]).read_text()
        schema2 = json.loads((classify_dir / axis / stage["doc"].replace(".md", ".schema.json")).read_text())
        second = run_stage(backend, system2, schema2, group, fields, set(stage["labels"]), False, batch, pool)
        for r in group:
            res = second.get(r["case_code"])
            row = out[r["case_code"]]
            if res and res["label_ok"]:
                row.update(label=res["label"], evidence2=res["evidence"], evidence2_ok=res["evidence_ok"])
            else:
                row.update(stage2_failed=True)
    return out


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0


def l1_of(label):
    return label if not label or label.startswith("_") else ".".join(label.split(".")[:2])


def compare(rows_a, rows_b, axis):
    common_ids = sorted(set(rows_a) & set(rows_b))
    pairs = [(rows_a[c][axis], rows_b[c][axis]) for c in common_ids if rows_a[c][axis] and rows_b[c][axis]]
    l1 = [(l1_of(a), l1_of(b)) for a, b in pairs]
    return {"n": len(pairs), "l1_agree": round(sum(a == b for a, b in l1) / max(1, len(l1)), 4), "kappa_l1": kappa(l1),
            "leaf_agree": round(sum(a == b for a, b in pairs) / max(1, len(pairs)), 4), "kappa_leaf": kappa(pairs)}


def load_reference(path, version, sample, pass_name):
    ref = {}
    for line in open(path):
        r = json.loads(line)
        if r.get("taxonomy") == version and r.get("sample") == sample and r.get("pass") == pass_name:
            ref[r["case_code"]] = {ax: r[ax]["primary"] for ax in AXES}
    return ref


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", choices=("openai", "claude"), default="openai")
    ap.add_argument("--base-url", default="https://api.deepseek.com")
    ap.add_argument("--model", default="deepseek-v4-flash", help="openai 백엔드의 모델 id. claude 백엔드면 haiku 등")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--extra-body", default="{}", help='요청 본문에 더할 JSON. 예: thinking을 끄는 서버별 옵션')
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--schema-mode", choices=("json_object", "json_schema", "vllm"), default="json_object",
                    help="json_object: JSON 모드만. json_schema: OpenAI식 strict schema. vllm: guided_json")
    ap.add_argument("--case-codes", default=str(REPO / "taxonomy" / "heldout_case_codes.txt"))
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N건만(0이면 전부)")
    ap.add_argument("--axes", default=",".join(AXES))
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(KIT / "runs" / "latest"))
    ap.add_argument("--reference", default=str(REPO / "taxonomy" / "labels_sample.jsonl"),
                    help="비교할 기준 라벨(taxonomy/labels_sample.jsonl 형식)")
    ap.add_argument("--reference-version", default="v4")
    ap.add_argument("--reference-sample", default="heldout")
    ap.add_argument("--classify-dir", default=str(CLASSIFY), help="절차서 폴더(비교용으로 다른 판을 줄 때)")
    args = ap.parse_args()
    classify_dir = Path(args.classify_dir)

    manifest = json.loads((classify_dir / "manifest.json").read_text())
    common = (classify_dir / "common.md").read_text()
    canonical = {json.loads(l)["case_code"]: json.loads(l) for l in open(REPO / "dataset" / "canonical.jsonl", encoding="utf-8")}
    codes = [c.strip() for c in Path(args.case_codes).read_text().splitlines() if c.strip()]
    records = [canonical[c] for c in (codes[:args.limit] if args.limit else codes)]
    axes = [a for a in args.axes.split(",") if a]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.backend == "openai":
        backend = OpenAIBackend(args.base_url, args.model, args.api_key_env, json.loads(args.extra_body),
                                KIT / "runs" / "cache", args.max_tokens, args.schema_mode)
    else:
        backend = ClaudeBackend(args.model)

    passes = {}
    with ThreadPoolExecutor(args.workers) as pool:
        for p in range(args.passes):
            order = records[:]
            random.Random(1000 + p).shuffle(order)
            passes[p] = {axis: label_axis(backend, axis, order, args.batch, pool, manifest, common, classify_dir) for axis in axes}

    with open(out_dir / "labels.jsonl", "w", encoding="utf-8") as f:
        for p, by_axis in passes.items():
            for r in records:
                f.write(json.dumps({"case_code": r["case_code"], "pass": p,
                                    **{ax: by_axis[ax][r["case_code"]] for ax in axes}}, ensure_ascii=False) + "\n")

    flat = {p: {r["case_code"]: {ax: by_axis[ax][r["case_code"]]["label"] for ax in axes} for r in records}
            for p, by_axis in passes.items()}
    stats = {"backend": args.backend, "model": args.model, "records": len(records), "passes": args.passes, "axes": {}}
    for ax in axes:
        rows = [v for by_axis in passes.values() for v in by_axis[ax].values()]
        model_rows = [v for v in rows if v["by"] == "model"]
        stats["axes"][ax] = {
            "invalid": sum(1 for v in rows if not v["valid"] or v.get("label") is None),
            "stage2_failed": sum(1 for v in rows if v.get("stage2_failed")),
            "evidence_ok_l1": round(sum(v["evidence_ok"] for v in model_rows) / max(1, len(model_rows)), 4),
            "evidence_ok_l2": round(sum(v.get("evidence2_ok", False) for v in model_rows if "evidence2" in v)
                                    / max(1, sum(1 for v in model_rows if "evidence2" in v)), 4),
            "by_code": sum(1 for v in rows if v["by"] == "code"),
            "l1_share": dict(collections.Counter(l1_of(v["label"]) for v in passes[0][ax].values()).most_common()),
        }
        if args.passes > 1:
            stats["axes"][ax]["self_agreement"] = compare(flat[0], flat[1], ax)
    if args.reference and Path(args.reference).exists():
        ref = load_reference(args.reference, args.reference_version, args.reference_sample, "A")
        if ref:
            for ax in axes:
                stats["axes"][ax]["vs_reference"] = compare(flat[0], ref, ax)
            stats["reference"] = {"file": args.reference, "version": args.reference_version, "sample": args.reference_sample,
                                  "pass": "A", "matched": len(set(ref) & set(flat[0]))}
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
