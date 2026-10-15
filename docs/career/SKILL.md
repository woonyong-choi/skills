---
name: career
description: "채용 공고(JD)에 맞춘 한국어 개발자 이력서·포트폴리오를 경력 원본에서 만들거나 고칠 때 사용. 자기소개서만 쓰는 작업 제외."
---

# Career

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 범위: 지원 폴더, JD 분석, 경력 원본 대조, 이력서·포트폴리오 작성·검증, 교정 기록
- 필요할 때만 읽기: 포트폴리오 그림 원본 작성 → repo-docs-figures `references/syntax.md` 필수 확인

## 입력

- 필수: 새 JD(URL, 본문, 파일)와 경력 원본(`<Vault>/career/master.md`, `cases/*.md`). 형식·사실 줄 요건·없을 때 처리: [경력 원본](references/source.md) 필수 확인. 비공개 원본 주소의 스킬 내 기재 금지
- 원본 전체 읽기 필수. 짧은 이력서·키워드 목록·요약으로 대체 금지. 미완성 원본은 있는 내용만 사용하고 빈 곳 보고
- 기본값: 이력서와 포트폴리오 둘 다, 한국어, 고정 양식(`assets/typst/`)

## 지원 폴더

Vault 미등록이면 쓰기 전 사용자에게 Vault 절대 경로 요청(repo-docs `references/project-context.md` Vault 흐름). 등록 뒤 `<Vault>/career/`가 없으면 생성

```text
<Vault>/career/
  master.md
  cases/{사례}.md
  cases/figures/{사례}-{그림}.thinkflow
  {마감일}-{회사명}-{직군명}/
    jd.md
    전략.md
    career.typ
    이력서.typ
    이력서.pdf
    포트폴리오.typ
    포트폴리오.pdf
    figures/{사례}-{그림}.thinkflow
    figures/{사례}-{그림}.svg
    figures/{사례}-{그림}.png
```

- `{마감일}`: JD 마감일 `YYYY-MM-DD`, 상시·미표기면 `상시`. `{회사명}`·`{직군명}`: JD 표기 그대로, 공백은 `-`, `/` 삭제. 예 `2026-11-30-토스-백엔드-개발자`
- 같은 공고 재작업: 기존 폴더 수정. 다른 공고: 새 폴더
- `master.md`·`cases/`: 사용자 요청 없이 수정 금지
- `전략.md` 절: `# SPEC`, `# PLAN`, `# IMPLEMENT`, `# VERIFY`. 점수·선택 JSON·근거 순위표 금지

## 교정

사용자가 사실·선호·작업 방식을 교정하면 [교정 기록](references/corrections.md) 필수 확인. 이번 작업에만 즉시 반영, 이전 지원 폴더 재작업 금지

## 사실 경계

- JD는 강조만 결정, 지원자 사실 생성 금지
- 신원·시기·회사·프로젝트 경계·담당 범위·수치 조건·공개 범위·현재 상태 보존
- 조사·제안·구현·빌드·배포·운영 관찰·기기·E2E 검증·지속 성과 구분. 채택 안 된 제안은 반응과 결과를 사실대로
- 팀 성과는 본인 기여가 분명할 때만. 진행 중은 진행 중, 없는 요구는 공백
- 수치는 방법·범위를 알 때만. 근거 보강 제안은 `전략.md` 별도 절, 완료 경험처럼 쓰기 금지
- 공백·참고 등 메모는 `jd.md`·`전략.md`에만. 제출 문서에는 근거·범위·상태·결과만

## 흐름

확인 질문 없이 1~4 연속 실행. 출처 충돌, 핵심 주장의 담당·증명 범위 불명, 동등한 포지셔닝 둘, 구조를 바꾸는 시각 요청일 때만 질문

1. SPEC: [JD 분석](references/jd.md) 필수 확인 → JD 원문 확보·신원 확정 → `jd.md` 작성 → 경력 원본 전체 읽기. `전략.md` SPEC에 출처·캡처 시각, 채용 이유, 명시·추정 요구, 중심 포지셔닝 2~3개, 과장 금지 사실, 공백 기록. 사례 선택·순서 결정 금지
2. PLAN: SPEC과 원본 전체를 한 번에 대조. 이력서 선두 성과, 포트폴리오 사례, 줄이기·빼기·합치기, 순서와 쪽 흐름, 근거 보강 제안 결정과 짧은 이유 기록. 수치 점수·고정 사례 수 금지
   - 문제·담당·기술 메커니즘·검증 근거 중 하나라도 다르면 사례 분리
   - 새 독립 사례: 다른 메커니즘, JD 적합, 문제·행동·검증의 독립 근거 세 조건 모두 충족 시만
3. IMPLEMENT: [작성 규칙](references/writing.md) 필수 확인 → 양식 복사 → 작성 → 그림 생성 → 원본 재검토로 보강
4. VERIFY: [검증](references/validation.md) 필수 확인 → 실행 결과를 `전략.md` VERIFY에 기록

## 고정 양식

- `assets/typst/career.typ`를 지원 폴더에 그대로 복사, 수정 금지. 색·글꼴·크기·간격·helper 변경 금지, 검증에서 원본과 SHA-256 일치 확인
- `resume.typ`→`이력서.typ`, `portfolio.typ`→`포트폴리오.typ`로 복사 후 `{}` 자리와 절·항목·사례 반복 수만 변경. 새 helper·직접 스타일 금지
- 인쇄 문서 양식이라 design-tokens 대상 아님

## 그림

- 포트폴리오 아키텍처·흐름 그림: ThinkFlow 정지 그림만. 원본 `figures/{사례}-{그림}.thinkflow`, 가로 배치 기본
- 생성: `python3 <이 스킬 폴더>/scripts/figures.py <지원 폴더>/figures --thinkflow <ThinkFlow 경로>`. Python 3.9+·Node.js·ThinkFlow 체크아웃·playwright-core Chrome 필요(`CHROME_PATH` 선택). 원본마다 SVG와 그림 영역만 찍은 2배 PNG, 실패 종료 1
- 삽입: `#diagram("figures/{사례}-{그림}.png", [{결론 한 문장}])`. Typst가 SVG CSS 변수를 그리지 못해 PNG 사용, SVG 직접 삽입 금지
- 실제 관계를 보여 줄 때만. 장식 그림 금지
