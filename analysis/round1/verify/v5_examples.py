import sys
sys.argv=[sys.argv[0]]
exec(open("analysis/round1/verify/v4_bm25_vs_graph.py").read().split("pairs=json.load")[0])
Q=[("eNB Reset 뒤 MME가 S1 context has already been removed 찍고 Authentication Request를 못 보낸다. 원인과 2.4.x 패치가 있나?",["DF-CORE-2023-01928","DF-CORE-2023-01752","DF-CORE-2023-01749"]),
("EKS kernel 4.14에서 MME만 SCTP_PEER_ADDR_PARAMS setsockopt Invalid argument로 뜨지 않는다",["DF-CORE-2020-00530","DF-CORE-2020-00252"]),
("cluster_alloc: Assertion buffer failed는 어느 NF에서 나든 원인 후보가 무엇인가",["DF-CORE-2019-00125","DF-CORE-2020-00260"]),
("v2.8.0 SGW-C의 ogs_assert(bearer)가 v2.7.6에서 고친 것과 같은 문제인가",["DF-CORE-2025-02441","DF-CORE-2025-02442","DF-CORE-2026-02455","DF-CORE-2026-02884","DF-CORE-2026-02926"]),
("bounded_object_pool UBSAN shift를 고친 MR에 같이 들어간 수정은",["DF-RAN-DU-2026-01076","DF-RAN-DU-2026-01073"]),
("gNB commit 56a771d 빌드에서 srsUE가 붙지 않는 사례를 원인별로",["DF-RAN-DU-2023-00395","DF-RAN-DU-2023-00396","DF-RAN-DU-2023-00397","DF-RAN-CU-2023-00147","DF-UE-2023-00251","DF-RAN-DU-2023-00436"]),
("free5gc NEF에서 inbound 인증이 빠진 API 전부와 그것을 고친 PR",["DF-CORE-2026-02559","DF-CORE-2026-02560","DF-CORE-2026-02561","DF-CORE-2026-02562","DF-CORE-2026-02563"])]
for q,ans in Q:
    top=search(tok(q))
    print(q[:50]); print("   ", {a:(top.index(a)+1 if a in top else ">51", C[a]["cause_basis"]) for a in ans})
