# 기존 6단계 경로와의 접점

읽기 확인: `paper_finalization_20260926/experiment_v3/protocol.py`의 `fact_tuple`와 `apply_gate`는 subject/relation/value/time의 정확한 일치, 전사 후보 공통 지지를 쓴다. `conditional_method_extension_20260927/runtime/policy.py`의 C fallback은 기존 fact_id와 subject/relation/time 유지, 현재 발화의 인용, 새 값이 포함된 문자 그대로의 quote를 확인한다. 이 기계적 원칙은 `tuple_support_adapter.py`에 **독립된 축소 검사**로 옮겼다. 이 검사는 source reader의 의미 판정을 대신하지 않고 DB 실행도 하지 않는다.

기존 runner를 그대로 사용할 수 없는 근거는 구체적이다.

- frozen `RELATIONS`는 `residence` 등 개인경험 관계 10개로 고정돼 `train.semi.departure`를 거부한다. `SLOTS`, JSON schema, witness validation과 SQLite store도 해당 enum에 묶여 있다.
- `turn_id`와 `source_turns`가 `t1/t2`뿐이어서 MultiWOZ의 앞선 모든 턴과 정확한 근거 턴을 보존하지 못한다. 여기서는 `dialogue_id#turnN`을 사용한다.
- prompt는 여러 입력을 같은 발화의 **전사 대안**이라고 설명한다. 원문 c1 한 개에 그대로 적용하면 검사의 의미가 달라진다.
- `memory_permission=allowed`라는 source 근거가 없다. 별도 task contract의 sandbox 상태편집 가정을 원문 동의로 위장하면 안 된다.
- 기존 reply/receipt는 개인기억 저장과 한국어 응답을 전제로 한다. MultiWOZ의 예약 작업 완료를 주장해서는 안 된다.

따라서 이 파일들은 기존 동결 프로토콜·enum·평가점수·실행 DB를 수정하지 않는다. 여섯 단계 물리 상한을 유지한 새 전이 runner를 본체가 만들 경우, 공개 패킷만 모델에 주고 비공개 reference를 완전 분리하며 source-native 관계와 정확한 턴 ID를 지원해야 한다. 원문 c1만 있으므로 전사 간 불일치 조건은 없고 그 효과는 평가 불가하다. 하지만 한 후보의 추출이 사실을 빠뜨리거나 최종 제안과 충돌하면 B의 HOLD와 C/E의 추가 조건은 여전히 서로 다른 결과를 낼 수 있다. 같은 raw 제안에서 그 차이를 진단하되 보장된 개선으로 말하지 않는다. 정정 vs 계획변경/질문을 구별하는 작업 상태 의미 진단으로만 보고한다.
