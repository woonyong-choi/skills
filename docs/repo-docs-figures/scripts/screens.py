"""docs/assets/screens.json의 화면을 촬영해 배경·모서리·그림자를 합성한 라이트·다크 PNG로 저장.

인자: shoot 또는 check, --config(기본 docs/assets/screens.json), --out(기본 설정 파일 폴더), --run-id(기본 시각)
출력: {이름}-light.png·{이름}-dark.png, stderr 실패 이유, 종료 0 성공·1 실패·2 인자 오류
실행 조건: Python 3.9 이상, 웹 화면은 Python Playwright와 Chromium, 터미널 화면은 VHS. 1MB 초과 시 oxipng가 있으면 무손실 압축
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, NamedTuple

HERE = Path(__file__).resolve().parent

PAGE = 960
SCALE = 2
WINDOW = {"single": 960, "two": 640, "zoom": 640}
HEIGHT = 720
LIMIT = 1024 * 1024
SCHEMES = ("light", "dark")
# 저장소 디자인 정본이 없을 때의 무채색 기본값. screens.json의 style이 있으면 그 값 사용
DEFAULT_STYLE = {
    "padding": 48,
    "gap": 32,
    "radius": 12,
    "shadow": "0 8px 24px rgba(0, 0, 0, 0.18)",
    "background": {"light": "#e5e5e5", "dark": "#262626"},
}
NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
BAD_NAME = re.compile(r"^(?:image|img|screenshot|screen)\d*$|\d{4}-?\d{2}-?\d{2}")
KIND_ONLY = re.compile(r"^(?:\S+\s)?(?:스크린샷|화면|이미지|그림|screenshot|screen|image)$", re.IGNORECASE)


class Capture(NamedTuple):
    kind: str
    source: str
    width: int
    scale: int
    scheme: str
    selector: str | None
    clip: dict | None


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def layout(kind: str, style: dict) -> dict:
    """합성 페이지 폭(CSS px)·배율·장면 열 위치. 최종 파일 폭 = page × scale"""
    inner = PAGE - 2 * style["padding"]
    if kind == "single":
        columns = [(style["padding"], inner)]
    else:
        width = (inner - style["gap"]) // 2
        columns = [(style["padding"], width), (style["padding"] + width + style["gap"], width)]
    return {"page": PAGE, "scale": SCALE, "columns": columns}


def plan(entry: dict, scheme: str) -> list[Capture]:
    """한 테마의 촬영 목록. 확대는 같은 화면의 영역을 배율 2배로 다시 촬영"""
    kind = "command" if "command" in entry else "url"
    sources = entry[kind] if isinstance(entry[kind], list) else [entry[kind]]
    width = entry.get("width", WINDOW[entry["layout"]])
    base = [Capture(kind, source, width, SCALE, scheme, entry.get("select"), None) for source in sources]
    if entry["layout"] == "zoom":
        base.append(base[0]._replace(scale=SCALE * 2, clip=entry["zoom"], selector=None))
    return base


def validate(config: dict) -> list[str]:
    errors = []
    for entry in config.get("screens", []):
        name = str(entry.get("name", ""))
        if not NAME.fullmatch(name) or BAD_NAME.search(name):
            errors.append(f"{name or '(이름 없음)'}: 이름은 보여 주는 것을 영어 소문자 kebab-case로(번호·날짜·한글 금지)")
        alt = str(entry.get("alt") or "").strip()
        if not alt or alt.endswith(".") or KIND_ONLY.match(alt) or (name and name in alt):
            errors.append(f"{name}: 대체 글은 그림을 봐야 알 수 있는 결론 한 문장(마침표·파일 이름·그림 종류만 금지)")
        kind = entry.get("layout")
        if kind not in WINDOW:
            errors.append(f"{name}: layout은 single, two, zoom 중 하나")
            continue
        target = entry.get("url", entry.get("command"))
        count = len(target) if isinstance(target, list) else (1 if target else 0)
        if count != (2 if kind == "two" else 1):
            errors.append(f"{name}: url 또는 command가 {kind}에 맞지 않음(two는 두 개, 나머지는 한 개)")
        if kind == "zoom" and not {"x", "y", "width", "height"} <= set(entry.get("zoom") or {}):
            errors.append(f"{name}: zoom 영역 x, y, width, height 필요")
    return errors


def png_width(data: bytes) -> int:
    return int.from_bytes(data[16:20], "big") if data[:8] == b"\x89PNG\r\n\x1a\n" else 0


def check(config: dict, out: Path) -> list[str]:
    """저장된 PNG 대조: 대체 글, 라이트·다크 두 장, 폭 1920px, 1MB 이하"""
    errors = validate(config)
    for entry in config.get("screens", []):
        for scheme in SCHEMES:
            path = out / f"{entry.get('name')}-{scheme}.png"
            if not path.is_file():
                errors.append(f"{path.name}: 파일 없음")
                continue
            data = path.read_bytes()
            if png_width(data) != PAGE * SCALE:
                errors.append(f"{path.name}: 폭 {png_width(data)}px, {PAGE * SCALE}px 필요")
            if len(data) > LIMIT:
                errors.append(f"{path.name}: {len(data)} bytes, 1MB 초과")
    return errors


def compose(images: list[bytes], kind: str, style: dict, scheme: str) -> tuple[str, dict]:
    """합성용 HTML. 장면은 열 폭에 맞춰 줄이기만 하고 늘리지 않음"""
    geometry = layout(kind, style)
    tags = []
    for (left, width), data in zip(geometry["columns"], images):
        uri = "data:image/png;base64," + base64.b64encode(data).decode()
        shown = min(width, png_width(data) // geometry["scale"])
        tags.append(f'<img src="{uri}" style="position:absolute;left:{left}px;top:{style["padding"]}px;width:{shown}px">')
    css = (
        f"html,body{{margin:0;background:{style['background'][scheme]}}}"
        f"#frame{{position:relative;width:{geometry['page']}px}}"
        f"img{{display:block;border-radius:{style['radius']}px;box-shadow:{style['shadow']}}}"
    )
    return f"<!doctype html><style>{css}</style><div id=frame>{''.join(tags)}</div>", geometry


def shrink(data: bytes) -> bytes:
    """1MB 초과면 설치된 oxipng로 무손실 압축. 그래도 넘으면 실패"""
    if len(data) > LIMIT and shutil.which("oxipng"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "shot.png"
            path.write_bytes(data)
            subprocess.run(["oxipng", "-q", "-o", "4", "--strip", "safe", str(path)], check=True)
            data = path.read_bytes()
    if len(data) > LIMIT:
        raise RuntimeError(f"{len(data)} bytes, 무손실 압축 뒤에도 1MB 초과")
    return data


def shoot(config: dict, out: Path, capture: Callable[[Capture], bytes], render: Callable[[str, dict], bytes]) -> int:
    """전체 촬영이 성공한 뒤에만 out에 저장. 하나라도 실패하면 기존 파일 유지, 종료 1"""
    errors = validate(config)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    style = {**DEFAULT_STYLE, **config.get("style", {})}
    staged: dict[str, bytes] = {}
    try:
        for entry in config["screens"]:
            for scheme in SCHEMES:
                images = [capture(item) for item in plan(entry, scheme)]
                html, geometry = compose(images, entry["layout"], style, scheme)
                data = shrink(render(html, geometry))
                if png_width(data) != PAGE * SCALE:
                    raise RuntimeError(f"{entry['name']}-{scheme}.png: 폭 {png_width(data)}px")
                staged[f"{entry['name']}-{scheme}.png"] = data
    except Exception as error:  # 촬영·합성 도구의 모든 실패를 이유와 함께 보고
        print(f"촬영 실패, 기존 파일 유지: {error}", file=sys.stderr)
        return 1
    for name, data in staged.items():
        temporary = out / f".{name}.tmp"
        temporary.write_bytes(data)
        temporary.replace(out / name)
    return 0


class Browser:
    """Playwright Chromium으로 웹 화면 촬영과 합성 HTML 렌더링. 터미널 화면은 VHS"""

    def __enter__(self) -> "Browser":
        from playwright.sync_api import sync_playwright

        self.manager = sync_playwright().start()
        self.browser = self.manager.chromium.launch()
        return self

    def __exit__(self, *_: object) -> None:
        self.browser.close()
        self.manager.stop()

    def capture(self, item: Capture) -> bytes:
        if item.kind == "command":
            return terminal(item)
        page = self.browser.new_page(viewport={"width": item.width, "height": HEIGHT}, device_scale_factor=item.scale, color_scheme=item.scheme)
        try:
            page.goto(item.source, wait_until="networkidle")
            if item.clip:
                return page.screenshot(clip=item.clip, animations="disabled", caret="hide")
            if item.selector:
                return page.locator(item.selector).screenshot(animations="disabled", caret="hide")
            return page.screenshot(full_page=True, animations="disabled", caret="hide")
        finally:
            page.close()

    def render(self, html: str, geometry: dict) -> bytes:
        page = self.browser.new_page(viewport={"width": geometry["page"], "height": HEIGHT}, device_scale_factor=geometry["scale"])
        try:
            page.set_content(html, wait_until="load")
            page.evaluate(
                """() => { const frame = document.getElementById('frame');
                const bottom = Math.max(...[...frame.querySelectorAll('img')].map(img => img.offsetTop + img.offsetHeight));
                frame.style.height = (bottom + parseInt(getComputedStyle(frame.querySelector('img')).top)) + 'px'; }"""
            )
            return page.locator("#frame").screenshot()
        finally:
            page.close()


def terminal(item: Capture) -> bytes:
    """VHS Screenshot으로 터미널 창 안쪽 촬영. 창 폭·글자 크기에 배율 반영"""
    if shutil.which("vhs") is None:
        raise RuntimeError("vhs not found on PATH")
    theme = "Builtin Light" if item.scheme == "light" else "Builtin Dark"
    with tempfile.TemporaryDirectory() as folder:
        shot = Path(folder) / "shot.png"
        tape = Path(folder) / "shot.tape"
        tape.write_text(
            f'Output "{Path(folder) / "shot.gif"}"\nSet Shell "bash"\nSet Theme "{theme}"\n'
            f"Set FontSize {16 * item.scale}\nSet Width {item.width * item.scale}\nSet Height {HEIGHT * item.scale}\nSet Padding {24 * item.scale}\n"
            f"Hide\nType \"export PS1='$ ' && clear\"\nEnter\nShow\nType {json.dumps(item.source)}\nEnter\nSleep 2s\nScreenshot \"{shot}\"\n",
            encoding="utf-8",
        )
        subprocess.run(["vhs", str(tape)], check=True, capture_output=True)
        return shot.read_bytes()


def discard(folder: Path) -> None:
    """합성 데이터 폴더를 휴지통으로 이동. 휴지통 도구가 없으면 지우지 않고 경로 보고"""
    for command in (["trash", str(folder)], ["gio", "trash", str(folder)]):
        if shutil.which(command[0]) and subprocess.run(command, capture_output=True).returncode == 0:
            return
    print(f"휴지통 도구 없음, 직접 확인 필요: {folder}", file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("shoot", "check"))
    parser.add_argument("--config", type=Path, default=Path("docs/assets/screens.json"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--run-id", default=time.strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args(argv)
    config = load(args.config)
    out = args.out or args.config.parent
    if args.action == "check":
        errors = check(config, out)
        print("\n".join(errors), file=sys.stderr) if errors else None
        return 1 if errors else 0
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
    if top.returncode or not top.stdout.strip():
        print("촬영 중단: git 저장소 밖에서 실행됨(합성 데이터는 저장소 .local/runs/ 아래에 만든다)", file=sys.stderr)
        return 2
    if not args.run_id or Path(args.run_id).name != args.run_id or args.run_id in (".", ".."):
        print("촬영 중단: run-id는 비어 있지 않은 단일 폴더 이름이어야 한다", file=sys.stderr)
        return 2
    runs = Path(top.stdout.strip()).resolve() / ".local" / "runs"
    data = runs / f"screenshots-{args.run_id}"
    try:
        if runs.resolve() != runs or data.is_symlink():
            raise ValueError(f"합성 데이터 경로에 심볼릭 링크가 있음: {data}")
        data.mkdir(parents=True)
        owned = data.lstat()
    except (OSError, ValueError) as error:
        print(f"촬영 중단: 합성 데이터 폴더 신규 생성 실패: {error}", file=sys.stderr)
        return 2
    try:
        os.environ["SCREENS_DATA"] = str(data)
        for entry in config.get("screens", []):
            for key in ("url", "command"):
                if key in entry:
                    values = entry[key] if isinstance(entry[key], list) else [entry[key]]
                    values = [value.replace("{data}", str(data)) for value in values]
                    entry[key] = values if isinstance(entry[key], list) else values[0]
        with Browser() as browser:
            return shoot(config, out, browser.capture, browser.render)
    finally:
        try:
            current = data.lstat()
            is_owned = data.resolve() == data and (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino)
        except OSError:
            is_owned = False
        if is_owned:
            discard(data)
        else:
            print(f"합성 데이터 폴더 변경 감지, 정리하지 않음: {data}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
