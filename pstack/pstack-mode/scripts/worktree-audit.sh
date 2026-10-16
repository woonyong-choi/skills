#!/usr/bin/env bash
# 읽기 전용 워크트리 정리 감사. 모든 git 워크트리를 크기, 머지 상태, 커밋 안 한
# 변경, 원격·PR 상태, 그 워크트리에서 작업한 가장 최근 대화로 분류하고 크기순 표와
# 추천 분류를 출력한다. 아무것도 지우지 않는다. 삭제는 플레이북에서 사람이 승인한다.
#
# 사용법: worktree-audit.sh [-b|--base <ref>] [repo-path]
#   repo-path 기본값은 현재 저장소.
#   -b는 MERGED 열이 비교할 ref (예 origin/integration).
#   없으면 origin/HEAD, origin/main, origin/master 순으로 고른다.
#   origin/HEAD는 원격 기본 브랜치일 뿐 PR이 머지되는 브랜치와 다를 수 있다.
#   다르면 -b를 넘긴다.
#
# 대화 기록 위치 (Claude Code, Codex, OpenCode):
#   ~/.claude/projects, ~/.codex/sessions, ~/.local/share/opencode
set -u

base=""
while [ $# -gt 0 ]; do
	case "$1" in
	-b|--base) [ $# -ge 2 ] || { echo "오류: $1 뒤에 ref가 필요함" >&2; exit 2; }; base="$2"; shift 2 ;;
	-h|--help) sed -n '2,/^set -u/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
	-*) echo "오류: 알 수 없는 옵션 $1" >&2; exit 2 ;;
	*) break ;;
	esac
done

repo="${1:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$repo" ] && { echo "오류: git 저장소 안이 아님. 저장소 경로를 넘길 것" >&2; exit 1; }
cd "$repo" || exit 1
git rev-parse --git-dir >/dev/null 2>&1 || { echo "오류: git 저장소가 아님 ($repo)" >&2; exit 1; }

main_wt=$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')

if [ -z "$base" ]; then
	for cand in "$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)" origin/main origin/master; do
		[ -n "$cand" ] && git rev-parse --verify --quiet "$cand^{commit}" >/dev/null && { base="$cand"; break; }
	done
	[ -z "$base" ] && { echo "오류: base ref 없음 (origin/HEAD, origin/main, origin/master 모두 없음). -b <ref>를 넘길 것" >&2; exit 1; }
	echo "경고: -b가 없어 MERGED를 $base 기준으로 확인함" >&2
fi

# -b가 아직 fetch하지 않은 브랜치일 수 있어 확인 전에 가져온다. 명시한 refspec은
# single-branch clone에서도 원격 추적 ref를 만든다.
case "$base" in
origin/*) git fetch origin "+refs/heads/${base#origin/}:refs/remotes/$base" --quiet 2>/dev/null \
	|| echo "경고: $base fetch 실패. MERGED 열이 오래됐을 수 있음" >&2 ;;
esac
git rev-parse --verify --quiet "$base^{commit}" >/dev/null 2>&1 || { echo "오류: base ref를 찾을 수 없음 ($base)" >&2; exit 1; }

prs=$(mktemp)
trap 'rm -f "$prs"' EXIT
if raw=$(gh pr list --author "@me" --state all --limit 1000 \
	--json number,state,headRefName 2>/dev/null); then
	printf '%s' "$raw" | jq '[.[] | {number, state: (.state | ascii_downcase), head: .headRefName}]' > "$prs" 2>/dev/null
fi
[ -s "$prs" ] || echo "[]" > "$prs"

transcript_roots=()
for dir in "$HOME/.claude/projects" "$HOME/.codex/sessions" "${XDG_DATA_HOME:-$HOME/.local/share}/opencode"; do
	[ -d "$dir" ] && transcript_roots+=("$dir")
done

# GNU(Linux)와 BSD(macOS)의 stat, date 옵션이 다르다.
if stat -c %Y / >/dev/null 2>&1; then
	mtime_list() { xargs -0 stat -c '%Y %n' 2>/dev/null; }
else
	mtime_list() { xargs -0 stat -f '%m %N' 2>/dev/null; }
fi
if date -d @0 >/dev/null 2>&1; then
	day_of() { date -d "@$1" '+%Y-%m-%d'; }
else
	day_of() { date -r "$1" '+%Y-%m-%d'; }
fi

files_mentioning() {
	if command -v rg >/dev/null 2>&1; then
		rg -uu -l -0 -F -e "$1/" -e "$1\"" "${transcript_roots[@]}" 2>/dev/null
	else
		grep -rlZ -F -e "$1/" -e "$1\"" "${transcript_roots[@]}" 2>/dev/null
	fi
}

now=$(date +%s)

echo "# base: $base"
printf "SIZE\tAGE\tMERGED\tDIRTY\tREMOTE\tPR\tLAST_CHAT\tBUCKET\tWORKTREE\n"

git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r wt; do
	[ "$wt" = "$main_wt" ] && continue

	size=$(du -sh "$wt" 2>/dev/null | awk '{print $1}')
	head=$(git -C "$wt" rev-parse HEAD 2>/dev/null)
	head_ts=$(git -C "$wt" log -1 --format='%ct' HEAD 2>/dev/null || echo 0)
	age=$([ "$head_ts" -gt 0 ] 2>/dev/null && echo "$(( (now - head_ts) / 86400 ))d" || echo "?")

	# squash-merge한 브랜치는 base의 조상이 아니므로 진짜 신호는 PR 상태다.
	git merge-base --is-ancestor "$head" "$base" 2>/dev/null && merged=YES || merged=no

	porcelain=$(git -C "$wt" status --porcelain 2>/dev/null)
	if [ -z "$porcelain" ]; then dirty=clean
	elif printf '%s\n' "$porcelain" | grep -qv '^??'; then
		dirty="wip:$(printf '%s\n' "$porcelain" | grep -cv '^??')"
	else dirty="scratch:$(printf '%s\n' "$porcelain" | grep -c '^??')"; fi

	branch=$(git -C "$wt" symbolic-ref --quiet --short HEAD 2>/dev/null || echo "")
	if [ -z "$branch" ]; then remote=detached
	elif git -C "$wt" show-ref --verify --quiet "refs/remotes/origin/$branch"; then
		[ "$(git -C "$wt" rev-parse "origin/$branch" 2>/dev/null)" = "$head" ] \
			&& remote=pushed \
			|| remote="ahead$(git -C "$wt" rev-list --count "origin/$branch..HEAD" 2>/dev/null)"
	else remote=no-remote; fi

	pr=$([ -n "$branch" ] && jq -r --arg b "$branch" \
		'.[] | select(.head==$b) | "#\(.number)/\(.state)"' "$prs" 2>/dev/null | head -1)
	[ -z "$pr" ] && pr="-"

	# 경로 뒤에 / 또는 따옴표가 와야 일치로 본다. glint-482가 glint-482-r37에 걸리지 않게 한다.
	last="-"; last_ts=0
	if [ ${#transcript_roots[@]} -gt 0 ]; then
		f=$(files_mentioning "$wt" | mtime_list | sort -rn | head -1)
		if [ -n "$f" ]; then last_ts=${f%% *}
			last=$(day_of "$last_ts"); fi
	fi
	recent=$([ "$last_ts" -gt 0 ] 2>/dev/null && [ $(( (now - last_ts) / 86400 )) -le 4 ] && echo yes || echo no)

	case "$dirty" in wip:*) bucket=hold-wip ;; *)
		case "$pr" in */open|*/draft) bucket=hold-open-pr ;; *)
			if [ "$recent" = yes ]; then bucket=verify-recent-chat
			elif [ "$merged" = YES ] || [ "$pr" != "-" ]; then bucket=safe
			else bucket=review; fi ;;
		esac ;;
	esac

	printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
		"$size" "$age" "$merged" "$dirty" "$remote" "$pr" "$last" "$bucket" "$wt"
done | sort -t$'\t' -k1,1 -rh
