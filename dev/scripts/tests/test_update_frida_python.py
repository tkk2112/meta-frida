# SPDX-License-Identifier: MIT

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typing import Any

import pytest
import update_frida as updater


class TestFridaPythonUpdate(unittest.TestCase):
    VERSION = "17.23.0"
    CHECKSUM = "721284b8681eb745ac1e8ba20d99401121d8fcfce225efee5103f513d2752f13"

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name)
        self.lock = self.root / "conf/include/frida_lock.inc"
        self.lock.parent.mkdir(parents=True)

        root_patch = patch.object(updater, "ROOT", self.root)
        lock_patch = patch.object(updater, "LOCK_FILE", self.lock)

        root_patch.start()
        lock_patch.start()
        self.addCleanup(root_patch.stop)
        self.addCleanup(lock_patch.stop)

        self.metadata: dict[str, Any] = {
            "info": {"version": self.VERSION},
            "urls": [
                {
                    "packagetype": "bdist_wheel",
                    "filename": "frida-example.whl",
                    "digests": {"sha256": "f" * 64},
                },
                {
                    "packagetype": "sdist",
                    "filename": f"frida-{self.VERSION}.tar.gz",
                    "digests": {"sha256": self.CHECKSUM},
                },
            ],
        }

    def write_lock(self, checksum=None):
        checksum = self.CHECKSUM if checksum is None else checksum
        self.lock.write_text(
            f'FRIDA_VERSION = "{self.VERSION}"\nFRIDA_PYTHON_SHA256 = "{checksum}"\n',
            encoding="utf-8",
        )

    def test_selects_sdist_not_wheel(self):
        result = updater.frida_python_sdist_checksum(self.metadata, self.VERSION)
        assert result == self.CHECKSUM

    def test_rejects_missing_sdist(self):
        data = {
            **self.metadata,
            "urls": [self.metadata["urls"][0]],
        }

        with pytest.raises(RuntimeError, match="source archive"):
            updater.frida_python_sdist_checksum(data, self.VERSION)

    def test_rejects_duplicate_sdist(self):
        sdist = self.metadata["urls"][1]
        data = {
            **self.metadata,
            "urls": [sdist, sdist],
        }

        with pytest.raises(RuntimeError, match="found 2"):
            updater.frida_python_sdist_checksum(data, self.VERSION)

    def test_rejects_wrong_filename(self):
        data = {
            **self.metadata,
            "urls": [
                {
                    **self.metadata["urls"][1],
                    "filename": "unexpected.tar.gz",
                },
            ],
        }

        with pytest.raises(RuntimeError, match="unexpected"):
            updater.frida_python_sdist_checksum(data, self.VERSION)

    def test_rejects_invalid_checksum(self):
        data = {
            **self.metadata,
            "urls": [
                {
                    **self.metadata["urls"][1],
                    "digests": {"sha256": "invalid"},
                },
            ],
        }

        with pytest.raises(RuntimeError, match="invalid"):
            updater.frida_python_sdist_checksum(data, self.VERSION)

    def test_check_accepts_matching_checksum(self):
        self.write_lock()

        with patch.object(
            updater,
            "frida_python_metadata",
            return_value=self.metadata,
        ):
            updater.check_frida_python_checksum()

    def test_check_rejects_mismatch(self):
        self.write_lock("a" * 64)

        with (
            patch.object(
                updater,
                "frida_python_metadata",
                return_value=self.metadata,
            ),
            pytest.raises(RuntimeError, match="checksum mismatch"),
        ):
            updater.check_frida_python_checksum()

    def test_check_rejects_missing_pin(self):
        self.lock.write_text(
            f'FRIDA_VERSION = "{self.VERSION}"\n',
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="missing or invalid"):
            updater.check_frida_python_checksum()

    def test_generated_lock_contains_checksum(self):
        contents = updater.format_lock(
            version=self.VERSION,
            python_sha256=self.CHECKSUM,
            release_revision="a" * 40,
            releng_url="https://github.com/frida/releng.git",
            releng_revision="b" * 40,
            components={},
            packages={},
            meson_options={},
            gvdb_url="https://github.com/GNOME/gvdb.git",
            gvdb_revision="c" * 40,
        )

        assignments = updater.parse_lock_assignments(contents)

        assert assignments["FRIDA_VERSION"] == self.VERSION
        assert assignments["FRIDA_PYTHON_SHA256"] == self.CHECKSUM


if __name__ == "__main__":
    unittest.main()
