# README 틀

절 이름은 영어 원본 기준. 한국어 절 이름: 번역 절

## 오픈소스형

````text
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.png">
    <img src="docs/assets/logo-light.png" alt="{제품 이름} logo" height="80">
  </picture>
</p>

<h1 align="center">{제품 이름}</h1>

<p align="center">
  {한 줄 소개}<br>
  {license·CI·배포 버전 뱃지}<br>
  English | <a href="README.ko.md">한국어</a><br>
  <a href="#quick-start">Quick start</a> · <a href="#how-it-works">How it works</a> · <a href="#status">Status</a>
</p>

![{데모가 보여 주는 결론}](docs/assets/demo.gif)

> [!NOTE]
> {단계 알림}

## Quick start

{필요한 도구 한 문장}

```sh
{실제로 실행한 설치·첫 실행 명령}
```

## Why

{누가 무엇을 할 때 무엇이 어려운가} → {이 도구의 해결}. {대신 쓸 도구가 더 나은 경우 한 문장}

## How it works

1. {입력}
2. {처리}
3. {결과}

![{흐름 그림의 결론}](docs/assets/{이름}.svg)

The full design is in [{문서 제목}](docs/design/{주제}.md).

## Status

| Available | Not yet | Next | Measured |
|---|---|---|---|
| {있는 것} | {아직 없는 것} | [{상위 이슈}]({링크}) | {보고서 수치와 조건} |

{호환 약속 한 문장}

## Documentation

- [{시작 문서 제목}]({경로}): {답하는 것}
- [All documents](docs/README.md)

## Development

```sh
{빌드}
{테스트}
{린트}
{포맷 검사}
```

## License

[{SPDX}](LICENSE)
````

## 포트폴리오형

````text
<p align="center">
  <img src="docs/assets/logo-light.png" alt="{제품 이름} logo" height="80">
</p>

<h1 align="center">{제품 이름}</h1>

<p align="center">
  {무엇을 하는 시스템인지} · {규모 숫자 하나}<br>
  {핵심 기술 4~6개 뱃지, 이름과 버전}
</p>

![{실행 화면이 보여 주는 결론}](docs/assets/demo.gif)

## Problem and constraints

{왜 필요했나}. {무엇이 막았나}

## Design decisions

| Decision | Why | Alternatives not chosen |
|---|---|---|
| {결정} | {고른 이유} | {고르지 않은 대안} |

## Implementation

1. {핵심 흐름}

![{구조 그림의 결론}](docs/assets/{이름}.svg)

## Results

| Metric | Before | After | Conditions |
|---|---|---|---|
| {지표} | {이전} | {이후} | {측정 조건} |

## Running

```sh
{실제로 돌아가는 명령}
```
````
