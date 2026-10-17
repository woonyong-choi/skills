"""Torso CLI 산출물에서 토큰을 유지한 밝은·어두운 README SVG를 생성한다.

사용: python3 scripts/render_readme.py <Torso 작업본>/src/cli.js (저장소 어디서나 실행)
인자: 위치 인자 하나. Torso 작업본의 src/cli.js 경로(CI는 .runtime/torso/src/cli.js)
출력: docs/assets/skill-exposure-{light,dark}.svg, docs/assets/skill-quality-{light,dark}.svg를 덮어쓴다. 중간 SVG는 .runtime/figures/에 둔다. Torso 검사(check --strict)가 하나라도 실패하면 렌더 전에 traceback과 함께 종료 1로 끝난다
실행 조건: Python 3.9 이상, Node.js 22, 의존성을 설치한 Torso 작업본
"""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('skill-exposure', 'skill-quality')
STRICT = '--strict'


def source_path(name: str) -> Path:
    return ROOT / 'docs/assets' / (name + '.torso')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('cli', type=Path, help='Torso src/cli.js')
    args = parser.parse_args()
    output = ROOT / '.runtime/figures'
    output.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        subprocess.run(['node', str(args.cli), 'check', str(source_path(name)), STRICT], check=True)
    for name in SOURCES:
        subprocess.run(['node', str(args.cli), 'render', str(source_path(name)), STRICT, '--static', '--out', str(output)], check=True)
        svg = (output / (name + '.svg')).read_text()
        if svg.count('<svg ') != 1:
            raise ValueError('expected one root svg')
        for theme in ('light', 'dark'):
            # Torso 토큰의 공개 data-theme 선택자만 고정하고 색·배치 값은 유지한다.
            themed = svg.replace('<svg ', f'<svg data-theme="{theme}" ', 1)
            (ROOT / 'docs/assets' / f'{name}-{theme}.svg').write_text(themed)

if __name__ == '__main__':
    main()
