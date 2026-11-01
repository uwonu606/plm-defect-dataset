# 변환 샘플 v1

어투·용어·필드 채우는 법을 확인받기 위한 샘플이다. 실제 이슈에서 변환한 10건과 제외한 이슈 목록으로 이루어진다. 합성 사례 4건은 합성을 쓰지 않기로 해서 지웠다. 필드 정의는 [schema.md](../docs/schema.md)에 있다.

## 실제 사례

### DF-CORE-2024-00001
- **title**: [UPF] F-TEID.ch=1인 PFCP Session Establishment Request 처리 중 assert 실패로 비정상 종료(crash)
- **equipment**: CORE
- **location**: UPF / PFCP Session Establishment / v2.7.2
- **problem**: fuzz 테스트에서 SMF가 보낸 PFCP Session Establishment Request를 처리하던 UPF가 assert 실패로 비정상 종료한다. v2.7.2에서 재현되지만 매번 재현되지는 않는다.
- **cause**: SMF가 최초 Session Establishment Request에 F-TEID를 넣지 않은 경우, F-TEID.ch=1(UPF가 TEID를 새로 할당해야 함)인데도 TEID 복원용 swap이 실행됐다.
- **cause_basis**: 명시
- **cause_class**: 프로토콜 처리
- **resolution**: F-TEID.ch=0일 때만 TEID swap을 하도록 조건을 추가했다(PR #3610).
- **origin**: ran-real · <https://github.com/open5gs/open5gs/issues/3574>

### DF-CORE-2026-00002
- **title**: [MME] implicit detach 중 UE context가 먼저 해제되어 EMM FSM EXIT 처리에서 비정상 종료
- **equipment**: CORE
- **location**: MME / EMM FSM `emm_state_registered()` / implicit detach
- **problem**: EMM REGISTERED 상태 UE의 implicit detach timer가 만료되면 MME가 `ogs_assert(mme_ue)` 실패로 비정상 종료한다. UE가 ECM-IDLE이고 GTP session이 없는 경로에서 발생한다.
- **cause**: `mme_send_delete_session_or_detach()`가 `mme_ue_remove()`를 바로 호출한 뒤 `OGS_FSM_TRAN()`이 실행되어, FSM이 EXIT 신호를 처리할 때 UE context가 이미 해제돼 있었다.
- **cause_basis**: 명시
- **cause_class**: 상태 관리
- **resolution**: S1 context가 없는 implicit detach 경로에서 UE context 제거를 FSM 처리 뒤로 미뤘다(PR #4304).
- **origin**: ran-real · <https://github.com/open5gs/open5gs/issues/4298>

### DF-CORE-2021-00003
- **title**: [UDM] Nudm_SDM GetDataSets에서 dataset-names 파라미터를 무시해 404 DATA NOT FOUND 응답
- **equipment**: CORE
- **location**: UDM / Nudm_SDM `getSupiProcedure` / free5GC v3.0.x
- **problem**: `GET /nudm-sdm/v1/{supi}?dataset-names=AM`처럼 AM data만 요청해도 UDM이 404 DATA NOT FOUND를 돌려주고 절차를 끝낸다.
- **cause**: `getSupiProcedure`가 dataset-names를 쓰지 않고 UDR에 전체 data set을 조회했다. 그래서 trace data가 없는 가입자는 조회 실패로 처리됐다.
- **cause_basis**: 명시
- **cause_class**: 규격 미준수
- **resolution**: 지정한 data set만 조회하도록 고쳤다. TS 29.503 5.2.2.2.9를 따른다(udm PR #9).
- **origin**: ran-real · <https://github.com/free5gc/free5gc/issues/200>

### DF-CORE-2021-00004
- **title**: [PCF] BDT policy 생성 요청에 500 Internal Server Error 응답
- **equipment**: CORE
- **location**: PCF / Npcf_BDTPolicyControl `POST /bdtpolicies`
- **problem**: BDT policy 생성 요청을 보내면 PCF가 본문 없이 500 Internal Server Error를 돌려준다.
- **cause**: 수신한 BdtReqData의 필수 IE를 검사하지 않고 처리를 진행했다.
- **cause_basis**: 추론
- **cause_class**: 입력 검증
- **resolution**: 처리 전에 BdtReqData 필수 IE 검사를 추가하고 처리 로직 버그를 고쳤다. TS 29.554 5.6.2.3을 따른다(pcf PR #4).
- **origin**: ran-real · <https://github.com/free5gc/free5gc/issues/255>

### DF-OAM-2020-00005
- **title**: [AGW enodebd] eNB 통계 초기화 중 AttributeError로 enodebd 비정상 종료
- **equipment**: OAM
- **location**: Access Gateway enodebd / `stats_manager.py` clear_stats
- **problem**: gateway에서 enodebd가 `AttributeError: '_LabelWrapper' object has no attribute 'set'`을 내고 비정상 종료한다.
- **cause**: datapath metrics에 eNB 이름 라벨(`enodeb`)이 추가됐는데, 통계를 초기화할 때 라벨 없이 값을 설정해서 prometheus_client가 예외를 냈다.
- **cause_basis**: 명시
- **cause_class**: 구현 오류
- **resolution**: 라벨이 붙은 datapath metrics는 초기화 대상에서 뺐다(PR #3627).
- **origin**: ran-real · <https://github.com/magma/magma/issues/3624>

### DF-RAN-CU-2025-00006
- **title**: [CU-CP] intra-CU handover 중 DU index 손상으로 std::out_of_range 비정상 종료
- **equipment**: RAN-CU
- **location**: CU-CP / intra-CU handover `handle_intra_cu_handover()` / DU 9대 : CU 1대 구성
- **problem**: 실외 상용 구성에서 handover 중 CU가 `std::out_of_range`로 비정상 종료한다. 대부분의 handover는 정상이지만 하루 한 번 이상 발생한다.
- **cause**: handover task가 함수 지역 변수인 `source_du_index`, `target_du_index`를 참조로 캡처했다. 함수가 반환된 뒤 coroutine이 해제된 스택 값을 읽어 잘못된 index로 접근했다.
- **cause_basis**: 명시
- **cause_class**: 자원 관리
- **resolution**: DU index를 값으로 캡처하도록 고쳤다(commit "cu_cp: fix handover DU index lifetime").
- **origin**: ran-real · <https://github.com/srsran/srsRAN_Project/issues/1307>

### DF-RAN-CU-2018-00007
- **title**: [eNB RRC] SIB1에 광고하지 않은 SIB3 송신, 설정한 SIB4는 미송신
- **equipment**: RAN-CU
- **location**: eNB RRC / SIB 스케줄링 `sib.conf` `si_mapping_info`
- **problem**: optional SIB를 설정하지 않았는데도 SIB1 `schedulingInfoList`에 없는 빈 SIB3가 송신된다. SIB4를 설정하면 SIB1에는 광고되지만 실제로는 SIB2, SIB3만 송신된다.
- **cause**: SIB 매핑 정보를 처리할 때 SIB 개수와 index 계산이 틀렸다.
- **cause_basis**: 추론
- **cause_class**: 설정
- **resolution**: SIB 매핑 카운팅 로직을 고쳤다(PR #135).
- **origin**: ran-real · <https://github.com/srsran/srsRAN_4G/issues/134>

### DF-RAN-CU-2026-00008
- **title**: [CU-CP RRC] RRC Resume Complete에 실린 NAS 메시지를 AMF로 전달하지 않음
- **equipment**: RAN-CU
- **location**: CU-CP RRC / RRC resume 절차 / F1AP·NGAP
- **problem**: piggyback NAS가 담긴 RRC Resume Complete를 받으면 NAS 메시지가 AMF로 전달되지 않고 사라진다. F1AP·NGAP pcap에서 확인된다.
- **cause**: RRC resume 절차가 Resume Complete의 NAS 메시지를 UL NAS TRANSPORT로 보내는 처리를 하지 않았다.
- **cause_basis**: 추론
- **cause_class**: 프로토콜 처리
- **resolution**: UE resume 뒤 NAS 메시지를 UL NAS TRANSPORT로 보낸다. peer에서 UE context를 가져온 경우에는 path switch 뒤에 보낸다. 단위 테스트를 추가했다(MR !1968).
- **origin**: ran-real · <https://gitlab.com/ocudu/ocudu/-/work_items/971>

### DF-PLATFORM-2022-00009
- **title**: [플랫폼 설치] Debian ISO 설치 후 재부팅 시 간헐적으로 emergency mode 진입
- **equipment**: PLATFORM
- **location**: StarlingX Debian ISO 설치 / AIO-SX / lvm2
- **problem**: H/W 랩에서 ISO 설치 후 재부팅하면 가끔 login prompt 대신 emergency mode prompt가 뜬다. 다시 설치하면 대개 정상이다.
- **cause**: LV activation이 비결정적 순서로 일어나 provisioning 단계에서 볼륨이 준비되지 않았다.
- **cause_basis**: 추론
- **cause_class**: 플랫폼
- **resolution**: lvm2 upstream의 event_activation 수정을 적용했다(starlingx/integ commit 5253741).
- **origin**: adjacent-real · <https://bugs.launchpad.net/bugs/1979105>

### DF-PLATFORM-2018-00010
- **title**: [OpenShift node] 프로젝트 static egress IP 대신 node IP로 트래픽이 간헐적으로 나감
- **equipment**: PLATFORM
- **location**: OpenShift node(kube-proxy, kubelet) iptables 연동 / 3.9.0
- **problem**: 프로젝트 단위 static egress IP를 설정했는데 일부 프로젝트의 트래픽이 한동안 egress IP를 가진 node의 IP로 나간다.
- **cause**: kube-proxy와 kubelet이 iptables 연동 설정 기본값을 서로 다르게 받았다. 그래서 잘못된 iptables 규칙이 주기적으로 추가됐다.
- **cause_basis**: 명시
- **cause_class**: 설정
- **resolution**: 두 구성 요소의 설정 불일치를 없애서 잘못된 규칙이 더는 추가되지 않는다.
- **origin**: adjacent-real · <https://bugzilla.redhat.com/show_bug.cgi?id=1560584>

## 제외한 이슈

v1에서는 후보 28건 중 18건을 아래 이유로 뺐다. 지금 규칙([schema.md](../docs/schema.md))에서는 단말 쪽 결함, 테스트·CI 실패, 빌드, 기능 요청도 레코드가 된다.

| 이유 | 건수 | 예 |
|---|---|---|
| 원인을 추론할 근거가 없음 | 3 | open5gs#548, free5gc#117, OAI#972 |
| 단말(UE) 쪽 결함 | 2 | OAI#1072, OAI#1026 |
| 테스트·CI 실패 | 4 | OCUDU#931, OCUDU#913, Neutron#1552063, Neutron#1896766 |
| 빌드·패키징 | 3 | srsRAN_4G#99, StarlingX#1788872, StarlingX#1833444 |
| 기능 요청·개선·정리 | 6 | magma#8, magma#6396, Neutron#1201537, #1251653, #1291570, #2092907 |
