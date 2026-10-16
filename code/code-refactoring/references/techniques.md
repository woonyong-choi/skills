# 기법 목록

『리팩터링 2판』의 기법을 언제 쓰는지 정리한다. 괄호 안은 책의 영문 이름이다. `↔`로 이은 두 기법은 서로 반대 방향이고, 상황에 맞는 쪽을 고른다. 쓰는 때 칸도 같은 순서로 `↔` 앞뒤에 적는다.

## 기본

| 기법 | 쓰는 때 |
|---|---|
| 함수 추출 ↔ 함수 인라인 (Extract / Inline Function) | 코드 덩어리에 의도를 드러내는 이름을 붙일 때 ↔ 함수 본문이 이름만큼 명확하거나 호출 단계가 과할 때 |
| 변수 추출 ↔ 변수 인라인 (Extract / Inline Variable) | 복잡한 식의 일부에 이름을 붙일 때 ↔ 변수 이름이 식보다 나을 게 없을 때 |
| 함수 시그니처 변경 (Change Function Declaration) | 함수 이름이나 매개변수를 바꿀 때. 호출하는 곳이 많으면 새 함수를 추가하고 조금씩 옮긴다. |
| 변수 캡슐화 (Encapsulate Variable) | 넓은 범위에서 쓰는 데이터를 getter, setter 같은 함수로만 다루게 할 때 |
| 변수 이름 변경 (Rename Variable) | 변수 이름이 역할을 드러내지 못할 때 |
| 매개변수 묶음 타입 도입 (Introduce Parameter Object) | 늘 함께 넘기는 매개변수들을 타입 하나로 묶을 때 |
| 관련 함수를 타입으로 묶기 (Combine Functions into Class) | 같은 데이터를 다루는 함수들을 그 데이터의 메서드로 옮길 때 |
| 파생값 계산을 변환 함수로 묶기 (Combine Functions into Transform) | 원본 데이터에서 파생값을 계산하는 로직이 흩어졌을 때. 원본은 바꾸지 않고 새 결과를 돌려준다. |
| 처리 단계 분리 (Split Phase) | 두 가지 일을 섞어 하는 함수를 앞 단계 결과를 넘기는 두 단계로 나눌 때. 모듈을 나누는 기준으로는 쓰지 않는다([단계](../SKILL.md#단계)). |

## 캡슐화

| 기법 | 쓰는 때 |
|---|---|
| 레코드 캡슐화 (Encapsulate Record) | 수정할 수 있는 레코드나 맵을 접근 메서드가 있는 타입으로 바꿀 때 |
| 컬렉션 캡슐화 (Encapsulate Collection) | 컬렉션을 그대로 노출하지 않고 추가, 삭제 메서드를 줄 때. 조회는 복사본을 돌려준다. |
| 기본 타입을 값 타입으로 (Replace Primitive with Object) | 기본 타입 값에 검증이나 동작이 붙기 시작할 때 |
| 임시 변수를 함수로 (Replace Temp with Query) | 계산 결과를 담아 두는 임시 변수를 계산 함수로 바꿀 때 |
| 타입 분리 ↔ 타입 합치기 (Extract / Inline Class) | 클래스나 struct의 책임이 둘 이상일 때 ↔ 클래스나 struct가 하는 일이 거의 없을 때 |
| 위임 숨기기 ↔ 위임 래퍼 제거 (Hide Delegate / Remove Middle Man) | 호출하는 쪽이 내부 객체를 알 필요가 없을 때 ↔ 넘기기만 하는 메서드가 너무 많을 때 |
| 알고리즘 교체 (Substitute Algorithm) | 같은 입출력 계약을 지키면서 분기와 중복을 줄이는 알고리즘으로 바꿀 때. 동작과 성능 영향을 확인한다. |

## 기능 이동

| 기법 | 쓰는 때 |
|---|---|
| 함수 이동 (Move Function) | 함수가 다른 모듈의 데이터나 함수를 더 많이 쓸 때 |
| 필드 이동 (Move Field) | 필드가 다른 타입과 함께 바뀌거나 함께 전달될 때 |
| 반복 코드를 함수 안으로 ↔ 호출하는 쪽으로 (Move Statements into Function / to Callers) | 호출할 때마다 같은 코드가 앞뒤에 붙을 때 ↔ 일부 호출하는 쪽만 다르게 동작해야 할 때 |
| 중복 코드를 기존 함수 호출로 (Replace Inline Code with Function Call) | 같은 일을 하는 함수가 이미 있을 때 |
| 코드 순서 옮기기 (Slide Statements) | 관련 코드를 한곳에 모으거나 변수 선언을 쓰는 곳 가까이로 옮길 때 |
| 반복문 분리 (Split Loop) | 반복문 하나가 두 가지 일을 할 때. 성능 영향은 측정한 뒤 판단한다. |
| 반복문을 map·filter로 (Replace Loop with Pipeline) | 변환과 선택 조건을 각각 표현할 수 있고 외부 상태 변경이나 break, continue에 기대지 않을 때. 동작과 성능 영향을 확인한다. |
| 안 쓰는 코드 삭제 (Remove Dead Code) | 호출되지 않는 코드가 있을 때. 지운 동작이 다시 필요하면 git 기록에서 되살린다. |

## 데이터

| 기법 | 쓰는 때 |
|---|---|
| 변수 분리 (Split Variable) | 한 변수에 뜻이 다른 값을 여러 번 대입할 때 |
| 필드 이름 변경 (Rename Field) | 필드 이름이 역할을 드러내지 못할 때 |
| 계산 가능한 필드를 함수로 (Replace Derived Variable with Query) | 다른 값으로 계산할 수 있는 값을 따로 저장해 어긋날 위험이 있을 때 |
| 참조를 값으로 ↔ 값을 참조로 (Change Reference to Value / Value to Reference) | 불변 값으로 다뤄도 될 때 ↔ 같은 대상을 여러 곳이 공유하고 함께 갱신해야 할 때 |

## 조건문

| 기법 | 쓰는 때 |
|---|---|
| 조건문을 함수로 분리 (Decompose Conditional) | 복잡한 조건식과 각 분기 내용을 이름 있는 함수로 뺄 때 |
| 조건식 합치기 (Consolidate Conditional Expression) | 결과가 같은 여러 조건을 하나로 합칠 때 |
| early return (Replace Nested Conditional with Guard Clauses) | 예외 상황을 먼저 반환하고 정상 흐름의 중첩을 없앨 때 |
| 분기를 다형성으로 (Replace Conditional with Polymorphism) | 타입별 분기가 되풀이되거나 기본 동작에 변형이 붙을 때 |
| 특수 케이스 객체 (Introduce Special Case) | null이나 "알 수 없음" 같은 특수값 검사가 여러 곳에 되풀이될 때 |
| assert 추가 (Introduce Assertion) | 늘 참이어야 하는 가정을 언어별 단언으로 드러낼 때. 단언 실패는 프로그래머의 실수다. |

## API

| 기법 | 쓰는 때 |
|---|---|
| 조회와 변경 분리 (Separate Query from Modifier) | 값을 돌려주는 함수가 상태도 바꿀 때 |
| 함수 매개변수화 (Parameterize Function) | 값만 다르고 로직이 같은 함수들이 있을 때 |
| bool 플래그 인자 제거 (Remove Flag Argument) | 인자 값으로 동작을 고르는 함수를 동작별 함수로 나눌 때 |
| 객체 통째로 전달 (Preserve Whole Object) | 한 객체에서 값 여러 개를 꺼내 넘길 때 |
| 매개변수를 내부 조회로 ↔ 내부 조회를 매개변수로 (Replace Parameter with Query / Query with Parameter) | 함수가 직접 구할 수 있는 값을 받을 때 ↔ 함수가 전역이나 외부 상태에 기대 같은 입력에 다른 결과를 낼 때 |
| setter 제거 (Remove Setting Method) | 생성 뒤 바뀌면 안 되는 필드가 있을 때 |
| 생성자를 팩토리 함수로 (Replace Constructor with Factory Function) | 생성자의 이름이나 반환 타입 제약이 불편할 때 |
| 함수를 명령 객체로 ↔ 명령을 함수로 (Replace Function with Command / Command with Function) | 복잡한 함수에 단계 분리, 취소, 상태가 필요할 때 ↔ 명령 객체가 하는 일이 단순할 때 |

## 상속

| 기법 | 쓰는 때 |
|---|---|
| 메서드 올리기 ↔ 메서드 내리기 (Pull Up / Push Down Method) | 하위 클래스들이 같은 메서드를 가질 때 ↔ 일부 하위 클래스만 쓰는 메서드가 있을 때 |
| 필드 올리기 ↔ 필드 내리기 (Pull Up / Push Down Field) | 하위 클래스들이 같은 필드를 가질 때 ↔ 일부 하위 클래스만 쓰는 필드가 있을 때 |
| 생성자 공통부 올리기 (Pull Up Constructor Body) | 하위 클래스 생성자들에 공통 코드가 있을 때 |
| 타입 코드를 하위 타입으로 ↔ 하위 타입 제거 (Replace Type Code with Subclasses / Remove Subclass) | 타입 코드 값에 따라 동작이 달라질 때 ↔ 하위 타입이 하는 일이 거의 없을 때 |
| 부모 타입 추출 (Extract Superclass) | 비슷한 일을 하는 클래스들에 공통 부분이 있을 때 |
| 계층 합치기 (Collapse Hierarchy) | 부모와 자식 클래스가 거의 같을 때 |
| 하위 클래스 상속을 위임으로 (Replace Subclass with Delegate) | 변형 기준이 둘 이상 필요하거나 부모와 자식의 결합이 강할 때 |
| 부모 클래스 상속을 위임으로 (Replace Superclass with Delegate) | 부모 기능의 일부만 필요하거나 부모 인터페이스가 맞지 않을 때 |
