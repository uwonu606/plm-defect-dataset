# PLM 결함 공개 대체 데이터셋

통신 장비 조직의 사내 PLM 결함 문서(약 9,000건)를 대신해, 공개 이슈 트래커의 실제 기록으로 만든 결함 레코드 10,000건이다. 검색·RAG·에이전트 설계를 사내 데이터 없이 시험하는 데 쓴다. 합성 레코드는 없다.

## 구성

| 경로 | 내용 |
|---|---|
| `dataset/` | 레코드 10,000건. `canonical`은 정본, `records`는 같은 레코드를 작성자 문체·오타·한영 혼용으로 다시 쓴 검색 대상본이다 |
| `docs/schema.md` | 필드, 장비군, 원인 분류, `cause_basis` 판정 기준 |
| `docs/personas.md` | `records`를 다시 쓴 작성자 14명의 문체 |
| `docs/design/` | 네트워크 부서 에이전트·GraphRAG·온톨로지 설계 검토 |
| `analysis/` | 설계 검토의 수치를 낸 스크립트와 출력 |
| `sim/` | 설계 구상을 같은 테스트셋에서 비교한 시뮬레이터, 테스트셋, 결과 |
| `taxonomy/` | 문제점·원인·해결책 분류 체계(SKOS 모양 JSON), Haiku 라벨링 스크립트, v2·v3 라벨 표본 |
| `openllm-kit/` | 오픈 LLM용 분류 절차서·키워드 사전·노하우·라벨러. `taxonomy/`에서 생성한다 |
| `samples/` | 변환 어투를 확인받은 샘플 |
| `tools/` | 수집부터 조립까지의 스크립트 |

## 데이터 출처

| 묶음 | 출처 | 건수 |
|---|---|---|
| `ran-core` | open5gs, magma, OAI(GitLab·GitHub), free5GC, OCUDU, srsRAN_4G, srsRAN_Project | 6,087 |
| `adjacent-network` | OpenStack Neutron(Launchpad), Red Hat Bugzilla 네트워크 컴포넌트 | 3,913 |

레코드마다 `source_url`과 `source_license`가 있다. 원본 이슈의 저작권과 이용 조건은 각 출처를 따른다.

## 다시 만들기

원본 수집본 `raw/`(412MB)와 중간 산출물 `work/`는 GitHub 파일 한도를 넘어서 레포에 없다. 다시 만들 때는 아래 순서로 돈다.

| 단계 | 스크립트 | 산출물 |
|---|---|---|
| 수집 | `tools/collect.py`(GitHub·GitLab·Bugzilla, `gh auth token` 사용), `tools/collect_launchpad.py` | `raw/*.jsonl` |
| 정규화 | `tools/normalize.py` | `work/candidates.jsonl` |
| 배치 | `tools/make_pilot.py`, `tools/make_full.py` | `work/pilot/`, `work/full/` |
| 변환 | LLM 에이전트가 배치마다 정본(`canonical-*`)과 문체본(`styled-*`)을 쓴다. 작성자는 `tools/assign_personas.py`가 배정한다 | `work/*/` |
| 조립 | `python3 -I tools/assemble.py` | `dataset/` |

## 설계 검토

| 문서 | 다루는 것 |
|---|---|
| [01-graphrag-ontology.md](docs/design/01-graphrag-ontology.md) | 부서 수요와 향후 데이터, GraphRAG 구성, 온톨로지 판정 |
| [02-roles-planner-clarify.md](docs/design/02-roles-planner-clarify.md) | 역할 분담, planner, 되질문, 멀티모달, LlamaIndex |
| [03-simulation.md](docs/design/03-simulation.md) | 고정 DAG, LLM 루프, planner, 되질문 정책을 245문항 테스트셋으로 비교한 결과 |
| [04-taxonomy.md](docs/design/04-taxonomy.md) | 문제점·원인·해결책 세 축 분류 체계 v3, 깊이 정책, Haiku 실측, 새 문서 종류 적합성 |

설계 문서는 여러 에이전트가 조사·설계·반박을 거쳐 쓴 권고안이다. 결론은 가설이고, 문서 안의 평가 게이트로 검증한다. 문서에 나오는 `~/` 경로는 작성자 로컬 자료라서 레포에 없다.
