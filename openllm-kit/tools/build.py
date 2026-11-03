"""taxonomy/*.json(원천)에서 오픈 LLM용 절차서·스키마·키워드 사전을 만든다. 원천은 고치지 않는다."""
import csv
import json
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SOURCE = KIT.parent / "taxonomy"
AXES = ("problem", "cause", "resolution")

EVIDENCE_FIELDS = {
    "problem": ["record_type", "title", "problem"],
    "cause": ["record_type", "cause", "resolution"],
    "resolution": ["record_type", "resolution"],
}

QUESTIONS = {
    "problem": [
        ("이미 동작하던 process·서비스가 예기치 않게 끝났거나(crash, abort, assert, panic, 스스로 재시작) 응답 없이 멈췄나?", "p.halt"),
        ("설치하거나 기동·초기화하는 단계가 끝나지 않았나?", "p.stage.install|p.stage.startup"),
        ("단말·가입자·peer 노드·관리 시스템 사이의 접속 수립, 연결 유지, 데이터 전달이 실패하거나 나빠졌나?", "p.conn"),
        ("인증·권한·격리·무결성 같은 보안 통제가 적용되지 않아, 허용되면 안 되는 접근·조작·노출이 가능한가?", "p.sec"),
        ("process는 살아 있는데 요청·작업이 오류로 끝나거나 결과·상태가 기대·규격·운영자 설정과 다른가?", "p.func"),
        ("결과는 맞지만 느리거나, 처리량이 모자라거나, 자원을 필요 이상 쓰거나 계속 늘리나?", "p.perf"),
        ("서비스 증상 없이 장비·부품·설비·자원 상태가 정상 범위를 벗어났거나 곧 벗어난다고 보고됐나?", "p.state"),
        ("제품 동작은 맞고 문서·예시 설정·로그·경고·알람·화면 문구가 틀리거나 빠지거나 헷갈리게 하나?", "p.info"),
        ("빌드하거나 시험하는 단계(compile, CI job, 시험 실행)가 실패했나?", "p.stage.build|p.stage.test"),
        ("있는 기능의 오동작이 아니라, 없는 기능·지원이나 코드·시험·절차 보강이 요청 배경인가?", "p.gap"),
    ],
    "cause": [
        ("결함이 아니라고 판정됐나(설계대로, 미지원, 분석 도구 오탐, 보고자의 규격·코드 오독)?", "_na"),
        ("원인 서술과 해결 서술 어디에도 무엇이 어떻게 틀렸는지(메커니즘)가 없나? '고쳤다', 'PR #N', '최신 버전에서 해결', '시험을 끔'뿐이면 예. 원인을 단정한 문장이 있으면 짧아도 아니오.", "_none"),
        ("함께 쓰는 외부 구성요소(우리 레포 밖의 library·kernel module·toolchain·연동 시스템)가 의도적으로 바뀌었거나(새 버전의 API·기본값·동작 변경), 선언·설치된 버전이 맞지 않거나 빠졌나? 고친 곳이 시험 코드여도 예. 외부 구성요소는 그대로인데 우리가 잘못 썼거나, 외부 구성요소 자체의 bug거나, 우리 코드 안의 모듈 연결이 빠졌으면 아니오.", "c.supply"),
        ("결함이 시험 자산(test case, fixture, 시험 데이터, 판정 기준, 시험 job 구성) 안에 있나?", "c.test"),
        ("제품과 운용 조직이 통제하지 않는 외부 사건·조건(정전, 물리 손상, 공격, 외부 서비스 장애)이 원인인가?", "c.env"),
        ("HW 요소(장비·보드·부품·회로·FPGA 논리)의 설계나 물리 상태가 원인인가?", "c.hw"),
        ("사람이 수행한 작업 절차나 망·시스템의 구성·용량 설계가 원인인가?", "c.operation"),
        ("코드는 맞고 설정 값·기본값·정책 파일·가입자·망 데이터·문서 내용이 틀렸거나 빠졌나?", "c.content"),
        ("빌드 스크립트·패키지 manifest·CI pipeline처럼 산출물을 만드는 정의가 틀렸나?", "c.supply"),
        ("SW·FW 소스 코드가 의도·요구·계약과 다르게 작성됐나? 외부 library·kernel의 bug도 예.", "c.code"),
    ],
    "resolution": [
        ("기록이 다루는 제품(배포되는 SW·HW·기본 설정·문서·시험·빌드 산출물)이 바뀌었고 그 변경이 들어갔다고 적혔나?", "r.change"),
        ("제품은 그대로 두고 이 설치·현장의 설정·버전·환경·장비를 바꾸거나 서비스를 되살렸나, 또는 그렇게 하라는 구체적 안내가 있나?", "r.field"),
        ("작업 절차·검토·교육·감시·연락 체계처럼 일하는 방식을 바꿨나?", "r.process"),
        ("책임자가 조사나 검토 뒤 제품을 바꾸지 않기로 판정하고 닫았나?", "r.verdict"),
        ("해결도 판정도 없지만, 고치겠다는 약속, 반영되지 않은 수정안(patch·PR·보고자가 제시한 수정), 해결 없이 닫힌 사실(자동 종료·정리 라벨) 가운데 하나는 적혔나?", "r.unresolved"),
    ],
}

QUESTION_NOTES = {
    "problem": "Q1~Q9는 실행에서 관찰됐거나 코드 검토로 예상된 잘못된 동작을 묻는다. 개선·기능 요청이 바라는 상태(더 빠르게, 더 적게, 새로 지원)는 관찰된 잘못이 아니므로 Q10이다. 증상이 여럿이면 먼저 \"예\"가 나온 쪽이 주 라벨이다. 질문 순서가 서비스 영향 순서다. 라벨이 둘 적힌 질문은 그 가운데 맞는 하나를 답한다.",
    "cause": "레코드 유형이 '기능 요청'이면 코드가 이미 _na로 정했으므로 이 문서까지 오지 않는다. Q1·Q2·Q3·Q4의 순서는 원천(taxonomy/cause.json 루트)이 정한 우선순위다. Q5 이후의 순서는 이 키트가 정했다. 나머지를 받는 c.code를 마지막에 둔 것이다.",
    "resolution": "조치가 여럿이면 먼저 \"예\"가 나온 쪽이 주 라벨이다. 질문 순서가 원천이 정한 결과의 강도 순서다.",
}

FALLBACK = {
    "problem": "어느 질문에도 \"예\"가 없으면: 기술 증상을 판정할 내용이 없으면 `_none`, 현상도 부족함도 없는 작업 기록·문의면 `_na`, 현상은 있는데 맞는 곳이 없으면 `_other`.",
    "cause": "Q3~Q10 어디에도 \"예\"가 없고 메커니즘은 적혀 있으면 `_other`.",
    "resolution": "어느 질문에도 \"예\"가 없으면: 조치·판정·예정·종결 사실이 하나도 없으면 `_none`, 해결할 문제가 없는 기록이면 `_na`, 조치는 있는데 맞는 곳이 없으면 `_other`.",
}

AXIS_KO = {"problem": "문제점", "cause": "원인", "resolution": "해결책"}
FIELD_KO = {"record_type": "레코드 유형", "title": "제목", "problem": "현상", "cause": "원인 서술", "resolution": "해결 서술"}


def load(axis):
    return json.loads((SOURCE / f"{axis}.json").read_text())


def children_of(concepts):
    out = {}
    for c in concepts:
        out.setdefault(c["broader"], []).append(c)
    return out


def level(concept_id):
    return concept_id.count(".")


def l1_question_label(axis, label, kids):
    if "|" in label:
        return " 또는 ".join(f"`{x}`" for x in label.split("|"))
    if label.startswith("_") or label not in kids:
        return f"`{label}`"
    names = ", ".join(k["pref_label"]["ko"] for k in kids[label])
    return f"`{label}` (하위: {names})"


def stage1(axis, data):
    kids = children_of(data["concepts"])
    l1 = [c for c in data["concepts"] if level(c["id"]) == 1]
    fields = ", ".join(FIELD_KO[f] for f in EVIDENCE_FIELDS[axis])
    lines = [
        f"# {AXIS_KO[axis]} 축 1단계: 대분류 고르기",
        "",
        f"축의 질문은 \"{data['axis_definition']['criterion']}\"이다. 근거는 {fields}에서만 찾는다.",
        "",
        "## 할 일",
        "",
        "1. 레코드를 읽는다.",
        "2. 아래 질문을 Q1부터 차례로 묻고, 처음 \"예\"가 나온 질문에서 멈춘다. 그 질문의 라벨이 답이다.",
        "3. 멈춘 질문에 \"예\"라고 답하게 한 구절을 레코드 원문에서 그대로 복사해 evidence에 넣는다.",
        "",
        f"{QUESTION_NOTES[axis]}",
        "",
        "완료 기준: 레코드마다 `label`이 아래 라벨 목록 안의 값이고, `stop`이 멈춘 질문 번호(어느 질문에도 \"예\"가 없어 마지막 안내로 끝났으면 0)이고, `evidence`가 원문에 글자 그대로 있는 구절이다.",
        "",
        "## 질문",
        "",
        "| Q | 질문 | \"예\"이면 |",
        "|---|---|---|",
    ]
    for i, (question, label) in enumerate(QUESTIONS[axis], 1):
        lines.append(f"| {i} | {question} | {l1_question_label(axis, label, kids)} |")
    lines += ["", FALLBACK[axis], "", "## 대분류 정의", ""]
    for c in l1:
        lines.append(f"- `{c['id']}` {c['pref_label']['ko']} ({c['pref_label']['en']}): {c['definition']}")
    lines += ["", "## 특수 코드", ""]
    for s in data["special_codes"]:
        lines.append(f"- `{s['id']}`: {s['definition']}")
    lines += ["", "## 출력", "", "JSON 객체 하나만 낸다.", "", "```json",
              '{"results": [{"id": "<레코드 id>", "stop": 3, "label": "<라벨>", "evidence": "<원문 구절>"}]}',
              "```", ""]
    return "\n".join(lines)


def describe(c, depth_mark=""):
    out = [f"### {depth_mark}`{c['id']}` {c['pref_label']['ko']} ({c['pref_label']['en']})", ""]
    if c.get("std_mapping"):
        out.append(f"- 표준 대응: {c['std_mapping']}")
    out += [f"- 정의: {c['definition']}", f"- 포함: {c['include']}", f"- 이웃과 가르기: {c['exclude']}", ""]
    return out


def stage2(axis, data, parent):
    kids = children_of(data["concepts"])
    lines = [
        f"# {AXIS_KO[axis]} 축 2단계: `{parent['id']}` {parent['pref_label']['ko']} 아래 고르기",
        "",
        f"이 레코드는 1단계에서 `{parent['id']}`로 정해졌다. 이제 그 아래 노드 하나를 고른다.",
        "",
        "## 할 일",
        "",
        "1. 아래 '고르는 규칙'이 있으면 그 순서를 따른다. 없으면 정의·포함 기준이 가장 잘 맞는 노드를 고른다.",
        "2. 더 아래 노드(세분류)가 있으면 거기까지 내려간다. 세분류를 가를 근거가 없으면 그 위 노드에서 멈춘다.",
        f"3. 하위를 가를 근거가 없으면 `{parent['id']}` 그대로 답한다.",
        "4. 고른 노드의 포함 기준에 맞는 구절을 레코드 원문에서 그대로 복사해 evidence에 넣는다.",
        "",
        "완료 기준: 레코드마다 `label`이 아래 목록 안의 값이고, `evidence`가 원문에 글자 그대로 있는 구절이다.",
        "",
    ]
    if axis == "cause" and parent["id"] == "c.code":
        rule = parent["include"].split("L2는 고친 내용", 1)[1]
        lines += ["## 고르는 규칙", "", "L2는 고친 내용" + rule, ""]
    lines += ["## 하위 노드", ""]
    for c in kids.get(parent["id"], []):
        lines += describe(c)
        for g in kids.get(c["id"], []):
            lines += describe(g, "└ ")
    labels = [parent["id"]] + [c["id"] for c in data["concepts"] if c["id"].startswith(parent["id"] + ".")]
    lines += ["## 출력", "", f"`label`은 {', '.join(f'`{x}`' for x in labels)} 가운데 하나다. JSON 객체 하나만 낸다.", "",
              "```json", '{"results": [{"id": "<레코드 id>", "label": "<라벨>", "evidence": "<원문 구절>"}]}', "```", ""]
    return "\n".join(lines), labels


def schema(labels, with_stop):
    item = {"type": "object", "properties": {"id": {"type": "string"}, "label": {"type": "string", "enum": labels},
                                             "evidence": {"type": "string"}},
            "required": ["id", "label", "evidence"]}
    if with_stop:
        item["properties"]["stop"] = {"type": "integer", "minimum": 0}
        item["required"].append("stop")
    return {"type": "object", "properties": {"results": {"type": "array", "items": item}}, "required": ["results"]}


def lexicon_rows():
    rows = []
    for axis in AXES:
        data = load(axis)
        for c in data["concepts"]:
            rows.append({"axis": axis, "kind": "node", "id": c["id"], "level": level(c["id"]), "parent": c["broader"],
                         "ko": c["pref_label"]["ko"], "en": c["pref_label"]["en"],
                         "alt_labels": "; ".join(c.get("alt_labels") or []), "std_mapping": c.get("std_mapping") or "",
                         "definition": c["definition"], "examples": "; ".join(c.get("examples") or [])})
        for s in data["special_codes"]:
            rows.append({"axis": axis, "kind": "special", "id": s["id"], "level": 0, "parent": "", "ko": s.get("label_ko", ""),
                         "en": "", "alt_labels": "", "std_mapping": "", "definition": s["definition"], "examples": ""})
        for f in data["facets"]:
            definition = f.get("definition") or ""
            values = f.get("values")
            rows.append({"axis": axis, "kind": "facet", "id": f.get("id", ""), "level": 0, "parent": "",
                         "ko": f.get("label_ko", ""), "en": "", "alt_labels": "", "std_mapping": "",
                         "definition": definition if isinstance(definition, str) else json.dumps(definition, ensure_ascii=False),
                         "examples": values if isinstance(values, str) else json.dumps(values, ensure_ascii=False) if values else ""})
    return rows


def main():
    manifest = {"source": "taxonomy/*.json", "versions": {}, "axes": {}}
    for axis in AXES:
        data = load(axis)
        manifest["versions"][axis] = data["version"]
        out = KIT / "classify" / axis
        out.mkdir(parents=True, exist_ok=True)
        (out / "1-l1.md").write_text(stage1(axis, data))
        l1_labels = sorted({x for _, label in QUESTIONS[axis] for x in label.split("|")} | {s["id"] for s in data["special_codes"]})
        (out / "1-l1.schema.json").write_text(json.dumps(schema(l1_labels, True), ensure_ascii=False, indent=1) + "\n")
        kids = children_of(data["concepts"])
        stage2_files = {}
        for c in data["concepts"]:
            if level(c["id"]) == 1 and kids.get(c["id"]) and c["id"] in l1_labels:
                text, labels = stage2(axis, data, c)
                (out / f"2-{c['id']}.md").write_text(text)
                (out / f"2-{c['id']}.schema.json").write_text(json.dumps(schema(labels, False), ensure_ascii=False, indent=1) + "\n")
                stage2_files[c["id"]] = {"doc": f"2-{c['id']}.md", "labels": labels}
        manifest["axes"][axis] = {"evidence_fields": EVIDENCE_FIELDS[axis], "l1_doc": "1-l1.md", "l1_labels": l1_labels,
                                  "questions": [{"q": i, "label": label} for i, (_, label) in enumerate(QUESTIONS[axis], 1)],
                                  "stage2": stage2_files}
    (KIT / "classify" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    rows = lexicon_rows()
    (KIT / "keywords").mkdir(exist_ok=True)
    (KIT / "keywords" / "lexicon.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    with open(KIT / "keywords" / "lexicon.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"versions": manifest["versions"], "lexicon_rows": len(rows),
                      "stage2_docs": {a: len(v["stage2"]) for a, v in manifest["axes"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
