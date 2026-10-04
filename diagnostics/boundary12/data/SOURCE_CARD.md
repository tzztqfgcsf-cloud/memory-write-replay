# 정정 의미 경계 개발 사례 — source card

- 출처: AI가 2026-09-27에 직접 작성한 한국어 대화 사례 12개(6쌍). 이전 pilot 이후 의도적으로 만든 개발용 경계 사례이며 자연 표본이나 확증 평가 자료가 아니다. 사람 발화·사람 정답으로 취급하지 않는다.
- 작성 범위: 공개 입력 `public.json`과 분리된 작성자 기대 상태 `reference.json`. 기대 상태의 `provenance`는 `AI_AUTHORED_NOT_HUMAN_GOLD`다. 작성 과정에서 모델 출력, 코드, 이전 correction specificity 자료 또는 점수를 보지 않았다.
- 구성: 각 쌍은 같은 `t1` 설명과 같은 단일 기존 DB 사실 `f1`을 공유한다. `t2`의 두 전사 대안은 한 화자의 동일 발화를 옮긴 가능한 표기다. W007은 부정어 탈락 여부에 따라 두 전사가 의미상 충돌할 수 있게 작성했다. 쌍마다 현재 화자 사실 `f1`의 정정이 지지되는 사례 한 개와 지지되지 않는 사례 한 개를 넣었다. 여섯 경계는 자기/타인, 현재/과거, 긍정/부정, 실제/가정, 자기주장/인용, 확정/철회된 확신이다.
- 판정 범위: `memory_permission`은 모두 `allowed`다. 가능하다고 가정한 DB 변경은 기존 `f1`의 `value` 갱신 하나뿐이다. 새 사실·다른 사람의 사실·과거 사실·가정·인용을 추가 저장하는 것은 이 자료의 기대 상태에 포함하지 않는다. 지지되지 않는 사례에서 기대 `f1` 값은 기존 값 그대로다.
- 순서: W001–W012는 여섯 쌍이 섞이도록 고정한 식별자다. 공개 ID, 쌍, family 자체에 지지 여부를 나타내는 표지를 넣지 않았다. 정답과 근거는 `reference.json`에만 둔다.
- 해석 한계: 이 자료의 작성자 의미 판단은 정답 기준의 독립 검증이 아니다. 이 자료에서의 성공은 의도적으로 만든 경계 사례에 대한 개발 신호로만 읽으며, 실제 시니어 음성 인식이나 기억 효용으로 일반화하지 않는다.

Integration note before any model call: one common explicit single-current-record scope instruction was appended to every history. This aligns whole-state scoring with an observable task instruction; no labels or case-specific hints were added. Source and reference finalized before freeze.
