---
name: principle-laziness-protocol
description: "리팩터링할 때, diff 크기를 평가할 때, 추상화·계층·신호 전달 경로를 더하고 싶을 때 적용한다. 삭제 쪽으로 기울고, 문제를 푸는 가장 작은 변경을 고른다."
disable-model-invocation: true
user-invocable: false
---

# 게으름 규약(Laziness Protocol)

- **결정을 한곳에 모은다.** 같은 선택을 여러 곳에서 되풀이하지 않는다. 정본 하나 뒤에 두고 결과를 단순한 플래그로 넘긴다.
- **diff를 최소로 한다.** 문제를 푸는 가장 작은 변경을 한다. "우아한" 보일러플레이트보다 적은 줄이 낫다.
