# 설계 검토 분석 스크립트

`docs/design/`의 수치를 낸 스크립트와 출력이다. 레포 루트에서 `python3 -I analysis/<경로>.py`로 돈다.

| 폴더 | 문서 | 내용 |
|---|---|---|
| `round1/profile/` | 01 [profile] | 엔티티 추출 커버리지, 관계 실측 |
| `round1/raw/` | 01 [raw] | 원본 필드, 버려진 정보, 총무성 사례집 |
| `round1/verify/`, `round1/skeptic/` | 01 [verify], [skeptic] | 반박 단계의 재측정 |
| `round1/*.py`, `round1/design/` | 01 [needs], [ontology] | 버전·location 분할·어휘 커버리지. 입력 파일을 인자로 받는다 |
| `round2/multimodal/` | 02 [attachments] | 첨부·로그·이미지 비율 |
| `round2/clarify-slots/` | 02 [clarify-data] | slot을 지운 질의로 본 되질문 효과 |
| `round2/design-fixed-pipeline/`, `round2/planner-design/`, `round2/refuter-data/` | 02 | 설계안과 반박의 측정 |
| `round2/framework-facts/` | 02 [frameworks] | 프레임워크 기능 확인 |

일부 스크립트는 `raw/`나 `work/`를 읽어서 레포만으로는 돌지 않는다. 1MB가 넘는 중간 산출물과 외부 표준 문서 사본은 넣지 않았다. 스크립트를 다시 돌리면 생긴다.
