"""폴더의 DiagramPlay 원본을 정지 SVG와 인쇄용 PNG(그림 영역만, 라이트, 2배, 캔버스 배경 투명)로 만든다.

사용: python3 figures.py <공고 폴더>/figures --diagramplay <DiagramPlay 체크아웃>. 결과는 원본 옆에 생성, 문서는 /figures/{이름}.png로 참조
인자: 그림 폴더, DiagramPlay 체크아웃(없으면 DIAGRAMPLAY_PATH). Chrome 경로는 CHROME_PATH(없으면 playwright 기본)
출력: 원본마다 {이름}.svg·{이름}.png, stdout 만든 PNG 경로, 종료 0 성공·1 실패·2 인자 오류
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SHOT = """
import { chromium } from 'playwright-core';
const [files, chrome] = JSON.parse(process.argv[1]);
const browser = await chromium.launch(chrome ? { executablePath: chrome } : {});
const page = await browser.newPage({ deviceScaleFactor: 2, colorScheme: 'light' });
for (const [svg, png] of files) {
  await page.goto('file://' + svg);
  await page.$$eval('.fl-canvas-surface', (els) => els.forEach((el) => el.remove()));
  await page.locator('svg').first().screenshot({ path: png, animations: 'disabled', omitBackground: true });
}
await browser.close();
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--diagramplay", type=Path, default=os.environ.get("DIAGRAMPLAY_PATH"))
    args = parser.parse_args()
    if args.diagramplay is None or not (args.diagramplay / "src" / "cli.js").is_file():
        parser.error("--diagramplay must be a DiagramPlay checkout")
    folder = args.folder.resolve()
    sources = sorted(folder.glob("*.diagramplay"))
    if not sources:
        print(f"no .diagramplay in {folder}", file=sys.stderr)
        return 1
    cli = str(args.diagramplay.resolve() / "src" / "cli.js")
    try:
        subprocess.run(["node", cli, "check", *map(str, sources), "--strict"], check=True)
        subprocess.run(["node", cli, "render", *map(str, sources), "--strict", "--static", "--out", str(folder)], check=True)
        pairs = [[str(folder / f"{s.stem}.svg"), str(folder / f"{s.stem}.png")] for s in sources]
        payload = json.dumps([pairs, os.environ.get("CHROME_PATH")])
        subprocess.run(["node", "--input-type=module", "-e", SHOT, payload], check=True, cwd=args.diagramplay)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"figures failed: {error}", file=sys.stderr)
        return 1
    for _, png in pairs:
        print(png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
