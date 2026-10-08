"""Tests for the checked-in releng Meson option snapshot."""

from __future__ import annotations

import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "update_frida.py"
MODULE = runpy.run_path(str(SCRIPT), run_name="meta_frida_test")


class RelengMesonTest(unittest.TestCase):
    def test_options_and_conditions_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deps.toml").write_text(
                """
[capstone]
url = "https://github.com/frida/capstone.git"
version = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
options = [
    { value = "-Darchs=all", when = "not machine.is_freestanding" },
    "-Dcli=disabled",
]
[zlib]
url = "https://github.com/frida/zlib.git"
version = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
""",
                encoding="utf-8",
            )
            packages = {
                "capstone": SimpleNamespace(url="https://github.com/frida/capstone.git", version="a" * 40),
                "zlib": SimpleNamespace(url="https://github.com/frida/zlib.git", version="b" * 40),
            }
            options = MODULE["read_releng_meson_options"](root, packages)

            assert options["capstone"] == [
                ("-Darchs=all", "not machine.is_freestanding"),
                ("-Dcli=disabled", ""),
            ]
            assert options["zlib"] == []

            lock = MODULE["format_lock"](
                version="17.23.0",
                release_revision="c" * 40,
                releng_url="https://github.com/frida/releng.git",
                releng_revision="d" * 40,
                components={},
                packages=packages,
                meson_options=options,
                gvdb_url="https://gitlab.gnome.org/GNOME/gvdb.git",
                gvdb_revision="e" * 40,
            )
            assert 'FRIDA_DEP_MESON_COUNT[capstone] = "2"' in lock
            assert 'FRIDA_DEP_MESON_WHEN[capstone-000] = "not machine.is_freestanding"' in lock
            assert 'FRIDA_DEP_MESON_COUNT[zlib] = "0"' in lock

    def test_source_mismatch_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deps.toml").write_text(
                '[zlib]\nurl = "https://github.com/frida/zlib.git"\nversion = "a"\n',
                encoding="utf-8",
            )
            packages = {"zlib": SimpleNamespace(url="https://github.com/frida/zlib.git", version="b")}

            try:
                MODULE["read_releng_meson_options"](root, packages)
            except RuntimeError as exc:
                error = str(exc)
            else:
                raise AssertionError("expected a source-pin mismatch")

            assert "disagree about source pins" in error


if __name__ == "__main__":
    unittest.main()
