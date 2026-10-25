---
name: code-style
description: "언어 공통의 이름, 오류, 주석, 테스트 규칙으로 코드를 쓰거나 검토할 때 쓴다."
---

# 코드 스타일

원칙 스킬(just의 `principle-*`)에 없는 코드 공통 세부를 정하는 정본이다. 언어별 스킬은 [언어별 스킬](references/language.md)에 적은 항목만 정하고, 그 밖에서 이 스킬과 부딪히면 이 스킬을 따른다.

## 조건별 읽기

- 판단 기준(최소 변경, 검증, 테스트 방식, 경계, 동시성, 근본 원인)의 정본은 원칙 스킬이다. 검증과 증거 재사용은 **principle-prove-it-works** 스킬이 맡는다. 이 스킬은 그 밖의 수치, 이름, 순서, 오류 형식, 데이터, 운영 세부를 정한다.
- 편집 전 훅이 편집하는 파일의 종류와 내용 조건에 맞는 원칙 파일, 아래 표의 절, 언어별 스킬을 함께 전달한다. 대응표의 정본은 mode `scripts/rules/rule-map.json`이다.
- 직접 조회할 때는 `python3 <mode 스킬 폴더>/scripts/rules/read_rules.py <파일...>`로 편집할 파일에 맞는 규칙을 고르거나 `--ids <ID...>`로 ID를 지정한다. Python 3.9 이상과 표준 라이브러리로 돈다. 오류가 나면 종료 코드 2로 끝나고 일부만 출력하지 않는다.
- 작은 수정이라도 해당하는 오류, 검사, 예외 규칙을 빼지 않는다. 새 함수에는 이름, 수치, 선언, 공개 범위 규칙과 실제 변경 조건을 모두 적용한다.

| ID | 적용 조건 | 정본 |
|---|---|---|
| CS-CORE | 모든 코드 작성과 검토 | 이 문서의 머리와 원칙 절 |
| CS-FAILURE | 실패할 수 있는 입력, 외부 경계, 오류 변경(결함과 장애 복구 포함) | 이 문서의 실패 처리 절 |
| CS-LANGUAGE | 언어별 스킬을 만들거나 고칠 때 | [언어별 스킬](references/language.md) |
| CS-SIZE | 함수, 타입, 분기, 매개변수, 파일 크기 변경 | [수치 기준](references/structure.md#수치-기준) |
| CS-NAME | 이름 추가와 변경 | [이름](references/structure.md#이름) |
| CS-CONDITION | 조건식과 분기 변경 | [조건식](references/structure.md#조건식) |
| CS-ORDER | 선언 추가와 이동 | [선언 순서](references/structure.md#선언-순서) |
| CS-VISIBILITY | 공개 범위, 필드, 주석 추가와 변경 | [공개 범위와 주석](references/structure.md#공개-범위와-주석) |
| CS-ERROR | 실패할 수 있는 입력, 외부 경계, 오류, 로그 변경 | [오류와 로그](references/errors.md) |
| CS-TEST | 테스트 선택, 추가, 변경(훅은 테스트 경로의 파일에 넘긴다) | [테스트](references/testing.md) |
| CS-DATA | 데이터, 공유 상태, 비동기 변경 | [데이터와 동시성](references/data-and-concurrency.md) |
| CS-RESOURCES | 성능, 자원, 캐시, 큐 변경 | [자원과 성능](references/resources.md) |
| CS-INTERFACES | 화면과 API 변경(훅은 CSS, JSX, TSX 파일에만 넘기므로 API 변경이면 직접 읽는다) | [화면과 API](references/interfaces.md) |
| CS-OPERATIONS | 신뢰 경계, 외부 입력, 권한, 의존성, 배포, 복구 변경 | [보안과 운영](references/operations.md) |

## 원칙

- 대소문자 표기와 포맷은 언어의 공식 관례와 포매터를 따른다. 예시 이름의 snake_case와 PascalCase는 설명용이다.
- 클래스가 없는 언어에서는 클래스를 struct, trait, module로, 상속을 조합과 인터페이스로 바꿔 적용한다.
- 리팩터링은 기능을 추가하기 직전, 코드를 이해하는 중, 작업하다 문제를 발견했을 때, 코드 리뷰 중에 한다.
- 앞으로 고칠 일이 없는 코드는 리팩터링하지 않는다. 재작성, 이전, 재검증의 총비용이 리팩터링 비용보다 작다는 비교 근거가 있는 코드도 리팩터링하지 않는다.
- 외부 사용자 때문에 공개 API를 호출하는 쪽까지 한 번에 바꿀 수 없으면 다음 순서로 바꾼다.
  1. 새 함수를 추가한다.
  2. 기존 함수가 새 함수를 호출하게 하고 deprecated로 표시한다.
  3. 호출하는 쪽을 새 함수로 옮긴다.
  4. 기존 함수를 지운다.
- 성능은 프로파일링으로 확인한 병목만 최적화한다.
- 이름은 역할이 드러나게 짓는다. 쓰는 범위가 넓을수록 구체적으로 짓고, 짧은 루프 변수처럼 범위가 좁으면 짧은 이름을 허용한다. 세부는 [이름](references/structure.md#이름)을 따른다.
- 설명이 필요한 코드 덩어리는 함수로 추출한다. 크기 수치는 목표가 아니라 경고선이다. 수치 안에 든다는 이유로 품질을 판정하지 않는다. 수치는 [수치 기준](references/structure.md#수치-기준)에 있다.
- 주석은 CS-VISIBILITY의 주석 조건과 형식을 따른다.

## 실패 처리

1. 지금의 영향과 진행 중인 작업을 확인한다. 허용된 범위에서 피해를 막고, 원본, 아직 보내지 않은 것, 근거를 보존한다.
2. 원인 찾기와 수정은 **principle-fix-root-causes** 스킬과 **principle-attack-the-premise** 스킬을 따른다.
3. 원래 실패, 인접 경계, 기존 정상 동작, 실패 뒤 다음 요청, 복구 데이터를 다시 검사한다.

- 효과가 불명확한 외부 작업을 다시 실행하지 않는다. 무관한 변경을 한꺼번에 되돌리지 않는다.
- 시간 초과만으로 교착이나 효과 실패를 확정하지 않는다. 긴급 복구와 장기 개선을 나눈다.

## 구분

- 결과가 달라지는 미확정 설계 선택은 **repo-docs-design** 스킬이 맡는다.
- 리팩터링 기법 고르기는 [code-refactoring](../code-refactoring/SKILL.md)이 맡는다.
- 파일과 모듈 이름은 [folder-naming](../folder-naming/SKILL.md)이 맡는다.
- UI의 시각과 모션 변경은 **design-tokens** 스킬이 맡는다.
- CSS 변경은 [code-style-css](../code-style-css/SKILL.md)가 맡는다.
- 언어별 표기, 문법, 도구 설정은 각 언어별 스킬이 맡는다.
