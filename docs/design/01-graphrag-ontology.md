# 네트워크 부서 결함 에이전트와 GraphRAG 권고안 (최종)

## 이 문서를 읽는 법

**결론:** 지금은 OWL 온톨로지와 범용 GraphRAG를 만들지 않습니다. 대신 다음 네 가지로 시작합니다.

- **검색:** 한국어 형태소 BM25, dense 검색, reranker를 합친 hybrid 검색을 기준선으로 둡니다.
- **그래프:** 레코드 사이의 명시적 관계 세 가지만 edge로 저장합니다. 중복, 같은 저장소의 issue 참조(xref), 같은 수정(PR·commit)입니다. 에러 문구·함수·파일을 공유하는 레코드는 edge로 저장하지 않습니다. 질의할 때 식별자 색인에서 찾아 "관련 사례"로만 보여 줍니다.
- **원인 이어받기:** 원인 이어받기는 중복과 xref 경로로만 합니다. 같은 수정 관계는 수정 추적에만 씁니다. 같은 수정을 공유하는 레코드 쌍도 원인 분류가 같은 비율이 절반 아래이기 때문입니다(#B-4).
- **에이전트:** 슬롯이 켜질 때만 단계를 실행하는 고정 파이프라인으로 둡니다. 자유 계획형 agent나 단일 라벨 router는 쓰지 않습니다.

**그래프에 거는 기대:** 기대치를 낮춰 잡습니다. 그래프가 원인을 이어받아 줄 수 있는 약한 원인 레코드(원인이 추론 또는 미상인 3,193건)는 많아야 169건(5.3%)입니다. 단순 BM25만 써도 그래프 이웃의 절반 이상이 상위 20건 안에 나옵니다(#B-1). 그래서 그래프 확장은 "그래프로만 닿는 범위"를 잰 뒤 S2 평가를 통과해야 켜는 선택 도구로 둡니다. 같은 수정과 중복 관계는 수정 추적과 근거 제시에 쓰므로 처음부터 둡니다.

**출처 표기:** 숫자 뒤 괄호는 그 숫자가 나온 조사를 가리킵니다. 스크립트 경로는 모두 `analysis/round1/` 기준입니다.

| 표기 | 조사 내용 |
|---|---|
| [profile] | 엔티티 추출 커버리지와 edge 실측(`profile/`) |
| [raw] | 원본 수집 데이터의 필드, 수집·정규화 스크립트가 버린 정보, 총무성 사례집 조사(`raw/`) |
| [needs] | 부서 수요와 향후 데이터 소스 조사 |
| [graphrag] | GraphRAG 방식과 저장소 비교 조사 |
| [ontology] | 온톨로지와 표준 검토 조사 |
| [심사] | 설계안 세 개를 교차 검증한 결과 |
| [verify] | 데이터 근거 반박에서 다시 잰 값(`verify/v1~v6*.py`) |
| [skeptic] | 온톨로지·그래프 반박에서 다시 잰 값(`skeptic/mlt.py`, `skeptic/jf2.py`) |
| [fact-check] | 외부 사실을 1차 출처(논문, PyPI, GitHub, 규격)로 다시 확인한 결과 |
| [이번 실행] | 이 문서를 쓰며 `python3 -I`로 `dataset/canonical.jsonl`과 `analysis/round1/` 출력을 다시 본 결과 |

**수치 재현성 규칙:** 그래프 수치는 어떤 edge 집합으로 쟀는지에 따라 달라집니다. 그래서 수치 옆에 edge 집합을 적습니다. 같은 스크립트를 다시 돌려도 값이 달라진 적이 있습니다(582→579, 40.9%→40.8%, 635→628, 741→688 [verify, skeptic]). 이 문서는 다시 돌린 값을 씁니다.

---

## A. 네트워크 부서에 필요한 것과 앞으로 들어올 데이터

### A-1. 사용자 유형별 필요

needs 조사는 부서 질문 22개를 유형별로 나눴습니다. 이 22개는 실제 수요 조사가 아니라 조사자가 직접 지은 예시입니다. 그중 5개는 검색 한 번으로 답이 나옵니다. 나머지 17개는 대부분 두 경우 중 하나입니다. 하나는 버전을 정규화한 뒤 SQL·필터로 풀리는 질문입니다. 다른 하나는 아직 없는 데이터(티켓, 알람, 인벤토리, 코드 저장소)가 있어야 풀리는 질문입니다. 지금 데이터로 그래프 순회가 꼭 필요한 질문은 거의 없습니다. needs 표의 '지금' 열에서 지금 가능한 연결 질문은 사실상 집계 하나였습니다 [skeptic]. 그래서 처음 붙이는 도구는 검색, 필터·집계, 수정 추적입니다. 실제 질문 분포는 파일럿 로그로 다시 잽니다.

| 사용자 | 하는 일 | 지금 데이터로 되는가 |
|---|---|---|
| 개발·결함 분석 | 유사 사례 찾기, 원인 후보 좁히기, 중복·회귀 판정 | 된다. 버전 회귀 판정은 버전을 정규화한 뒤에 된다 |
| 시험·QA | 실패 로그를 기존 결함과 맞춰 보기, 회귀 시험 범위 정하기 | 대부분 된다. 규격 조항 연결은 규격 문서가 들어와야 된다 |
| 현장 기술지원(TAC) | 알려진 결함인지 판정, 패치 여부, 결함인지 설정 문제인지 구분 | 일부 된다. 영향 버전과 수정 버전이 둘 다 있는 레코드가 6.8%뿐이다 [profile] |
| 운영 NOC | 알람 묶기, 장애 직전 변경 찾기 | 안 된다. 알람을 언급한 레코드가 4건, 셀 ID가 있는 레코드가 0.8%다 [needs] |
| 품질·릴리스 관리 | 원인별 재발 추이, CVE 영향 범위 | 집계는 된다. 열린 결함 집계는 상태 필드가 없어서 안 된다. 원인 분류가 빈 3,647건은 원인별 집계에서 빠진다(#B-2 `aggregate`) |

### A-2. 먼저 제공할 기능

| # | 기능 | 지금 데이터로 되는가 | 근거 |
|---|---|---|---|
| F1 | 증상·로그로 비슷한 과거 결함과 그 원인·수정을 찾고, 근거 레코드를 인용한다 | 된다 | 질문 하나에 근거 문서 하나가 대응하는 질문에서는 벡터 RAG가 GraphRAG와 같거나 나았다. NQ F1은 64.78 대 63.01, fact retrieval recall은 83.21% 대 70.29%다 [graphrag, fact-check: arXiv 2502.11371, 2506.05690]. Ericsson ETAgent는 쓸모가 "surfacing specific historical evidence"에서 나온다고 썼다 [needs] |
| F2 | 원인 이어받기. 원인이 추론·미상인 결함에서 중복·xref 관계로 이어진 원인 명시 레코드를 경로와 함께 보여 준다 | 일부 된다. 규모가 작다 | 중복과 xref로 원인 명시 레코드에 닿는 약한 원인 레코드는 많아야 169건(5.3%)이다(중복 23, xref 146, `profile/out/p2_edges.txt` 9절 [이번 실행]). 에러 문구·함수·파일로 이어진 레코드는 "관련 사례"로만 보여 주고, 원인을 이어받았다고 표시하지 않는다(#B-4) |
| F3 | 수정 추적. "패치 있어? 어느 버전·브랜치에?"와 "같은 수정으로 함께 고친 결함은?"에 답한다 | 일부 된다 | 정본 resolution의 59.8%가 PR·commit·review 참조를 문장으로 담고 있어서, 같은 저장소 안의 참조는 정규식으로 지금 뽑을 수 있다(`profile/out/p6.txt`). repo, merged 여부, sha, 백포트 branch 같은 구조는 raw를 복원해야 생긴다. raw에는 수정 링크가 56% 있지만 정본에 오지 않았다(`tools/assemble.py:10-14`) [raw]. 같은 수정을 2~5건이 공유하는 묶음은 329개, 레코드로 682건이다 [raw, verify/v2_fixgroups.py] |
| F4 | 결함인지 설정 문제인지 판정을 돕는다 | 된다 | 원인 명시 레코드 중 `결함 아님`이 323건, `설정`이 415건이다 [심사] |
| (F5) | 정해진 집계(장비군·원인·기간별) | 된다 | 그래프가 아니라 SQL template으로 푼다 [profile] |

### A-3. 앞으로 들어올 데이터와 편입 순서

**원칙:** 소스 하나를 편입할 때 다섯 가지를 한 묶음으로 붙입니다. 커넥터, 노드·edge, 도구, 파이프라인 슬롯, 그 소스로만 답할 수 있는 평가 문항 20~50건과 그 정답입니다. 평가 문항과 정답은 커넥터보다 먼저 만듭니다.

**시기:** 아래 시기는 모두 [추정]입니다(사례: needs 조사가 공개 사례와 연동 비용으로 매긴 순위, 13개 소스). 실제 시기는 사내 데이터 owner와 연동 일정을 확인해야 압니다.

| 단계 | 소스 | 그래프·에이전트에 생기는 것 | 시기 [추정] |
|---|---|---|---|
| E0 | raw 복원: fix_refs, labels, closed_at, 수정 릴리스, 백포트 | Fix 노드, SAME_FIX edge, `trace_fix` 도구 | 지금 |
| E1 | 릴리스 노트·버전 목록 | 버전 노드에 `release_date`, ReleaseNoteItem 노드, FIXED_IN 보강 | 0~3개월 |
| E2 | CVE·보안 권고(공개 feed) | CVE 노드. CVE와 결함은 식별자를 정확히 맞춰 잇는다. CVE의 reference URL은 정본 `source_url`에, fix commit은 Fix 노드에 맞춘다. 버전 범위를 펼치는 함수는 CVE와 SoftwareVersion 사이(어느 설치 버전이 노출됐는가)에만 쓴다. 예: CVE-2025-15176 → open5gs issue #4180 → DF-CORE-2025-02406(UPF, `decode_ipv6_header()` assert, 원인 명시), 수정 commit b72d834, v2.7.6에서 수정 [fact-check, 이번 실행] | 3~6개월 |
| E3 | 고객 trouble ticket·TAC 문의 | Ticket 노드, REPORTED_AS(티켓과 결함은 다대다), 고객사별 행 단위 권한, `ticket_lookup` | 0~6개월. 가장 가치가 크다 |
| E4 | 코드 저장소(MR, commit, 바뀐 파일) | Change 노드, 파일을 Component로 매핑 | 0~6개월 |
| E5 | 3GPP·O-RAN 규격 | 조항 단위 별도 색인, `spec_lookup`. 원인이 `규격 미준수`인 214건(원인 명시 163건)을 SpecClause에 연결 [심사] | 언제든 가능 |
| E6 | 시험 리포트·로그 | TestRun 노드. 기존 에러 시그니처 색인을 재사용 | 3~9개월 |
| E7 | 알람 코드 사전, 그다음 FM(장비가 올리는 고장 경보) 스트림 | AlarmType 노드와 Component 연결. 스트림은 그래프에 넣지 않는다 | 6~12개월 |
| E8 | 장애 보고서(post-mortem), 작업 절차서(MOP) | Incident 노드. 총무성 사례집 91건으로 스키마를 먼저 시험한다 [raw] | 6~12개월 |
| E9 | PM(시간별 KPI), CM(설정), 토폴로지·인벤토리 | 그래프에는 key만 둔다. 원본은 TSDB와 기존 시스템에 두고 `kpi_query`·`config_diff` 도구로 조회한다 | 12개월 이후 |

E2에서 버전 범위와 프로토콜로 CVE를 결함에 이으면 안 됩니다. CVE-2025-15176 "up to 2.7.5"를 open5gs PFCP 결함 142건에 이으면 관계없는 결함에 틀린 edge가 생깁니다. 게다가 실제 해당 결함인 02406은 본문에 'PFCP'가 없어서 이 142건에 들지 않으므로 빠집니다 [fact-check].

**순서의 근거**
- **티켓을 앞에 둔 이유:** ETAgent는 진단 질문에서 가장 크게 앞섰습니다 [needs]. AT&T는 "we've loaded every trouble ticket in the company"라고 말했습니다 [fact-check: sdxcentral]. support ticket으로 RCA 지식 베이스를 만든 연구도 있습니다(arXiv 2604.06171) [fact-check]. 다만 이 연구는 구축 방법을 비교했을 뿐이라서 순서의 근거로는 쓰지 않습니다.
- **FM을 뒤에 둔 이유:** 운영망 연동 비용 때문입니다. TN-AutoRCA는 알람·토폴로지 그래프를 입력으로 두고 에이전트 반복 루프로 F1을 0.59에서 0.92로 올렸습니다(같은 모델 Gemini-2.5-Pro 기준, arXiv 2507.18190 Table 1·2) [fact-check]. 그래프만의 기여는 따로 재지 않았으므로 이 수치를 FM 그래프의 가치 근거로 쓰지 않습니다.
- **PM·CM을 도구로 조회하는 이유:** [추정] 시계열을 노드로 넣으면 그래프가 커지고 탐색 비용이 늘어난다(사례: TeleLogsAgent 벤치마크가 KPI·셀 정보를 HTTP·MCP 엔드포인트로 노출, 1건) [fact-check]. 그래프 방식과 직접 비교한 사례는 없습니다.
- **CM 쓰기 자동화를 미루는 이유:** 의도를 설정으로 바꾸는 GSMA TeleYAML 벤치마크에서 상위 모델도 30점 아래였습니다 [needs, fact-check].

### A-4. 지금 열어 둘 확장점

**다섯 축.** 들어올 데이터가 공통으로 붙을 다섯 축을 지금 정해 둡니다. 이름은 3GPP와 TMF 표준에 맞춥니다.

| 축 | 개념 | 표준 이름 정렬 [ontology, fact-check] |
|---|---|---|
| 무엇이 | Component: NF, 플랫폼 구성요소, SW 모듈을 BROADER(상위 개념)로 잇는다 | 3GPP TS 28.541 IOC(AMFFunction, GNBDUFunction 등) |
| 어느 판에서 | SoftwareVersion(product_line, version, build, order_key) | ManagedElement의 `swVersion`. IM은 TS 28.622, YANG은 TS 28.623(me.yang:229) |
| 어떻게 보였나 | Symptom(정규화한 고장 모드), ErrorSignature(고유 문자열) | TS 28.111 FM의 `probableCause`·`specificProblem`(fm.yang:551-697) |
| 언제 | 사건 시각(`occurred_at`)과 유효 기간(`valid_from`/`valid_to`)을 따로 둔다 | – |
| 무엇이 바뀌었나 | Change(type, target, time, actor): commit·MR, 패치, CM 변경, MOP 수행 | NORIA-O ChangeRequest·ChangeAction(#C) |

**스키마에서 바꿔야 하는 것**
1. `필수:` SoftwareVersion을 1급 엔티티로 둡니다. 결함과는 `affected_in`, `fixed_in`, `introduced_in`으로 잇습니다. 이것이 없으면 `trace_fix`의 버전 답과 `search_cases`의 `version_range` 필터가 동작하지 않습니다. location 마지막 칸에 버전이 있는 레코드는 전체의 25.3%뿐이라서 본문에서 뽑아 정규화해야 합니다 [needs, 초안 실행]. 이 비율은 3구간 이상인 7,436건만 분모로 잡으면 34.0%입니다.
2. `필수:` 여러 레코드에서 만든 파생 객체의 권한 상속 규칙을 E3(고객 티켓) 편입의 진입 조건으로 둡니다. 파생 객체는 RootCause 요약, 클러스터, 임베딩, df 통계, 집계 결과입니다. 파생 객체는 구성원 등급 가운데 가장 높은 것을 물려받습니다. 클러스터 요약은 열람자 권한으로 다시 만들거나 구성원 단위로 가립니다. 이 규칙이 없으면 고객 티켓 내용이 public 클러스터 요약으로 샙니다 [심사].
3. `제안:` 모든 노드와 edge에 `access_level`, `source`, `extractor`(rule·dict·llm·human), `extractor_version`, `valid_from/valid_to`를 둡니다. 1단계 데이터는 모두 공개 이슈라서, 나중에 열을 더해도 기본값 public으로 채우면 됩니다 [skeptic]. 다만 사내 PLM을 적재하기 전과 E3 전에는 반드시 있어야 합니다. `extractor_version`은 #B-8의 멱등 재추출 키로 쓰므로 지금 둡니다.
4. `제안:` 알람 코드 사전 노드 `AlarmType`은 E7 때 더합니다. 지금 데이터는 4건이고, property graph에서 노드 타입을 나중에 더하는 비용은 작습니다 [skeptic]. 알람과 결함은 문자열로 맞출 수 없어서 알람 → Component → 결함 경로로 잇는다는 설계는 유지합니다.
5. `제안:` 제품 분류(EquipmentDomain, NetworkFunction)와 설치된 실물(ManagedElement, Site, Cell)을 나눕니다. 현장 결함과 개발 결함을 잇는 다리는 `ManagedElement.swVersion`과 SoftwareVersion의 연결입니다 [ontology].
6. `제안:` 결함 간 관계에 유형을 붙입니다. `duplicate_of` 하나를 duplicate_of, regression_of, related_to, reported_as로 넓힙니다 [needs].
7. `제안:` 고객 티켓은 고객사 단위로 격리합니다(customer_id 단위 RLS). 감사 로그도 민감 데이터로 보고 보존 기간을 정합니다 [심사].

---

## B. 에이전트와 GraphRAG 구성

### B-1. 세 층 원칙과 그래프 이득의 크기

노드와 관계를 역할에 따라 세 층으로 나눕니다.

- **분류 축:** NF, 인터페이스, 버전, 증상, 원인 분류입니다. 필터와 집계에만 쓰고 탐색에 쓰지 않습니다. 이 값들은 허브이기 때문입니다. 레코드 수가 UE 2,028건, AMF 852건이고, (NF, 인터페이스, cause_class) 조합 edge를 써도 최대 연결 요소가 330입니다 [profile].
- **증거 관계:** 두 가지로 나눕니다.
  - **명시 관계 edge:** 중복, xref, 같은 수정입니다. edge 테이블에 저장합니다.
  - **식별자 공유:** 에러 문구·함수·파일을 공유하는 관계입니다. edge로 펼치지 않습니다. `식별자 → case_code` 역색인과 질의할 때 거는 df 컷으로 같은 이웃을 얻습니다(pivot 검색). 이렇게 하면 edge 생애주기, 증분 df 재계산, 연결 요소 감시가 이 관계에는 필요 없습니다 [skeptic].
- **정적 지식:** BROADER(상위 개념), CONNECTS(인터페이스가 잇는 두 NF, TS 23.501), REALIZES(구현 이름에서 NF로) 같은 어휘 사이 관계입니다. 질의를 넓히는 데만 씁니다.

**관계의 품질은 두 기준으로 잽니다.** 하나는 두 레코드가 관련 사례인지(관련성)입니다. 다른 하나는 원인이 같은지(원인 일치)입니다. profile 조사의 표본 정밀도 8/10·9/10은 제목만 보고 관련성을 판정한 값이라서, 원인 일치의 근거로 쓸 수 없습니다(`profile/check_edge_precision.py:19-22`) [verify]. 원인 일치는 두 단계로 봅니다. 먼저 두 레코드가 모두 원인 명시인 쌍에서 cause_class가 같은 비율을 셉니다. LLM 없이 바로 셀 수 있습니다. cause_class는 거친 분류라서, 실제로 같은 원인인 비율은 이 값보다 낮습니다. 그다음 사람이 표본을 보고 판정합니다. 관계별 값은 #B-4에 있습니다.

**관계가 닿는 범위.** 수치마다 쓴 관계 집합을 적습니다.

| 관계 집합 | 이어지는 레코드 | 원인 명시 레코드 중 이어지는 것 | 가장 큰 연결 요소 | 출처 |
|---|---|---|---|---|
| 중복 + xref | 1,021건(10.2%) | – | – | verify/v6_on_graph.py |
| 중복 + xref + 에러 문구 + 함수(df≤10) | 2,004건(20.0%) | – | 220 | verify/v6_on_graph.py |
| 위 + 파일(df≤10) | 3,343건(33.4%) | 1,769건(37.5%) | 594 | verify/v6_on_graph.py |
| profile 원래 집합(중복, xref, PR·MR, commit, 함수, 파일, 에러 문구) | 4,081건(40.8%) | 2,125건(45.1%) | 628 | profile/out/p2_edges.txt 8절 [이번 실행] |

**그래프 이득의 크기.** 그래프로만 닿는 몫은 작습니다. 두 반박이 서로 다른 관계 집합으로 쟀고 결론이 같았습니다.
- 중복·xref·에러 문구·함수·파일 관계로 원인 명시 이웃이 있는 약한 원인 seed는 755건입니다. 그 seed의 제목과 현상만 질의로 넣어도 57%(431건)는 BM25 상위 20건에 원인 명시 이웃이 나왔습니다. 같은 저장소 필터를 걸면 62%(469건)였습니다. 그래프로만 닿는 seed는 약 286건이고, 약한 원인 3,193건의 9%입니다(verify/v4_bm25_vs_graph.py).
- profile 원래 집합으로 seed 579건을 잡으면 52.5%(304건)가 이미 BM25 상위 20건에 있었습니다. 그래프만의 몫은 약 275건, 전체의 2.8%입니다(skeptic/mlt.py).
- 그래프로만 닿는 이웃의 cause_class 일치율은 0.4~0.55입니다. 그래서 [추정] 원인까지 맞는 경우는 150건 안팎이다(사례: #B-4의 cause_class 일치율 측정, 1건).
- dense 검색과 reranker를 붙이면 이 몫이 얼마나 더 줄지는 아직 재지 않았습니다. S1c 단계에서 잽니다(#B-9).

반대로 메타데이터 필터만으로 충분하지도 않습니다. 원인 미상 1,553건은 cause_class가 모두 비어 있어서 필터로 좁힐 수 없습니다(verify/v1_counts.py).

### B-2. 에이전트 구성

```
질문 → 정규화기(식별자·버전·필터·별칭, 슬롯 감지)
     → search_cases (+ 식별자가 있으면 find_by_identifier)
     → [상위 결과의 원인이 추론·미상]  expand_related
     → [버전·패치 슬롯]              trace_fix
     → [집계 슬롯]                  aggregate
     → [개념 슬롯]                  lookup_vocab
     → 근거 검증기 → 답(인용) / "없음" / "부분 답"
     → 감사 로그 → 평가셋 후보
```

**고정 파이프라인으로 두는 이유:** 단일 라벨 router로는 대표 질문부터 처리하지 못합니다. 예를 들어 "원인과 2.4.x 패치가 있나?"는 원인과 수정을 한 질문에 함께 묻습니다 [skeptic]. 그래서 단계 순서를 고정하고, 각 단계는 해당 슬롯이 켜질 때만 실행합니다. 집계 슬롯만 켜지면 검색을 건너뜁니다. 슬롯은 규칙과 작은 LLM 다중 라벨 분류기로 감지합니다. 도구 호출은 6회가 상한이고, 상한에 닿으면 "부분 답"으로 표시합니다.

**정규화기**는 LLM을 쓰지 않는 결정적 구성 요소입니다.
- 식별자를 뽑습니다. 대상은 에러 문구, 버전, commit, PR, issue, 함수, CVE입니다.
- 별칭 사전으로 질의를 넓힙니다. 예: `먹통` → hang, `nnrf-nfm` → Nnrf_NFManagement.
- 필터와 슬롯을 뽑습니다.

적재할 때와 질의할 때 같은 사전을 씁니다. 그래야 "SGW-C", "sgwc", "src/sgwc/"가 같은 ID로 모입니다.

**도구.** MCP 서버 하나로 노출합니다. 1단계에는 쓰기 도구가 없습니다.

| 도구 | 입력 | 출력 |
|---|---|---|
| `search_cases` | query, filters{equipment, record_type, origin, cause_basis, product, version_range, created_range}, k | `[{case_code, title, snippet, score, cause_basis, cause_class}]`, `no_match` |
| `find_by_identifier` | kind(error_sig·function·file·commit·fix_ref·issue·source_url·cve·version), value, repo? | `[{case_code, field, matched_text, role}]` |
| `get_case` | case_code | 레코드, fix_refs, 이웃 관계 요약, access_level |
| `expand_related` | case_codes[], relations[], max_hops≤2, df_max=10 | `[{case_code, path:[{relation, via_value, relatedness, cause_agreement}], inherits_cause, cause_basis}]` |
| `trace_fix` | case_code 또는 fix_ref(repo, kind, id) | `{status, fix_refs[], sibling_cases[], fixed_in_versions[], backport_branches[], evidence_span}` |
| `aggregate` | template_id, params | 표(행 상한 200), 실행한 SQL 원문, `excluded`(빠진 레코드 수와 이유) |
| `lookup_vocab` | term 또는 concept_id | 정의, 별칭, 상하위 개념, 표준 대응, 연결 인터페이스 |
| 이후 | `ticket_lookup`, `spec_lookup`, `cve_lookup`, `match_log`, `alarm_to_component`, `change_window`, `kpi_query` | #A-3의 단계별로 연다 |

`expand_related`의 relations 규칙은 다음과 같습니다.
- `duplicate`와 `xref`만 `inherits_cause`를 켤 수 있습니다.
- `same_fix`는 `trace_fix`의 sibling_cases로만 쓰고, 원인 경로에서는 뺍니다.
- `error_sig`·`function`·`file`은 역색인 pivot으로 1-hop만 갑니다. 결과에는 "관련 사례"라고 표시합니다.

`trace_fix.status`는 다음 중 하나입니다.

| status | 판정 조건 |
|---|---|
| `fixed_in_version` | 수정이 들어간 버전을 안다 |
| `not_backported` | 다른 브랜치에서 고쳤고, 물은 브랜치에는 반영되지 않았거나 반영 계획이 없다고 적혀 있다 |
| `wont_fix` | 고치지 않기로 했다 |
| `fix_ref_only` | PR·commit 참조가 실제로 있지만 수정 버전은 모른다 |
| `workaround_only` | 우회 방법만 있다 |
| `unknown` | 위 어느 것도 아니다 |

이 상태들을 정식 답으로 두어야 버전이 없는데 있는 것처럼 답하는 실패를 막습니다. 영향·수정 버전이 둘 다 있는 레코드가 6.8%뿐이라서 필요한 장치입니다 [profile]. `not_backported`와 `wont_fix`는 TAC 질문("내 버전에 패치 있어?")의 흔한 답 형태입니다 [skeptic].

`aggregate`는 원인 분류별 집계에서 cause_class가 빈 레코드 수를 `excluded`에 담습니다. 그 레코드는 원인 미상 1,553건과 해당 없음 2,094건입니다(verify/v1_counts.py). 답에는 "원인 미상 n건 제외"를 반드시 적습니다.

자유 Text2Cypher·Text2SQL은 쓰지 않습니다. LLM은 template의 파라미터만 채웁니다 [graphrag].

**근거 인용**
- 원인·수정 문장마다 `[DF-CORE-2023-01752 · cause · 추론]`처럼 case_code, 필드, cause_basis를 붙입니다.
- 다른 레코드에서 가져온 원인에는 경로와 관계 유형을 붙입니다. 중복 경로로 가져온 원인은 "이어받은 원인", xref 경로로 가져온 원인은 "원인 후보"로 표시합니다. 관련성 판정만 있는 경로("관련 사례")에서는 원인을 가져오지 않습니다. LLM이 만든 관계를 거쳤으면 "자동 추출 연결"이라고 표시합니다.
- 검증기는 두 가지를 기계적으로 확인합니다. 인용한 case_code가 이번 도구 출력에 있었는지, 큰따옴표로 인용한 구절이 그 필드에 그대로 있는지입니다. 인용이 없는 원인 주장은 지웁니다.

**"없음" 판정.** 그래프가 아니라 seed 검색 점수로 합니다. 확장 결과는 seed 검색에 기대기 때문에 seed 점수가 더 직접적인 기권 신호입니다. reranker 최고점이 임계값보다 낮고 식별자도 정확히 맞지 않으면 "유사 사례 없음"으로 답합니다. 외부 결과는 참고로만 씁니다. 답이 없는 질의에서 전역 요약 방식(Global)은 19.27까지 떨어졌지만, 로컬·KG 방식은 80~99였고 RAG는 96.01이었습니다(arXiv 2502.11371 Table 2) [fact-check]. reranker 점수 분포는 질의 언어에 따라 다를 수 있습니다. records 본문은 라틴 문자가 한글의 약 4배입니다(한글 0.83M자, 라틴 3.28M자 [graphrag]). 그래서 임계값은 dev에서 질의 언어(한국어·영어·혼용)별로 따로 정합니다.

**권한**
- PostgreSQL RLS로 검색 SQL 안에서 행을 거릅니다. 등급은 public, internal, customer_restricted, security_embargo 네 단계입니다.
- MCP 2026-07-28판은 OAuth로 client와 server 사이만 인증합니다 [fact-check]. 그래서 사용자 신원은 MCP 서버가 요청마다 DB까지 넘깁니다. 트랜잭션마다 `SET LOCAL ROLE` 또는 `SET LOCAL app.user_id`로 넘기고, connection pool에 돌려줄 때 초기화합니다. agent는 권한 필터를 고를 수 없습니다.
- 시험 항목: 역할별로 같은 질의를 돌려 결과 집합을 비교하고, pool 재사용 뒤 신원이 남지 않는지 확인합니다.
- 질의, 도구 호출, 반환된 case_code를 감사 로그에 남깁니다.

**회귀 테스트.** 질문은 `verify/v5_examples.py`의 목록에서 가져왔습니다.

| # | 질문 | 확인하는 경로 | 기대 결과 |
|---|---|---|---|
| R1 | "eNB Reset 뒤 MME가 S1 context has already been removed 찍고 Authentication Request를 못 보낸다. 원인과 2.4.x 패치가 있나?" | 검색 + 수정 추적(그래프 불필요) | BM25만으로 01928이 1위, 01752가 2위에 나온다 [verify/v5]. `trace_fix(01752)`는 `not_backported`를 낸다. 근거는 01752 resolution "main branch에만 반영했고 r2.5.x, r2.4.x에는 반영할 계획이 없다"이다 [이번 실행]. 원인은 01752의 cause를 `추론`으로 인용한다. 01752에는 PR·commit 참조가 없으므로 `fix_ref_only`가 나오면 실패다 |
| R2 | "v2.8.0 SGW-C의 ogs_assert(bearer)가 v2.7.6에서 고친 것과 같은 문제인가" | 검색 + 관계 확장 | 정답은 02441, 02442, 02455, 02884, 02926이다. BM25만 쓰면 02926은 26위, 02884는 51위 밖이다 [verify/v5]. 확장 뒤 상위 20건에 정답이 모두 들어야 한다 |
| R3 | "gNB commit 56a771d 빌드에서 srsUE가 붙지 않는 사례를 원인별로" | 식별자 정확 일치 + 확장 | BM25만 쓰면 RAN-CU-00147은 51위 밖, RAN-DU-00436은 46위다 [verify/v5]. 둘 다 원인 미상이므로 답이 원인을 지어내지 않고 `미상`으로 표시해야 한다 |

### B-3. 노드와 색인 스키마

| 노드·테이블 | 층 | 지금 채우는 법 | 비고 |
|---|---|---|---|
| Case | 사건 | 정본 필드. 검색 대상 본문은 records | |
| Fix(repo 필수, kind=PR·MR·review·commit, id, merged, role) | 증거 | raw 복원. 수정 링크 56%, commit sha 44.2% [raw] | role은 fix, related, tested_with, not_related 중 하나 |
| `case_identifier(case_code, kind, value, repo, field)` 역색인 | 증거 | 정규식 | 에러 문구 고유값 1,685개, 함수 2,358개, 파일 2,191개 [profile]. df는 질의할 때 센다 |
| SoftwareVersion | 축 | location·본문 정규식, raw의 수정 릴리스·백포트 | 본문 어디든 버전이 있는 레코드 50.6% [needs] |
| Product/Repo | 필터 | source_id. free5gc는 하위 저장소까지 나눈다 | PR 번호 충돌을 막기 위해서다 [profile] |
| EquipmentDomain(6), CauseClass(14) | 분류 | `docs/schema.md:60-90` | |
| NetworkFunction, Interface/Protocol | 분류 | 3GPP 사전과 별칭 | NF 사전 커버리지 42.0%, 느슨한 사전 49.1%, ran-core 69.0% [profile] |
| PlatformComponent(OVS, ML2, L3 agent…) | 분류 | 별도 Neutron 사전 | adjacent-network 커버리지 58.5% [profile] |
| ImplementationComponent(srsUE, nr-softmodem, AGW 구성요소…) | 분류 | 사전. NF와는 REALIZES 다대다로 잇는다 | 구현 이름으로만 NF가 나오는 레코드 417건, magma 구성요소 926건 [profile] |
| Label/Component | 분류 | raw labels(64.5%) [raw] | free5gc·ocudu·magma는 거의 그대로 쓸 수 있다 |
| Symptom | 분류 | 증상 어휘에 grounding | 구어 표현을 정규화한다. 예: "죽음"이 canonical 2회, records 501회 [profile] |
| RootCause | 판단(조건부) | LLM 요약과 클러스터링, 사람 리뷰 | S4 게이트를 통과해야 만든다 |
| IncidentType, Incident | 사건 | 사례집 91건을 손으로 태깅 | 건 단위가 아니라 유형 단위로만 잇는다 [raw] |
| 이후 | ReleaseNoteItem, CVE, Ticket, Change, SpecClause, TestRun, AlarmType, ManagedElement·Site·Cell | #A-3의 단계별로 채운다 | KPI는 key만 둔다 |

NF·인터페이스 커버리지는 조사마다 다르게 나왔습니다. needs의 35.7%(NF)와 18.2%(인터페이스)는 짧은 정규식으로 잰 값이고, profile의 42.0%와 32.2%는 더 큰 사전으로 잰 값입니다. 이 문서는 profile 값을 씁니다.

### B-4. 관계 스키마와 처음 상태

관련성은 profile의 제목 표본 판정입니다. 원인 일치 상한은 두 레코드가 모두 원인 명시인 쌍에서 cause_class가 같은 비율이고, 괄호 안은 쌍 수입니다(verify/v3_cause_agree.py). 실제로 같은 원인인 비율은 이 값보다 낮습니다. 비교 기준선은 같은 저장소 아무 쌍 0.19, 같은 저장소·장비군 0.20입니다.

| 관계 | 저장 방식 | 규모 | 관련성 | 원인 일치 상한 | 쓰는 경로 | 처음 상태 |
|---|---|---|---|---|---|---|
| DUPLICATE_OF | edge | 74쌍 [profile] | 정본 필드라 확실 | 0.94(17) | 원인 이어받기, 수정 추적 | 켠다 |
| XREF(같은 저장소 이슈 참조, stack trace 줄 제거, fan-out≤3) | edge | edge 626개(무방향), 995건이 이어짐 [profile] | 23/25 | 0.73(219) | "원인 후보", 관련 사례 | 켠다 |
| SAME_FIX(role=fix, repo 확정) | edge | 329묶음, 682건 [raw] | 정규식만 쓰면 PR 2/10, commit 6/10 [profile] | PR·MR 0.44(699), commit 0.46(179) | 수정 추적만(sibling_cases) | repo 보정과 role 분류를 마친 뒤 표본을 다시 판정하고 켠다 |
| 에러 문구 공유(df≤10) | 역색인 pivot | 688쌍 [이번 실행; 초안 741] | 9/10 | 0.55(206) | 관련 사례 | 켠다 |
| 함수 공유(df≤10) | 역색인 pivot | 1,167쌍 | 8/10 | 0.52(645) | 관련 사례 | 켠다 |
| 파일 공유(df≤10) | 역색인 pivot | 3,784쌍. 레코드 유형이 다른 쌍 919 [verify] | 8/10 | 0.41(1,209) | 관련 사례, 가중치를 낮춘다 | 켠다 |
| AFFECTS_VERSION / FIXED_IN | edge | 희소 | 재지 않음 | – | `trace_fix`·필터 | 켠다 |
| SAME_ROOT_CAUSE | edge | 없음 | 재지 않음 | – | 원인 이어받기 | S4 조건부 |
| OBSERVED_IN, INVOLVES, CLASSIFIED_AS, IN_DOMAIN, EXHIBITS | 열·필터 | 허브 | – | – | 필터·집계 | 탐색에 쓰지 않는다 |
| BROADER, CONNECTS, REALIZES | 어휘 테이블 | 손 입력 수십~수백 줄 | – | – | 질의 확장 | 켠다 |

**원인 이어받기를 켜는 조건:** 관계 유형별로 사람이 30쌍을 판정해서 같은 원인 비율이 0.6 이상이어야 합니다(출발값). xref는 cause_class 일치율이 0.73이라서 이 기준을 넘더라도 "원인 후보"로만 표시합니다.

**edge 행의 열:** 저장하는 edge 행은 `(src, dst, type, via_value, relatedness, cause_agreement, basis, extractor, extractor_version, confidence, evidence_span, access_level, valid_from, valid_to)`를 갖습니다. confidence가 0.7보다 낮은 LLM edge는 1-hop까지만 따라갑니다. 역색인 pivot은 질의할 때 df>10인 값을 버립니다. 그래서 허브는 별도 장치 없이 막힙니다.

### B-5. 추출 방법

| 대상 | 방법 | 이유 |
|---|---|---|
| fix_refs, labels, closed_at, importance, 백포트 | raw 복원. 프로젝트 파일은 건드리지 않고 별도 파이프라인으로 붙인다 | 이미 있는 구조화 정보이고 LLM 비용이 0이다 [raw]. `tools/assemble.py` 수정은 사용자 승인 뒤에만 한다 |
| 에러 시그니처, 함수, 파일, 버전, 설정 키, case_code, CVE, issue 번호, source_url | 정규식 | 문체 변형본(records)에서도 값 단위 재현율이 94.7~99.6%다 [profile] |
| NF, 프로토콜, Neutron 구성요소, 구현 이름, SBI 표기 | SKOS altLabel 사전. 대소문자를 무시하고 코드 경로(`src/mme/`)는 뺀다 | NF·프로토콜 27종이 표기 94가지로 나온다. SBI는 서비스명 26종과 URI 경로 29종이 섞이고, 매핑이 없으면 경로 표기만 있는 78건이 끊긴다 [profile] |
| PR의 repo 확정, 참조 역할, 부정 참조("관계가 없다"), 범위 표기(`#858~#862`) | 규칙 뒤 LLM 보정. 닫힌 출력 스키마를 쓰고, 해당 문장만 입력한다 | 정규식이 틀리는 것으로 확인된 경우다 [profile]. 사람 200건 검수 기준은 #B-9 A 단계 |
| Symptom, RootCause 진술 | LLM. 어휘 ID에 grounding하고, 실패하면 후보 큐로 보낸다 | grounding 없이 ID를 맡기면 GO ID 정답이 3/100이었다(SPIRES) [ontology, fact-check] |
| 사전에 걸리지 않은 인터페이스 | 처음에는 LLM 추출 대상에 넣지 않는다 | graphrag 조사의 "사전에 안 걸린 69%"는 프로토콜 사전이 걸리지 않은 레코드 비율이지, 인터페이스를 놓친 비율이 아니다. adjacent-network의 통신 엔티티는 2.1%다 [profile, 심사]. 미검출 레코드 200건을 손라벨해서 놓친 비율을 정한 뒤 LLM 대상을 정한다 |

**자유 텍스트 칸을 노드로 쓰지 않습니다.** location 둘째 구간만 봐도 고유값이 9,151개이고 [graphrag](같은 정의로 records에서 다시 세면 9,175개 [skeptic]), 기능·모듈 값은 5,869종 중 5,191종이 한 번만 나오기 때문입니다 [ontology].

**자유 LLM 추출(MS GraphRAG 기본 방식)은 쓰지 않습니다.** 이유는 셋입니다.
- 질의 1회 prompt가 MS-GraphRAG local 38,707 token, global 331,375 token입니다(arXiv 2506.05690 Figure 8·9 표). 같은 논문 본문은 global을 최대 4×10^4로 적어서 표와 한 자릿수가 다릅니다 [fact-check]. 어느 값을 써도 결론은 같습니다.
- grounding 없는 추출은 ID 정확도가 낮습니다(위 SPIRES).
- Microsoft GraphRAG는 maintenance mode입니다. README에 "won't be accepting new PRs or implementing new features"라고 적혀 있습니다 [fact-check].

### B-6. 저장소

PostgreSQL 하나로 시작합니다.
- 벡터: pgvector 0.8.0 이상. iterative index scan(`hnsw.iterative_scan`, `hnsw.max_scan_tuples`)으로 RLS·필터 뒤 결과가 k보다 모자라는 문제를 줄입니다 [fact-check].
- 한국어 BM25: ParadeDB `pdb.lindera(korean)`. 라이선스는 AGPL-3.0이고, pg_search 0.25.0부터는 pgvector가 먼저 깔려 있어야 합니다 [fact-check]. 대안은 OpenSearch Nori 또는 pg_bigm입니다.
- 관계: edge 테이블, 역색인 테이블, recursive CTE
- 권한: RLS

**근거**
- [추정] 명시 관계 edge는 수천 개 이하라서 2-hop recursive CTE로 충분하다(사례: 중복 74쌍, xref 626개, 같은 수정 329묶음 [profile, raw], 1건).
- Apache AGE를 쓰지 않는 이유는 성숙도가 아닙니다. AGE는 공식 릴리스도 모두 `-rc0` 태그를 답니다. PG18용 1.7.0은 stable이고, 1.8.0은 승인 대기입니다 [fact-check]. 쓰지 않는 이유는 2-hop이면 CTE로 충분하고, 확장을 하나 줄이면 관리형 DB 허용 문제도 하나 줄기 때문입니다.
- Kuzu는 2025-10-10에 archived됐습니다(v0.11.3). Neo4j Community에는 RBAC가 없습니다 [graphrag, fact-check].

**관리형 PostgreSQL이면 전제가 깨집니다.** 관리형 PostgreSQL(RDS 등)에는 pg_search를 설치할 수 없다는 보고가 있습니다 [fact-check: 3자 출처]. ParadeDB가 내놓은 방식은 관리형 DB를 publisher로, ParadeDB를 subscriber로 두는 logical replication인데, 이 방식은 인덱스와 스키마를 복제하지 않습니다. 사내 DB가 관리형이면 "DB 하나 + 같은 SQL 안의 RLS"라는 전제가 깨집니다. 그때의 퇴로는 OpenSearch Nori와 문서 단위 보안입니다. 이 경우 권한 경계가 두 곳으로 갈라지는 비용이 생깁니다(#D).

**Neo4j로 옮길 신호:** 다음 가운데 하나가 생기면 Neo4j를 읽기 복제본으로 붙입니다. 부서 단위 RBAC가 필요하면 Enterprise 비용이 함께 생깁니다.
- DB 쪽 그래프 질의 p95가 1초를 넘는다. 에이전트 전체 지연과 따로 기록합니다. 전체 지연의 대부분은 LLM과 reranker에서 나오기 때문입니다 [skeptic].
- 3-hop 이상 질의가 로그의 10%를 넘는다.
- GDS 알고리즘이 필요해진다.

알람·KPI 샘플은 그래프에 넣지 않고 TSDB에 둡니다.

### B-7. 검색 흐름

1. **정규화:** 식별자, 필터, 별칭 확장, 슬롯을 뽑습니다.
2. **병렬 검색:**
   - 식별자가 있으면 `find_by_identifier`로 정확히 맞춥니다.
   - 동시에 hybrid 검색을 돌립니다. BM25와 dense(bge-m3 또는 Qwen3-Embedding)를 RRF로 합치고, reranker(bge-reranker-v2-m3 또는 Qwen3-Reranker)로 상위 20건을 고릅니다 [graphrag].
   - 분류 축은 SQL WHERE 필터로만 겁니다.
3. **관계 확장:** 상위 결과의 원인이 추론·미상이거나 버전·패치 슬롯이 켜졌을 때만 합니다. S2를 통과하기 전에는 중복·xref 확장과 수정 추적만 켜고, 관련 사례 pivot은 꺼 둡니다. 상위 5건을 seed로 잡습니다. 점수는 seed 점수 × 관계 가중치 × hop 감쇠로 매기고, 원인 명시 레코드를 우대합니다.
4. **통합:** 검색 결과와 확장 결과를 합쳐 다시 rerank합니다. 질의를 한쪽으로 보내는 Selection은 +1.1%, 두 결과를 합치는 Integration은 +6.4%였기 때문입니다 [graphrag, fact-check].
5. **생성과 검증:** 인용 검증기를 거치고, 임계값보다 낮으면 "없음"으로 답합니다.

### B-8. 증분 업데이트와 운영 감시

- **재추출:** 추출기는 `(case_code, extractor_version)` 키로 멱등하게 다시 돌립니다. 임베딩은 바뀐 레코드만 다시 계산합니다.
- **식별자 색인:** 새 레코드의 식별자 행만 더합니다. df는 질의할 때 세므로 edge를 닫거나 df를 따로 재계산할 일이 없습니다.
- **명시 관계 삭제:** soft delete로 처리합니다. 사실은 지우지 않고 `valid_to`로 닫습니다.
- **사전 변경:** 별칭 사전에 버전을 매기고, 사전이 바뀌면 영향받는 레코드만 다시 grounding합니다.
- **야간 감시:** 명시 관계 edge만 대상으로, 종류별 개수와 가장 큰 연결 요소 크기를 야간에 기록합니다. 기준선은 처음 구축할 때 재고, 스크립트 버전과 관계 집합을 함께 남깁니다. 가장 큰 연결 요소가 기준선의 두 배를 넘으면 경보를 냅니다.
- **RootCause 재클러스터링:** 다시 돌릴 때 겹침 비율로 기존 ID를 이어받아 인용 링크를 지킵니다.
- **회귀 확인:** 업데이트마다 전체 평가셋과 R1~R3을 다시 돌립니다.

### B-9. 평가

**평가셋 구성(300~500문항).** 1~2주에 씨앗 100문항으로 시작해 8주차에 300문항 이상으로 늘립니다.

| 하위셋 | 비율 |
|---|---|
| 단일 증상 검색 | 40% |
| 원인 이어받기·멀티홉(측정으로 정의, 아래 참조) | S1c 결과로 정한다 |
| 수정 추적 | 10% 이상. `not_backported`·`wont_fix` 문항을 포함한다 |
| 결함인지 설정인지 | 10% |
| 집계 | 5% |
| 답이 없는 질문 | 10~15% |

**할당**
- **origin:** ran-core 문항을 60~70% 이상으로 둡니다. 할당하지 않으면 플랫폼 클라우드 결함이 기준을 정합니다. 원인 명시 4,713건 중 adjacent-network가 2,483건(52.7%), PLATFORM이 2,618건(55.5%)이기 때문입니다 [skeptic]. 통과 기준은 origin별로 따로 겁니다.
- **작은 장비군:** RAN-CU(원인 명시 150건), OAM(126건), UE에 최소 문항 수를 정합니다. 출발값은 장비군별 20문항입니다.
- **질의 언어:** 한국어, 영어, 혼용을 나눠 기록하고 지표도 언어별로 보고합니다.
- 검색 대상은 records이고, 정답 case_code는 canonical 기준입니다.

**멀티홉 하위셋의 정의.** 질문 모양이 아니라 측정으로 정합니다. 멀티홉 문항은 두 조건을 모두 만족하는 질문입니다. 첫째, S1 기준선(BM25+dense+rerank)의 상위 20건이 정답을 하나 이상 놓칩니다. 둘째, 그 정답까지 이어지는 증거 관계 경로가 있습니다. 정답은 관계와 무관하게 전문가가 같은 원인으로 확정한 것만 씁니다. 처음 예시 7개 가운데 2·7번은 BM25만으로 원인 명시 정답이 2위에 나오고, 1번도 2위가 원인과 패치 상태를 이미 담고 있습니다(verify/v5_examples.py). 그래서 이 셋은 멀티홉 문항이 아닙니다.

**정답 묶음.** 출처마다 태그를 붙입니다. (a)~(c)는 정답 후보 큐로만 쓰고, 5~6주차의 원인 일치 확인을 거친 것만 정답에 넣습니다.

| 묶음 | 내용 | 쓸 수 있는 규모 |
|---|---|---|
| (a) 같은 수정 | 구성원이 모두 원인 명시인 같은 수정 묶음 94개. cause_class가 같은 것은 55개뿐이다. neutron의 Related-Bug commit이 섞이고, MR 하나가 버그와 기능 요청을 함께 닫기도 한다 [verify/v2, skeptic/jf2] | 전문가 확인을 마친 것만. cause_class가 다른 39개를 먼저 본다 |
| (b) 중복 | 74쌍 중 두 쪽 다 원인 명시인 쌍은 17개다. 한쪽만 명시인 쌍은 23개다(미상→명시 12, 추론→명시 7, 명시→미상·추론 4). 34쌍은 명시 레코드가 없다 [verify/v1] | 여러 정답 묶음 17개, 약한 원인 질문 → 정답 1개 23개 |
| (c) xref 연결 요소 | issue 교차참조로 이어진 연결 요소 [profile] | cause_class 불일치를 거른 뒤 |
| (d) 관계와 무관한 묶음 | 최소 60개. 절반은 LLM이 cause 문장 유사도로 후보를 내고 전문가가 확정한다. 나머지 절반은 전문가가 증상·로그에서 출발해 직접 묶는다. 앞 방식만 쓰면 정답이 dense 검색 쪽으로 치우친다 [심사] | 전부 |

(a)~(c)는 증거 관계와 원천이 같아서 그래프 이득을 부풀립니다. 그래서 그래프 확장(S2)과 RootCause(S4)는 (d)로만 판정합니다. S1 지표도 출처별로 따로 보고합니다.

**누수 점검과 분할**
- 질문이 정답 레코드의 title·problem과 공유하는 3-gram 비율의 중앙값을 함께 보고합니다.
- 로그 문자열이 아닌 3-gram을 5개 넘게 공유하는 문항은 다시 씁니다.
- dev 40%, test 60%로 나눕니다. 임계값과 가중치는 dev에서만 맞추고, test는 마지막에 한 번만 봅니다.
- 비교는 paired bootstrap 95% 신뢰구간으로 합니다.

**지표**
- 검색: Hit@5, 묶음 Recall@10/@20, MRR, nDCG@10. case_code만 비교하므로 LLM이 필요 없습니다.
- 없음 판정: 답이 없는 질문의 정답 기권율, 답이 있는 질문의 오기권율. 둘 다 질의 언어별로 봅니다.
- 수정 추적: `trace_fix.status` 정확도
- 생성: 인용 구조 유효성, 주장 지지율. 주장 지지율은 LLM judge를 답 순서를 바꿔 두 번 돌리고 사람 50건 표본으로 확인합니다 [graphrag].
- 운영: p95 지연(에이전트 전체와 DB 그래프 질의를 따로)

**단계별 통과 기준.** 수치는 모두 설계 출발값입니다. dev 결과를 보고 한 번만 조정합니다.

| 단계 | 비교 | 통과 기준 |
|---|---|---|
| S0 평가셋 | – | 8주차까지 300문항 이상. origin·장비군·언어 할당을 충족한다. 없음 문항 30 이상. (d) 묶음 60개 이상, 전문가 2인 일치율 0.85 이상. (d)에서 나온 멀티홉 문항 수 N을 S1c 결과로 정해 채운다(출발값 40). (a)~(c) 원인 일치 확인을 마친다 |
| A 추출 품질 | 손라벨 200건 | 관계를 만드는 추출기(SAME_FIX의 repo·role, XREF 참조 역할)는 정밀도 0.95 이상, 재현율 0.90 이상. 식별자 정규식은 records 본문에 실제로 남아 있는 값 대비 페르소나별 재현율 97% 이상. P14는 이 기준에서 뺀다. P14는 세부를 빼고 결론만 쓰는 페르소나라서(`docs/personas.md:29`), 빠진 값이 본문에 아예 없다(`profile/out/p4.txt:33-38`). P14 레코드가 정답인 질문의 Hit@k는 따로 본다. 관계 유형별 30쌍에서 관련성 0.90 이상을 보고, 같은 원인 비율도 함께 보고한다. 분류 축 linking(NF·인터페이스)은 여기서 판정하지 않고 S1b로 판정한다 |
| S1 hybrid | BM25 / dense / hybrid / +rerank | single-hop Hit@5 0.80 이상, MRR 0.65 이상, 기권율 0.85 이상, 오기권율 0.10 이하. 모두 언어별로 본다. hybrid+rerank가 가장 좋은 단일 방식보다 Recall@10이 5pt 넘게 낫지 않으면 단순한 쪽을 쓴다. ETAgent의 MRR 0.815 [needs]는 데이터가 달라서 참고값으로만 쓴다 |
| S1b 별칭 확장 | S1 대 S1과 별칭 확장 | 별칭 표기 문항 Recall@10 +3pp 이상(신뢰구간 하한 > 0), 전체 하락 1pp 이하 |
| S1c 그래프 단독 도달 범위(1~2일) | S1 상위 20건 대 관계 경로 | 약한 원인 seed와 (d) 질문에서 S1 상위 20건이 놓치고 관계 경로로만 닿는 정답 수를 관계 유형별로 센다. 이 수가 N을 채우지 못하면 S2를 하지 않는다. 그 경우 그래프는 수정 추적과 중복·xref 표시에만 둔다 |
| S2 그래프 확장 | S1 대 S1과 expand_related, 관계 유형별로 하나씩 빼 보기 | 멀티홉 하위셋 Recall@20 이득의 신뢰구간 하한 > 0. 이득 크기 기준은 출발값 +10pp이고, dev의 문항별 차이 분산으로 paired bootstrap 검정력을 계산해 다시 정한다. single-hop Hit@5 하락 1pp 이하. "이어받은 원인"으로 표시한 답 50건의 원인 정답률을 관계 유형별로 재서 0.80 이상. 기여가 1pp 미만인 관계 유형은 끈다 |
| S3 에이전트 | 파이프라인 대 검색만 | 인용 구조 유효성 100%, 주장 지지율 0.90 이상, cause_basis 표시 정확도 100%, `trace_fix.status` 정확도 0.90 이상, 슬롯 감지 오류 10% 이하. p95 지연은 검색 경로 15초 이하, 확장 경로 30초 이하 |
| S4 RootCause | S2 대 S2와 SAME_ROOT_CAUSE | (d) 대비 클러스터 purity 0.80 이상, 리뷰어 간 Cohen's kappa 0.6 이상, 묶음 Recall@20 +5pp 이상. 못 넘으면 RootCause 노드를 만들지 않는다 |
| 파일럿 | 엔지니어 5~10명, 2주 | "도움 됨" 60% 이상, 슬롯 미감지 비율 15% 이하. ETAgent 선호 72%는 전문가 11명이 foundation model·enterprise baseline과 블라인드로 비교한 값이라서 질문 형식이 달라 직접 비교하지 않는다 [fact-check] |

도메인 모델안의 p95 8초는 근거가 없어서 쓰지 않습니다 [심사].

### B-10. 로드맵

**인력 가정:** 검색·ML 엔지니어 1명, 데이터·백엔드 엔지니어 1명, 네트워크 도메인 전문가 0.3~0.5명(정답 확정과 어휘 리뷰), E3부터 보안 담당 0.2명입니다. 이 가정을 뒷받침하는 사례는 없습니다.

| 주 | 할 일 | 끝나는 조건 |
|---|---|---|
| 1~2 | 씨앗 100문항과 평가 harness, E0 raw 복원, 어휘 시드(schema.md 분류, 3GPP 이름 58개, Neutron, 구현 이름, SBI 매핑, std_mapping 열). 사내 PLM owner에게 필드 목록과 채움률을 요청한다. 특히 PR·commit·issue 번호 필드가 있는지 묻는다. (d) 시범 10묶음을 만들며 걸린 시간을 잰다 | 복원율이 56%·64.5% [raw]와 맞음. 사내 메타데이터 수령 |
| 3~4 | Postgres hybrid 검색과 ablation 4종, 별칭 사전 v0, 버전 정규화 v0(`version_range` 필터용), 식별자 역색인. S1 직후 S1c 상한 분석 | S1, S1b, S1c |
| 5~6 | 명시 관계 edge(중복, xref, SAME_FIX의 repo·role LLM 분류 200건 검수), `trace_fix` v0와 상태 판정, (a)~(c) 원인 일치 확인, (d) 묶음 계속 | A 단계 |
| 7~8 | 파이프라인, MCP 도구, 인용 검증기, 언어별 기권 임계값, RLS와 신원 전달, 평가셋 300문항. S1c가 통과했으면 8주차 끝에 S2를 판정한다 | S0, S3, S2 |
| 9~10 | 파일럿(수정 추적 포함). 질의 로그를 평가셋 v1로 옮긴다. 사례집 유형 태깅 | 파일럿 기준 |
| 11~13 | S4 RootCause 판정(스키마 강제 추출과 자유 추출을 200건으로 비교), 버전 정규화 확장, E1·E2 | S4, E1·E2 하위셋 |
| 사내 데이터 전환 시 | 사내 PLM 200건에 profile·verify 스크립트를 다시 돌린다 | 관계 연결률을 같은 관계 집합 기준값(#B-1 표)과 비교 |
| 14~ | E3 티켓부터 차례로 편입한다. E3 진입 조건은 #A-4 2번과 권한 열(#A-4 3번)이다 | 소스마다 하위셋 통과, 기존 문항 회귀 없음. 소스 하나에 걸리는 기간은 모르고, E3에서 잰다 |

---

## C. 온톨로지 판정

**만들 수 있는가:** 만들 수 있습니다. 분류 체계가 이미 반쯤 있습니다.
- `docs/schema.md`에 장비군 6종(:60-69), 원인 분류 14종(:73-90), cause_basis 4종(:51-58)이 있습니다 [ontology].
- 3GPP NF·프로토콜 이름 58개가 ran-core 레코드의 67.8%를 덮습니다. adjacent-network는 16.9%만 덮습니다 [ontology].

**효율적인가:** 지금 OWL/RDF로 정식 온톨로지를 만드는 것은 비효율적입니다. 근거는 둘입니다.
1. **병목은 이름 정규화입니다.** 클래스 설계가 모자란 것이 아닙니다. 기능·모듈 값 5,869종 중 5,191종이 한 번만 나옵니다 [ontology]. 대소문자 변형, 구현 이름 417건, SBI 이원 표기도 있습니다 [profile]. 이 문제는 통제 어휘가 풉니다.
2. **reasoner가 할 일이 거의 없습니다.** 핵심 질의는 유사도와 순회입니다. 필요한 상하위 확장("RAN-CU 아래 전부")은 BROADER 재귀 순회로 됩니다 [ontology].

비용 비교는 근거로 쓰지 않습니다. 초안이 든 사례(NORIA-O의 저작권 연도 범위, ETSI ENI 031의 엔티티 종류 수)는 공수를 잰 값이 아니기 때문입니다 [skeptic]. OWL 구축 공수는 모르고, 같은 규모 조직의 구축 기록을 보면 알 수 있습니다.

**권하는 범위**
1. **SKOS 모양 통제 어휘:** `concept(id, scheme, pref_label, alt_labels[], broader, std_mapping, source)`. std_mapping에는 `AMFFunction@28.541` 같은 표준 대응을 적습니다. NF·관리 객체 이름은 3GPP SA5 NRM(TS 28.541, 28.622/28.623)에, 알람 필드는 TS 28.111 FM에, 티켓·알람 API는 TMF621·TMF642에 맞춥니다 [ontology, fact-check].
2. **property graph 스키마:** #B-3·#B-4의 노드·관계를 DDL로 관리하고, MCP 도구의 입출력 계약(JSON Schema)과 같은 원천에서 만듭니다. 스키마가 둘로 갈라지면 하나가 낡기 때문입니다.
3. **스키마 강제 추출과 grounding:** LLM은 Symptom과 RootCause에만 쓰고 어휘 ID에 grounding합니다. LLM은 동의어 후보와 신규 개념 후보를 제안하고, 확정은 사람이 주 1회 리뷰로 합니다.
4. `제안:` 단일 원천을 LinkML로 두면 DDL, Pydantic, JSON Schema를 생성할 수 있고, 나중에 SHACL·OWL도 같은 파일에서 내보낼 수 있습니다. 4주 안에 생성 산출물을 실제로 쓰지 않으면 손으로 쓴 DDL과 Pydantic으로 내려갑니다.

**NORIA-O에서 빌릴 것.** NORIA-O(v0.3, 자체 클래스 30개, BSD-4-Clause)에는 Defect, SoftwareVersion, RootCause 클래스가 없습니다 [ontology, fact-check]. 그래서 통째로 들여오지 않고, 다섯 축에 맞는 패턴만 std_mapping 열에 적습니다.

| NORIA-O 클래스 | 이 설계의 대응 |
|---|---|
| TroubleTicket, EventRecord | Ticket(E3), 알람 이벤트(E7) |
| AnomalyPattern(Folio FailureMode의 하위 클래스) | Symptom |
| ChangeRequest, ChangeAction | Change |
| ProductModel | Product |

**대안 비교**

| 대안 | 판정 |
|---|---|
| 어휘와 hybrid 검색만 두고 그래프는 두지 않음 | S1c나 S2를 넘지 못할 때의 퇴로다. 어휘, 필터, 수정 추적, 중복·xref 표시는 그대로 남는다 |
| 스키마 없는 GraphRAG(MS GraphRAG, LightRAG) | 권하지 않는다. 질의당 token이 크고(#B-5), grounding 없는 추출은 ID가 흩어진다. MS GraphRAG는 maintenance mode라서 새 기능이 없다 [fact-check]. F2·F3를 대신하지 못한다 |
| NORIA-O를 그대로 들여오기 | 권하지 않는다. 위 표의 패턴만 빌린다 |
| 처음부터 OWL 정식 온톨로지 | 권하지 않는다. 근거는 위의 두 가지다 |

**정식 온톨로지로 넘어갈 신호.** 아래 가운데 둘 이상이 생기면 다시 엽니다 [ontology].
- 다른 부서, 고객 운영사, 벤더와 표준 모델(3GPP NRM, TMF SID)로 데이터를 주고받아야 한다.
- PLM, 티켓, 알람, CMDB처럼 ID 체계가 3개 이상 겹쳐서 alignment를 선언적으로 관리해야 한다.
- 제약 규칙이 수십 개를 넘어 SHACL 같은 검증 언어가 필요하다.
- 분류 추론(소속 판정)이 필요한 질의가 반복해서 들어온다.

첫 번째 신호가 없으면 RDF 변환은 나중에 해도 됩니다. property graph를 RDF로 옮기는 RML 매핑 경로가 있습니다 [ontology].

---

## D. 남은 불확실성과 확인 방법

| 불확실성 | 왜 중요한가 | 확인 방법 |
|---|---|---|
| 사내 PLM의 모양이 대체 데이터와 다르다 | 명시 관계는 공개 저장소의 수정 링크와 issue 번호에서 나온다. 수정 링크 비율은 adjacent 92.4%, ran-core 38.9%다 [profile]. 사내 PLM에 이 필드가 없으면 #B-3·#B-4 대부분이 흔들린다 | 1~2주차에 owner에게 필드 목록과 채움률을 받는다. 전환 시 사내 200건에 스크립트를 다시 돌린다. 중복+xref 연결률이 10.2%의 절반, 또는 식별자 pivot 포함 연결률이 33.4%의 절반(#B-1 표)보다 낮으면 그래프 층을 수정 추적만 남기고 줄인다 |
| dense+rerank 뒤 그래프로만 닿는 범위 | BM25 기준으로는 약한 원인 레코드의 9%, 전체의 2.8%였다(#B-1). dense가 더 줄일 수 있다 | S1c에서 잰다 |
| 원인 이어받기가 틀린 원인을 퍼뜨린다 | xref의 cause_class 일치율이 0.73이고, 같은 원인 비율은 이보다 낮다(#B-4) | S2의 관계 유형별 50건 감사에서 오답이 20%를 넘으면 그 관계의 원인 이어받기를 끄고 "관련 사례"로 내린다 |
| 3GPP 이름 정렬이 사내 모듈 트리와 맞지 않을 수 있다 | 벤더 고유 보드·블록 이름은 NRM IOC에 대응하지 않을 수 있다 | 사내 필드를 매핑할 때 대응되지 않는 비율을 잰다 |
| 다섯 축이 정말 안 바뀌는가 | 티켓·결함 다대다, 사이트별 설치 버전, bi-temporal 질의는 질의 template를 바꾼다 | E3 직전 설계 검토에서 template 재작성 비율을 잰다. 30%를 넘으면 축을 다시 연다 |
| 사내 DB가 자체 운영인지 관리형인지 | 관리형이면 pg_search를 쓸 수 없어서 "DB 하나 + 같은 SQL 안의 RLS"가 깨진다(#B-6). ParadeDB 라이선스는 AGPL-3.0으로 확인했다 [fact-check] | 사내 DB 플랫폼 팀에 확장 허용 여부를 묻는다. 안 되면 OpenSearch Nori와 문서 단위 보안으로 가고, 권한 경계가 둘로 갈라지는 비용을 설계에 적는다 |
| RLS와 BM25 custom scan, ANN 인덱스를 함께 쓸 때의 정확성과 recall | pg_search custom scan이 RLS 정책과 맞게 동작하는지 문서에서 확인되지 않았다. pgvector HNSW는 필터를 사후에 건다 [심사, fact-check] | 권한 정책을 건 테이블에서 역할별 EXPLAIN과 결과 집합을 비교한다. pgvector 0.8.0 iterative scan을 켠 뒤 등급별 Recall@k를 잰다. 떨어지면 등급별 partition을 검토한다 |
| MCP 서버에서 DB까지 신원 전달 | pool을 재사용할 때 이전 요청의 신원이 남으면 권한이 샌다 | #B-2 권한의 시험 항목을 7~8주차 S3에 넣는다 |
| 기권 임계값의 언어 의존성 | 한국어 질문과 영문 위주 본문 사이에서 reranker 점수 분포가 다를 수 있다 | S1에서 언어별 기권율·오기권율을 본다 |
| df≤10 임계값의 규모 의존성 | 1만 건에서 정한 값이다 | 사내 데이터에서 df 분포와 pivot 결과 수를 본다 |
| 묶음 (d)를 만드는 비용 | 전문가 0.3~0.5명으로 60개 이상, 일치율 0.85를 맞춰야 한다 | 2주차 시범 10묶음에 걸린 시간으로 일정을 다시 잡는다 |
| 데이터 도착 순서 | 시기가 모두 [추정]이다 | 사내 데이터 owner 인터뷰. FM이 먼저 오면 E7의 알람 사전을 앞당긴다 |
| 정규식으로 잰 Procedure 33.0%, Symptom 31.8% | 정밀도를 재지 않은 하한값이다(도메인 모델안의 실측) | A 단계 손라벨 200건에서 정밀도와 재현율을 잰다 |

외부 도구·명세 사실은 반박 단계에서 1차 출처로 확인했습니다. graphrag 3.3.0, neo4j-graphrag 1.23.0, MCP 명세 2026-07-28(stable), Kuzu archived, AGE 1.7.0 stable·1.8.0 승인 대기입니다 [fact-check].

---

## 반영하지 않은 반박

- **(a) 묶음 중 cause_class가 같은 55개를 자동 채택하자는 제안(ontology-and-graph-skeptic):** 반영하지 않았습니다. 데이터 근거 반박이 보였듯 cause_class는 거친 분류라서, cause_class가 같다고 원인까지 같지는 않습니다. 그래서 94개 전부를 전문가가 확정합니다. cause_class 일치는 확인 순서를 정하는 데만 씁니다.
- **A-4 "1·2·4번"을 '제안'으로 내리자는 제안 중 1번(SoftwareVersion)(ontology-and-graph-skeptic):** 1번은 '필수'로 남겼습니다. 반박의 근거(공개 데이터라 권한 열은 기본값으로 채울 수 있다, AlarmType 데이터는 4건이다)는 2·4번에만 해당합니다. SoftwareVersion이 없으면 `trace_fix`의 버전 답과 `version_range` 필터가 동작하지 않습니다. 2번(권한 열 등)과 4번(AlarmType)은 '제안'으로 내렸습니다.
- **router를 남기되 다중 라벨로 두자는 대안(ontology-and-graph-skeptic):** 같은 반박이 낸 다른 대안인 고정 파이프라인을 택했습니다. 다중 라벨 분류기는 슬롯 감지에만 씁니다.

---

## 변경 로그

- 결론: 그래프를 "식별자 공유 property graph"에서 "명시 관계 edge 세 종류 + 식별자 역색인 pivot"으로 바꿨다. 원인 이어받기를 중복·xref로 한정하고, 그래프 이득의 기대치(5.3%, 그래프만의 몫 2.8~9%)를 적었다.
- A-1: 부서 질문 22개가 조사자가 지은 예시라는 점을 밝혔다. 그래프 확장 도구는 S2 뒤의 선택 도구로 내렸다.
- A-2: F2를 "일부 된다, 최대 169건"으로 고쳤다. 582건(18.2%)은 처음에 끄는 PR·commit 관계를 포함한 값이라 뺐다. F3는 정본 resolution 59.8%를 근거로 "일부 된다"로 고쳤다.
- A-3: CVE-2025-15176 예시를 PFCP 142건에서 issue #4180 → DF-CORE-2025-02406 정확 일치로 바꿨다. 버전 범위 함수는 CVE와 SoftwareVersion 사이에만 쓴다. TN-AutoRCA 수치는 같은 모델 기준 0.59→0.92로 고치고, 그래프만의 기여가 측정되지 않았다고 적었다. TeleLogsAgent는 [추정]으로 내렸고 'TelcoInsight'는 뺐다.
- A-4: 표준 이름에 TS 28.111(FM)과 28.622/28.623(ManagedElement)을 적었다. 권한 열과 AlarmType을 '제안'으로 내렸다. 파생 객체 권한 규칙은 E3 진입 조건인 '필수'로 옮겼다.
- B-1: 관계 품질을 관련성과 원인 일치 두 기준으로 나눴다. 관계 집합별 연결률 표(10.2%, 20.0%, 33.4%, 40.8%)와 BM25 대비 그래프 단독 도달 범위를 더했다.
- B-2: router를 슬롯 기반 고정 파이프라인으로 바꿨다. `trace_fix.status`에 `not_backported`와 `wont_fix`를 더하고, `fix_ref_only`는 PR·commit 참조가 실제로 있을 때로 좁혔다. `find_by_identifier`에 issue·source_url·cve를 더했다. `aggregate`에 원인 미상 제외 표시를 더했다. 인용 표시를 "이어받은 원인"·"원인 후보"·"관련 사례"로 나눴다. MCP에서 DB까지의 신원 전달 방식을 더했다. 없음 판정 근거를 Global 방식 한정으로 고쳤고, 임계값은 언어별로 정한다.
- B-2 회귀 테스트: 예시 1의 기대값을 `not_backported`로 바꾸고 그래프 없이 풀리는 수정 추적 테스트로 옮겼다. 멀티홉 테스트는 검색만으로 안 되는 예시 4·3번으로 바꿨다.
- B-3·B-4: ErrorSignature·CodeSymbol 노드와 공유 edge를 역색인 테이블로 바꿨다. 관계 표에 원인 일치 상한(cause_class 일치율) 열을 더했다. SAME_FIX는 수정 추적 전용으로 바꿨다. 에러 문구 쌍 수는 다시 돌린 값 688로 고쳤다.
- B-5: location 고유값 9,151개는 "자유 텍스트 칸을 노드로 쓰지 않는다"의 근거로 옮겼다. token 표와 본문 서술이 엇갈린다는 점과 MS GraphRAG의 maintenance mode를 더했다.
- B-6: AGE를 쓰지 않는 이유를 rc 태그에서 CTE 충분성으로 바꿨다. ParadeDB AGPL-3.0, 관리형 PostgreSQL 위험, pgvector 0.8.0 iterative scan, pg_search 0.25.0의 pgvector 선행 요건을 더했다. Neo4j 이전 신호를 DB 쪽 질의 p95 1초로 바꿨다.
- B-8: 식별자 공유 관계의 df 재계산·valid_to 닫기·연결 요소 감시를 없앴다. 야간 감시는 명시 관계에만 두고 기준선은 구축 때 잰다. 수치 재현성 규칙을 더했다.
- B-9: 멀티홉 하위셋을 측정으로 정의했다. origin·장비군·언어 할당을 더했다. 정답 묶음 (a)는 후보 큐로 바꿨고 (b)는 17쌍+23쌍으로 나눴다. 원인 일치 확인 단계를 더했다. P14를 재현율 기준에서 뺐다. 분류 축 linking 기준을 S1b로 옮겼다. S1c(그래프 단독 도달 범위) 단계를 새로 넣었다. S2 표본 크기와 검정력은 bootstrap으로 다시 정하게 했다. S3에 `trace_fix.status` 정확도를 더했다. ETAgent 72%와 직접 비교하지 않는다고 적었다.
- B-10: (d) 시범 묶음과 사내 PLM 메타데이터 요청을 1~2주차로, 버전 정규화 v0를 3~4주차로, `trace_fix`를 5~6주차로 당겼다. S2 판정은 S0 뒤인 8주차 끝으로 옮겼다. 소스당 기간 [추정]은 근거가 없어서 "모름"으로 바꿨다.
- C: 비용 비교 사례를 근거에서 뺐다. NORIA-O에서 빌릴 패턴에 AnomalyPattern, ChangeRequest·ChangeAction, ProductModel을 더했다.
- D: 외부 도구 사실 행을 "확인함"으로 닫았다. ParadeDB·RLS 행을 관리형 DB와 custom scan 확인으로 바꿨다. 그래프 단독 도달 범위, 신원 전달, 언어 의존성 행을 더했다. 사내 비교 기준을 관계 집합별 연결률로 바꿨다.

---

이 권고안의 검증 상태는 `작성함`입니다. 이번에 직접 확인한 것은 세 가지이고 모두 `실행 확인함`입니다.
- `python3 -I`로 `dataset/canonical.jsonl`에서 DF-CORE-2023-01752, DF-CORE-2025-02406, DF-RAN-CU-2023-00147, DF-RAN-DU-2023-00436 원문을 읽었습니다.
- `profile/out/p2_edges.txt` 8·9절에서 40.8%, 628, 688, 중복 23·xref 146, 579/3193을 확인했습니다.
- `verify/v5_examples.py`에서 R1~R3 질문과 정답 목록을 확인했습니다.

나머지 수치는 각 조사와 세 반박에서 인용했습니다. 반박의 스크립트는 `analysis/round1/verify/`와 같은 폴더의 `skeptic/`에 있습니다. 프로젝트 파일은 수정하지 않았습니다.