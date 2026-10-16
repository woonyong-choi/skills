---
kind: explain
title: 작업 기록이 이어지는 방식
target: work-continuity
---

세션이 끝나도 다음 세션이 같은 작업을 이어받도록 체크포인트를 남긴다.

## 전체 흐름

세션이 일을 하는 동안 훅이 상태를 모으고, 끝날 때 체크포인트로 남긴다.

```thinkflow
thinkflow
title "체크포인트가 남는 경로"
box session "세션"
box hook "훅"
store record "체크포인트"
session -> hook "상태"
hook -> record "저장"
```

## 정리

:::note[판단]
체크포인트는 상태가 바뀔 때만 게시한다.
:::
