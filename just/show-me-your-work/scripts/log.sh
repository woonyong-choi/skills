#!/usr/bin/env bash
# show-me-your-work 결정 기록(TSV)에 올바른 형식의 행 하나를 덧붙인다.
# 사용법: log.sh <logfile> <phase> <decision> <why> <evidence> <result>
# 워크트리의 `.local/` 아래 경로는 기본 체크아웃(공통 git 디렉터리의 상위)의 `.local/`로 옮겨 쓴다.
# 워크트리를 지워도 기록이 남게 하려는 것이다. 실제로 쓴 경로는 stderr에 한 줄로 알린다.
set -euo pipefail

if [ "$#" -ne 6 ]; then
	printf '사용법: log.sh <logfile> <phase> <decision> <why> <evidence> <result>\n' >&2
	exit 1
fi

logfile="$1"
shift

# 없는 끝부분은 그대로 두고, 있는 가장 가까운 상위 폴더를 실제 경로로 푼다.
canonical() {
	local path="$1" rest=""
	case "$path" in
		/*) ;;
		*) path="$PWD/$path" ;;
	esac
	while [ ! -d "$path" ]; do
		rest="/$(basename "$path")$rest"
		path="$(dirname "$path")"
	done
	printf '%s%s' "$(cd "$path" && pwd -P)" "$rest"
}

target="$(canonical "$logfile")"
probe="$target"
while [ ! -d "$probe" ]; do probe="$(dirname "$probe")"; done
if top="$(git -C "$probe" rev-parse --show-toplevel 2>/dev/null)" \
	&& common="$(git -C "$probe" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
	top="$(cd "$top" && pwd -P)"
	shared="$top"
	if [ "$(basename "$common")" = ".git" ] && [ -d "$common" ]; then
		shared="$(cd "$(dirname "$common")" && pwd -P)"
	fi
	case "$target" in
		"$top/.local/"*)
			target="$shared/.local/${target#"$top/.local/"}"
			mkdir -p "$shared/.local"
			if [ ! -e "$shared/.local/.gitignore" ] \
				&& ! git -C "$shared" check-ignore -q .local/decisions/probe 2>/dev/null; then
				printf '*\n' > "$shared/.local/.gitignore"
			fi
			if [ "$shared" != "$top" ]; then
				printf 'log.sh: %s\n' "$target" >&2
			fi
			;;
	esac
fi
logfile="$target"

logdir="$(dirname "$logfile")"
if [ ! -d "$logdir" ]; then
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
