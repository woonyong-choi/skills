# 비용 해석·예·측정

```rust
// cost: time O(n log n), heap O(n), stack O(1), alloc 1
// mem: heap ≈ n·size(Entry)
// vars: n = entries.len()
// basis: estimate
// alt: HashMap 색인. time O(n), heap ≈ n·(size(Key) + size(Entry)). 잃는 것: 정렬 순서
```

- 시간: 최악 기준. 평균이 다르면 `time O(n) avg, O(n²) worst`
- `heap`: 이 함수가 새로 할당해 동시에 살아 있는 최대 크기. 입력으로 받은 것 제외, 반환값 포함
- `stack`: 재귀 깊이와 큰 지역 배열 기준. 없으면 O(1)
- 숫자 바이트: 크기가 정해진 타입(`u64` = 8바이트 등)이나 측정값만. 그 밖에는 기호 식(지어낸 수치 방지)

| 언어 | 주석 기호 | 힙 측정 | 시간 측정 |
|---|---|---|---|
| Rust | `//` | `dhat` | `criterion` |
| Kotlin | `//` | JFR 할당 기록 | JMH |
| Python | `#` | `tracemalloc` | `pytest-benchmark` |
| JavaScript | `//` | `node --heap-prof` | `node --cpu-prof` |
