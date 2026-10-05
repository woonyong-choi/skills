# 표본

설계 단계 영어 원본의 절 구성. 글자 복사 대상 아님(repo-docs references/writing.md 절 구성 7)

````text
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.png">
    <img src="docs/assets/logo-light.png" alt="{제품 이름} logo" width="{검증한 표시 폭}">
  </picture>
</p>

<h1 align="center">{제품 이름}</h1>

<p align="center">
  {제품 범주와 하는 일}
</p>

<p align="center">
  English | <a href="README.ko.md">한국어</a><br>
  <a href="#how-it-works">How it works</a> · <a href="#status">Status</a> · <a href="#roadmap">Roadmap</a> · <a href="#documentation">Documentation</a>
</p>

{독자의 문제, 제품의 해결 방법, 비교 대상이 있으면 차이}

> [!NOTE]
> Design stage. There is no runnable code yet.

![Design: {설계 그림이 보여 주는 결론}](docs/assets/architecture.svg)

## How it works

The following is the designed behavior.

1. {사용 장면의 입력}
2. {제품의 처리}
3. {사용자가 확인하는 결과}

The full design is in [{기능 설계}](docs/design/{주제}.md).

## Status

The design documents and decision records are public. There is no code yet. Formats and commands may change without notice before 1.0.

## Roadmap

1. {현재 단계와 기능}. (in progress)
2. {다음 단계와 기능}. (next)

## Documentation

The design documents are written in Korean.

- [Architecture](docs/architecture.md): code map and invariants
- [All documents](docs/README.md)
````
