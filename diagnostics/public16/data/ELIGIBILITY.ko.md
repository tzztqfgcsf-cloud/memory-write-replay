# 원문16 사례의 잠정 적격성

이 표는 작성자 AI의 source-reader 분류이며 사람 gold/데이터셋 정정 라벨이 아니다. 대상 뒤 system 발화와 후속 상태값은 `provisional_reference.json`에만 있다.

|사례|잠정 범주|개발 해석|
|---|---|---|
|`MW24-MUL1790-t2`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-PMUL1919-t4`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-PMUL1033-t6`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-PMUL0945-t4`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-SNG01176-t6`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-MUL1930-t8`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-PMUL3804-t4`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-MUL1523-t4`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-MUL1664-t10`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-PMUL4646-t16`|same_task_self_repair|correct_focal_sandbox_state_if_supported|
|`MW24-PMUL1635-t14`|changed_plan|do_not_treat_prior_state_as_initially_false|
|`MW24-SNG1006-t6`|fallback_after_booking_failure|do_not_treat_prior_state_as_initially_false|
|`MW24-PMUL4852-t4`|changed_preference|do_not_treat_prior_state_as_initially_false|
|`MW24-MUL0329-t8`|assistant_misunderstanding|avoid_unsupported_correction_or_hold_for_review|
|`MW24-SNG0984-t6`|verification_question|avoid_unsupported_correction_or_hold_for_review|
|`MW24-PMUL1690-t4`|source_annotation_conflict|avoid_unsupported_correction_or_hold_for_review|

16사례는 별개 대화다. 공개 패킷에는 이 범주와 뒤 상태를 넣지 않았다. `MW24-PMUL1690-t4`는 주석 충돌로 데이터셋값 점수에서 제외/미결이다. 나머지도 독립 사람 판정 전에는 의미 gold가 아니다.
