# 분류 체계

결함 기록을 문제점(problem)·원인(cause)·해결책(resolution) 세 축으로 나누는 통제 어휘다. 설계와 근거는 [04-taxonomy.md](../docs/design/04-taxonomy.md)에 있다.

## 파일

| 파일 | 내용 |
|---|---|
| `problem.json`, `cause.json`, `resolution.json` | v3 분류 체계. 축마다 한 파일 |
| `label.py` | 정본 표본을 Haiku로 두 번(pass A·B) 라벨링하고 일치도·분포를 낸다 |
| `labels_sample.jsonl` | 라벨 2,700행. v2 1,800행(개정 표본·held-out)과 v3 900행(held-out) |
| `heldout_case_codes.txt` | held-out 450건. 분류 체계를 고칠 때 보지 않았고 examples에도 없다. 다음 판도 이 목록으로 잰다 |

## JSON 모양

SKOS 모양 통제 어휘다. 축 루트가 `scheme`, 노드가 `concepts`다.

| 키 | 내용 |
|---|---|
| `scheme` | 축 루트(`p`, `c`, `r`). 정의와 주 라벨 고르는 규칙이 `include`에 있다 |
| `concepts[]` | `id`, `broader`(부모 id, L1은 루트), `pref_label{ko,en}`, `alt_labels`(v2 이름), `definition`, `include`, `exclude`, `examples`(case_code), `std_mapping`, `status`, `v2_ids` |
| `special_codes[]` | `_none` 정보 없음, `_na` 해당 없음, `_other` 맞는 노드 없음. 트리 밖이다 |
| `depth_policy` | 최대 깊이 3, 노드를 열고 합치는 조건 |
| `facets[]` | 트리 밖 속성(위치, 원인 소재, 조치 주체 등). 정의만 했다 |
| `open_conditions`, `changes_from_v2` | 다시 나눌 후보와 조건, v2에서 바뀐 것 |

`status`는 measured(v2와 같고 실측 있음), revised(정의 고침), merged(합침), new(v2에 없음)다. 앞의 하나만 실측됐다. `v2_ids`는 v2 라벨을 옮길 때 쓴다. 한 v2 id가 여러 v3 노드에 나오면 다시 달아야 한다.

## 라벨링

```sh
python3 -I taxonomy/label.py --dry-run                       # 표본과 system prompt만 만든다
python3 -I taxonomy/label.py --sample-size 450 --version v3  # Haiku 두 pass, 약 90회 호출
python3 -I taxonomy/label.py --case-codes taxonomy/heldout_case_codes.txt --version v4 --seed 20261104  # held-out으로 새 판을 잰다
```

| 인자 | 기본값 | 뜻 |
|---|---|---|
| `--sample-size` | 450 | record_type × origin × equipment 층화 표본 크기 |
| `--seed` | 20261103 | 450건·이 seed가 v2를 실측한 개정 표본이다 |
| `--version` | v3 | 출력에 적는 버전 이름 |
| `--taxonomy-dir` | `taxonomy/` | 세 JSON이 있는 폴더 |
| `--out` | 임시 폴더 `plm-taxonomy-<version>` | `labels.jsonl`, `stats.json`, `sample.json`, `system_prompt.txt` |
| `--workers` | 6 | 동시 호출 수. 6을 넘기지 않는다 |
| `--case-codes` | 없음 | 층화 표본 대신 이 파일의 case_code를 라벨링한다 |

Haiku 호출은 `sim/llm.py`의 `ask`(Claude Code CLI)를 쓰고 `sim/runs/llm_cache`에 캐시된다.

## labels_sample.jsonl

한 행이 레코드 하나의 pass 하나다.

| 키 | 값 |
|---|---|
| `case_code` | 정본 레코드 id |
| `sample` | `revision`(v2를 고칠 때 읽은 450건) 또는 `heldout`(고칠 때 보지 않은 450건) |
| `pass` | `A` 또는 `B` |
| `taxonomy` | `v2` 또는 `v3`. v3 행은 held-out만 있다 |
| `problem`, `cause`, `resolution` | `{"primary": id, "secondary": id 또는 null}` |

held-out 레코드는 분류 체계의 examples에 쓰지 않는다. 다음 판을 잴 때도 이 450건을 그대로 쓸 수 있다.
