#!/usr/bin/env bash
# show-me-your-work 결정 기록(TSV)에 올바른 형식의 행 하나를 덧붙인다.
# 사용법: log.sh <logfile> <phase> <decision> <why> <evidence> <result>
set -euo pipefail

if [ "$#" -ne 6 ]; then
	printf '사용법: log.sh <logfile> <phase> <decision> <why> <evidence> <result>\n' >&2
	exit 1
fi

logfile="$1"
shift

logdir="$(dirname "$logfile")"
if [ -n "$logdir" ] && [ "$logdir" != "." ] && [ ! -d "$logdir" ]; then
	mkdir -p "$logdir"
fi

# `>`가 아니라 `>>`를 쓴다. 네트워크 마운트에서는 있는 파일도 이 검사에 실패할 수
# 있는데, 그때 잃는 것은 행이 아니라 남는 머리 행 하나다.
if [ ! -s "$logfile" ]; then
	printf 'ts\tphase\tdecision\twhy\tevidence\tresult\n' >> "$logfile"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# 기록은 스프레드시트로도 열리므로 PR 제목, 파일 이름, 생성된 글 같은 외부 입력이
# 수식(=, +, -, @로 시작)으로 실행되지 않게 작은따옴표를 붙인다.
clean() {
	local v
	v=$(printf '%s' "$1" | tr '\t\n\r' '   ')
	case "$v" in
		=*|+*|-*|@*) printf "'%s" "$v" ;;
		*) printf '%s' "$v" ;;
	esac
}
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
	"$ts" "$(clean "$1")" "$(clean "$2")" "$(clean "$3")" "$(clean "$4")" "$(clean "$5")" \
	>> "$logfile"
