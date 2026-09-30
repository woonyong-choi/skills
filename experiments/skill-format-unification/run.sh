#!/usr/bin/env bash
# 사용: ./run.sh collect|process|analyze|verify|all
set -euo pipefail
cd "$(dirname "$0")"
export TOOLS=${TOOLS:-$HOME/.cache/skill-exp-tools}
tools() {
  [ -d "$TOOLS/node_modules/gpt-tokenizer" ] && return
  mkdir -p "$TOOLS"
  npm install --prefix "$TOOLS" gpt-tokenizer@2.9.0 @anthropic-ai/tokenizer@0.0.4 >/dev/null
}
case "${1:-}" in
  collect) bash scripts/01-collect.sh ;;
  process) tools; python3 scripts/02-process.py ;;
  analyze) tools; python3 scripts/02-process.py; python3 scripts/03-analyze.py ;;
  verify) (cd data && sha256sum -c --quiet SHA256SUMS) ;;
  all) "$0" verify; "$0" analyze ;;
  *) echo "사용: $0 collect|process|analyze|verify|all" >&2; exit 2 ;;
esac
