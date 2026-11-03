# 오픈 LLM용 분류·검색 키트

이 레포에서 얻은 분류 키워드와 노하우를, 사내 오픈 LLM(DeepSeek V4 Flash를 전제로 함)이 그대로 읽고 쓸 수 있는 모양으로 모았다. 정의의 원천은 `../taxonomy/*.json` 하나다. 이 폴더의 절차서와 키워드 사전은 그 원천에서 생성한다.

## 구성

| 경로 | 내용 | 읽는 쪽 |
|---|---|---|
| `classify/common.md` | 모든 분류 호출 앞에 붙이는 공통 규칙 | 모델 |
| `classify/<축>/1-l1.md` | 1단계: 대분류를 순서 있는 예/아니오 질문으로 고르는 절차서 | 모델 |
| `classify/<축>/2-<L1>.md` | 2단계: 고른 대분류 아래 노드만 담은 절차서. 하위가 있는 대분류만 있다 | 모델 |
| `classify/<축>/*.schema.json` | 단계별 출력 JSON schema(라벨 값 목록 포함) | 서빙·검증 코드 |
| `classify/manifest.json` | 축별 근거 필드, 질문→라벨 대응, 단계 문서 목록 | 라벨러 |
| `keywords/lexicon.json`, `.csv` | 노드·특수 코드·facet 101행 사전(한·영 이름, 옛 이름, 표준 대응, 정의, 예시 case_code) | 검색 필터·사람·모델 |
| `knowhow/taxonomy-method.md` | 새 문서 종류가 들어올 때 분류 체계를 넓히고 고치는 절차와 구조 규칙 | 모델·사람 |
| `knowhow/search-agent.md` | 결함 검색 에이전트에서 남길 칸, 계획·되묻기 규칙, 데이터에 맞춘 임시값 | 모델·사람 |
| `tools/build.py` | 원천 JSON에서 `classify/`와 `keywords/`를 다시 만든다 | 사람 |
| `tools/label.py` | 절차서로 레코드를 축마다 2단계로 라벨링하고 코드로 검증한다 | 사람 |

## 분류 호출의 모양

한 레코드를 축마다 따로, 두 단계로 분류한다. 호출 하나의 시스템 프롬프트는 공통 규칙 520자에 단계 문서 1,244~9,166자를 더한 크기다. 한 번에 세 축·68개 노드를 다 넣던 이전 라벨러(`taxonomy/label.py`, 35,881자)보다 작다.

1. **코드 규칙**: 코드가 정할 수 있는 것은 모델을 부르지 않는다. 지금은 레코드 유형이 '기능 요청'이면 원인 `_na` 하나다.
2. **1단계**: `common.md` + `<축>/1-l1.md`. 질문을 Q1부터 묻고 처음 "예"에서 멈춘다. 출력은 `{id, stop, label, evidence}`다.
3. **2단계**: 1단계 라벨에 하위가 있으면 `common.md` + `<축>/2-<L1>.md`. 출력은 `{id, label, evidence}`다.
4. **검증**: 라벨이 schema의 값 목록 안에 있는지, evidence가 그 단계에 준 필드 원문에 글자 그대로 있는지 코드가 본다. 틀린 레코드는 한 건씩 한 번 다시 묻는다.

축마다 모델에게 주는 필드가 다르다. 원인 축에는 제목과 현상을 주지 않는다. 제목·현상으로 원인을 짐작하지 않는다는 규칙을 입력 구성으로 강제한 것이다.

| 축 | 주는 필드 |
|---|---|
| problem | record_type, title, problem |
| cause | record_type, cause, resolution |
| resolution | record_type, resolution |

## DeepSeek V4 Flash로 돌리기

`tools/label.py`는 OpenAI 호환 chat completions를 부르고, `response_format: {"type": "json_object"}`와 temperature 0을 쓴다. 결과는 `runs/cache/`에 캐시된다.

```bash
export DEEPSEEK_API_KEY=...
python3 -I openllm-kit/tools/label.py --backend openai \
  --base-url https://api.deepseek.com --model deepseek-v4-flash \
  --case-codes taxonomy/heldout_case_codes.txt --passes 2 --out openllm-kit/runs/deepseek
```

사내 vLLM·llama.cpp 서버면 `--base-url`과 `--model`만 바꾼다. 서버마다 thinking(추론) 모드를 끄는 옵션이 다르면 `--extra-body '{...}'`로 넘긴다. 제3자 호스트 문서에 따르면 thinking을 켠 채 JSON 출력을 강제하면 `content`가 비어 오거나 토큰 한도에 걸릴 수 있다.

라벨 값을 서버에서 묶으려면 `--schema-mode`를 고른다. 단계마다 `*.schema.json`을 요청에 싣는다.

| 값 | 요청에 싣는 것 | 쓰는 곳 |
|---|---|---|
| `json_object`(기본) | `response_format: json_object` | JSON 모드만 되는 API |
| `json_schema` | `response_format: json_schema`(strict) | OpenAI식 structured output을 받는 서버 |
| `vllm` | `guided_json` | 사내 vLLM |

어느 모드든 라벨 값 목록과 evidence 실재는 코드가 다시 검사한다.

결과는 `--out` 아래 `labels.jsonl`과 `stats.json`이다. stats에는 축별 무효 출력 수, evidence 실재 비율, 두 pass 자기 일치, 기준 라벨(`taxonomy/labels_sample.jsonl`의 Haiku v4 held-out pass A)과의 일치가 들어간다.

## Haiku로 확인한 것

DeepSeek은 돌려 보지 않았다. 이 환경에서는 같은 절차를 Claude Haiku로 돌려 절차서와 라벨러가 끝까지 도는지, 기존 한 번 호출 프롬프트와 비교해 어떤지를 봤다. held-out 450건 가운데 9건마다 1건씩 뽑은, 서로 겹치지 않는 50건 표본 세 개를 썼다.

| 확인한 것 | 결과 |
|---|---|
| 출력 형식 | 무효 출력 0건, evidence가 원문에 그대로 있는 비율 100%(세 표본, 세 축) |
| 코드 규칙 | 원인 축 기능 요청은 모델을 부르지 않고 `_na`로 정해졌다 |
| 자기 일치(같은 모델 두 pass, L1 kappa) | 표본마다 흔들렸다. 문제점 축이 표본 B에서 0.76, 표본 C에서 0.90. 기존 한 번 호출 프롬프트는 같은 표본에서 0.93, 0.90 |
| 기준 라벨(기존 프롬프트 v4)과의 일치(L1 kappa) | 0.78~0.92. 절차가 다른 만큼 경계 사례에서 갈린다 |

표본 A·B에서 기준 라벨과 갈린 자리를 읽어, 질문 문장이 원천 정의의 제외 기준을 잘라낸 곳 다섯 군데를 원천대로 고쳤다. 다음 표본에서 다시 재 보니 차이는 1~2건 수준이었다. Haiku에서는 이 절차가 기존 한 번 호출보다 낫다고도, 못하다고도 말할 수 없다. 이 절차의 목적은 더 작은 모델에서 호출마다 싣는 정의를 줄이고 검증을 코드로 옮기는 것이라, 실제 판단은 DeepSeek으로 같은 held-out을 돌려 봐야 한다.

## 다시 만들기

```bash
python3 -I openllm-kit/tools/build.py
```

`taxonomy/*.json`을 고친 뒤 돌린다. 1단계 질문의 문장과 순서는 `tools/build.py`의 `QUESTIONS`에 있다. 원인 축 Q1~Q4의 순서는 원천 루트가 정한 우선순위이고, Q5 이후 순서는 이 키트가 정했다.
