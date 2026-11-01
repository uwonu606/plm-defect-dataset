# 작성자 문체 비교

시범 정본과 문체 버전을 작성자마다 한 건씩 나란히 놓았다. 작성자 정의는 [personas.md](../docs/personas.md)에 있다.

## P02 · DF-RAN-CU-2026-00001

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [gNB RRC] DRB 없이 SRB2만 남은 UE의 RRCReestablishment에서 `num_pdu_sessions > 0` assert 실패로 비정상 종료(crash) | [gNB RRC] DRB가 없고 SRB2만 남아 있는 UE에서 RRCReestablishment 시 `num_pdu_sessions > 0` assert 실패로 gNB가 비정상 종료(crash)되는 문제 |
| `location` | gNB RRC / RRCReestablishment `cuup_notify_reestablishment()` `rrc_gNB.c` / E1 | gNB RRC / RRCReestablishment 처리부 `cuup_notify_reestablishment()` (`rrc_gNB.c`) / E1 인터페이스 |
| `problem` | COTS UE가 SRB1·SRB2만 있고 DRB가 없는 상태에서 RRCReestablishment가 일어나면 gNB가 assert 실패로 비정상 종료한다. Quectel UE로 PDU session을 `AT+CGACT=1,1`로 맺고 `AT+CGACT=0,1`로 해제한 뒤 RRCReestablishment를 일으키면 재현된다. 로그: `Assertion (num_pdu_sessions > 0) failed!` `In cuup_notify_reestablishment() /home/user/openairinterface5g/openair2/RRC/NR/rrc_gNB.c:1105`. 보고자는 커버리지가 나쁜 곳에서 PDU session 수립 전에 재수립이 일어나도 같은 상황이 된다고 적었다. | COTS UE가 SRB1, SRB2만 가지고 있고 DRB는 없는 상태에서 RRCReestablishment가 발생하면 gNB가 assert 실패로 비정상 종료(crash)하는 현상이 있었습니다. Quectel UE를 사용해서 `AT+CGACT=1,1`로 PDU session을 맺은 다음 `AT+CGACT=0,1`로 해제하고, 그 뒤에 RRCReestablishment를 일으키면 재현되는것을 확인했습니다. 로그는 다음과 같습니다: `Assertion (num_pdu_sessions > 0) failed!` `In cuup_notify_reestablishment() /home/user/openairinterface5g/openair2/RRC/NR/rrc_gNB.c:1105`. 그리고 보고자 분께서는 커버리지가 나쁜 곳에서 PDU session이 수립되기 전에 재수립이 일어나는 경우에도 같은 상황이 된다고 적어 주셨습니다. |
| `cause` | PDU session 해제로 DRB가 모두 없어진 UE에 대해서도 RRCReestablishment 처리 중 CU-UP 통지(E1 bearer modification)를 시도했다. TS 38.331 5.3.1.1에 따라 마지막 DRB를 해제할 때 SRB2도 함께 해제해야 하는데 gNB가 SRB2를 남겨 두었다. | PDU session 해제로 인해서 DRB가 모두 없어진 UE인데도, RRCReestablishment를 처리하는 중에 CU-UP 통지(E1 bearer modification)를 시도했습니다. TS 38.331 5.3.1.1에 따르면 마지막 DRB를 해제할 때 SRB2도 같이 해제해야 하는데, gNB가 SRB2를 그대로 남겨 둔 것이 원인으로 보임 |
| `resolution` | `cuup_notify_reestablishment()`가 DRB 목록이 비어 있으면 바로 반환하도록 고쳤다(commit cb9dab74e). PDU session 해제 뒤의 잘못된 connected 상태도 함께 고쳤다(PR #225). | `cuup_notify_reestablishment()`에서 DRB 목록이 비어 있으면 바로 반환하도록 수정했습니다(commit cb9dab74e). 그리고 PDU session 해제 뒤에 잘못된 connected 상태로 남아 있던 부분도 함께 수정했습니다(PR #225). |

## P03 · DF-RAN-CU-2023-00005

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [gNB RRC/NGAP] RHEL 8에서 PDUSessionResourceSetupRequestTransfer 디코딩 중 asn_set_add segfault | [gNB RRC/NGAP] segfault in asn_set_add during PDUSessionResourceSetupRequestTransfer decode on RHEL 8 |
| `location` | gNB RRC `decodePDUSessionResourceSetup()` rrc_gNB_NGAP.c:285 / NGAP PDUSessionResourceSetupRequestTransfer aper_decode / RHEL 8 | gNB RRC `decodePDUSessionResourceSetup()` rrc_gNB_NGAP.c:285 / NGAP PDUSessionResourceSetupRequestTransfer aper_decode / RHEL 8 |
| `problem` | UE 여러 대를 붙이거나 UE 하나를 끊었다 다시 붙이면 gNB가 비정상 종료(crash)한다. rfsim에서 UE가 IP를 받은 뒤 ctrl+c로 끊고 다시 실행하면 재현된다. `Thread 9 "TASK_RRC_GNB" received signal SIGSEGV, Segmentation fault.` backtrace는 `asn_set_add()` asn_SET_OF.c:24에서 멈춘다. | UE 여러 대 붙이거나 UE 하나 끊었다 다시 붙이면 gNB crash. rfsim에서 UE가 IP 받은 뒤 ctrl+c로 끊고 다시 실행하면 재현. `Thread 9 "TASK_RRC_GNB" received signal SIGSEGV, Segmentation fault.` backtrace stops at `asn_set_add()` asn_SET_OF.c:24. |
| `cause` | `aper_decode()`에 넘기는 변수를 제대로 초기화하지 않았다. | `aper_decode()`에 넘기는 변수 초기화안 됨. |
| `resolution` | uper_decode(), aper_decode()에 넘기는 변수를 제대로 초기화했다. 모든 호출처를 점검해 dlsim의 잘못된 사용도 고쳤다(MR !2161). | uper_decode(), aper_decode() 넘기는 변수 제대로 초기화. 모든 호출처 점검, dlsim 잘못된 사용도 수정(MR !2161). |

## P04 · DF-RAN-DU-2026-00001

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [imscope] 2026.w17에서 C++가 함수 정의의 VLA를 처리하지 못해 imscope 빌드 실패 | [imscope] 2026.w17 C++ VLA 함수 정의 미처리로 imscope 빌드 실패 |
| `location` | PHY imscope `imscope.cpp`, nr_modulation.h / 2026.w17 | PHY imscope `imscope.cpp`, nr_modulation.h / 2026.w17 |
| `problem` | `cmake -B build-imscope -GNinja -DENABLE_IMSCOPE=ON` 뒤 `ninja -C build-imscope imscope`가 실패한다. `nr_modulation.h:40:46: error: use of parameter outside function body before ‘]’ token` | cmake -B build-imscope -GNinja -DENABLE_IMSCOPE=ON 뒤 ninja -C build-imscope imscope 실패<br>`nr_modulation.h:40:46: error: use of parameter outside function body before ‘]’ token` |
| `cause` | imscope.cpp가 include하는 header에 함수 정의의 VLA(`c16_t mod_symbs[nbCodes][encoded_len]`)가 들어갔는데, C++는 OAI 옵션에서 이를 알지 못한다. !3762의 commit 0dd1243e6eae345de761ebfb3bad38467b8fce80에서 생긴 regression이다. | imscope.cpp가 include하는 header에 함수 정의 VLA(`c16_t mod_symbs[nbCodes][encoded_len]`) 포함 C++는 OAI 옵션에서 미인식 !3762 commit 0dd1243e6eae345de761ebfb3bad38467b8fce80 regression |
| `resolution` | imscope에 필요한 header가 VLA를 직접·간접으로 include하지 않게 해서 C++ source에서 include할 수 있게 했다(MR !4076, imscope·tracy 빌드 수정). | imscope용 header가 VLA를 직간접 include하지 않도록 수정 C++ source에서 include 가능(MR !4076 imscope·tracy 빌드 수정) |

## P05 · DF-UE-2025-00001

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [NR UE RRC·RLC] optional IE인 rlc-Config, physCellId를 확인 없이 참조해 crafted DL-DCCH-Message로 segfault | [NR UE RRC·RLC] optional IE rlc-Config, physCellId를 확인 없이 참조해 crafted DL-DCCH-Message로 segfault |
| `location` | NR UE RLC `nr_rlc_add_drb()` nr_rlc_oai_api.c, NR UE RRC rrc_UE.c:1713 / DL-DCCH rrcReconfiguration / 2025.w45 | NR UE RLC `nr_rlc_add_drb()` nr_rlc_oai_api.c, NR UE RRC rrc_UE.c:1713 / DL-DCCH rrcReconfiguration / 2025.w45 |
| `problem` | 조작한 DL-DCCH-Message(rrcReconfiguration)로 NR UE에서 segfault 두 건을 일으킬 수 있다. 첫째는 `nr_rlc_add_drb()`의 `rlc_BearerConfig->rlc_Config->present` 접근이고, 둘째는 `rrc->phyCellID = *reconfigurationWithSync->spCellConfigCommon->physCellId;`이다. | 조작한 DL-DCCH-Message(rrcReconfiguration)로 NR UE에서 segfault 2건을 유발할 수 있다.<br>1. rrcReconfiguration에 조작한 DL-DCCH-Message를 전달한다.<br>2. `nr_rlc_add_drb()`의 `rlc_BearerConfig->rlc_Config->present` 접근에서 첫 번째 segfault가 발생한다.<br>3. `rrc->phyCellID = *reconfigurationWithSync->spCellConfigCommon->physCellId;`에서 두 번째 segfault가 발생한다. |
| `cause` | ASN.1 정의에서 RLC-BearerConfig의 rlc-Config와 ServingCellConfigCommon의 physCellId는 OPTIONAL인데, 코드가 있는지 확인하지 않고 바로 역참조했다. | ASN.1 정의상 RLC-BearerConfig의 rlc-Config와 ServingCellConfigCommon의 physCellId는 OPTIONAL인데, 코드가 존재 여부를 확인하지 않고 바로 역참조했다. |
| `resolution` | MR !3750(Handling newly opened UE issues)이 #1024, #1025, #1026, #1030, #1031과 함께 닫았다. | MR !3750(Handling newly opened UE issues)이 #1024, #1025, #1026, #1030, #1031과 함께 종료했다. |

## P06 · DF-UE-2016-00002

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [NAS] EIA1·EIA2 XMAC 계산의 count를 논리 OR로 만들어 두 번째 DL NAS Transport부터 integrity 검사 실패 | [NAS] EIA1·EIA2 XMAC 계산 count를 논리 OR로 만들어 두 번째 DL NAS Transport부터 integrity 검사 실패 |
| `location` | NAS 공통 API `_nas_message_get_mac()` openair3/NAS/COMMON/API/NETWORK/nas_message.c:1306, 1372 / EIA1·EIA2 | NAS 공통 API `_nas_message_get_mac()` openair3/NAS/COMMON/API/NETWORK/nas_message.c:1306, 1372 / EIA1·EIA2 |
| `problem` | COTS UE(EIA1), OAI eNB, COTS EPC 구성에서 attach하면 두 번째 DL NAS Transport 메시지를 받을 때 `mac != msg->header.message_authentication_code`로 NAS integrity 검사가 실패한다. DL NAS Transport가 두 번 이상인 attach에서 재현된다. | COTS UE(EIA1), OAI eNB, COTS EPC 구성에서 attach하면 두 번째 DL NAS Transport 메시지를 받을 때 `mac != msg->header.message_authentication_code`로 NAS integrity 검사가 실패한다. DL NAS Transport가 두 번 이상인 attach에서 재현된다. |
| `cause` | EIA1, EIA2용 count를 만들 때 bit OR `\|` 대신 논리 OR `\|\|`를 써서 count 값이 틀렸다. | EIA1, EIA2용 count를 생성할 때 bit OR `\|` 대신 논리 OR `\|\|`를 사용해 count 값이 잘못됐다. |
| `resolution` | 원문에 반영 기록이 없다. 보고자는 ul_count, dl_count 계산의 `\|\|`를 `\|`로 바꾸는 수정안을 냈다. | 반영된 MR·PR 기록은 없다. 보고자가 ul_count, dl_count 계산의 `\|\|`를 `\|`로 바꾸는 수정안을 제시했다. |

## P07 · DF-CORE-2026-00002

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [NSSF] NSSF 설정에 없는 TAI로 NSSelection 요청 시 nil pointer dereference panic, HTTP 500 응답 | [NSSF] NSSF 설정에 없는 TAI로 NSSelection을 요청하면 nil pointer dereference panic이 발생하고 HTTP 500으로 응답한다 |
| `location` | NSSF / Nnssf_NSSelection `GET /nnssf-nsselection/v2/network-slice-information` / `nsselection_network_slice_information.go:588` | NSSF / Nnssf_NSSelection (`GET /nnssf-nsselection/v2/network-slice-information`) / `nsselection_network_slice_information.go:588` |
| `problem` | 형식은 맞지만 `nssfcfg.yaml`에 없는 TAI로 NSSelection 요청을 보내면 NSSF가 Go runtime panic을 내고 500 Internal Server Error를 돌려준다. 로그: `[WARN][NSSF][Util] No TA {"plmnId":{"mcc":"460","mnc":"00"},"tac":"000001"} in NSSF configuration` 뒤에 `panic: runtime error: invalid memory address or nil pointer dereference`. 보고자는 Gin recovery가 panic을 잡아 process는 살아 있지만, 요청한 AMF가 500을 받아 해당 UE의 PDU session 수립이 실패한다고 적었다. | 조건: 형식은 유효하나 `nssfcfg.yaml`에 정의되지 않은 TAI로 NSSelection을 요청한다. 결과: NSSF에서 Go runtime panic이 발생하고 500 Internal Server Error가 반환된다. 로그는 `[WARN][NSSF][Util] No TA {"plmnId":{"mcc":"460","mnc":"00"},"tac":"000001"} in NSSF configuration` 다음에 `panic: runtime error: invalid memory address or nil pointer dereference`가 이어진다. 보고자에 따르면 Gin recovery가 panic을 처리하므로 process는 유지되지만, 요청한 AMF가 500을 수신하므로 해당 UE의 PDU session 수립은 실패한다. |
| `cause` | `nsselectionForPduSession`이 설정에서 TA를 찾지 못하면 결과 변수가 nil로 남는데, 588행이 nil 검사 없이 이 값을 참조했다. | `nsselectionForPduSession`은 설정에서 TA를 찾지 못하면 결과 변수를 nil로 둔다. 588행은 nil 여부를 검사하지 않고 이 값을 참조한다. |
| `resolution` | 메인테이너가 재현하지 못했다. 같은 TAI 요청에 OAuth token이 있으면 200 `rejectedNssaiInTa`, 없으면 401이 돌아왔다. 메인테이너는 commit hash, `nssfcfg.yaml`, 전체 로그를 요청하고 free5gc 4.2.2에서 해소됐는지 확인해 보라고 답했다. | 메인테이너는 재현에 실패했다. 동일한 TAI 요청에 대해 OAuth token이 있으면 200(`rejectedNssaiInTa`), 없으면 401이 반환되었다. 메인테이너는 commit hash, `nssfcfg.yaml`, 전체 로그를 요청하였고, free5gc 4.2.2에서 해소되었는지 확인할 것을 권했다. |

## P08 · DF-CORE-2026-00004

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [SMF] PCF가 CreateSMPolicyError로 응답하면 unchecked type assertion으로 panic, PDU Session Establishment가 500으로 실패 | [SMF] PCF가 CreateSMPolicyError로 응답하면 SMF 패닉(unchecked type assertion), PDU Session Establishment 500으로 실패 |
| `location` | SMF / Npcf_SMPolicyControl_CreateSMPolicy 오류 응답 처리 `pdu_session.go:194` / main branch | SMF / Npcf_SMPolicyControl_CreateSMPolicy 에러 응답 처리 `pdu_session.go:194` / main 브랜치 |
| `problem` | PDU Session Establishment 중 SMF가 호출한 `Npcf_SMPolicyControl_CreateSMPolicy`가 실패하고 PCF가 `SMPolicyControl.CreateSMPolicyError` 타입으로 응답하면 SMF에서 panic이 난다. UDR에 SM Policy Data가 없는 SUPI로 `POST /nsmf-pdusession/v1/sm-contexts`를 한 번 보내면 기본 배포에서 재현된다. Gin recover가 panic을 잡아 process는 살아 있지만, 요청은 HTTP 500으로 실패하고 매번 stack trace가 로그에 찍힌다. | PCF 에러 오면 SMF 패닉 터짐(프로세스는 안 죽음). PDU Session Establishment 중에 SMF가 부른 `Npcf_SMPolicyControl_CreateSMPolicy`가 실패하고 PCF가 `SMPolicyControl.CreateSMPolicyError` 타입으로 응답하면 SMF에서 패닉 남. UDR에 SM Policy Data 없는 SUPI로 `POST /nsmf-pdusession/v1/sm-contexts` 한번만 쏴도 기본 배포에서 바로 재현됨. Gin recover가 패닉 잡아줘서 프로세스는 살아있는데, 요청은 HTTP 500으로 실패하고 매번 stack trace가 로그에 찍힘. |
| `cause` | `pdu_session.go:194`가 `problemDetails := openapiError.Model().(models.ProblemDetails)`로 단일 값 type assertion을 해서, 오류 본문이 `models.ProblemDetails`가 아닌 경우를 처리하지 못했다. TS 29.512에 따라 CreateSMPolicy는 더 구체적인 `SMPolicyControl.CreateSMPolicyError`를 돌려줄 수 있다. | `pdu_session.go:194`에서 `problemDetails := openapiError.Model().(models.ProblemDetails)`로 단일 값 type assertion을 해버려서, 에러 본문이 `models.ProblemDetails`가 아닌 경우를 못 받음. TS 29.512 보면 CreateSMPolicy는 더 구체적인 `SMPolicyControl.CreateSMPolicyError`를 돌려줄 수 있음. |
| `resolution` | smf PR #207로 고쳤다. 메인테이너는 최신 free5GC 버전에 이 수정이 들어 있다고 답했다. | smf PR #207로 고침. 메인테이너 말로는 최신 free5GC 버전엔 이 수정 들어가 있음. |

## P09 · DF-CORE-2020-00001

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [UPF 빌드] free5gc-stage-3에서 고친 testgtpv1 생성 누락과 README clone 경로가 free5gc 저장소에 반영되지 않음 | [UPF build] testgtpv1 generation fix and README clone path from free5gc-stage-3 not reflected in free5gc repo |
| `location` | UPF / libgtp5gnl gtpv1 빌드 `testgtpv1` / README | UPF / libgtp5gnl gtpv1 build `testgtpv1` / README |
| `problem` | free5gc-stage-3에 보고한 두 이슈가 free5gc 저장소에 완전히 합쳐지지 않았다. README의 git clone 위치가 틀렸다(stage-3 #4). upf의 libgtp5gnl 빌드 실패는 고쳐졌지만, gtpv1을 빌드할 때 testgtpv1이 생성되지 않는 문제를 고친 stage-3 PR #5는 합쳐지지 않았다(stage-3 #3). | 현상: Two issues reported to free5gc-stage-3 were not fully merged into the free5gc repo. The git clone location in README is wrong (stage-3 #4). The upf libgtp5gnl build failure was fixed, but stage-3 PR #5, which fixed testgtpv1 not being generated when building gtpv1, was not merged (stage-3 #3). |
| `cause` | 프로젝트가 free5gc/free5gc 저장소 하나로 옮겨 가면서 stage-3의 PR #5가 넘어오지 않았다. 두 저장소의 git history가 달라 format-patch로 옮길 수도 없었다. | 원인: When the project moved to the single free5gc/free5gc repo, stage-3 PR #5 did not come over. The two repos have different git history, so it could not be moved with format-patch either. |
| `resolution` | README의 git clone 경로를 고쳤다. gtpv1 빌드 때 testgtpv1이 생성되지 않는 문제는 PR #11로 고쳤다. | 조치: Fixed the git clone path in README. testgtpv1 not being generated on gtpv1 build was fixed by PR #11. |

## P10 · DF-OAM-2024-00002

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [webconsole] React 업그레이드 중 UE PDU session static IP 설정 UI가 빠짐 | [webconsole] React 업그레이드 중 UE PDU session static IP 설정 UI 누락 (v3.4.0) |
| `location` | webconsole / 가입자 등록 static IPv4 주소 설정 / v3.4.0 | webconsole > 가입자 등록 > static IPv4 주소 설정 (v3.4.0) |
| `problem` | free5gc 문서는 Dynamic/Static IPv4 address allocation을 지원한다고 적지만, v3.4.0 webconsole에서 UE에 할당할 PDU session static IP를 설정하는 곳을 찾을 수 없다. | free5gc 문서는 Dynamic/Static IPv4 address allocation(동적/정적 할당)을 지원한다고 적고 있지만, v3.4.0 webconsole(가입자 등록 화면)에서는 UE에 할당할 PDU session static IP를 설정하는 곳을 찾을 수 없다. |
| `cause` | webconsole의 React 업그레이드 작업 중 관련 component가 제거됐다. | webconsole의 React 업그레이드 작업 중에 관련 component(static IP 설정 UI)가 제거됐다. |
| `resolution` | 메인테이너가 webconsole PR #85로 UI를 다시 넣는다고 답했다. | 메인테이너가 UI를 다시 넣겠다고 답했다(webconsole PR #85). |

## P11 · DF-PLATFORM-2026-00001

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [CI O-RU pipeline] SR-IOV 설정 스크립트가 ethtool을 찾지 못함 | [CI O-RU pipeline] SR-IOV 설정 스크립트에서 ethtool 찾지 못함 |
| `location` | CI RAN-SA-ORU-CN5G / `setup_sriov.sh` / `dpdk-init` image | CI RAN-SA-ORU-CN5G / `setup_sriov.sh` / `dpdk-init` image |
| `problem` | Jenkins job RAN-SA-ORU-CN5G에서 SR-IOV 설정 스크립트가 `ethtool -G enp1s0f0np0 rx 8160 tx 8160` 단계에서 실패한다. 로그: `/tmp/setup_sriov.sh: 12: ethtool: not found`. 스크립트는 남은 단계를 계속 실행하고 `exit 0`으로 끝난다. | [현상] Jenkins job RAN-SA-ORU-CN5G에서 SR-IOV 설정 스크립트가 `ethtool -G enp1s0f0np0 rx 8160 tx 8160` 단계에서 실패함. 로그: `/tmp/setup_sriov.sh: 12: ethtool: not found`. 스크립트는 남은 단계를 계속 실행하고 `exit 0`으로 종료됨. Jenkins job RAN-SA-ORU-CN5G에서 SR-IOV 설정 스크립트가 `ethtool -G enp1s0f0np0 rx 8160 tx 8160` 단계에서 실패함. |
| `cause` | 스크립트를 실행하는 `dpdk-init` image에 ethtool이 설치되어 있지 않았다. | [원인] 스크립트를 실행하는 `dpdk-init` image에 ethtool이 설치되어있지 않았음. |
| `resolution` | `dpdk-init` image에 ethtool을 설치했다. 이후 job 260에서는 실패가 나오지 않는다. | [조치] `dpdk-init` image에 ethtool 설치. 이후 job 260에서는 실패 나오지 않음. |

## P12 · DF-PLATFORM-2021-00028

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [AGW 빌드] Vagrant AGW에서 `make run` 시 `/lte/gateway/python`이 없어 build_python 실패 | [AGW build] Vagrant AGW `make run` → build_python fail (`/lte/gateway/python` 없음) |
| `location` | AGW Vagrant 개발 환경 / `make run` build_python target / Ubuntu 18.04 | AGW Vagrant dev env / `make run` build_python target / Ubuntu 18.04 |
| `problem` | access gateway를 설정하며 `make run`을 실행하면 build_python target이 실패한다. `make[1]: *** /lte/gateway/python: No such file or directory.  Stop.` | access gateway 설정 중 `$ make run` → build_python target fail. `make[1]: *** /lte/gateway/python: No such file or directory.  Stop.` |
| `cause` | Ansible version 문제다. 같은 오류를 겪은 다른 사용자는 Ansible을 올리고 VM을 다시 provisioning해서 해결했다. | Ansible version 문제. 같은 오류 겪은 다른 사용자: Ansible upgrade + VM re-provisioning으로 해결. |
| `resolution` | Ansible을 업데이트하고 VM을 다시 provisioning하는 방법으로 해결됐다며 닫혔다. | Ansible update → VM re-provisioning으로 해결됐다며 close. |

## P13 · DF-PLATFORM-2022-00002

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [gtp5g] 커널 5.13 이상에서 gtp5g driver 컴파일 실패 | [gtp5g] kernel 5.13+ gtp5g driver build fail |
| `location` | gtp5g kernel module `gtp5g.c` `gtp5g_netdev_ops` / Linux 5.13 이상, Ubuntu 20.04 | gtp5g kernel module `gtp5g.c` `gtp5g_netdev_ops` / Linux 5.13+, Ubuntu 20.04 |
| `problem` | Ubuntu 20.04 최신 업데이트를 포함한 최근 커널에서 gtp driver가 컴파일되지 않는다. | Ubuntu 20.04 최신 업데이트 포함 최근 kernel에서 gtp driver 컴파일 안 됨. |
| `cause` | `gtp5g_netdev_ops`의 `.ndo_get_stats64`가 커널 버전과 관계없이 `ip_tunnel_get_stats64`를 썼다. 보고자의 패치는 커널 5.13 이상에서 이를 `dev_get_tstats64`로 바꾼다. | kernel 버전 의존성 문제 - `gtp5g_netdev_ops`의 `.ndo_get_stats64`가 kernel 버전 무관하게 `ip_tunnel_get_stats64` 사용, 보고자 패치는 5.13+에서 `dev_get_tstats64`로 교체. |
| `resolution` | 보고자가 `LINUX_VERSION_CODE >= KERNEL_VERSION(5,13,0)`이면 `dev_get_tstats64`를 쓰는 패치를 본문에 붙였다. 원문에 반영 기록은 없다. | 보고자 패치(`LINUX_VERSION_CODE >= KERNEL_VERSION(5,13,0)`이면 `dev_get_tstats64`) 본문 첨부, 반영 기록 없음. |

## P14 · DF-CORE-2026-00020

| 필드 | 정본 | 문체 버전 |
|---|---|---|
| `title` | [UDR] 없는 ueId로 amf-subscriptions DELETE 요청 시 nil interface type assertion panic | [UDR] 없는 ueId로 amf-subscriptions DELETE 시 panic, 500 |
| `location` | UDR / Nudr_DR `DELETE /nudr-dr/v2/subscription-data/{ueId}/{servingPlmnId}/ee-subscriptions/{subsId}/amf-subscriptions` / `event_amf_subscription_info_document.go` | UDR / Nudr_DR `DELETE /nudr-dr/v2/subscription-data/{ueId}/{servingPlmnId}/ee-subscriptions/{subsId}/amf-subscriptions` / `event_amf_subscription_info_document.go` |
| `problem` | 새로 시작한 UDR에 존재하지 않는 `ueId`, `subsId`(예: `x`)로 DELETE 요청 한 번을 보내면 UDR이 본문 없이 500 Internal Server Error를 돌려준다. 로그: `panic: interface conversion: interface {} is nil, not *context.UESubsData`. Gin recovery가 process를 살려 두지만 같은 요청으로 반복해서 일으킬 수 있다. | 없는 `ueId`/`subsId`로 DELETE 한 번이면 UDR이 본문 없이 500 반환(`panic: interface conversion: interface {} is nil, not *context.UESubsData`). process는 살아 있으나 반복 유발 가능. |
| `cause` | `RemoveAmfSubscriptionsInfoProcedure()`가 `UESubsCollection.Load(ueId)`에 실패하면 `pd`만 설정하고 실행을 계속해, nil 값을 `*udr_context.UESubsData`로 type assertion했다. | `RemoveAmfSubscriptionsInfoProcedure()`가 `UESubsCollection.Load(ueId)` 실패 후에도 계속 진행해 nil을 `*udr_context.UESubsData`로 type assertion. |
| `resolution` | `USER_NOT_FOUND`와 `SUBSCRIPTION_NOT_FOUND` 뒤에 바로 반환하고, `AmfSubscriptionInfos`를 읽기 전에 `eeSub == nil`을 검사하도록 고쳤다(PR #60). | `USER_NOT_FOUND`·`SUBSCRIPTION_NOT_FOUND` 뒤 즉시 반환, `AmfSubscriptionInfos` 읽기 전 `eeSub == nil` 검사 추가(PR #60). |
