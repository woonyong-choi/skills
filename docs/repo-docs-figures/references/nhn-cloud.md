# NHN Cloud 세트

NHN Cloud 구성도에만 해당하는 근거와 값이다. 원칙은 [클라우드 구성도 규칙](cloud-architecture.md)을 따르고, 이 문서는 그 원칙을 NHN 자산에 적용한 결과만 둔다.

## 근거

- 아이콘 벡터와 사용 안내는 [NHN 공식 저장소](https://github.com/nhn-cloud/Icons)다. 저장소가 안내하는 NHN Cloud Architecture Icons 가이드(v2.2, 2026-04-08판)의 Guidelines·Icons 장을 기준으로 삼는다.
- 가이드 판과 벡터 저장소의 commit은 따로 기록한다. 두 자료를 같은 배포본이라고 추정하지 않는다.
- [공식 README](https://github.com/nhn-cloud/Icons#readme)는 NHN Cloud 아키텍처 다이어그램 작성 용도를 안내하고 일반 오픈소스 라이선스를 밝히지 않는다. 비상업용이라는 사실을 포괄적 상업 이용이나 원본 재배포 허용으로 바꾸지 않는다.

## 종류

- 가이드는 아이콘을 서비스·리소스·일반 아이콘으로 나누고, 그룹에는 박스 형태 아이콘과 레이블을 함께 쓴다. 공통 규칙의 그룹 아이콘이 박스 형태 아이콘이다.
- 그룹은 레이블을 반드시 명시한다. 아이콘 위치는 바꿀 수 있다.
- 세트 이름과 아이콘 이름은 설치한 카탈로그에서 확인한다.

## 영역 외곽선

가이드의 그룹 예시에 쓰인 선 모양이다.

| 영역 | 외곽선 |
|---|---|
| Region | 점선 |
| Availability Zone | 점선 |
| Auto Scaling Group | 점선 |
| NHN Cloud, Organization, Project, On-Premise/IDC/Co-lo Zone | 실선 |
| VPC, Subnet, Security Groups | 실선 |
| Server Contents, Instance Contents, NHN Cloud Member | 실선 |
| Generic Group | 실선과 점선 예시가 모두 있으므로 실제 의미에 맞춰 고른다 |

- Availability Zone은 박스 형태 아이콘 없이 이름과 점선 경계로 표시한다.

## 경로

- 가이드의 화살표는 서비스의 흐름을 나타낸다. 실선은 주 경로, 점선은 보조 경로이고, 성공 상태를 따로 표시한다.
