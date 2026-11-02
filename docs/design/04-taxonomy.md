# 결함 분류 체계

## 결론

결함 기록을 문제점·원인·해결책 세 축으로 나누는 분류 체계 v3이다. 축마다 L1을 질문 하나로 나누고, 다른 기준(누구 것인지, 어디서 찾았는지, 무엇을 바꿨는지)은 facet으로 뺐다. 파일은 `taxonomy/problem.json`, `cause.json`, `resolution.json`이다.

| 축 | L1을 가르는 질문 | L1 |
|---|---|---|
| problem(문제점) | 무엇이 어떻게 잘못 보였나 | `p.halt` 비정상 종료·멈춤, `p.stage` 빌드·시험·설치·기동 실패, `p.conn` 접속·연결 이상, `p.func` 기능 오동작, `p.perf` 성능·자원 이상, `p.sec` 보안 통제 실패, `p.info` 문서·출력 문구 이상, `p.state` 구성요소·설비 상태 이상, `p.gap` 기능·개선 필요 |
| cause(원인) | 결함이 어떤 종류의 요소에 있었나 | `c.code` 소프트웨어 결함, `c.hw` 하드웨어 결함, `c.content` 설정·데이터·문서 내용 결함, `c.supply` 빌드·의존 구성 결함, `c.test` 시험 자산 결함, `c.operation` 운용·구축 결함, `c.env` 외부 조건·사건 |
| resolution(해결책) | 어떤 종류의 조치로 끝났나 | `r.change` 산출물 변경 반영, `r.field` 현장 조치·복구, `r.process` 절차·조직 조치, `r.verdict` 변경 없이 판정 종결, `r.unresolved` 해결되지 않음 |

깊이는 축 루트 아래 3단(L1·L2·L3)까지다. L1·L2는 표준 범주가 받치면 데이터가 없어도 열고, L3는 데이터 조건을 넘을 때만 연다. 그래서 L3는 cause의 `c.code.guard`와 `c.code.state` 아래 5개뿐이다.

v3는 다시 재지 않았다. v2를 Haiku로 두 번 단 실측과, 반박 세 건이 낸 근거로 고쳤다. 아래 숫자는 모두 v2(또는 v1) 실측이다.

## 용어

| 용어 | 뜻 |
|---|---|
| L1·L2·L3 | 축 루트 바로 아래가 L1(대분류), 그 아래가 L2(중분류), L3(세분류)다 |
| facet | 트리 밖에 따로 다는 속성이다. 예: 위치 facet NF=AMF |
| 특수 코드 | 트리 밖 라벨 셋이다. `_none` 정보 없음, `_na` 해당 없음, `_other` 맞는 노드 없음 |
| 주·보조 라벨 | 레코드마다 축별로 주 라벨 1개(필수)와 보조 라벨 0~1개를 단다 |
| 판정 가능 표 | 특수 코드를 뺀 주 라벨 표. 크기 규칙(2%, 25%)의 분모다 |
| pass A·B | 같은 Haiku·같은 프롬프트로 레코드 순서와 묶음만 바꿔 두 번 단 것이다 |
| kappa | Cohen's kappa. 두 pass가 우연히 같은 답을 낼 몫을 뺀 일치도다. 1이면 완전 일치다 |
| 개정 표본 | v2를 고칠 때 엇갈림을 읽은 450건이다(seed 20261103) |
| held-out | 개정 표본에 없고 어느 분류 체계 파일에도 인용되지 않은 450건이다(seed 20261104) |
| v1·v2·v3 | v1은 세 귀납 결과를 합친 판, v2는 v1 실측을 읽고 고친 판, v3는 v2에 반박을 반영한 이 판이다 |
| status | 노드마다 붙인 상태다. measured(v2와 같음), revised(정의 고침), merged(합침), new(v2에 없음) |

## 판정 원칙

세 축은 서로 독립이다. 한 축의 판정 조건에 다른 축의 값을 쓰지 않는다. v2에서 이 원칙이 깨진 세 곳을 고쳤다.

| v2에서 깨진 곳 | v3 |
|---|---|
| cause L1을 '무엇을 고쳐야 사라지나'로 골랐다. `c.env`는 '제품을 고치지 않고 해소'로 정의됐다 | L1을 '결함이 어떤 종류의 요소에 있었나'로 바꾸고, 고쳤는지는 resolution 축에만 둔다 |
| `r.change` L2(바꾼 산출물)가 cause L1을 되풀이했다. 원인이 `c.code`인 표 634개 중 631개가 `r.change.code`였다 | `r.change`를 잎으로 접고 바꾼 산출물은 변경 산출물 facet으로 옮겼다 |
| '결함 아님·미지원'이 `p.gap.capability`, `c.expect`, `r.verdict.not_defect` 세 곳에 적혔다 | 판정은 `r.verdict`만 담는다. cause는 `_na`, problem은 관찰된 증상 노드다 |

'어디서'(장비군·NF·프로토콜·제품·버전·모듈)는 세 축 모두 트리에 넣지 않는다. 'AMF crash'는 problem `p.halt` + 위치 facet NF=AMF다.

## 깊이·넓이 정책

| 규칙 | 값 | 근거 |
|---|---|---|
| 최대 깊이 | 3 | v1·v2 어디에도 4단 노드가 없었다. 2로 줄이면 held-out에서 안정된 L3(guard 0.969, state 0.957)를 잃는다 |
| L1 수 | 축마다 4~9 | 메인 세션 기본값. problem은 v2 그대로면 10개가 되어 `p.deploy`와 `p.dev`를 합쳤다 |
| 자식 수 | 2~9 | 메인 세션 기본값 |
| 한 층 한 기준 | 형제는 축의 질문 하나로 나눈다 | v2 엇갈림의 큰 몫이 기준이 섞인 곳에서 났다. held-out cause 엇갈림 58건 중 35건이 기준이 섞인 `c.code` 안이었다 |
| L1·L2 여는 근거 | 표준 범주가 받치거나, 둘 이상의 문서 종류에서 따로 판정 가능 | 빈도로만 열면 지금 데이터 모양을 따른다. `p.stage.install`은 표본 1.8%지만 StarlingX Critical 20건에서 35%였다 |
| L3 여는 조건 | 자식마다 판정 가능 표 2% 이상, held-out 같은 L2 안 L3 일치 0.9 이상. 표준 값과 1:1이면 2% 면제 | rebut-structure가 낸 조건이다. v2의 L3 12개 중 면제(`guard.access`)를 포함해 5개만 남는다 |
| 합치기 | 겹치거나 혼동되는 형제, 넓이 근거 없이 판정 가능 표 2% 미만인 노드 | 메인 세션 기본값에서 2% 규칙의 적용 범위만 좁혔다 |
| 중간 노드 배정 | 하위를 가를 근거가 없거나 맞는 자식이 없으면 중간 노드. 2%를 넘으면 자식 개설 후보 | v2는 축마다 규칙이 달랐다(resolution만 명시). `_other` 대신 중간 노드가 확장 신호를 모은다 |
| `_other` 비율 | 트리 적합성 근거로 쓰지 않는다 | 가상 레코드 72표 중 `_other`는 0표였다. 정의가 배제하는 경우(자사 HW를 `c.env`에)도 가까운 노드로 갔다 |

## 트리

### problem

| L1 | L2 | status | v2에서 |
|---|---|---|---|
| `p.halt` 비정상 종료·멈춤 | (잎) | measured | 같음 |
| `p.stage` 빌드·시험·설치·기동 실패 | `build` 빌드·환경 준비, `test` 시험, `install` 설치·업그레이드, `startup` 기동·초기화 | merged | `p.dev.build·test` + `p.deploy.*` |
| `p.conn` 접속·연결 이상 | `setup` 수립 실패, `delivery` 끊김·전달 실패 | revised | 서비스 영향만 있으면 `_none` |
| `p.func` 기능 오동작 | `fail` 요청·작업 실패, `wrong` 잘못된 결과·상태 | revised | 코드 읽기 지적을 받음 |
| `p.perf` 성능·자원 이상 | (잎) | revised | 코드 읽기 지적을 받음 |
| `p.sec` 보안 통제 실패 | (잎) | revised | 보조 라벨로 안 씀 |
| `p.info` 문서·출력 문구 이상 | `doc` 문서, `log` 로그·알람·화면 문구 | measured | 같음 |
| `p.state` 구성요소·설비 상태 이상 | `equipment` 장비·부품 고장, `environment` 환경·설비 조건 | new | 없음 |
| `p.gap` 기능·개선 필요 | `capability` 기능·지원 부재, `maint` 코드·시험·절차 보강 | revised | 미지원 판정 결함을 뺌 |

주 라벨은 서비스 영향이 큰 증상부터 고른다. 순서는 `p.halt` > `p.stage.install·startup` > `p.conn` > `p.sec` > `p.func` > `p.perf` > `p.state` > `p.info` > `p.stage.build·test` > `p.gap`이다.

### cause

| L1 | L2 | L3 | status |
|---|---|---|---|
| `c.code` 소프트웨어 결함 | `logic` 처리 논리 | (잎) | merged |
| | `guard` 검사·오류 처리 | `input` 입력 검증, `access` 인가·출처 검증, `error` 실패 결과·예외 처리 | measured |
| | `state` 상태·수명주기 | `lifecycle` 생성·정리 시점, `transition` 초기화·전이·복원 | measured |
| | `concurrency` 동시성·실행 순서 | (잎) | measured |
| | `resource` 자원·성능 | (잎) | merged |
| | `interface` 구성요소 계약 불일치 | (잎) | revised |
| | `encoding` 표현·인코딩 | (잎) | revised |
| `c.hw` 하드웨어 결함 | `design` HW 설계, `failure` 고장·제조 불량 | | new |
| `c.content` 설정·데이터·문서 내용 결함 | `config` 설정·데이터 값, `doc` 문서·절차서 | | revised |
| `c.supply` 빌드·의존 구성 결함 | `build` 빌드·패키징·CI 정의, `dependency` 의존 요소 변경·버전 부적합 | | revised |
| `c.test` 시험 자산 결함 | (잎) | | merged |
| `c.operation` 운용·구축 결함 | `procedure` 작업 절차, `design` 구성·용량 설계 | | new(L2) |
| `c.env` 외부 조건·사건 | `power` 전원·설비, `physical` 외부 물리 사건·전파, `attack` 악의적 공격, `service` 외부 서비스·기반 장애 | | new(L2) |

결함이 누구 것인지는 원인 소재 facet(자사 개발 / 공급사·OSS / 운용자·사용자 / 제3자 / 자연)에 적는다. upstream library bug와 kernel 회귀는 `c.code`, 운용자가 넣은 틀린 설정은 `c.content.config`로 간다.

### resolution

| L1 | L2 | status | v2에서 |
|---|---|---|---|
| `r.change` 산출물 변경 반영 | (잎) | merged | `r.change.code·test·build·doc` |
| `r.field` 현장 조치·복구 | `adjust` 설정·절차 조정, `upgrade` 다른 버전으로 해소, `env` 외부 환경 수정, `recover` 복구·교체 | revised | `recover` 새로 |
| `r.process` 절차·조직 조치 | (잎) | new | 없음 |
| `r.verdict` 변경 없이 판정 종결 | `not_defect` 결함 아님, `redirect` 다른 곳으로 넘김, `decline` 조치 안 함 결정 | measured | 같음 |
| `r.unresolved` 해결되지 않음 | `pending` 반영 대기, `abandoned` 해결 없이 종결 | measured | 자동 해소는 `recover`로 |

`r.change`와 `r.field`는 '누가 했나'가 아니라 '배포되는 산출물이 바뀌었나, 이 설치·현장만 바뀌었나'로 가른다. 주 라벨은 기록을 끝낸 조치, 보조 라벨은 다른 단계의 조치 하나(대개 재발 방지)다.

### 특수 코드

| 코드 | problem | cause | resolution |
|---|---|---|---|
| `_none` | 기술 증상을 판정할 내용이 없다. 서비스 영향만 있어도 여기 | 증상만 있고 원인·구체적 해결 서술이 없다 | 조치·판정·예정·종결 사실이 없다 |
| `_na` | 현상도 부족함도 없는 작업 기록·사용법 문의 | 고칠 결함이 없다(기능 요청, 결함 아님 판정, 사용법 문의) | 해결할 문제가 없는 공지·통지 |
| `_other` | 판정할 내용은 있지만 맞는 노드가 없다 | 같음 | 같음 |

### facet

| 축 | facet | 값 |
|---|---|---|
| 공통 | 위치 | 장비군·NF·프로토콜·제품·버전·모듈 |
| problem | 탐지 활동, 관찰 여부 | 운용·고객 신고·알람·시험·CI·코드 검토·분석 도구·보안 제보 / 관찰·예상 |
| problem | 재현성, 보안 영향, 서비스 영향, 계기 동작 | 항상·간헐·1회 / 있음·없음 / 중단·저하·영향 없음 / 설정 변경·upgrade 등 |
| cause | 원인 소재, 요구 출처, 누락·오류, 원인 역할 | 자사·공급사·운용자·제3자·자연 / 표준·상대 계약·내부 / ODC Qualifier / 근본·함께 보인 메커니즘·확대 기여 |
| resolution | 조치 주체, 변경 산출물, 임시성, 조치 단계 | 벤더·운용자·사용자·자동 / code·config·test·build·doc·hw / 임시 우회·영구 / 복구·근본 수정·재발 방지 |
| resolution | 조치 항목, 반영 범위, 고객 대응 | [{노드, 단계}] / 수정 버전·backport·lot / 보상·정정·설명·안내 |

facet은 정의만 했다. `taxonomy/label.py`는 트리 라벨만 단다.

## 합치기·나누기 결정

| 결정 | 근거 | 출처 |
|---|---|---|
| `p.deploy` + `p.dev` → `p.stage` | 같은 실패 모양을 환경(개발·운용)으로 갈랐다. 환경은 탐지 활동 facet이다. L1 10개도 막는다 | rebut-overlap, rebut-structure |
| `p.dev.finding` 없앰 | 루트가 facet이라고 한 탐지 활동·관찰 여부를 노드로 담았다. held-out problem 엇갈림 44건 중 15건에 `p.dev`가 끼었다 | rebut-overlap, rebut-structure |
| `p.state` 새 L1 | X.733 equipmentAlarm·environmentalAlarm 자리가 없었다. 가상 알람 3건이 두 pass 모두 `_other` | rebut-newdoc(필수) |
| `c.hw` 새 L1 | 자사 fan lot 불량·DRAM 제조 불량이 두 pass 모두 `c.env`(제품 밖)로 갔다 | rebut-overlap(필수) |
| `c.env` L2 넷 | 가상 장애 보고서 60표 중 47%가 `c.env` 잎 하나에 몰렸다. NORS가 Power Failure, Environment-External, Cable Damage를 나눈다 | rebut-newdoc(필수) |
| 누구 것인지 → 원인 소재·조치 주체 facet | 사업자 보고서에서 resolution A·B 불일치가 27%(결함 데이터 약 3%)였다. 원인은 '제품·사용 측' 기준점이 없어서다 | rebut-newdoc(필수, B안) |
| `c.operation` L2 procedure·design | 용량 산정 누락, 이중화 설계 오류가 `c.code.resource`·`c.content.config`·`c.operation` 사이에서 흔들렸다 | rebut-newdoc |
| `c.expect` 없앰 → `_na` | 처분이 세 축에 적혔다. 고칠 결함이 없으면 원인을 물을 수 없다 | rebut-overlap |
| `c.code.logic.case·decision·compute` → `logic` 잎 | held-out 엇갈림 1위(case↔decision 8건). 누락/오류는 ODC Qualifier라 facet이다. compute는 2% 미만이다 | rebut-overlap, rebut-structure |
| `c.code.conformance` 없앰 | 규격을 근거로 들었는지라는 작성자 문체로 판정됐다. procedure는 요구 출처 facet + `logic`, format은 `c.code.encoding` | rebut-overlap, rebut-structure |
| `c.code.resource`, `c.test` 잎으로 접음 | 갈래 전체가 판정 가능 표 1.7~2.0%(resource), test.env 2% 미만이고 표준 근거가 없다 | rebut-structure |
| `c.code.guard.access` 남김 | 2% 미만이지만 CWE 접근 제어 항목과 1:1로 대응한다 | rebut-structure |
| `r.change` 잎으로 접음 | L2가 cause L1을 되풀이했고 부모↔자식 엇갈림을 만들었다(held-out 5건) | rebut-overlap, rebut-structure |
| `r.field.recover` 새 L2 | 장비 교체·재시작이 `r.field.env`(외부 환경)에 섞였다. 알람 자동 해제는 `r.unresolved.abandoned`로 갔다 | rebut-overlap, rebut-newdoc |
| `r.process` 새 L1 | 사례집 91건 중 61건(67%)의 재발 방지책이 절차·검토·교육·체계·연락이었다 | rebut-newdoc(필수) |
| resolution 특수 코드 노드 추가 | v2 파일에 없었는데 v2 라벨은 `_none`을 11~13% 썼다 | rebut-structure(필수) |
| include·exclude에서 case_code 136개 제거 | 정의와 이번 표본용 경계 사례가 섞였다. 경계 사례는 v2 작업 기록에 남는다 | rebut-structure |

v2까지의 합치기(crash·hang → `p.halt`, `p.func.config` 폐지, interface.call·peer 합침, `r.verdict.duplicate` → `redirect`, planned·proposed → `pending`)는 그대로 이어받았다.

## 실측

### v1 → v2 일치도

같은 Haiku로 pass A·B를 단 일치도다. n=450에서 두 일치율 차이의 표준오차는 약 2%p다.

| 축 | 표본 | L1 일치 | 잎 일치 | kappa(L1) | kappa(잎) |
|---|---|---|---|---|---|
| problem | 개정 표본 | 0.929→0.958 | 0.900→0.944 | 0.915→0.950 | 0.891→0.939 |
| problem | held-out | 0.920→0.920 | 0.896→0.902 | 0.906→0.906 | 0.887→0.894 |
| cause | 개정 표본 | 0.927→0.967 | 0.840→0.896 | 0.899→0.954 | 0.824→0.885 |
| cause | held-out | 0.922→0.953 | 0.851→0.871 | 0.897→0.938 | 0.836→0.857 |
| resolution | 개정 표본 | 0.978→0.984 | 0.953→0.969 | 0.959→0.971 | 0.936→0.958 |
| resolution | held-out | 0.964→0.969 | 0.920→0.933 | 0.935→0.943 | 0.892→0.910 |

held-out에서 확실히 오른 것은 cause L1 하나다. 개정 표본의 상승에는 표본 맞춤이 섞였다. v1에서 일치했고 v2 파일에 인용되지 않은 레코드는 v2에서 오히려 내려갔다(cause 1.0→0.918).

### 특수 코드와 라벨 사용 (v2, 개정 표본 / held-out, 900표 기준)

| 축 | `_none` | `_na` | `_other` | 중간 노드 | 보조 라벨 |
|---|---|---|---|---|---|
| problem | 0% / 0% | 0.3% / 0% | 0% / 0% | 0% / 0% | 23.1% / 17.7% |
| cause | 14.6% / 17.2% | 20.9% / 21.0% | 0% / 0% | 0.3% / 0.9% | 10.6% / 9.4% |
| resolution | 13.3% / 11.2% | 0% / 0% | 0% / 0% | 2.9% / 3.1% | 14.2% / 14.8% |

cause `_na`는 기능 요청 94건 전부가 받았다. v3에서 `c.expect`를 `_na`로 옮기면 개정 표본 23.4%, held-out 22.2%가 된다.

### v2 L1 비중 (개정 표본, 900표 기준)

| 축 | 비중 |
|---|---|
| problem | func 20.4, conn 18.2, gap 17.9, dev 16.3, halt 13.4, info 5.3, deploy 4.2, perf 2.6, sec 1.2 |
| cause | code 44.6, supply 6.4, test 5.6, env 2.8, expect 2.6, operation 1.6, content 1.1 (나머지는 특수 코드) |
| resolution | change 65.1, unresolved 9.3, field 6.9, verdict 5.3 (나머지는 `_none`) |

### v3로 옮길 때

v2 라벨 1,800표(개정 표본·held-out, A·B)를 v3 id로 기계적으로 옮겨 봤다. 옮길 수 없는 표는 다시 달아야 한다.

| 축 | 다시 달아야 할 표 | 일부만 옮겨지는 표 | 이유 |
|---|---|---|---|
| problem | 4.1~4.9% | 0% | `p.dev.finding` |
| cause | 4.3~6.0% | 4.1~4.3% | `c.env`·`c.operation`이 여러 L1로 흩어진다. `c.supply.dependency` 중 upstream bug는 `c.code`로 간다 |
| resolution | 2.7~3.1% | 0% | `r.field.env`에서 `recover`가 떨어진다 |

옮길 수 있는 레코드만 보면 v3 잎 일치는 held-out에서 problem 0.914, cause 0.912, resolution 0.963이다. 합친 노드 덕에 오르는 값이라 v3의 실력으로 읽지 않는다. `r.change`는 판정 가능 표의 76~78%를 받는다.

`taxonomy/label.py`를 v3 파일로 20건 돌려 스크립트가 끝까지 도는 것을 확인했다(호출 4회, 오류 0, $0.03). 20건은 일치도를 말하기에 너무 적다.

## 새 문서 종류 적합성

rebut-newdoc과 rebut-overlap이 가상 레코드와 일본 총무성 통신 사고 사례집으로 v2를 시험했다. 가상 레코드는 에이전트가 지은 것이라 분포 근거가 아니고 경계 사례 시험으로만 쓴다.

| 문서 종류 | v2에서 본 것 | v3에서 받는 곳 |
|---|---|---|
| 알람(FM) | PSU 고장·온도 초과·인증서 만료 임박 3건이 두 pass 모두 `_other`. fronthaul 자동 clear가 `r.unresolved.abandoned` | `p.state`(만료 임박은 중간 노드), `c.hw`, `c.env.power`, `r.field.recover` |
| 장애 보고서 | 사례집 20건: `c.env` 47%, resolution A·B 불일치 27%, 재발 방지책 받을 노드 없음, 조치 중앙값 4개 | `c.env` L2, `c.operation.design`, 원인 소재·조치 주체 facet, `r.process`, 조치 항목 facet |
| 고객 티켓 | 사용법 문의가 `_na`와 `p.info.doc`로 갈림. 보상·청구 정정 자리 없음 | problem `_na`(사용법 문의), 고객 대응 facet |
| CVE | `p.sec` 1.2%라 2% 규칙이면 접힘. kernel use-after-free가 `c.supply.dependency`로 가 메커니즘을 잃음 | `p.sec` 유지(표준 근거), `c.code.state.lifecycle` + 원인 소재=공급사, `c.code.guard.access` |
| 시험 리포트 | '규격과 다르다'만 아는 기록의 자리 | `c.code` + 요구 출처=표준, `c.code.encoding` |
| 다른 트래커(StarlingX) | 20건 수동 라벨에서 새 L1 필요 없음, `p.deploy.install` 35% | `p.stage.install` |

깊이 3이 모자란 사례는 없었다. 모자란 것은 폭과 기준점이었다.

## 기존 cause_class 대응

`docs/schema.md`의 원인 분류 14종이 v3 어디로 가는지다. '주로 간 곳'은 v2 실측이다.

| cause_class | 주로 간 곳(v2) | v3 |
|---|---|---|
| 구현 오류 | `c.code` 0.98 | `c.code.logic` 등 `c.code` 아래 |
| 입력 검증 | `c.code.guard` 57/62표 | `c.code.guard.input` |
| 상태 관리 | `c.code` 0.96 | `c.code.state` |
| 동시성 | concurrency 21/28표 | `c.code.concurrency` |
| 자원 관리 | v1: state 6, resource 4표 | `c.code.resource`, 해제 후 사용은 `c.code.state.lifecycle` |
| 성능·타이밍 | v1: resource 9표 | `c.code.resource` |
| 프로토콜 처리 | `c.code` 1.0(logic 15, conformance 6표) | `c.code.logic`, `c.code.encoding`(요구 출처=표준) |
| 규격 미준수 | v1: `c.code` 1.0 | `c.code.logic`, `c.code.encoding`(요구 출처=표준) |
| 연동 | v1: interface 5, dependency 3표 | `c.code.interface`, `c.supply.dependency` |
| 설정 | 0.375로 흩어짐 | 주로 `c.content.config`(제공 값·운용 값 모두), 코드가 값을 잘못 읽으면 `c.code` |
| 플랫폼 | `c.env` 0.50 | `c.supply.dependency`, `c.code`(원인 소재=공급사), `c.content.config`, `c.env` |
| 빌드·의존성 | `c.supply` 0.81 | `c.supply` |
| 테스트 | `c.test` 0.82 | `c.test` |
| 결함 아님 | 0.52로 흩어짐 | `_na`. 처분은 `r.verdict.not_defect` |

'설정'과 '결함 아님'은 원인 종류라기보다 계기와 처분이라서 흩어졌다. v3에서 '설정'은 누가 넣었든 `c.content.config` 하나로 모인다.

## 현재 데이터에 맞춘 임시값

| 값 | 위치 | 임시인 이유 |
|---|---|---|
| 2%(합치기·L3) | `depth_policy` | 공개 트래커 결함 표본에서 정했다 |
| 25%(큰 잎) | `depth_policy` | 같음. `r.change`가 넘지만 독립 의미가 없어 남겼다 |
| 0.9(L3 일치) | `depth_policy` | held-out의 guard 0.969, state 0.957, logic 0.869를 가르는 값으로 골랐다 |
| problem 주 라벨 순서 | `p` 루트 include | v1 라벨러의 습관(halt 주 + conn 보조 13표, 반대 0표)에서 출발했고 원칙은 뒤에 붙였다 |
| cause `_na`에 레코드 유형 사용 | cause `_na` | '기능 요청' 유형 필드가 있는 데이터에서만 통한다. 유형이 없는 문서는 내용으로 판정한다 |
| examples | 노드마다 | 공개 트래커 레코드다. held-out 레코드는 쓰지 않았다 |
| v2 비중 | 이 문서 #실측 | 수정이 반영된 결함 위주 표본이라 `r.change`·`c.code`가 크다 |

## 한계

- v3는 재라벨하지 않았다(미검증). 고친 정의가 엇갈림을 줄이는지는 held-out으로 다시 재야 안다.
- 두 pass는 같은 모델·같은 프롬프트라서 일치도는 모델이 같은 답을 내는 정도의 상한이다. 사람 두 명의 일치도는 재지 않았다.
- `p.state`, `c.hw`, `c.env` L2, `c.operation` L2, `r.process`, `r.field.recover`는 실제 레코드 예시가 거의 없다. 근거는 표준 범주, 가상 레코드, 사례집 20건이다.
- 원인 소재 facet을 달기 전에는 '우리 탓인가'를 트리만으로 답하지 못한다. upstream bug와 자사 bug가 같은 `c.code`에 있다.
- `r.change`가 판정 가능 표의 76~78%라 이 데이터에서는 resolution 축의 구별력이 낮다.
- std_mapping 일부는 원문과 대조하지 않았다(IANAItuProbableCause 번호, CWE, OpenVEX, ITIL). 파일에 '미대조'·'미확인'으로 적었다.

## 반영하지 않은 반박

| 반박 | 출처·강도 | 이유 |
|---|---|---|
| `c.code.interface`를 L2에서 빼고 요구 출처 facet으로 | rebut-overlap, 제안 | ODC Defect Type에 Interface가 있는 메커니즘 값이다. 요구 출처 facet은 따로 두었다 |
| 보고자 오독·오용을 `c.operation`과 합쳐 '사용·해석 측 오류'로 | rebut-overlap, 제안 | 실패 없는 오독은 고칠 결함이 없어 `_na`로, 실제 실패를 낸 오용은 `c.content.config`·`c.operation.procedure`로 보냈다 |
| `c.env`·`c.operation` L2는 열지 말고 열 조건만 적기 | rebut-structure, 제안 | rebut-newdoc의 필수 지적(`c.env` 47%)과 새 넓이 규칙(표준 범주면 연다)에 따라 열었다 |
| `p.conn`을 facet으로 빼고 L1은 실패 모양만 | rebut-structure, 참고 A안 | 참고 등급이다. v2 판정 기준(접속·전달 실패가 원문에 적혔나)을 유지했다 |
| 재발 방지를 네 번째 축으로 | rebut-newdoc, 필수의 대안 | `r.process` L1 + 조치 단계·조치 항목 facet으로 받았다. 축을 늘리면 레코드마다 빈 칸이 생긴다 |
| 기준 시스템을 루트에 정의하는 A안 | rebut-newdoc, 필수의 대안 | 권고된 B안(facet)을 택했다. `r.change`의 '배포되는 산출물'만 A안에서 가져왔다 |
| `p.state` L2 '만료·고갈 임박' | rebut-newdoc, 제안 | 표준 대응을 찾지 못했다. 중간 노드 직접 배정으로 받고 열 조건에 적었다 |
| `_other` 대신 라벨러가 인용한 include 구절의 적합 비율 재기 | rebut-overlap, 참고 | `label.py`에 넣지 않았다. 새 문서 종류를 실측할 때의 과제로 남긴다 |
| StarlingX를 tag로 층화해 다시 뽑기 | rebut-newdoc, 참고 | 데이터 수집 과제라 이번 범위 밖이다 |

## 파일

| 경로 | 내용 |
|---|---|
| `taxonomy/problem.json`, `cause.json`, `resolution.json` | v3 분류 체계. 축 정의, 라벨 규칙, 깊이 정책, 노드, 특수 코드, facet, 열 조건, v2에서 바뀐 것 |
| `taxonomy/label.py` | Haiku 두 pass 라벨링과 일치도·분포 집계 |
| `taxonomy/labels_sample.jsonl` | v2 라벨 1,800행(개정 표본·held-out × pass A·B) |
| `taxonomy/README.md` | 사용법 |

반박과 실측의 작업 이름은 다음과 같다. 스크립트와 출력은 작성자 로컬 작업 폴더에 있어서 레포에 없다.

| 이름 | 한 일 |
|---|---|
| label-v1, label-v2 | v1·v2를 개정 표본과 held-out에 두 번씩 달아 일치도·분포를 냈다(Haiku, 합쳐 약 $1.5) |
| rebut-overlap | 겹침·누락 렌즈. 가상 레코드 12건 × 3축 × 2 pass, v2 라벨 교차 집계 |
| rebut-newdoc | 새 문서 종류 렌즈. 총무성 사례집 20건·가상 알람·티켓 10건을 Haiku로 두 번, StarlingX 20건 수동 |
| rebut-structure | 깊이·구조 렌즈. v1·v2 라벨 재집계, 새 Haiku 호출 없음 |
