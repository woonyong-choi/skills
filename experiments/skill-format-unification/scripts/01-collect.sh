#!/usr/bin/env bash
# 수집: 작업 폴더(SRC)의 스킬 스냅숏, 시험 입력, 에이전트 산출물을 data/raw로 복사
# SRC 구조: skills/(before) new.pre-fix/(r1) r2/(r2) r3/(r3) new/(after) test/{prompts.md,expected.json,facts3.md,catalog-*.md,trigger-*.json,w-a..w-f/}
# audit-findings*.jsonl은 대조 에이전트 보고를 손으로 기록한 파일이라 이 스크립트 대상 아님
# 트리거와 작성 산출물은 에이전트가 만든 것이라 다시 실행하면 값이 달라짐. raw/는 수집 뒤 수정 금지
set -euo pipefail
SRC=${SRC:?SRC 필요}
RAW=$(cd "$(dirname "$0")/.." && pwd)/data/raw
mkdir -p "$RAW/writers"
pack() { tar -C "$SRC" -czf "$RAW/skills-$2.tar.gz" --transform "s,^$1,skills," "$1"; }
pack skills before
pack new.pre-fix r1
pack r2 r2
pack r3 r3
pack new after
cp "$SRC/test/prompts.md" "$SRC/test/expected.json" "$RAW/"
cp "$SRC/test/facts3.md" "$RAW/facts.md"
cp "$SRC/test/catalog-old.md" "$RAW/catalog-before.md"
cp "$SRC/test/catalog-new.v1.md" "$RAW/catalog-r1.md"
cp "$SRC/test/catalog-new.md" "$RAW/catalog-after.md"
cp "$SRC/test/trigger-old.json" "$RAW/trigger-before-1.json"
cp "$SRC/test/trigger-new-a.json" "$RAW/trigger-r1-1.json"
cp "$SRC/test/trigger-new-b.json" "$RAW/trigger-r1-2.json"
cp "$SRC/test/trigger-after-1.json" "$RAW/trigger-after-1.json"
for x in "a r1-1" "b r1-2" "c r2-1" "d r2-2" "e r3-1" "f r3-2" "g r4-1" "h r4-2"; do
  set -- $x
  mkdir -p "$RAW/writers/$2"
  tar -C "$SRC/test/w-$1" --exclude=.git -cf - . | tar -C "$RAW/writers/$2" -xf -
done
