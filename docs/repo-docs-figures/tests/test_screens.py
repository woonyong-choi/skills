"""screens의 최종 폭·두 장면 여백·확대 재촬영·입력 검사·실패 시 기존 파일 보존 검증."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screens.py"
_SPEC = importlib.util.spec_from_file_location("screens", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
SCREENS = importlib.util.module_from_spec(_SPEC)
sys.modules["screens"] = SCREENS
_SPEC.loader.exec_module(SCREENS)

try:
    import playwright.sync_api  # noqa: F401

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def png(width: int, height: int) -> bytes:
    """무채색 한 장. 시험용 장면 이미지"""
    row = b"\x00" + b"\x80\x80\x80" * width
    body = zlib.compress(row * height)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", body) + chunk(b"IEND", b"")


ENTRY = {"name": "lag-table", "url": "http://localhost:8000/", "layout": "single", "alt": "지연이 늘어나는 토픽이 표 맨 위에 표시된다"}


class LayoutTest(unittest.TestCase):
    def test_final_width_is_1920_for_every_layout(self) -> None:
        for kind in ("single", "two", "zoom"):
            with self.subTest(kind=kind):
                layout = SCREENS.layout(kind, SCREENS.DEFAULT_STYLE)
                self.assertEqual(layout["page"] * layout["scale"], 1920)

    def test_window_width_by_layout(self) -> None:
        self.assertEqual(SCREENS.WINDOW["single"], 960)
        self.assertEqual(SCREENS.WINDOW["two"], 640)
        self.assertEqual(SCREENS.WINDOW["zoom"], 640)

    def test_two_scene_gap_is_fixed(self) -> None:
        for style in (SCREENS.DEFAULT_STYLE, {**SCREENS.DEFAULT_STYLE, "padding": 24}):
            with self.subTest(padding=style["padding"]):
                columns = SCREENS.layout("two", style)["columns"]
                (left, left_width), (right, _) = columns
                self.assertEqual(right - (left + left_width), style["gap"])


class ComposeTest(unittest.TestCase):
    def test_scene_is_never_stretched(self) -> None:
        html, _ = SCREENS.compose([png(400, 4), png(4000, 4)], "two", SCREENS.DEFAULT_STYLE, "light")
        widths = [int(value) for value in __import__("re").findall(r"width:(\d+)px\">", html)]
        column = SCREENS.layout("two", SCREENS.DEFAULT_STYLE)["columns"][0][1]
        self.assertEqual(widths, [200, column])


class PlanTest(unittest.TestCase):
    def test_zoom_recaptures_region_at_double_scale(self) -> None:
        entry = {**ENTRY, "layout": "zoom", "zoom": {"x": 10, "y": 20, "width": 200, "height": 100}}
        main, zoom = SCREENS.plan(entry, "light")
        self.assertEqual((main.source, main.width, main.clip), (zoom.source, zoom.width, None))
        self.assertEqual(zoom.clip, entry["zoom"])
        self.assertEqual(zoom.scale, main.scale * 2)

    def test_two_scenes_capture_each_target(self) -> None:
        entry = {**ENTRY, "layout": "two", "url": ["http://localhost/a", "http://localhost/b"]}
        captures = SCREENS.plan(entry, "dark")
        self.assertEqual([capture.source for capture in captures], entry["url"])
        self.assertTrue(all(capture.width == 640 and capture.scheme == "dark" for capture in captures))


class ValidateTest(unittest.TestCase):
    def test_missing_alt_is_error(self) -> None:
        for alt in (None, "", "lag-table 스크린샷"):
            with self.subTest(alt=alt):
                entry = {key: value for key, value in ENTRY.items() if key != "alt"}
                if alt is not None:
                    entry["alt"] = alt
                errors = SCREENS.validate({"screens": [entry]})
                self.assertTrue(any("lag-table" in error and "대체 글" in error for error in errors), errors)

    def test_name_must_be_kebab_case(self) -> None:
        for name in ("image1", "Lag_Table", "지연-표", "lag-table-2026-10-16"):
            with self.subTest(name=name):
                self.assertTrue(SCREENS.validate({"screens": [{**ENTRY, "name": name}]}))


class CheckTest(unittest.TestCase):
    def test_missing_dark_file_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "lag-table-light.png").write_bytes(png(1920, 4))
            errors = SCREENS.check({"screens": [ENTRY]}, Path(folder))
        self.assertTrue(any("lag-table-dark.png" in error for error in errors), errors)

    def test_width_and_size_limits(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "lag-table-light.png").write_bytes(png(1280, 4))
            (Path(folder) / "lag-table-dark.png").write_bytes(png(1920, 4) + b"\x00" * (1024 * 1024))
            errors = SCREENS.check({"screens": [ENTRY]}, Path(folder))
        self.assertTrue(any("lag-table-light.png" in error and "1920" in error for error in errors), errors)
        self.assertTrue(any("lag-table-dark.png" in error and "1MB" in error for error in errors), errors)


class FailureTest(unittest.TestCase):
    def test_failure_keeps_existing_files(self) -> None:
        second = {**ENTRY, "name": "lag-detail", "alt": "지연이 큰 파티션만 따로 표시된다"}
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            for name in ("lag-table-light.png", "lag-table-dark.png"):
                (out / name).write_bytes(b"old")
            calls = []

            def capture(item):
                calls.append(item)
                if len(calls) > 2:
                    raise RuntimeError("capture failed")
                return png(1920, 4)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = SCREENS.shoot({"screens": [ENTRY, second]}, out, capture, lambda html, layout: png(1920, 4))
            self.assertEqual(code, 1)
            self.assertIn("capture failed", stderr.getvalue())
            self.assertEqual((out / "lag-table-light.png").read_bytes(), b"old")
            self.assertEqual((out / "lag-table-dark.png").read_bytes(), b"old")
            self.assertFalse((out / "lag-detail-light.png").exists())

    def test_success_writes_light_and_dark(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            code = SCREENS.shoot({"screens": [ENTRY]}, out, lambda item: png(1920, 4), lambda html, layout: png(1920, 4))
            self.assertEqual(code, 0)
            self.assertEqual(sorted(path.name for path in out.iterdir()), ["lag-table-dark.png", "lag-table-light.png"])

    def test_config_file_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "screens.json"
            path.write_text(json.dumps({"screens": [ENTRY]}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(SCREENS.load(path)["screens"][0]["name"], "lag-table")


class CleanupOwnershipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.out = self.root / "assets"
        self.out.mkdir()
        self.config = self.out / "screens.json"
        self.config.write_text(json.dumps({"screens": [{**ENTRY, "url": "{data}/scene"}]}), encoding="utf-8")
        self.data = self.root / ".local" / "runs" / "screenshots-owned"
        self.argv = ["shoot", "--config", str(self.config), "--run-id", "owned"]
        self.stack.enter_context(mock.patch.dict(SCREENS.os.environ))
        self.stack.enter_context(mock.patch.object(SCREENS.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=str(self.root))))
        self.discard = self.stack.enter_context(mock.patch.object(SCREENS, "discard"))
        self.browser_type = self.stack.enter_context(mock.patch.object(SCREENS, "Browser"))
        self.browser = self.browser_type.return_value.__enter__.return_value
        self.browser.capture.return_value = png(1920, 4)
        self.browser.render.return_value = png(1920, 4)
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def test_main_rejects_run_id_path_components_without_cleanup(self) -> None:
        for run_id in ("x/../../..", "x/../../../..", "x/../other", "", ".", ".."):
            with self.subTest(run_id=run_id):
                self.assertEqual(SCREENS.main(self.argv[:-1] + [run_id]), 2)
                self.discard.assert_not_called()
                self.browser_type.assert_not_called()
                self.assertFalse((self.root / ".local").exists())

    def test_main_rejects_existing_folder_without_cleanup(self) -> None:
        self.data.mkdir(parents=True)
        marker = self.data / "keep"
        marker.write_text("existing", encoding="utf-8")

        self.assertEqual(SCREENS.main(self.argv), 2)
        self.discard.assert_not_called()
        self.browser_type.assert_not_called()
        self.assertEqual(marker.read_text(encoding="utf-8"), "existing")

    def test_main_rejects_symlink_paths_without_cleanup(self) -> None:
        target = self.root / "target"
        target.mkdir()
        for link in (self.root / ".local", self.root / ".local" / "runs", self.data):
            with self.subTest(link=link):
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=True)
                try:
                    self.assertEqual(SCREENS.main(self.argv), 2)
                    self.discard.assert_not_called()
                    self.browser_type.assert_not_called()
                    self.assertEqual(list(target.iterdir()), [])
                finally:
                    link.unlink()

    def test_main_creation_failure_does_not_cleanup(self) -> None:
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            self.assertEqual(SCREENS.main(self.argv), 2)
        self.discard.assert_not_called()
        self.browser_type.assert_not_called()

    def test_main_default_run_id_cleans_only_new_folder_and_keeps_output(self) -> None:
        expected = self.root / ".local" / "runs" / "screenshots-20261019-123456"
        with mock.patch.object(SCREENS.time, "strftime", return_value="20261019-123456"):
            self.assertEqual(SCREENS.main(self.argv[:-2]), 0)

        self.discard.assert_called_once_with(expected)
        self.assertTrue(expected.is_dir())
        self.assertEqual(SCREENS.os.environ["SCREENS_DATA"], str(expected))
        self.assertEqual(self.browser.capture.call_args.args[0].source, f"{expected}/scene")
        self.assertEqual(SCREENS.check({"screens": [ENTRY]}, self.out), [])
        self.assertTrue(self.config.is_file())

    def test_main_capture_failure_cleans_only_new_folder_and_keeps_output(self) -> None:
        output = self.out / "lag-table-light.png"
        output.write_bytes(b"existing")
        self.browser.capture.side_effect = RuntimeError("capture failed")

        self.assertEqual(SCREENS.main(self.argv), 1)
        self.discard.assert_called_once_with(self.data)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_main_does_not_cleanup_replaced_folder(self) -> None:
        saved = self.root / "saved"

        def replace_folder(item: SCREENS.Capture) -> bytes:
            if not saved.exists():
                self.data.rename(saved)
                self.data.mkdir()
                (self.data / "keep").write_text("replacement", encoding="utf-8")
            return png(1920, 4)

        self.browser.capture.side_effect = replace_folder
        self.assertEqual(SCREENS.main(self.argv), 0)
        self.discard.assert_not_called()
        self.assertTrue(saved.is_dir())
        self.assertEqual((self.data / "keep").read_text(encoding="utf-8"), "replacement")


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright 없음")
class CaptureTest(unittest.TestCase):
    def test_real_capture_and_compose_is_1920_wide(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "app.html"
            page.write_text("<!doctype html><body style='margin:0'><main id=app style='height:300px'>앱</main>", encoding="utf-8")
            entry = {**ENTRY, "url": page.as_uri(), "select": "#app"}
            out = Path(folder) / "assets"
            out.mkdir()
            with SCREENS.Browser() as browser:
                code = SCREENS.shoot({"screens": [entry]}, out, browser.capture, browser.render)
            self.assertEqual(code, 0)
            for scheme in ("light", "dark"):
                data = (out / f"lag-table-{scheme}.png").read_bytes()
                self.assertEqual(SCREENS.png_width(data), 1920)


if __name__ == "__main__":
    unittest.main()
