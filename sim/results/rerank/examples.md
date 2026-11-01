# 시뮬레이션 예시

test split에서 유형마다 첫 문항을 골라 다섯 구성의 실행 경로와 답을 나란히 둔다. 생성은 `python3 -I sim/make_examples.py`.

## single-003

```text
free5gc AMF에서 Registration Request를 비정상 길이로 보내면 NAS 파싱 중에 프로세스가 죽고, 그 뒤 reject 보내는 단계에서 또 터지는 것 같아요. 비슷한 증상 과거에 있었나요?
```

- 정답 case: `DF-CORE-2026-02530`

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.9163}) | 상위 3: DF-CORE-2021-00813, **DF-CORE-2026-02530**, DF-CORE-2021-00809 | 0 |
| dag_regex | slots={"product": "free5gc"} intents=[] → find_by_identifier({"n": 3}) → search({"filters": {"product": "free5gc"}, "top": 0.8729}) | 상위 3: DF-UE-2025-00378, DF-CORE-2020-00368, DF-CORE-2023-01947 | 0 |
| dag_llm_front | LLM 전처리(query="free5gc AMF Registration Request NAS 파싱 crash 비정상 길이 Registration Rej, in_scope=True) → slots={"product": "free5gc"} intents=[] → find_by_identifier({"n": 3}) → search({"filters": {"product": "free5gc"}, "top": 0.9685}) | 상위 3: DF-UE-2025-00378, DF-CORE-2020-00368, DF-CORE-2023-01947 | 1 |
| llm_loop | search({"query": "AMF Registration Request 비정상 길이 NAS 파싱 중 프로세스 크래시, reject 메시지 전송 단계에서 재크래시", "f) | 상위 3: **DF-CORE-2026-02530**, DF-CORE-2025-02417, DF-CORE-2026-02464 | 2 |
| llm_planner | search({"query": "AMF Registration Request NAS 파싱 중 비정상 길이 메시지로 프로세스 크래시", "filters": {"product":) → search({"query": "AMF Registration Reject 전송 단계에서 크래시 또는 패닉", "filters": {"product": "free5gc"}, ) → expand_related({"case_code": "$s1.top"}) | 상위 3: DF-CORE-2021-01151, **DF-CORE-2026-02530**, DF-CORE-2025-02324 | 1 |

## multihop-003

```text
free5gc 기반 N3IWF 테스트에서 UE를 라우터로 쓰는데, UE 뒤 10.0.1.2에서 보낸 ping만 실패하고 UE 자체 대역 ping은 돼요. 원인이 뭔지, 비슷한 사례 있는지 궁금합니다.
```

- 정답 case: `DF-CORE-2020-00276`

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.9842}) | 상위 3: DF-CORE-2020-00290, DF-CORE-2021-00894, DF-CORE-2021-00914 | 0 |
| dag_regex | slots={"product": "free5gc", "equipment": "UE", "cause_class": "테스트"} intents=['cause'] → find_by_identifier({"n": 0}) → search({"filters": {"product": "free5gc"}, "top": 0.9842}) → expand_related({"seed": "DF-CORE-2020-00290", "added": ["DF-CORE-2020-00276"]}) → expand_related({"seed": "DF-UE-2022-00207", "added": []}) → expand_related({"seed": "DF-CORE-2022-01512", "added": []}) | 상위 3: DF-CORE-2020-00290, **DF-CORE-2020-00276**, DF-CORE-2021-00894 | 0 |
| dag_llm_front | LLM 전처리(query="free5gc N3IWF UE router ping 실패 forwarding 라우팅 IPsec 10.0.1.2 ip_forw, in_scope=True) → slots={"product": "free5gc"} intents=['cause'] → find_by_identifier({"n": 0}) → search({"filters": {"product": "free5gc"}, "top": 0.9482}) → expand_related({"seed": "DF-UE-2022-00207", "added": []}) → expand_related({"seed": "DF-CORE-2022-01512", "added": []}) → expand_related({"seed": "DF-CORE-2020-00290", "added": ["DF-CORE-2020-00276"]}) | 상위 3: DF-UE-2021-00167, DF-UE-2022-00207, DF-CORE-2022-01512 | 1 |
| llm_loop | search({"query": "N3IWF 테스트 UE 라우터 뒤 단말 10.0.1.2 ping 실패, UE 대역 ping은 성공", "filters": {"product":) → get_case({"case_code": "DF-CORE-2020-00290"}) | 상위 3: DF-CORE-2020-00290, DF-CORE-2023-01883 | 3 |
| llm_planner | search({"query": "N3IWF 테스트에서 UE를 라우터로 사용, UE 뒤 단말 ping 실패, UE 자체 대역 ping 성공, 라우팅 또는 NAT 문제", "fi) → expand_related({"case_code": "$s1.top"}) | 상위 3: DF-CORE-2020-00290, **DF-CORE-2020-00276**, DF-CORE-2021-00894 | 1 |

## fix-003

```text
neutron.conf의 service_plugins에 lbaasv2 alias를 넣으면 neutron server가 아예 시작되지 않는데, 이 문제 고쳐진 패치나 수정 버전이 있는지 알려주세요.
```

- 정답 case: `DF-PLATFORM-2016-02206`
- 정답 수정 상태: `fixed_in_version`

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.9754}) | 상위 3: **DF-PLATFORM-2016-02206**, DF-PLATFORM-2017-02403, DF-PLATFORM-2016-02063 | 0 |
| dag_regex | slots={"product": "neutron"} intents=['fix'] → find_by_identifier({"n": 10}) → search({"filters": {"product": "neutron"}, "top": 0.9754}) → trace_fix({"case": "DF-PLATFORM-2018-02773", "status": "fix_ref_only"}) | 상위 3: DF-PLATFORM-2018-02773, DF-PLATFORM-2017-02521, DF-PLATFORM-2016-02078; status=fix_ref_only | 0 |
| dag_llm_front | LLM 전처리(query="neutron service_plugins lbaasv2 alias neutron-server 시작 실패 startup cr, in_scope=True) → slots={"product": "neutron"} intents=['fix'] → find_by_identifier({"n": 10}) → search({"filters": {"product": "neutron"}, "top": 0.9823}) → trace_fix({"case": "DF-PLATFORM-2018-02773", "status": "fix_ref_only"}) | 상위 3: DF-PLATFORM-2018-02773, DF-PLATFORM-2016-02078, DF-PLATFORM-2014-01112; status=fix_ref_only | 1 |
| llm_loop | search({"query": "neutron.conf service_plugins lbaasv2 alias neutron server fails to start", "fil) → trace_fix({"case_code": "DF-PLATFORM-2016-02206"}) | 상위 3: **DF-PLATFORM-2016-02206**, DF-PLATFORM-2015-01309, DF-PLATFORM-2016-02063; status=fix_ref_only | 3 |
| llm_planner | search({"query": "neutron server fails to start when lbaasv2 alias is added to service_plugins in) → find_by_identifier({"text": "lbaasv2"}) → trace_fix({"case_code": "$s1.top"}) | 상위 3: **DF-PLATFORM-2016-02206**, DF-PLATFORM-2018-02704, DF-PLATFORM-2015-01309; status=fix_ref_only | 1 |

## composite-003

```text
neutron LBaaS v2에서 존재하지 않는 subnet_id로 pool member를 추가하면 load balancer가 PENDING_UPDATE에서 10분 넘게 안 빠져나오는데, 왜 이런 건지랑 패치 여부 알려줘.
```

- 정답 case: `DF-PLATFORM-2016-01952`
- 정답 수정 상태: `fixed_in_version`

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.9992}) | 상위 3: **DF-PLATFORM-2016-01952**, DF-PLATFORM-2015-01654, DF-PLATFORM-2015-01238 | 0 |
| dag_regex | slots={"product": "neutron"} intents=['cause', 'fix'] → find_by_identifier({"n": 1}) → search({"filters": {"product": "neutron"}, "top": 0.9992}) → expand_related({"seed": "DF-PLATFORM-2016-02280", "added": []}) → expand_related({"seed": "DF-PLATFORM-2015-01654", "added": []}) → trace_fix({"case": "DF-PLATFORM-2016-02280", "status": "fix_ref_only"}) | 상위 3: DF-PLATFORM-2016-02280, **DF-PLATFORM-2016-01952**, DF-PLATFORM-2015-01654; status=fix_ref_only | 0 |
| dag_llm_front | LLM 전처리(query="neutron LBaaS v2 pool member subnet_id 존재하지 않음 PENDING_UPDATE stuck l, in_scope=True) → slots={"product": "neutron"} intents=['cause', 'fix'] → find_by_identifier({"n": 1}) → search({"filters": {"product": "neutron"}, "top": 0.9988}) → expand_related({"seed": "DF-PLATFORM-2016-02280", "added": []}) → expand_related({"seed": "DF-PLATFORM-2015-01654", "added": []}) → trace_fix({"case": "DF-PLATFORM-2016-02280", "status": "fix_ref_only"}) | 상위 3: DF-PLATFORM-2016-02280, **DF-PLATFORM-2016-01952**, DF-PLATFORM-2015-01654; status=fix_ref_only | 1 |
| llm_loop | search({"query": "LBaaS v2 pool member 존재하지 않는 subnet_id 추가 시 load balancer PENDING_UPDATE 고착", ") → trace_fix({"case_code": "DF-PLATFORM-2016-01952"}) | 상위 3: **DF-PLATFORM-2016-01952**; status=fixed_in_version | 3 |
| llm_planner | search({"query": "neutron LBaaS v2 pool member add nonexistent subnet_id load balancer stuck PEND) → expand_related({"case_code": "$s1.top"}) → trace_fix({"case_code": "$s1.top3"}) | 상위 3: **DF-PLATFORM-2016-01952**, DF-PLATFORM-2015-01238, DF-PLATFORM-2015-01697; status=fixed_in_version | 1 |

## logpaste-003

```text
현장에서 아래 로그가 반복해서 찍힙니다. 비슷한 사례와 원인 있으면 알려 주세요.
[2026-10-22 20:59:24.705] Validation of PDUSessionResourceSetupRequest failed
```

- 정답 case: `DF-RAN-CU-2026-00375`

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.3791}) | 상위 3: **DF-RAN-CU-2026-00375**, DF-RAN-CU-2026-00342, DF-CORE-2025-02222 | 0 |
| dag_regex | slots={} intents=['cause'] → find_by_identifier({"n": 2}) → search({"filters": {}, "top": 0.3791}) → expand_related({"seed": "DF-CORE-2023-01835", "added": []}) → expand_related({"seed": "DF-CORE-2026-02644", "added": []}) | 상위 3: **DF-RAN-CU-2026-00375**, DF-CORE-2023-01835, DF-RAN-CU-2026-00342 | 0 |
| dag_llm_front | LLM 전처리(query="PDUSessionResourceSetupRequest Validation failed NGAP PDU session res, in_scope=True) → slots={} intents=['cause'] → find_by_identifier({"n": 2}) → search({"filters": {}, "top": 0.642}) → expand_related({"seed": "DF-CORE-2023-01835", "added": []}) → expand_related({"seed": "DF-CORE-2025-02356", "added": []}) → expand_related({"seed": "DF-CORE-2021-01303", "added": []}) | 상위 3: **DF-RAN-CU-2026-00375**, DF-CORE-2023-01835, DF-RAN-CU-2026-00342 | 1 |
| llm_loop | find_by_identifier({"text": "Validation of PDUSessionResourceSetupRequest failed"}) → search({"query": "Validation of PDUSessionResourceSetupRequest failed NGAP PDU session resource s) → get_case({"case_code": "DF-RAN-CU-2026-00375"}) | 상위 3: **DF-RAN-CU-2026-00375**, DF-RAN-CU-2024-00206, DF-RAN-CU-2024-00205 | 4 |
| llm_planner | search({"query": "Validation of PDUSessionResourceSetupRequest failed 반복 발생", "k": 5}) → find_by_identifier({"text": "Validation of PDUSessionResourceSetupRequest failed"}) → expand_related({"case_code": "$s1.top"}) → trace_fix({"case_code": "$s1.top"}) | 상위 3: **DF-RAN-CU-2026-00375**, DF-CORE-2023-01835, DF-CORE-2021-00583; status=fix_ref_only | 1 |

## aggregate-003

```text
2019년에 등록된 open5gs CORE 장비 레코드 중 원인 분류가 '결함 아님'인 것은 몇 건이야?
```

- 정답 건수: 13

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.2568}) | 상위 3: DF-CORE-2026-02960, DF-CORE-2026-02856, DF-CORE-2026-02841 | 0 |
| dag_regex | slots={"product": "open5gs", "equipment": "CORE", "year": "2019", "record_type": "결함", "cause_class": "결함 아님"} intents=['aggregate', 'cause'] → aggregate({"product": "open5gs", "equipment": "CORE", "year": "2019", "record_type": "결함", "cause_cl) | count=13 | 0 |
| dag_llm_front | LLM 전처리(query="open5gs CORE 결함 아님 원인 분류 레코드 건수 2019", in_scope=True) → slots={"product": "open5gs", "equipment": "CORE", "year": "2019", "cause_class": "결함 아님"} intents=['aggregate'] → aggregate({"product": "open5gs", "equipment": "CORE", "year": "2019", "cause_class": "결함 아님"}) | count=13 | 1 |
| llm_loop | aggregate({"filters": {"product": "open5gs", "equipment": "CORE", "year": "2019", "cause_class": "결함) | count=13 | 2 |
| llm_planner | aggregate({"filters": {"product": "open5gs", "equipment": "CORE", "year": "2019", "cause_class": "결함) | count=13 | 1 |

## unanswerable-003

```text
광중계기 내부 온도가 올라가면서 출력이 떨어지는데, 방열 팬을 교체하기 전에 확인할 항목은 무엇인가요?
```

- 정답: 기권(데이터에 없음)

| 시스템 | 실행 경로 | 답 | LLM 호출 |
|---|---|---|---|
| search_only | search({"top": 0.0001}) | 기권; 상위 3: DF-PLATFORM-2021-03356, DF-CORE-2026-02543, DF-CORE-2021-00931 | 0 |
| dag_regex | slots={} intents=[] → find_by_identifier({"n": 0}) → search({"filters": {}, "top": 0.0002}) | 기권; 상위 3: DF-UE-2020-00155, DF-PLATFORM-2021-03356, DF-CORE-2026-02543 | 0 |
| dag_llm_front | LLM 전처리(query="광중계기 내부 온도 상승 출력 저하 방열 팬 optical repeater temperature output power fa, in_scope=False) → slots={} intents=['cause'] → find_by_identifier({"n": 0}) → search({"filters": {}, "top": 0.0256}) → expand_related({"seed": "DF-RAN-DU-2021-00294", "added": []}) | 기권; 상위 3: DF-UE-2020-00155, DF-CORE-2021-00931, DF-RAN-DU-2021-00294 | 1 |
| llm_loop | search({"query": "광중계기 내부 온도 상승 출력 저하 방열 팬", "k": 10}) → search({"query": "광중계기 방열 팬 내부 온도 상승 출력 저하 하드웨어 점검", "k": 10}) | 기권 | 3 |
| llm_planner | search({"query": "광중계기 내부 온도 상승 출력 저하 방열 팬 냉각", "filters": {}, "k": 5}) → expand_related({"case_code": "$s1.top"}) | 기권; 상위 3: DF-RAN-DU-2026-00939, DF-RAN-DU-2026-01028, DF-RAN-DU-2022-00313 | 1 |
