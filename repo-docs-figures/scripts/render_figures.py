"""그림 원본(.d2, .vl.json, .tape)을 SVG, GIF로 변환.

사용: python3 render_figures.py [원본 ...] (저장소 루트에서 실행, 인자가 없으면 git이 추적하는 모든 원본)
"""
import json
import os
import re
import subprocess
import sys

D2_PALETTE = """vars: {
  d2-config: {
    theme-overrides: {
      B1: "#1d4f91"
      B2: "#2a78d6"
      B3: "#7fa9e3"
      B4: "#dce8f8"
      B5: "#edf3fb"
      B6: "#f6f9fd"
      AA2: "#eb6834"
      AA4: "#fbe1d5"
      AA5: "#fdf1ea"
      AB4: "#d3efe4"
      AB5: "#e9f7f1"
      N1: "#0b0b0b"
      N2: "#52514e"
      N3: "#8a8983"
      N4: "#c3c2b7"
      N5: "#e6e5e1"
      N6: "#f3f3f1"
      N7: "#ffffff"
    }
  }
}
"""
VEGA_LITE_CONFIG = {
    "background": "#ffffff",
    "font": "Noto Sans CJK KR",
    "view": {"stroke": None},
    "mark": {"color": "#2a78d6"},
    "bar": {"cornerRadiusEnd": 4},
    "rule": {"color": "#eb6834", "strokeDash": [4, 4], "strokeWidth": 2},
    "errorbar": {"rule": {"color": "#0b0b0b", "strokeDash": [1, 0], "strokeWidth": 2}},
    "range": {"category": ["#2a78d6", "#eb6834"], "heatmap": ["#edf3fb", "#1d4f91"]},
    "axis": {"labelColor": "#52514e", "titleColor": "#52514e", "gridColor": "#e6e5e1",
             "domainColor": "#c3c2b7", "tickColor": "#c3c2b7", "labelFontSize": 11, "titleFontSize": 11},
    "title": {"color": "#0b0b0b", "subtitleColor": "#8a8983", "fontSize": 14,
              "subtitleFontSize": 11, "anchor": "start"},
    "legend": {"labelColor": "#52514e", "titleColor": "#52514e", "orient": "top"},
}
SKETCH = re.compile(r"(^|[{ ])sketch *:", re.M)


# cost: time O(s) + d2, heap O(s), stack O(1), io 3
# vars: s = 원본 글자 수, d2 = d2 변환 시간
# basis: estimate
def render_d2(source: str) -> None:
    text = open(source, encoding="utf-8").read()
    if SKETCH.search(text):
        print(f"{source}: 손그림 금지")
        raise SystemExit(1)
    target = source[: -len(".d2")] + ".svg"
    result = subprocess.run(
        ["d2", "--layout", "elk", "--theme", "0", "--pad", "24", "-", target],
        input=D2_PALETTE + text,
        text=True,
    )
    if result.returncode:
        raise SystemExit(1)
    os.chmod(target, 0o644)


# cost: time O(s) + vl, heap O(s + g), stack O(1), io 2
# vars: s = 원본 글자 수, g = 만든 SVG 글자 수, vl = vl-convert 변환 시간
# basis: estimate
def render_vega_lite(source: str) -> None:
    import vl_convert

    spec = json.load(open(source, encoding="utf-8"))
    if "config" in spec:
        raise SystemExit(source + ": config 금지")
    spec["config"] = VEGA_LITE_CONFIG
    target = source[: -len(".vl.json")] + ".svg"
    open(target, "w", encoding="utf-8").write(vl_convert.vegalite_to_svg(spec))


# cost: time O(n) + 변환 시간 합, heap O(n + s), stack O(1), io n
# vars: n = 원본 수, s = 가장 큰 원본 글자 수
# basis: estimate
def main(sources: list[str]) -> int:
    if not sources:
        listed = subprocess.run(["git", "ls-files", "--", "*.d2", "*.vl.json", "*.tape"], capture_output=True, text=True, check=True)
        sources = listed.stdout.split()
    for source in sources:
        if source.endswith(".d2"):
            render_d2(source)
        elif source.endswith(".vl.json"):
            render_vega_lite(source)
        elif source.endswith(".tape"):
            if subprocess.run(["vhs", source]).returncode:
                return 1
        else:
            print(f"{source}: 원본 형식 아님")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
