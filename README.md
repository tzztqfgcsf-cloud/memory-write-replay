# Sorieum Paper Supplements

소리이음 논문의 두 보완 작업을 정리한 연구 보고서입니다. 정리 기준일: 2026-10-04.

## 보고서

- [PDF로 읽기](Sorieum_Supplementary_Report_KO.pdf)
- [편집 가능한 Word 파일](Sorieum_Supplementary_Report_KO.docx)

## 수록 내용

1. **추출기 및 검증기 보완** — Gemini 2.5 Flash 핵심 5사례의 corrected-extractor 비교, 다른 모델에서의 적용 확인, 저장된 Review 제안에 대한 LLM 검증기 비교와 호출 비용.
2. **외부 데이터 검증** — DSTC2 실제 ASR 후보를 이용한 승인 규칙 비교, 실제 성공·실패 사례, CareCall-mem 라벨 확보 상태.

## 핵심 결과

- 선택한 5사례에서 원지침 대비 수정 지침의 정정 성공은 **1/5 → 5/5**, AGREE 보류는 **4/5 → 0/5**였다. 사례별 1회 추출을 사용한 사후 메커니즘 진단이다.
- DSTC2의 Gemini 3.1 Pro 완결 표본은 **48개 대화·41명 화자·1회 반복**이다. ALLOW 대비 AGREE/WITNESS는 잘못된 새 기록 3건을 막았지만 올바른 변경 17건도 막았다. 전체 목표 일치는 **33/48 → 18/48**이었다.
- 기존 5사례의 모든 읽기에서 인정한 정정이 사실 목록에서 빠지는 패턴은 이 외부 표본에서 재현되지 않았다.
- CareCall-mem은 필요한 원본 사람 연산 라벨 파일이 확보되지 않아 아직 평가하지 않았다.

두 실험은 비교 단위가 다르므로 하나의 평균 개선율로 합산하지 않는다. 세부 지표, 분모, 부분 표본, 불확실성 및 원고 반영 방향은 보고서에 기재했다.

## 공개 범위

이 저장소는 보완 결과 보고서를 공유한다. 전체 실험 코드·원자료·모델 응답을 포함한 재현 패키지는 아니다. 저장소 공개는 논문의 게재 또는 심사 완료를 의미하지 않는다.

## 외부 데이터 출처

- CareCall-memory: https://github.com/naver-ai/carecall-memory
- CareCall 논문: https://aclanthology.org/2022.findings-emnlp.276/
- DSTC 자료: https://github.com/matthen/dstc
- DSTC2 논문: https://aclanthology.org/W14-4337/

외부 데이터 자체는 이 저장소에서 재배포하지 않는다.
