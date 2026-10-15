"""ThinkFlow CLI 산출물에서 토큰을 유지한 밝은·어두운 README SVG를 생성한다."""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# cost: time O(n + r), heap O(n), stack O(1), io 8
# vars: n = SVG 크기, r = ThinkFlow 검사·렌더 비용
# basis: estimate
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('thinkflow', type=Path, help='ThinkFlow src/cli.js')
    args = parser.parse_args()
    output = ROOT / '.runtime/figures'
    output.mkdir(parents=True, exist_ok=True)
    sources = ('skill-exposure', 'skill-quality')
    for name in sources:
        source = ROOT / 'docs/assets' / (name + '.thinkflow')
        options = ['--strict']
        subprocess.run(['node', str(args.thinkflow), 'check', str(source), *options], check=True)
    for name in sources:
        source = ROOT / 'docs/assets' / (name + '.thinkflow')
        options = ['--strict']
        subprocess.run(['node', str(args.thinkflow), 'render', str(source), *options, '--static', '--out', str(output)], check=True)
        svg = (output / (name + '.svg')).read_text()
        if svg.count('<svg ') != 1:
            raise ValueError('expected one root svg')
        for theme in ('light', 'dark'):
            # ThinkFlow 토큰의 공개 data-theme 선택자만 고정하고 색·배치 값은 유지한다.
            themed = svg.replace('<svg ', f'<svg data-theme="{theme}" ', 1)
            (ROOT / 'docs/assets' / f'{name}-{theme}.svg').write_text(themed)

if __name__ == '__main__':
    main()
