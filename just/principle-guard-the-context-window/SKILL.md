---
name: principle-guard-the-context-window
description: "컨텍스트가 차오를 때(큰 출력, 긴 파일, 반복해서 읽기, 병렬 분배 계획) 적용한다. 대량 작업은 서브에이전트로 보내고, 메인 흐름에는 원본 데이터가 아니라 요약을 둔다."
disable-model-invocation: true
user-invocable: false
---

# 컨텍스트 창 지키기(Guard the Context Window)

**이유:** 컨텍스트가 넘치면 추론 품질이 떨어지고, 압축으로 인한 왜곡이 생기고, 진행이 멈춘다.

**방법:**
- **단계 크기를 정하고 범위를 제한한다.** 단계마다 파일 수를 제한하고, 턴 예산을 정하고, 수단 자체가 드는 비용도 계산에 넣는다.
